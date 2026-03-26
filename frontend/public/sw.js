// Service Worker for Fuze PWA — Full feature set with production hardening
const CACHE_VERSION = '__BUILD_HASH__';
const SHELL_CACHE = `shell-${CACHE_VERSION}`;
const ASSET_CACHE = `assets-${CACHE_VERSION}`;

const PRECACHE_URLS = ['/index.html', '/manifest.json'];

// Auth routes that must NEVER be served from cache.
const AUTH_BYPASS_ROUTES = new Set([
  '/oauth/callback',
  '/auth/callback',
  '/login',
]);

const MAX_ASSET_ENTRIES = 120;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== ASSET_CACHE)
          .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests.
  if (url.origin !== self.location.origin) return;

  // Bypass auth-related routes directly to network.
  if (AUTH_BYPASS_ROUTES.has(url.pathname)) {
    event.respondWith(fetch(request));
    return;
  }

  // Keep LinkedIn analysis/extract endpoints resilient with IndexedDB fallback.
  if (url.pathname === '/api/linkedin/extract') {
    event.respondWith(handleLinkedInExtraction(request));
    return;
  }

  if (url.pathname === '/api/linkedin/analyze') {
    event.respondWith(handleLinkedInAnalysis(request));
    return;
  }

  if (url.pathname.startsWith('/api/recommendations')) {
    event.respondWith(handleRecommendations(request));
    return;
  }

  // Network-first for document navigations, with offline shell fallback.
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  // Cache-first for Vite hashed static assets.
  if (isStaticAsset(url.pathname)) {
    event.respondWith(handleStaticAssetRequest(request));
    return;
  }

  // For all other requests (including non-LinkedIn APIs): network only.
});

async function handleNavigationRequest(request) {
  try {
    const response = await fetch(request);

    if (response && response.ok) {
      const cache = await caches.open(SHELL_CACHE);
      await cache.put(request, response.clone());
      await cache.put('/index.html', response.clone());
    }

    return response;
  } catch (error) {
    const cached = await caches.match('/index.html', { cacheName: SHELL_CACHE });
    if (cached) return cached;

    return new Response('Offline mode: page not available', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

async function handleStaticAssetRequest(request) {
  const cached = await caches.match(request, { cacheName: ASSET_CACHE });
  if (cached) return cached;

  const response = await fetch(request);

  if (response && response.ok) {
    const cache = await caches.open(ASSET_CACHE);
    await cache.put(request, response.clone());
    await trimCache(ASSET_CACHE, MAX_ASSET_ENTRIES);
  }

  return response;
}

function isStaticAsset(pathname) {
  return pathname.startsWith('/assets/') || /\.(js|css|woff2?|png|jpg|jpeg|svg|ico|webp)$/.test(pathname);
}

async function handleLinkedInExtraction(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      await storeApiData('linkedinData', request.url, response.clone());
    }
    return response;
  } catch (error) {
    const fallback = await getLatestApiData('linkedinData', request.url);
    if (fallback) {
      return jsonResponse(fallback, 200, { 'X-Offline-Source': 'indexeddb' });
    }

    return jsonResponse({
      error: 'Offline mode: LinkedIn extraction not available',
      message: 'Please check your connection and try again',
    }, 503);
  }
}

async function handleLinkedInAnalysis(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      await storeApiData('analysisData', request.url, response.clone());
    }
    return response;
  } catch (error) {
    const fallback = await getLatestApiData('analysisData', request.url);
    if (fallback) {
      return jsonResponse(fallback, 200, { 'X-Offline-Source': 'indexeddb' });
    }

    // Queue analysis for background sync when possible.
    if (request.method === 'POST') {
      await queuePendingAnalysis(request);
    }

    return jsonResponse({
      error: 'Offline mode: Content analysis not available',
      message: 'Please check your connection and try again',
    }, 503);
  }
}

async function handleRecommendations(request) {
  try {
    return await fetch(request);
  } catch (error) {
    return jsonResponse({
      error: 'Offline mode: Recommendations not available',
      message: 'Please check your connection and try again',
    }, 503);
  }
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'linkedin-analysis-sync') {
    event.waitUntil(performBackgroundLinkedInAnalysis());
  }
});

async function performBackgroundLinkedInAnalysis() {
  try {
    const db = await openIndexedDB();
    const pendingItems = await idbGetAll(db, 'pendingAnalysis');

    for (const item of pendingItems) {
      try {
        const response = await fetch('/api/linkedin/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.data),
        });

        if (response.ok) {
          await idbDelete(db, 'pendingAnalysis', item.id);
        }
      } catch (error) {
        // Keep item queued for a future sync attempt.
      }
    }
  } catch (error) {
    // No-op: sync retries later.
  }
}

self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New content analysis ready!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1,
    },
    actions: [
      {
        action: 'explore',
        title: 'View Analysis',
        icon: '/icons/icon-72x72.png',
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/icon-72x72.png',
      },
    ],
  };

  event.waitUntil(self.registration.showNotification('Fuze - Content Analysis', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(clients.openWindow('/linkedin-analyzer'));
  }
});

async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  const overflow = keys.length - maxEntries;

  if (overflow > 0) {
    await Promise.all(keys.slice(0, overflow).map((key) => cache.delete(key)));
  }
}

function jsonResponse(payload, status, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    statusText: status === 503 ? 'Service Unavailable' : 'OK',
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
  });
}

async function storeApiData(storeName, requestUrl, response) {
  try {
    const payload = await response.json();
    const db = await openIndexedDB();
    await idbPut(db, storeName, {
      id: Date.now(),
      url: requestUrl,
      data: payload,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    // Skip storage errors to keep network response path stable.
  }
}

async function getLatestApiData(storeName, requestUrl) {
  try {
    const db = await openIndexedDB();
    const records = await idbGetAll(db, storeName);
    const matches = records
      .filter((item) => item.url === requestUrl)
      .sort((a, b) => (a.id > b.id ? -1 : 1));
    return matches[0]?.data || null;
  } catch (error) {
    return null;
  }
}

async function queuePendingAnalysis(request) {
  try {
    const bodyText = await request.clone().text();
    const body = bodyText ? JSON.parse(bodyText) : {};
    const db = await openIndexedDB();

    await idbPut(db, 'pendingAnalysis', {
      id: Date.now(),
      data: body,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    // Ignore queue failures.
  }
}

async function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FuzePWA', 2);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('linkedinData')) {
        db.createObjectStore('linkedinData', { keyPath: 'id' });
      }

      if (!db.objectStoreNames.contains('analysisData')) {
        db.createObjectStore('analysisData', { keyPath: 'id' });
      }

      if (!db.objectStoreNames.contains('pendingAnalysis')) {
        db.createObjectStore('pendingAnalysis', { keyPath: 'id' });
      }
    };
  });
}

function idbGetAll(db, storeName) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction([storeName], 'readonly');
    const store = tx.objectStore(storeName);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

function idbPut(db, storeName, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction([storeName], 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.put(value);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}

function idbDelete(db, storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction([storeName], 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.delete(key);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}
