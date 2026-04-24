import axios from 'axios'
import { v4 as uuidv4 } from 'uuid'

const DEFAULT_PROD_API_URL = 'https://Ujjwaljain16-fuze-backend.hf.space'

// Get base URL from environment or automatically detect
const getBaseURL = () => {
  // Check if we're in development (localhost or 127.0.0.1)
  const isDevelopment = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1'
  
  if (isDevelopment) {
    // Development: Use HTTP localhost
    return import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'
  } else {
    // Production: Prefer environment variable; fall back to known backend URL.
    const apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl) {
      console.error('VITE_API_URL is not set in production, using fallback API URL:', DEFAULT_PROD_API_URL)
      return DEFAULT_PROD_API_URL
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

// Request interceptor to add CSRF token and correlation ID
api.interceptors.request.use(
  async (config) => {
    // Inject Correlation ID for end-to-end traceability
    const requestId = uuidv4()
    config.headers['X-Request-ID'] = requestId
    
    // Authorization header is now automatically handled by cookies (HttpOnly)
    
    // CSRF Protection: For mutating requests, extract the CSRF token from the cookie
    // Flask-JWT-Extended sets 'csrf_access_token' in a non-HttpOnly cookie
    if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
      const csrfCookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_access_token='))
      
      if (csrfCookie) {
        const csrfToken = csrfCookie.split('=')[1]
        config.headers['X-CSRF-TOKEN'] = csrfToken
      }
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
        // Attempt to refresh the access token using the HttpOnly refresh cookie
        await axios.post(
          `${baseURL}/api/auth/refresh`,
          {},
          { withCredentials: true }
        )
        // Refresh succeeded (backend set new access cookie) - retry the original request
        return api(originalRequest)
      } catch {
        // Refresh failed (refresh token expired) - clear user state
        localStorage.removeItem('user')
        window.dispatchEvent(new CustomEvent('authExpired'))
      }
    }
    return Promise.reject(error)
  }
)

// Proactive token refresh - now simplified as it just hits the refresh endpoint
export const refreshTokenIfNeeded = async () => {
  try {
    // We can't decode HttpOnly cookies from JS, so we just hit the refresh endpoint
    // to ensure we have a valid access cookie before starting long operations.
    await axios.post(
      `${baseURL}/api/auth/refresh`,
      {},
      { withCredentials: true }
    )
  } catch (error) {
    console.warn('Proactive refresh failed:', error)
  }
}

// CSRF token initialization is no longer needed as tokens are read directly from cookies in the interceptor
export const initializeCSRF = async () => {
  // No-op for backward compatibility in AuthContext
  return Promise.resolve()
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