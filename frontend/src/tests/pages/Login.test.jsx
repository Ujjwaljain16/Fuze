/**
 * Integration tests for Login page
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Login from '../../pages/Login'
import { AuthProvider } from '../../contexts/AuthContext'
import { ToastProvider } from '../../contexts/ToastContext'
import api from '../../services/api'

vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: {
      post: vi.fn(),
      get: vi.fn(),
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

// Note: We'll use the actual AuthContext but mock the API calls

const renderLogin = () => {
  // Clear any existing auth state
  localStorage.removeItem('token')
  
  return render(
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders login form', () => {
    renderLogin()
    // Login form may use different label patterns, check for input fields
    const emailInput = screen.getByPlaceholderText(/email/i) || screen.queryByRole('textbox', { name: /email/i })
    const passwordInput = screen.getByPlaceholderText(/password/i) || screen.getByLabelText(/password/i)
    expect(emailInput || passwordInput).toBeTruthy()
  })

  it('switches between login and signup', () => {
    renderLogin()
    
    // Find the toggle button in the tab switcher (not the submit button or link)
    const toggleButtons = screen.getAllByText(/sign up/i)
    // The toggle button should be in the tab switcher, not the submit button
    const toggleButton = toggleButtons.find(btn => 
      btn.className.includes('flex-1') || btn.closest('[class*="bg-gray-800"]')
    ) || toggleButtons[0]
    fireEvent.click(toggleButton)
    
    // After switching, should show signup fields
    const usernameField = screen.queryByPlaceholderText(/username/i) || screen.queryByLabelText(/username/i)
    const confirmPasswordField = screen.queryByPlaceholderText(/confirm/i) || screen.queryByLabelText(/confirm/i)
    expect(usernameField || confirmPasswordField).toBeTruthy()
  })

  it('validates password strength', async () => {
    renderLogin()
    
    // Switch to signup - find the toggle button in the tab switcher
    const toggleButtons = screen.getAllByText(/sign up/i)
    const toggleButton = toggleButtons.find(btn => 
      btn.className.includes('flex-1') || btn.closest('[class*="bg-gray-800"]')
    ) || toggleButtons[0]
    fireEvent.click(toggleButton)
    
    // Wait for signup form to appear
    await waitFor(() => {
      const passwordInputs = screen.getAllByPlaceholderText(/password/i)
      expect(passwordInputs.length).toBeGreaterThan(0)
    }, { timeout: 2000 })
    
    // Get the first password input (not confirm password) by name attribute
    const passwordInputs = screen.getAllByPlaceholderText(/password/i)
    const passwordInput = passwordInputs.find(input => 
      input.name === 'password' && !input.name.includes('confirm')
    ) || passwordInputs.find(input => 
      input.placeholder.toLowerCase().includes('create') || 
      input.placeholder.toLowerCase().includes('strong')
    ) || passwordInputs[0]
    
    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    
    // Should show password strength indicator or validation message
    // Use getAllByText to handle multiple matches and check for the specific requirement text
    await waitFor(() => {
      // Check for the specific "At least 8 characters" requirement text
      const requirementText = screen.getAllByText(/at least 8 characters/i)
      expect(requirementText.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })

  it('submits login form', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        access_token: 'mock-token',
        user: { id: 1, email: 'test@example.com' }
      }
    })

    renderLogin()
    
    // Wait for form to be ready
    await waitFor(() => {
      const emailInput = screen.queryByPlaceholderText(/email/i) || screen.queryByLabelText(/email/i)
      expect(emailInput).toBeTruthy()
    }, { timeout: 2000 })
    
    const emailInput = screen.getByPlaceholderText(/email/i) || screen.getByLabelText(/email/i)
    // In login mode, there should be only one password field - get by name
    const passwordInput = screen.getByPlaceholderText(/password/i) || 
      screen.getByLabelText(/password/i) ||
      (() => {
        const inputs = screen.getAllByPlaceholderText(/password/i)
        return inputs.find(input => input.name === 'password') || inputs[0]
      })()
    
    fireEvent.change(emailInput, {
      target: { value: 'test@example.com' }
    })
    fireEvent.change(passwordInput, {
      target: { value: 'password123' }
    })
    
    // Find the form and submit it
    const form = emailInput.closest('form')
    if (form) {
      fireEvent.submit(form)
    } else {
      // Fallback: find submit button
      const submitButtons = screen.getAllByRole('button', { name: /sign in|login/i })
      const submitButton = submitButtons.find(btn => 
        btn.type === 'submit' || btn.className.includes('w-full') || btn.textContent.includes('to Fuze')
      ) || submitButtons[0]
      fireEvent.click(submitButton)
    }
    
    // Wait for either the API call or the login function to be called
    await waitFor(() => {
      const apiCalled = api.post.mock.calls.some(call => 
        call[0] === '/api/auth/login' &&
        call[1]?.email === 'test@example.com' &&
        call[1]?.password === 'password123'
      )
      expect(apiCalled).toBe(true)
    }, { timeout: 5000 })
  })
})

