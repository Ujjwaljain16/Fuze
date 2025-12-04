import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useState, useEffect } from 'react'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()
  const [hasApiKey, setHasApiKey] = useState(null)

  // Listen for API key status from dashboard or API key added event
  useEffect(() => {
    const handleApiKeyAdded = () => {
      setHasApiKey(true)
    }

    const handleApiKeyStatus = (event) => {
      setHasApiKey(event.detail?.has_api_key || false)
    }

    window.addEventListener('apiKeyAdded', handleApiKeyAdded)
    window.addEventListener('apiKeyStatus', handleApiKeyStatus)
    return () => {
      window.removeEventListener('apiKeyAdded', handleApiKeyAdded)
      window.removeEventListener('apiKeyStatus', handleApiKeyStatus)
    }
  }, [])

  // Don't show fullScreen loader here - let individual pages handle their own loading states
  // The initial app loading is handled in App.jsx
  if (loading) {
    // Just return null or a minimal loader - pages will show their own loaders
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  // If we haven't checked API key status yet (null), render children
  // Dashboard will emit apiKeyStatus event after loading
  if (hasApiKey === null) {
    return children
  }

  // If user is authenticated but doesn't have API key
  if (hasApiKey === false) {
    // Allow access to profile page so they can set up API key
    if (location.pathname === '/profile') {
      return children
    }

    // For all other pages, redirect directly to profile with a message
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-md w-full p-8 text-center">
          <div className="mb-6">
            <div className="w-16 h-16 bg-cyan-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H7l2-4-2-4h4l2.257-2.743A6 6 0 0115 7z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Setup Required</h2>
            <p className="text-gray-400 mb-6">
              You need to add your Gemini API key to access Fuze's AI features.
            </p>
            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4 mb-6">
              <p className="text-cyan-400 text-sm">
                Get your free API key from Google AI Studio - it only takes 2 minutes!
              </p>
            </div>
          </div>
          <button
            onClick={() => window.location.href = '/profile?api_key_required=true'}
            className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            <span>Add API Key Now</span>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
          <p className="text-xs text-gray-500 mt-4">
            This will redirect you to your profile where you can add your API key.
          </p>
        </div>
      </div>
    )
  }

  return children
}

export default ProtectedRoute 