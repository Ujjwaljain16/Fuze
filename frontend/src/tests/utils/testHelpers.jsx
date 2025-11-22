/**
 * Test utilities and helpers for frontend tests
 */
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../../contexts/AuthContext'
import { ToastProvider } from '../../contexts/ToastContext'

/**
 * Render component with all providers
 */
export const renderWithProviders = (ui, options = {}) => {
  const {
    ...renderOptions
  } = options

  const Wrapper = ({ children }) => {
    return (
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    )
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

/**
 * Mock API responses
 */
export const mockApiResponse = (data, status = 200) => {
  return Promise.resolve({
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {}
  })
}

/**
 * Mock API error
 */
export const mockApiError = (message, status = 400) => {
  return Promise.reject({
    response: {
      data: { error: message },
      status,
      statusText: 'Bad Request'
    }
  })
}

