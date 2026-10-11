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

export const baseURL = getBaseURL()

// API configuration removed for production

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout - should be fast with optimizations
})

// Session tokens live in localStorage['user'] ({ token/access_token, refresh_token, ...profile }).
// The API is on a different site than the app, so its cookies are never sent with our requests:
// the access token goes in the Authorization header and the refresh token is sent explicitly.
const readStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

const storeTokens = (accessToken, refreshToken) => {
  const user = readStoredUser()
  if (!user) return
  if (accessToken) {
    user.token = accessToken
    user.access_token = accessToken
  }
  if (refreshToken) user.refresh_token = refreshToken
  localStorage.setItem('user', JSON.stringify(user))
}

const tokenExpiresWithin = (token, seconds) => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return !payload.exp || payload.exp * 1000 - Date.now() < seconds * 1000
  } catch {
    return true
  }
}

// Request interceptor: correlation ID + bearer token
api.interceptors.request.use(
  async (config) => {
    // Inject Correlation ID for end-to-end traceability
    const requestId = uuidv4()
    config.headers['X-Request-ID'] = requestId
    
    const token = readStoredUser()?.token || readStoredUser()?.access_token
    if (token && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Single-flight refresh guard & helper
let inFlightRefreshPromise = null

const executeTokenRefresh = async () => {
  if (inFlightRefreshPromise) {
    return inFlightRefreshPromise
  }

  inFlightRefreshPromise = (async () => {
    try {
      const refreshToken = readStoredUser()?.refresh_token
      // Without a stored refresh token (sessions from before this change) fall back to the cookie,
      // which works when the app and API share a site (local dev, same-domain deploys).
      const headers = refreshToken ? { Authorization: `Bearer ${refreshToken}` } : {}
      const response = await axios.post(`${baseURL}/api/auth/refresh`, {}, { withCredentials: true, headers })
      // Refresh tokens rotate: the old one is now spent, so the new pair must be saved together.
      storeTokens(response.data?.access_token, response.data?.refresh_token)
      return response
    } finally {
      inFlightRefreshPromise = null
    }
  })()

  return inFlightRefreshPromise
}

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    // Handle token expiration (ignore auth endpoints: login, logout, refresh, supabase-oauth)
    const AUTH_BYPASS_URLS = ['/api/auth/login', '/api/auth/logout', '/api/auth/refresh', '/api/auth/supabase-oauth']
    const isAuthUrl = AUTH_BYPASS_URLS.some((path) => originalRequest.url?.includes(path))

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthUrl) {
      originalRequest._retry = true
      try {
        const refreshResponse = await executeTokenRefresh()
        const newAccessToken = refreshResponse.data?.access_token
        if (newAccessToken) {
          originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`
        }

        // Refresh succeeded - retry the original request with new access token
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

// Proactive token refresh - simplified using executeTokenRefresh
export const refreshTokenIfNeeded = async () => {
  const token = readStoredUser()?.token || readStoredUser()?.access_token
  if (token && !tokenExpiresWithin(token, 120)) return
  try {
    await executeTokenRefresh()
  } catch (error) {
    console.warn('Proactive refresh failed:', error)
  }
}

// Kept for AuthContext's existing call; API requests authenticate with the bearer header.
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

// Every API error body is {"error": "<snake_case_code>", "message": "<human sentence>"}:
// branch on the code, show the message.
export const getApiErrorCode = (error) => {
  const code = error?.response?.data?.error
  return typeof code === 'string' ? code : null
}

export const getApiErrorMessage = (error, fallback = ERROR_MESSAGES[ERROR_TYPES.UNKNOWN]) => {
  const message = error?.response?.data?.message
  return typeof message === 'string' && message.trim() ? message : fallback
}

// Error handler utility
export const handleApiError = (error, context = '') => {
  console.error(`API Error${context ? ` (${context})` : ''}:`, error);

  let errorType = ERROR_TYPES.UNKNOWN;
  let message = ERROR_MESSAGES[ERROR_TYPES.UNKNOWN];
  let statusCode = 0;
  let code = null;

  if (error.response) {
    // Server responded with error status
    statusCode = error.response.status;
    code = getApiErrorCode(error);
    const serverMessage = getApiErrorMessage(error, null);

    switch (statusCode) {
      case 400:
        errorType = ERROR_TYPES.VALIDATION;
        message = serverMessage || 'Invalid request data';
        break;
      case 401:
        // Check if this is a login attempt with wrong credentials
        if (code === 'invalid_credentials') {
          errorType = ERROR_TYPES.VALIDATION;
          message = 'Invalid credentials';
        } else {
          errorType = ERROR_TYPES.AUTH;
          message = serverMessage || 'Authentication required';
        }
        break;
      case 403:
        errorType = ERROR_TYPES.AUTH;
        message = serverMessage || 'Access denied';
        break;
      case 404:
        message = serverMessage || 'Resource not found';
        break;
      case 409:
        errorType = ERROR_TYPES.VALIDATION;
        message = serverMessage || 'Conflict with existing data';
        break;
      case 422:
        errorType = ERROR_TYPES.VALIDATION;
        message = serverMessage || 'Validation failed';
        break;
      case 429:
        errorType = ERROR_TYPES.RATE_LIMIT;
        message = serverMessage || 'Rate limit exceeded';
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        errorType = ERROR_TYPES.SERVER;
        message = serverMessage || 'Server temporarily unavailable';
        break;
      default:
        message = serverMessage || `Server error (${statusCode})`;
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
    code,
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