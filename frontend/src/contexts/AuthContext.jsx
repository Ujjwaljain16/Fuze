import { createContext, useContext, useState, useEffect } from 'react'
import api, { initializeCSRF } from '../services/api'

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

  useEffect(() => {
    const initializeAuth = async () => {
      // Initialize CSRF token
      await initializeCSRF()
      
      if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`
        // Fetch user data when token is available
        await fetchUser()
      }
      setLoading(false)
    }
    
    initializeAuth()
  }, [token])

  const fetchUser = async () => {
    try {
      const response = await api.get('/api/profile')
      setUser(response.data)
    } catch (error) {
      console.error('Error fetching user data:', error)
      // If token is invalid, logout
      if (error.response?.status === 401) {
        logout()
      }
    }
  }

  const login = async (email, password) => {
    try {
      const response = await api.post('/api/auth/login', { email, password })
      const { access_token, user: userData } = response.data
      
      setToken(access_token)
      setUser(userData)
      localStorage.setItem('token', access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.message || 'Login failed' 
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
      return { success: true, message: response.data.message }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.message || 'Registration failed' 
      }
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
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