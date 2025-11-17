import axios from 'axios'

// Get base URL from environment or automatically detect
const getBaseURL = () => {
  // Check if we're in development (localhost or 127.0.0.1)
  const isDevelopment = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1'
  
  if (isDevelopment) {
    // Development: Use HTTP localhost
    return import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'
  } else {
    // Production: Use environment variable (required)
    const apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl) {
      console.error('⚠️ VITE_API_URL environment variable is not set in production!')
      throw new Error('API URL not configured. Please set VITE_API_URL environment variable.')
    }
    return apiUrl
  }
}

const baseURL = getBaseURL()

// Only log in development
if (import.meta.env.DEV) {
  console.log('🌐 API Base URL:', baseURL)
  console.log('🏠 Current hostname:', window.location.hostname)
}

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for cookies and CSRF
})

// CSRF token management - optimized for performance
let csrfToken = null

// Request interceptor to add auth token and CSRF token
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Only add CSRF token for non-GET requests and only if CSRF is actually enabled
    if (config.method !== 'get' && csrfToken && csrfToken !== 'csrf_disabled') {
      config.headers['X-CSRF-TOKEN'] = csrfToken
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    // Handle CSRF token errors
    if (error.response?.status === 400 && error.response?.data?.error === 'csrf_error') {
      try {
        // Get new CSRF token
        const csrfResponse = await axios.get(`${baseURL}/api/auth/csrf-token`, {
          withCredentials: true
        })
        csrfToken = csrfResponse.data.csrf_token
        
        // Retry the original request with new CSRF token
        if (originalRequest.method !== 'get') {
          originalRequest.headers['X-CSRF-TOKEN'] = csrfToken
        }
        return api(originalRequest)
      } catch (csrfError) {
        console.error('Failed to get CSRF token:', csrfError)
        return Promise.reject(error)
      }
    }
    
    // Handle token expiration
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        // Attempt to refresh the access token
        const oldToken = localStorage.getItem('token');
        const res = await axios.post(
          `${baseURL}/api/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: oldToken ? { Authorization: `Bearer ${oldToken}` } : {}
          }
        )
        const newToken = res.data.access_token
        localStorage.setItem('token', newToken)
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Proactive token refresh for long-running requests
export const refreshTokenIfNeeded = async () => {
  try {
    const token = localStorage.getItem('token')
    if (!token) return
    
    // Decode JWT token to check expiration (without verification for client-side)
    const payload = JSON.parse(atob(token.split('.')[1]))
    const expirationTime = payload.exp * 1000 // Convert to milliseconds
    const currentTime = Date.now()
    const timeUntilExpiration = expirationTime - currentTime
    
    // If token expires in less than 5 minutes, refresh it
    if (timeUntilExpiration < 5 * 60 * 1000) {
      if (import.meta.env.DEV) {
        console.log('Token expires soon, refreshing proactively...')
      }
      const res = await axios.post(
        `${baseURL}/api/auth/refresh`,
        {},
        {
          withCredentials: true,
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        }
      )
      const newToken = res.data.access_token
      localStorage.setItem('token', newToken)
      if (import.meta.env.DEV) {
        console.log('Token refreshed successfully')
      }
    }
  } catch (error) {
    console.warn('Failed to refresh token proactively:', error)
  }
}

// Initialize CSRF token on app startup - optimized for performance
export const initializeCSRF = async () => {
  try {
    // Use a timeout to prevent blocking the UI
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout
    
    const response = await axios.get(`${baseURL}/api/auth/csrf-token`, {
      withCredentials: true,
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    csrfToken = response.data.csrf_token
    if (import.meta.env.DEV) {
      console.log('🔐 CSRF token initialized')
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.warn('⚠️ CSRF token request timed out, continuing without CSRF')
    } else {
      console.warn('⚠️ CSRF token initialization failed, continuing without CSRF:', error.message)
    }
    csrfToken = 'csrf_disabled'
  }
}

export default api 