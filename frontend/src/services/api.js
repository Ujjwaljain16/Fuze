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
      console.error('VITE_API_URL environment variable is not set in production!')
      throw new Error('API URL not configured. Please set VITE_API_URL environment variable.')
    }
    return apiUrl
  }
}

const baseURL = getBaseURL()

// API configuration removed for production

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for cookies and CSRF
  timeout: 30000, // 30 second timeout - should be fast with optimizations
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
    
    // Handle token expiration (but NOT for login requests)
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/auth/login')) {
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
      } catch {
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
    }
  } catch (error) {
    console.warn('Failed to refresh token proactively:', error)
  }
}

// Initialize CSRF token on app startup - optimized for performance
export const initializeCSRF = async () => {
  try {
    // Increased timeout for Hugging Face Spaces (may have higher latency)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
    
    const response = await axios.get(`${baseURL}/api/auth/csrf-token`, {
      withCredentials: true,
      signal: controller.signal,
      timeout: 10000 // Also set axios timeout
    })
    
    clearTimeout(timeoutId)
    csrfToken = response.data.csrf_token
  } catch (error) {
    if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
      console.warn('CSRF token request timed out, continuing without CSRF')
    } else {
      console.warn('CSRF token initialization failed, continuing without CSRF:', error.message)
    }
    csrfToken = 'csrf_disabled'
  }
}

// ============================================================================
// COMPREHENSIVE ERROR HANDLING SYSTEM
// ============================================================================

// Error types for consistent handling
export const ERROR_TYPES = {
  NETWORK: 'network',
  AUTH: 'auth',
  VALIDATION: 'validation',
  SERVER: 'server',
  RATE_LIMIT: 'rate_limit',
  UNKNOWN: 'unknown'
};

// User-friendly error messages
export const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK]: 'Network connection failed. Please check your internet and try again.',
  [ERROR_TYPES.AUTH]: 'Your session has expired. Please log in again.',
  [ERROR_TYPES.VALIDATION]: 'Please check your input and try again.',
  [ERROR_TYPES.SERVER]: 'Server error occurred. Please try again later.',
  [ERROR_TYPES.RATE_LIMIT]: 'Too many requests. Please wait a moment before trying again.',
  [ERROR_TYPES.UNKNOWN]: 'An unexpected error occurred. Please try again.'
};

// Error handler utility
export const handleApiError = (error, context = '') => {
  console.error(`API Error${context ? ` (${context})` : ''}:`, error);

  let errorType = ERROR_TYPES.UNKNOWN;
  let message = ERROR_MESSAGES[ERROR_TYPES.UNKNOWN];
  let statusCode = 0;

  if (error.response) {
    // Server responded with error status
    statusCode = error.response.status;
    const data = error.response.data;

    switch (statusCode) {
      case 400:
        errorType = ERROR_TYPES.VALIDATION;
        message = data?.message || data?.error || 'Invalid request data';
        break;
      case 401:
        // Check if this is a login attempt with wrong credentials
        if (data?.message === 'Invalid credentials') {
          errorType = ERROR_TYPES.VALIDATION;
          message = 'Invalid credentials';
        } else {
          errorType = ERROR_TYPES.AUTH;
          message = data?.message || 'Authentication required';
        }
        break;
      case 403:
        errorType = ERROR_TYPES.AUTH;
        message = data?.message || 'Access denied';
        break;
      case 404:
        message = data?.message || 'Resource not found';
        break;
      case 409:
        errorType = ERROR_TYPES.VALIDATION;
        message = data?.message || 'Conflict with existing data';
        break;
      case 422:
        errorType = ERROR_TYPES.VALIDATION;
        message = data?.message || 'Validation failed';
        break;
      case 429:
        errorType = ERROR_TYPES.RATE_LIMIT;
        message = data?.message || 'Rate limit exceeded';
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        errorType = ERROR_TYPES.SERVER;
        message = data?.message || 'Server temporarily unavailable';
        break;
      default:
        message = data?.message || data?.error || `Server error (${statusCode})`;
    }
  } else if (error.request) {
    // Network error
    errorType = ERROR_TYPES.NETWORK;
    message = ERROR_MESSAGES[ERROR_TYPES.NETWORK];
  } else {
    // Other error
    message = error.message || ERROR_MESSAGES[ERROR_TYPES.UNKNOWN];
  }

  return {
    type: errorType,
    message,
    statusCode,
    originalError: error,
    isRetryable: errorType === ERROR_TYPES.NETWORK || errorType === ERROR_TYPES.SERVER,
    userMessage: ERROR_MESSAGES[errorType] || message
  };
};

// Retry mechanism for failed requests
export const retryRequest = async (requestFn, maxRetries = 3, delay = 1000) => {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;

      const errorInfo = handleApiError(error);
      if (!errorInfo.isRetryable || attempt === maxRetries) {
        throw error;
      }

      // Exponential backoff
      const waitTime = delay * Math.pow(2, attempt - 1);

      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }

  throw lastError;
};

// Enhanced error display hook - Note: This is a utility function, not a React hook
// Components should import and use this pattern: const { error } = useToast(); const { handleError } = useErrorHandler();
export const createErrorHandler = (toastFunctions) => {
  const { error: showErrorToast, success: showSuccessToast } = toastFunctions;

  const handleError = (error, context = '', showToast = true) => {
    const errorInfo = handleApiError(error, context);

    if (showToast) {
      showErrorToast(errorInfo.userMessage);
    }

    // Log detailed error for debugging
    if (import.meta.env.DEV) {
      console.error('Error details:', {
        context,
        type: errorInfo.type,
        statusCode: errorInfo.statusCode,
        message: errorInfo.message,
        originalError: errorInfo.originalError
      });
    }

    return errorInfo;
  };

  const handleSuccess = (message) => {
    if (showSuccessToast) {
      showSuccessToast(message);
    }
  };

  return {
    handleError,
    handleSuccess,
    ERROR_TYPES
  };
};

// Username availability checking - optimized for real-time validation
export const checkUsernameAvailability = async (username) => {
  try {
    const response = await axios.post(`${baseURL}/api/auth/check-username`, {
      username: username.trim()
    });

    return {
      available: response.data.available,
      suggestions: response.data.suggestions || [],
      caseInsensitiveConflict: response.data.case_insensitive_conflict,
    };
  } catch (error) {
    const errorInfo = handleApiError(error, 'username check');
    return {
      available: false,
      error: errorInfo.userMessage,
      suggestions: error.response?.data?.suggestions || [],
    };
  }
};

export default api 