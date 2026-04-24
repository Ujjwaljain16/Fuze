import { createContext, useContext, useState, useEffect, useRef } from 'react'
import api, { initializeCSRF, handleApiError } from '../services/api'
import { useToast } from './ToastContext'

const AuthContext = createContext()

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const storedUser = localStorage.getItem('user')
      return storedUser ? JSON.parse(storedUser) : null
    } catch {
      return null
    }
  })
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
      
      // Attempt to fetch user data on mount (session is in cookies)
      // If user is not in localStorage, we must check the backend
      if (!userRef.current) {
        await fetchUser()
      }
      
      setLoading(false)
    }
    
    initializeAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Initialize once on mount

  // Listen for login events to refresh user state
  useEffect(() => {
    const handleUserLoggedIn = (event) => {
      // OAuth callback can provide user directly to avoid redirect races on mobile/PWA.
      if (event?.detail?.user) {
        setUser(event.detail.user)
        userRef.current = event.detail.user
        localStorage.setItem('user', JSON.stringify(event.detail.user))
      } else {
        // Otherwise just try to fetch the profile
        fetchUser()
      }
    }

    const handleAuthExpired = () => {
      logout()
    }

    window.addEventListener('userLoggedIn', handleUserLoggedIn)
    window.addEventListener('authExpired', handleAuthExpired)
    return () => {
      window.removeEventListener('userLoggedIn', handleUserLoggedIn)
      window.removeEventListener('authExpired', handleAuthExpired)
    }
  }, [])

  const fetchUser = async () => {
    try {
      // Profile endpoint is now cached and optimized - should be fast
      const response = await api.get('/api/profile')
      setUser(response.data)
      userRef.current = response.data
      localStorage.setItem('user', JSON.stringify(response.data))
      return true
    } catch (error) {
      const errorInfo = handleApiError(error, 'fetching user profile')

      // Handle authentication errors
      if (error.response?.status === 401) {
        // 401 means token is invalid/expired - clear stale auth state immediately.
        logout()
        return false
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
      const { user: userData } = response.data
      
      // Set state atomically to avoid race conditions
      setUser(userData)
      userRef.current = userData // Update ref immediately
      localStorage.setItem('user', JSON.stringify(userData))
      
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
      
      // Don't auto-login after registration - user should log in manually
      // Just return success message
      return { 
        success: true, 
        message: response.data.message || 'Registration successful! Please log in to continue.'
      }
    } catch (error) {
      const errorInfo = handleApiError(error, 'registration')
      return {
        success: false,
        error: errorInfo.userMessage
      }
    }
  }

  const logout = () => {
    setUser(null)
    userRef.current = null
    localStorage.removeItem('user')
    
    // Call logout endpoint to clear cookies
    api.post('/api/auth/logout').catch(console.error)
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
} 