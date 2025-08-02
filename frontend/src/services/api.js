import axios from 'axios'

// Get base URL from environment or default to localhost
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for cookies and CSRF
})

// CSRF token management
let csrfToken = null

// Request interceptor to add auth token and CSRF token
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Add CSRF token for non-GET requests (only if CSRF is enabled)
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
        const res = await axios.post(
          `${baseURL}/api/auth/refresh`,
          {},
          { withCredentials: true }
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

// Initialize CSRF token on app startup
export const initializeCSRF = async () => {
  try {
    const response = await axios.get(`${baseURL}/api/auth/csrf-token`, {
      withCredentials: true
    })
    csrfToken = response.data.csrf_token
  } catch (error) {
    console.warn('Failed to get CSRF token:', error)
  }
}

export default api 