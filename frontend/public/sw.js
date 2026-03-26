// Service Worker for Fuze PWA — Stable production-safe version
const CACHE_VERSION = '__BUILD_HASH__';
const SHELL_CACHE = `shell-${CACHE_VERSION}`;
const ASSET_CACHE = `assets-${CACHE_VERSION}`;

const PRECACHE_URLS = ['/index.html', '/manifest.json'];
const MAX_ASSET_ENTRIES = 120;

const AUTH_BYPASS_ROUTES = new Set([
  '/oauth/callback',
  '/auth/callback',
  '/login',
]);

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== SHELL_CACHE && k !== ASSET_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle only same-origin in SW; external APIs go straight to browser/network.
  if (url.origin !== self.location.origin) return;

  // Never cache auth callback/login routes.
  if (AUTH_BYPASS_ROUTES.has(url.pathname)) {
    event.respondWith(fetch(request));
    return;
  }

  // Keep API traffic network-only to avoid stale auth-sensitive data.
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // HTML navigation: network-first with offline fallback shell.
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  // Hashed static assets: cache-first with content-type guard.
  if (isStaticAsset(url.pathname)) {
    event.respondWith(handleStaticAssetRequest(request));
    return;
  }
});

async function handleNavigationRequest(request) {
  try {
    const response = await fetch(request);

    if (response && response.ok) {
      const cache = await caches.open(SHELL_CACHE);
      await cache.put('/index.html', response.clone());
      await cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    const cachedShell = await caches.match('/index.html', { cacheName: SHELL_CACHE });
    if (cachedShell) return cachedShell;

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

  if (isCacheableAssetResponse(response, request.url)) {
    const cache = await caches.open(ASSET_CACHE);
    await cache.put(request, response.clone());
    await trimCache(ASSET_CACHE, MAX_ASSET_ENTRIES);
  }

  return response;
}

function isStaticAsset(pathname) {
  return (
    pathname.startsWith('/assets/') ||
    /\.(js|css|woff2?|png|jpg|jpeg|svg|ico|webp|gif)$/.test(pathname)
  );
}

function isCacheableAssetResponse(response, requestUrl) {
  if (!response || !response.ok || response.type !== 'basic') return false;

  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('text/html')) return false;

  const pathname = new URL(requestUrl).pathname;

  if (pathname.endsWith('.css')) return contentType.includes('text/css');
  if (pathname.endsWith('.js')) return contentType.includes('javascript');
  if (/\.(woff2?|ttf|otf)$/.test(pathname)) return contentType.includes('font') || contentType.includes('application/octet-stream');
  if (/\.(png|jpg|jpeg|svg|ico|webp|gif)$/.test(pathname)) return contentType.startsWith('image/');

  return true;
}

async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  const overflow = keys.length - maxEntries;

  if (overflow > 0) {
    await Promise.all(keys.slice(0, overflow).map((key) => cache.delete(key)));
  }
}

// Background sync for LinkedIn content analysis queue (kept from legacy SW behavior).
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
    // Best effort only.
  }
}

// Push notification handling (kept from legacy SW behavior).
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

async function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FuzePWA', 2);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

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

function idbDelete(db, storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction([storeName], 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.delete(key);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
  });
}
