/**
 * Unit tests for useErrorHandler hook
 */
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { useErrorHandler } from '../../hooks/useErrorHandler'
import { ToastProvider } from '../../contexts/ToastContext'

const wrapper = ({ children }) => (
  <BrowserRouter>
    <ToastProvider>
      {children}
    </ToastProvider>
  </BrowserRouter>
)

describe('useErrorHandler', () => {
  it('provides error handling functions', () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper })
    
    expect(result.current).toHaveProperty('handleError')
    expect(result.current).toHaveProperty('handleSuccess')
  })

  it('handles API errors', () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper })
    
    const error = {
      response: {
        status: 400,
        data: { error: 'Bad request' }
      }
    }
    
    act(() => {
      result.current.handleError(error, 'test operation')
    })
    
    // Should not throw
    expect(result.current.handleError).toBeDefined()
  })

  it('handles network errors', () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper })
    
    const error = {
      message: 'Network Error',
      code: 'ECONNABORTED'
    }
    
    act(() => {
      result.current.handleError(error, 'test operation')
    })
    
    // Should not throw
    expect(result.current.handleError).toBeDefined()
  })
})

