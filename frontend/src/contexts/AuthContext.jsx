import { createContext, useContext, useState, useEffect, useRef } from 'react'
import api, { initializeCSRF, handleApiError } from '../services/api'
import { useToast } from './ToastContext'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)
  const userRef = useRef(null) // Track user to avoid closure issues
  const { error: showErrorToast } = useToast()

  // Update ref when user changes
  useEffect(() => {
    userRef.current = user
  }, [user])

  useEffect(() => {
    const initializeAuth = async () => {
      // Initialize CSRF token in background (non-blocking)
      initializeCSRF().catch(console.warn)
      
      if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`
        // Fetch user data when token is available
        // Only fetch if user is not already set (to avoid unnecessary calls after login)
        // Use ref to get current value, not closure value
        if (!userRef.current) {
          await fetchUser(true) // Pass true to indicate this is initialization
        }
      } else {
        // No token, ensure user is cleared
        setUser(null)
        userRef.current = null
      }
      setLoading(false)
    }
    
    initializeAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]) // Only depend on token, not user, to avoid loops

  const fetchUser = async (isInitialLoad = false) => {
    try {
      const response = await api.get('/api/profile')
      setUser(response.data)
      userRef.current = response.data
      return true
    } catch (error) {
      const errorInfo = handleApiError(error, 'fetching user profile')

      // Handle authentication errors
      if (error.response?.status === 401) {
        // Only logout if this is not an initial load, or if user is not set
        // This prevents logging out immediately after a successful login
        if (!isInitialLoad || !userRef.current) {
          logout()
          return false
        }
      }

      // Show error toast for non-auth errors
      if (error.response?.status !== 401) {
        showErrorToast(errorInfo.userMessage)
      }

      return false
    }
  }

  const login = async (email, password) => {
    try {
      const response = await api.post('/api/auth/login', { email, password })
      const { access_token, user: userData } = response.data
      
      // Set token first
      localStorage.setItem('token', access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      // Set state atomically to avoid race conditions
      setToken(access_token)
      setUser(userData)
      userRef.current = userData // Update ref immediately
      
      // Verify the user data is valid
      if (!userData || !userData.id) {
        console.error('Invalid user data received from login')
        return { 
          success: false, 
          error: 'Invalid response from server' 
        }
      }
      
      return { success: true }
    } catch (error) {
      const errorInfo = handleApiError(error, 'login')
      return {
        success: false,
        error: errorInfo.userMessage
      }
    }
  }

  const register = async (username, email, password, name) => {
    try {
      const response = await api.post('/api/auth/register', { 
        username, 
        email, 
        password,
        name 
      })
      
      // Mark that onboarding should be shown
      if (response.data.access_token) {
        const { access_token, user: userData } = response.data
        setToken(access_token)
        setUser(userData)
        localStorage.setItem('token', access_token)
        localStorage.setItem('show_onboarding', 'true')
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      }
      
      return { success: true, message: response.data.message }
    } catch (error) {
      const errorInfo = handleApiError(error, 'registration')
      return {
        success: false,
        error: errorInfo.userMessage
      }
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    userRef.current = null
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    
    // Call logout endpoint to clear cookies
    api.post('/api/auth/logout').catch(console.error)
  }

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
} 