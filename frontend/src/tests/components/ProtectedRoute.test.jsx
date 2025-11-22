/**
 * Unit tests for ProtectedRoute component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import ProtectedRoute from '../../components/ProtectedRoute'
import { AuthProvider } from '../../contexts/AuthContext'
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

const TestComponent = () => <div>Protected Content</div>

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    
    // Mock API calls FIRST
    api.get.mockImplementation((url) => {
      if (url === '/api/profile') {
        return Promise.resolve({
          data: { id: 1, email: 'test@example.com', username: 'testuser', name: 'Test User' }
        })
      }
      if (url === '/api/user/api-key/status') {
        return Promise.resolve({
          data: { has_api_key: true }
        })
      }
      return Promise.reject(new Error('Unknown endpoint'))
    })
  })

  it('renders children when authenticated', async () => {
    // Set token right before rendering (AuthContext reads it on mount)
    localStorage.setItem('token', 'mock-token')
    
    render(
      <MemoryRouter>
        <ToastProvider>
          <AuthProvider>
            <ProtectedRoute>
              <TestComponent />
            </ProtectedRoute>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    )
    
    // Wait for content to appear (this will happen after auth and API key checks)
    await waitFor(() => {
      const content = screen.queryByText('Protected Content')
      expect(content).toBeTruthy()
    }, { timeout: 15000 })
  })

  it('redirects to login when not authenticated', () => {
    localStorage.removeItem('token')
    
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <ToastProvider>
          <AuthProvider>
            <ProtectedRoute>
              <TestComponent />
            </ProtectedRoute>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    )
    
    // Should redirect to login (component won't render)
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })
})

