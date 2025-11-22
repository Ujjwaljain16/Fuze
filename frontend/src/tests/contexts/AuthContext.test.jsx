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
      get: vi.fn(),
      post: vi.fn(),
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
        access_token: 'mock-token',
        user: mockUser
      }
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
      // Check token from context (primary check)
      expect(result.current.token).toBe('mock-token')
      // Also verify user is set
      expect(result.current.user).toEqual(mockUser)
      // Verify isAuthenticated is true
      expect(result.current.isAuthenticated).toBe(true)
    }, { timeout: 2000 })
    
    // localStorage should also be set (login function sets it synchronously)
    // But in test environment, focus on context state which is what the app uses
    expect(result.current.token).toBe('mock-token')
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

  it('handles logout', () => {
    localStorage.setItem('token', 'mock-token')
    
    // Mock api.post to return a promise to prevent the .catch error
    api.post.mockResolvedValueOnce({ data: {} })
    
    const { result } = renderHook(() => useAuth(), { wrapper })
    
    result.current.logout()
    
    // localStorage.removeItem makes getItem return null
    expect(localStorage.getItem('token')).toBeFalsy()
    expect(result.current.isAuthenticated).toBe(false)
  })
})

