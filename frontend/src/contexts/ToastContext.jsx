import { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'

const ToastContext = createContext()

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  const addToast = useCallback(({ type = 'info', message, duration = 5000 }) => {
    const id = Date.now()
    const newToast = { id, type, message, duration }
    
    setToasts(prev => [...prev, newToast])
    
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }
  }, [removeToast])

  const success = useCallback((message, duration) => {
    addToast({ type: 'success', message, duration })
  }, [addToast])

  const error = useCallback((message, duration) => {
    addToast({ type: 'error', message, duration })
  }, [addToast])

  const warning = useCallback((message, duration) => {
    addToast({ type: 'warning', message, duration })
  }, [addToast])

  const info = useCallback((message, duration) => {
    addToast({ type: 'info', message, duration })
  }, [addToast])

  const ToastContainer = () => (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          <div className="toast-content">
            {toast.type === 'success' && <CheckCircle size={16} />}
            {toast.type === 'error' && <XCircle size={16} />}
            {toast.type === 'warning' && <AlertCircle size={16} />}
            {toast.type === 'info' && <AlertCircle size={16} />}
            <span>{toast.message}</span>
          </div>
          <button 
            className="toast-close"
            onClick={() => removeToast(toast.id)}
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )

  return (
    <ToastContext.Provider value={{ addToast, removeToast, success, error, warning, info }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  )
} 