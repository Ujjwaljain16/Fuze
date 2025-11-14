// Service Worker for Fuze PWA
const CACHE_NAME = 'fuze-v1.0.0';
const STATIC_CACHE = 'fuze-static-v1';
const DYNAMIC_CACHE = 'fuze-dynamic-v1';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/',
  '/index.html',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
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
  console.log('🔄 Service Worker installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('📦 Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('✅ Static files cached');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('❌ Cache installation failed:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle LinkedIn content extraction requests
  if (url.pathname === '/api/linkedin/extract') {
    event.respondWith(handleLinkedInExtraction(request));
    return;
  }
  
  // Handle LinkedIn content analysis requests
  if (url.pathname === '/api/linkedin/analyze') {
    event.respondWith(handleLinkedInAnalysis(request));
    return;
  }
  
  // Handle recommendation requests
  if (url.pathname.startsWith('/api/recommendations')) {
    event.respondWith(handleRecommendations(request));
    return;
  }
  
  // Handle static files (offline support)
  if (request.method === 'GET' && request.destination === 'document') {
    event.respondWith(handleStaticFiles(request));
    return;
  }
  
  // Handle API requests with network-first strategy
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleAPIRequests(request));
    return;
  }
  
  // Default: network first, fallback to cache
  event.respondWith(handleDefaultRequest(request));
});

// Handle LinkedIn content extraction
async function handleLinkedInExtraction(request) {
  try {
    // Try network first
    const response = await fetch(request);
    
    if (response.ok) {
      // Cache successful responses
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
      
      // Store in IndexedDB for offline access
      await storeLinkedInData(request, response.clone());
      
      return response;
    }
    
    throw new Error('Network request failed');
  } catch (error) {
    console.log('📱 LinkedIn extraction failed, trying offline cache...');
    
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
    
    if (response.ok) {
      // Cache analysis results
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
      
      // Store analysis in IndexedDB
      await storeAnalysisData(request, response.clone());
      
      return response;
    }
    
    throw new Error('Analysis request failed');
  } catch (error) {
    console.log('📱 LinkedIn analysis failed, trying offline cache...');
    
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
    
    if (response.ok) {
      // Cache recommendations
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
      
      return response;
    }
    
    throw new Error('Recommendations request failed');
  } catch (error) {
    console.log('📱 Recommendations failed, trying offline cache...');
    
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
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.error('❌ Static file handling failed:', error);
    return new Response('Offline mode: File not available', { status: 503 });
  }
}

// Handle API requests with network-first strategy
async function handleAPIRequests(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      // Cache successful API responses
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('📱 API request failed, trying offline cache...');
    
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
    console.log('📱 Network failed, trying cache...');
    
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
    console.error('❌ Failed to store LinkedIn data:', error);
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
    console.error('❌ Failed to store analysis data:', error);
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
    console.log('🔄 Background sync for LinkedIn analysis...');
    
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
          
          console.log('✅ Background analysis completed for:', item.id);
        }
      } catch (error) {
        console.error('❌ Background analysis failed for:', item.id, error);
      }
    }
  } catch (error) {
    console.error('❌ Background sync failed:', error);
  }
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('📱 Push notification received');
  
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
  console.log('📱 Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/linkedin-analyzer')
    );
  }
});

console.log('🚀 Fuze Service Worker loaded successfully!');
