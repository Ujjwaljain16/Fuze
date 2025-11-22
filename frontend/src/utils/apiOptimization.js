/**
 * Frontend API Optimization Utilities  
 * Optimizations for reducing API calls and improving performance:
 * - Request debouncing
 * - Request batching
 * - Response caching
 * - Request deduplication
 */

// REQUEST DEBOUNCING

const debounceMap = new Map()

export const debounceRequest = (key, requestFn, delay = 300) => {
  return new Promise((resolve, reject) => {
    // Clear existing timeout for this key
    if (debounceMap.has(key)) {
      clearTimeout(debounceMap.get(key).timeout)
    }
    
    // Set new timeout
    const timeout = setTimeout(async () => {
      try {
        const result = await requestFn()
        resolve(result)
      } catch (error) {
        reject(error)
      } finally {
        debounceMap.delete(key)
      }
    }, delay)
    
    debounceMap.set(key, { timeout, resolve, reject })
  })
}

// REQUEST BATCHING

const batchQueue = []
let batchTimeout = null
const BATCH_DELAY = 50 // ms

export const batchRequest = (requestFn) => {
  return new Promise((resolve, reject) => {
    batchQueue.push({ requestFn, resolve, reject })
    
    // Clear existing timeout
    if (batchTimeout) {
      clearTimeout(batchTimeout)
    }
    
    // Set new timeout
    batchTimeout = setTimeout(() => {
      const queue = [...batchQueue]
      batchQueue.length = 0
      batchTimeout = null
      
      // Execute all requests in parallel
      Promise.all(queue.map(item => 
        item.requestFn().then(item.resolve).catch(item.reject)
      ))
    }, BATCH_DELAY)
  })
}

// RESPONSE CACHING

const responseCache = new Map()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export const getCachedResponse = (cacheKey) => {
  const cached = responseCache.get(cacheKey)
  if (cached && Date.now() < cached.expiresAt) {
    return cached.data
  }
  
  // Remove expired entry
  if (cached) {
    responseCache.delete(cacheKey)
  }
  
  return null
}

export const setCachedResponse = (cacheKey, data, ttl = CACHE_TTL) => {
  responseCache.set(cacheKey, {
    data,
    expiresAt: Date.now() + ttl
  })
}

export const clearCache = (pattern = null) => {
  if (pattern) {
    // Clear cache entries matching pattern
    for (const key of responseCache.keys()) {
      if (key.includes(pattern)) {
        responseCache.delete(key)
      }
    }
  } else {
    // Clear all cache
    responseCache.clear()
  }
}

// REQUEST DEDUPLICATION

const pendingRequests = new Map()

export const deduplicateRequest = async (requestKey, requestFn) => {
  // If request is already in progress, return the same promise
  if (pendingRequests.has(requestKey)) {
    return pendingRequests.get(requestKey)
  }
  
  // Create new request promise
  const promise = requestFn()
    .finally(() => {
      // Remove from pending after completion
      pendingRequests.delete(requestKey)
    })
  
  pendingRequests.set(requestKey, promise)
  return promise
}

// OPTIMIZED API CALL WRAPPER

/**
 * Optimized API call with caching, deduplication, and error handling
 */
export const optimizedApiCall = async (
  apiFn,
  options = {
    cacheKey: null,
    cacheTTL: CACHE_TTL,
    debounceKey: null,
    debounceDelay: 300,
    deduplicate: false,
    batch: false
  }
) => {
  const {
    cacheKey,
    cacheTTL,
    debounceKey,
    debounceDelay,
    deduplicate,
    batch
  } = options
  
  // Check cache first
  if (cacheKey) {
    const cached = getCachedResponse(cacheKey)
    if (cached !== null) {
      return cached
    }
  }
  
  // Create request function
  const requestFn = async () => {
    const result = await apiFn()
    
    // Cache result if cache key provided
    if (cacheKey && result) {
      setCachedResponse(cacheKey, result, cacheTTL)
    }
    
    return result
  }
  
  // Apply optimizations
  let optimizedRequest = requestFn
  
  if (deduplicate && cacheKey) {
    optimizedRequest = () => deduplicateRequest(cacheKey, requestFn)
  }
  
  if (debounceKey) {
    optimizedRequest = () => debounceRequest(debounceKey, requestFn, debounceDelay)
  }
  
  if (batch) {
    optimizedRequest = () => batchRequest(requestFn)
  }
  
  return optimizedRequest()
}

// CLEANUP

// Clean up expired cache entries periodically
setInterval(() => {
  const now = Date.now()
  for (const [key, value] of responseCache.entries()) {
    if (now >= value.expiresAt) {
      responseCache.delete(key)
    }
  }
}, 60000) // Check every minute