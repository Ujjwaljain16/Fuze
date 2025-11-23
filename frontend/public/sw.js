// Service Worker for Fuze PWA
// Update version to force cache invalidation on new deployments
const CACHE_NAME = 'fuze-v1.1.0';
const STATIC_CACHE = 'fuze-static-v1.1';
const DYNAMIC_CACHE = 'fuze-dynamic-v1.1';

// Files to cache for offline functionality
// Note: Only cache same-origin files, not external API responses
// IMPORTANT: Don't cache index.html - it changes with each build (new JS file hashes)
const STATIC_FILES = [
  '/manifest.json'
  // Don't cache index.html - use network-first strategy
  // Don't cache JS/CSS - they're versioned and handled by Vite
  // '/static/js/bundle.js',
  // '/static/css/main.css',
  // '/icons/icon-192x192.png',
  // '/icons/icon-512x512.png'
];

// LinkedIn content analysis API endpoints
const API_ENDPOINTS = [
  '/api/linkedin/extract',
  '/api/linkedin/analyze',
  '/api/recommendations',
  '/api/projects'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Caching static files');
        // Use addAll with error handling - skip files that fail
        return Promise.allSettled(
          STATIC_FILES.map(url => 
            cache.add(url).catch(err => {
              console.warn(`Failed to cache ${url}:`, err);
              return null; // Continue even if one file fails
            })
          )
        );
      })
      .then(() => {
        console.log('Static files cached');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Cache installation failed:', error);
        // Continue even if caching fails
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log(' Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Delete all old caches (force fresh start)
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log(' Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker activated - all old caches cleared');
        // Force immediate activation and claim all clients
        return self.clients.claim();
      })
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // CRITICAL: Don't intercept ANY external requests (Hugging Face Spaces backend)
  // This prevents service worker from interfering with cross-origin API calls
  // Check this FIRST before any other logic
  if (url.hostname !== self.location.hostname) {
    // Let ALL external requests pass through without service worker interception
    return;
  }
  
  // Don't intercept ANY API requests (same-origin or external)
  // All API calls should go directly to the backend without SW interference
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  // Don't intercept JS module requests - let them pass through
  // This fixes the MIME type error for module scripts
  if (request.destination === 'script' && 
      (url.pathname.endsWith('.js') || request.headers.get('Accept')?.includes('application/javascript'))) {
    // Let JS modules pass through without service worker interception
    return;
  }
  
  // Don't intercept XHR/fetch requests (they're handled by axios directly)
  if (request.mode === 'cors') {
    return;
  }
  
  // Handle LinkedIn content extraction requests (only for same-origin)
  if (url.pathname === '/api/linkedin/extract' && url.origin === self.location.origin) {
    event.respondWith(handleLinkedInExtraction(request));
    return;
  }
  
  // Handle LinkedIn content analysis requests (only for same-origin)
  if (url.pathname === '/api/linkedin/analyze' && url.origin === self.location.origin) {
    event.respondWith(handleLinkedInAnalysis(request));
    return;
  }
  
  // Handle recommendation requests (only for same-origin)
  if (url.pathname.startsWith('/api/recommendations') && url.origin === self.location.origin) {
    event.respondWith(handleRecommendations(request));
    return;
  }
  
  // Handle index.html with network-first strategy (always get latest version)
  if (request.method === 'GET' && 
      request.destination === 'document' && 
      (url.pathname === '/' || url.pathname === '/index.html') &&
      url.origin === self.location.origin) {
    event.respondWith(handleIndexHtml(request));
    return;
  }
  
  // Handle other static files (offline support) - only for same-origin
  if (request.method === 'GET' && 
      request.destination === 'document' && 
      url.origin === self.location.origin) {
    event.respondWith(handleStaticFiles(request));
    return;
  }
  
  // Default: network first, fallback to cache (only for same-origin static files)
  if (url.origin === self.location.origin && 
      (request.destination === 'image' || 
       request.destination === 'style' || 
       request.destination === 'font')) {
    event.respondWith(handleDefaultRequest(request));
  }
});

// Handle LinkedIn content extraction
async function handleLinkedInExtraction(request) {
  try {
    // Try network first
    const response = await fetch(request);
    
    if (response.ok && response.status === 200) {
      // Only cache successful responses with proper error handling
      try {
        const cache = await caches.open(DYNAMIC_CACHE);
        // Clone response before caching (response can only be read once)
        const responseClone = response.clone();
        // Check if response is cacheable before putting
        if (responseClone.status === 200 && responseClone.type === 'basic') {
          await cache.put(request, responseClone);
        }
        
        // Store in IndexedDB for offline access
        await storeLinkedInData(request, response.clone());
      } catch (cacheError) {
        console.warn('Failed to cache LinkedIn extraction:', cacheError);
        // Continue even if caching fails
      }
      
      return response;
    }
    
    throw new Error('Network request failed');
  } catch (error) {
    console.log(' LinkedIn extraction failed, trying offline cache...');
    
    // Try to get from cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline response
    return new Response(
      JSON.stringify({
        error: 'Offline mode: LinkedIn extraction not available',
        message: 'Please check your connection and try again'
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle LinkedIn content analysis
async function handleLinkedInAnalysis(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok && response.status === 200) {
      // Only cache successful responses with proper error handling
      try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const responseClone = response.clone();
        if (responseClone.status === 200 && responseClone.type === 'basic') {
          await cache.put(request, responseClone);
        }
        
        // Store analysis in IndexedDB
        await storeAnalysisData(request, response.clone());
      } catch (cacheError) {
        console.warn('Failed to cache LinkedIn analysis:', cacheError);
        // Continue even if caching fails
      }
      
      return response;
    }
    
    throw new Error('Analysis request failed');
  } catch (error) {
    console.log(' LinkedIn analysis failed, trying offline cache...');
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(
      JSON.stringify({
        error: 'Offline mode: Content analysis not available',
        message: 'Please check your connection and try again'
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle recommendation requests
async function handleRecommendations(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok && response.status === 200) {
      // Only cache successful responses with proper error handling
      try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const responseClone = response.clone();
        if (responseClone.status === 200 && responseClone.type === 'basic') {
          await cache.put(request, responseClone);
        }
      } catch (cacheError) {
        console.warn('Failed to cache recommendations:', cacheError);
        // Continue even if caching fails
      }
      
      return response;
    }
    
    throw new Error('Recommendations request failed');
  } catch (error) {
    console.log(' Recommendations failed, trying offline cache...');
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(
      JSON.stringify({
        error: 'Offline mode: Recommendations not available',
        message: 'Please check your connection and try again'
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle static files with cache-first strategy
async function handleStaticFiles(request) {
  try {
    // Don't intercept JS module requests - let them go through normally
    const url = new URL(request.url);
    if (url.pathname.endsWith('.js') && request.headers.get('Accept')?.includes('application/javascript')) {
      // Let JS modules pass through without service worker interception
      return fetch(request);
    }
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const response = await fetch(request);
    if (response.ok && response.status === 200) {
      try {
        const cache = await caches.open(STATIC_CACHE);
        const responseClone = response.clone();
        if (responseClone.status === 200 && responseClone.type === 'basic') {
          await cache.put(request, responseClone);
        }
      } catch (cacheError) {
        console.warn('Failed to cache static file:', cacheError);
        // Continue even if caching fails
      }
    }
    
    return response;
  } catch (error) {
    console.error(' Static file handling failed:', error);
    return new Response('Offline mode: File not available', { status: 503 });
  }
}

// Handle API requests with network-first strategy
async function handleAPIRequests(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok && response.status === 200) {
      // Only cache successful API responses with proper error handling
      try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const responseClone = response.clone();
        // Only cache if response is cacheable (status 200 and type 'basic')
        if (responseClone.status === 200 && responseClone.type === 'basic') {
          await cache.put(request, responseClone);
        }
      } catch (cacheError) {
        console.warn('Failed to cache API response:', cacheError);
        // Continue even if caching fails - don't block the response
      }
    }
    
    return response;
  } catch (error) {
    console.log(' API request failed, trying offline cache...');
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(
      JSON.stringify({
        error: 'Offline mode: API not available',
        message: 'Please check your connection and try again'
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle default requests
async function handleDefaultRequest(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    console.log(' Network failed, trying cache...');
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response('Offline mode: Content not available', { status: 503 });
  }
}

// Store LinkedIn data in IndexedDB
async function storeLinkedInData(request, response) {
  try {
    const data = await response.json();
    
    // Store in IndexedDB for offline access
    const db = await openIndexedDB();
    const transaction = db.transaction(['linkedinData'], 'readwrite');
    const store = transaction.objectStore('linkedinData');
    
    await store.put({
      id: Date.now(),
      url: request.url,
      data: data,
      timestamp: new Date().toISOString()
    });
    
    console.log('💾 LinkedIn data stored offline');
  } catch (error) {
    console.error(' Failed to store LinkedIn data:', error);
  }
}

// Store analysis data in IndexedDB
async function storeAnalysisData(request, response) {
  try {
    const data = await response.json();
    
    const db = await openIndexedDB();
    const transaction = db.transaction(['analysisData'], 'readwrite');
    const store = transaction.objectStore('analysisData');
    
    await store.put({
      id: Date.now(),
      url: request.url,
      data: data,
      timestamp: new Date().toISOString()
    });
    
    console.log('💾 Analysis data stored offline');
  } catch (error) {
    console.error(' Failed to store analysis data:', error);
  }
}

// Open IndexedDB
async function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('FuzePWA', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object stores
      if (!db.objectStoreNames.contains('linkedinData')) {
        db.createObjectStore('linkedinData', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('analysisData')) {
        db.createObjectStore('analysisData', { keyPath: 'id' });
      }
    };
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
