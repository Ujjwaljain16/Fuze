/**
 * Unit tests for AuthContext
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../../contexts/AuthContext'
import { ToastProvider } from '../../contexts/ToastContext'
import api from '../../services/api'

// Mock API
vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: {
      get: vi.fn(() => Promise.resolve({ data: {} })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      defaults: {
        headers: {
          common: {}
        }
      },
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    },
    initializeCSRF: vi.fn(() => Promise.resolve())
  }
})

const wrapper = ({ children }) => (
  <BrowserRouter>
    <ToastProvider>
      <AuthProvider>{children}</AuthProvider>
    </ToastProvider>
  </BrowserRouter>
)

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('provides auth context', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current).toHaveProperty('user')
    expect(result.current).toHaveProperty('isAuthenticated')
    expect(result.current).toHaveProperty('login')
    expect(result.current).toHaveProperty('register')
    expect(result.current).toHaveProperty('logout')
  })

  it('handles login successfully', async () => {
    const mockUser = { id: 1, email: 'test@example.com', username: 'testuser' }
    
    // Ensure api.post is properly mocked - return a proper axios-like response
    api.post.mockResolvedValueOnce({
      data: {
        user: mockUser
      }
    })

    // Mock profile fetch which happens on mount
    api.get.mockResolvedValueOnce({
      data: mockUser
    })

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for auth to initialize
    await waitFor(() => {
      expect(result.current).toBeDefined()
    }, { timeout: 1000 })

    const loginResult = await result.current.login('test@example.com', 'password123')
    
    // Verify login was successful
    expect(loginResult.success).toBe(true)
    
    // Verify the API was called correctly
    expect(api.post).toHaveBeenCalledWith('/api/auth/login', {
      email: 'test@example.com',
      password: 'password123'
    })
    
    // Wait for state to update after login
    await waitFor(() => {
      // Also verify user is set
      expect(result.current.user).toEqual(mockUser)
      // Verify isAuthenticated is true
      expect(result.current.isAuthenticated).toBe(true)
    }, { timeout: 2000 })
    
    // User should be set
    expect(result.current.user).toEqual(mockUser)
  })

  it('handles login failure', async () => {
    api.post.mockRejectedValueOnce({
      response: {
        status: 401,
        data: { error: 'Invalid credentials' }
      }
    })

    const { result } = renderHook(() => useAuth(), { wrapper })

    const loginResult = await result.current.login('test@example.com', 'wrongpass')
    
    expect(loginResult.success).toBe(false)
    expect(loginResult.error).toBeDefined()
  })

  it('handles logout', async () => {
    const mockUser = { id: 1, username: 'test' }
    // Mock profile fetch on mount
    api.get.mockResolvedValueOnce({ data: mockUser })
    
    // Mock api.post for logout
    api.post.mockResolvedValueOnce({ data: {} })
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    // Wait for initial hydration
    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })

    // Perform logout
    result.current.logout()
    
    // Wait for state to clear
    await waitFor(() => {
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })
    
    expect(localStorage.getItem('user')).toBeFalsy()
  })
})

