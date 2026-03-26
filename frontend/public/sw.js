// Service Worker for Fuze PWA — Production Hardened
// Build hash injected by vite.config.js at deploy time
const CACHE_VERSION = '__BUILD_HASH__';
const SHELL_CACHE = `shell-${CACHE_VERSION}`;
const ASSET_CACHE = `assets-${CACHE_VERSION}`;

// Auth routes that must NEVER be served from cache
const AUTH_BYPASS_ROUTES = new Set([
  '/oauth/callback',
  '/auth/callback',
  '/login',
]);

// Delete old caches on activation
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== ASSET_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  // 1. Always bypass SW for auth routes — go straight to network
  if (AUTH_BYPASS_ROUTES.has(url.pathname)) {
    event.respondWith(fetch(event.request));
    return;
  }

  // 2. Network-first for HTML document navigations
  //    Falls back to cached shell only if offline
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache the fresh shell for offline use
          const clone = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() =>
          // Offline fallback — serve cached shell
          caches.match('/index.html', { cacheName: SHELL_CACHE })
        )
    );
    return;
  }

  // 3. Cache-first for static assets (JS, CSS, images, fonts)
  //    These are content-hashed by Vite so safe to cache aggressively
  if (
    url.pathname.startsWith('/assets/') ||
    url.pathname.match(/\.(js|css|woff2?|png|jpg|svg|ico)$/)
  ) {
    event.respondWith(
      caches.match(event.request).then(
        (cached) => cached || fetch(event.request).then((response) => {
          caches.open(ASSET_CACHE).then((cache) => cache.put(event.request, response.clone()));
          return response;
        })
      )
    );
    return;
  }

  // 4. Everything else (API calls etc.) — always network, never cache
  // event.respondWith not called = browser handles normally
});


}

// Background sync for LinkedIn content analysis
self.addEventListener('sync', (event) => {
  if (event.tag === 'linkedin-analysis-sync') {
    console.log(' Background sync for LinkedIn analysis...');
    
    event.waitUntil(
      performBackgroundLinkedInAnalysis()
    );
  }
});

// Perform background LinkedIn analysis
async function performBackgroundLinkedInAnalysis() {
  try {
    // Get pending analysis from IndexedDB
    const db = await openIndexedDB();
    const transaction = db.transaction(['pendingAnalysis'], 'readonly');
    const store = transaction.objectStore('pendingAnalysis');
    const pendingItems = await store.getAll();
    
    for (const item of pendingItems) {
      try {
        // Perform the analysis
        const response = await fetch('/api/linkedin/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.data)
        });
        
        if (response.ok) {
          // Remove from pending
          const deleteTransaction = db.transaction(['pendingAnalysis'], 'readwrite');
          const deleteStore = deleteTransaction.objectStore('pendingAnalysis');
          await deleteStore.delete(item.id);
          
          console.log('Background analysis completed for:', item.id);
        }
      } catch (error) {
        console.error(' Background analysis failed for:', item.id, error);
      }
    }
  } catch (error) {
    console.error(' Background sync failed:', error);
  }
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log(' Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New content analysis ready!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Analysis',
        icon: '/icons/icon-72x72.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/icon-72x72.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Fuze - Content Analysis', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log(' Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/linkedin-analyzer')
    );
  }
});

console.log(' Fuze Service Worker loaded successfully!');
