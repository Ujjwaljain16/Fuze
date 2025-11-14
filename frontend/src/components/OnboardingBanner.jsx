import { useState, useEffect } from 'react'
import { X, Key, Download, AlertCircle, ExternalLink, ArrowRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const OnboardingBanner = () => {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [hasApiKey, setHasApiKey] = useState(false)
  const [hasExtension, setHasExtension] = useState(false)
  const [loading, setLoading] = useState(true)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      checkSetupStatus()
    }
  }, [isAuthenticated])

  const checkSetupStatus = async () => {
    try {
      const response = await api.get('/api/user/api-key/status')
      setHasApiKey(response.data?.has_api_key || false)
      
      // Check if extension is installed (this would need to be implemented)
      // For now, we'll check localStorage or a flag
      const extensionInstalled = localStorage.getItem('extension_installed') === 'true'
      setHasExtension(extensionInstalled)
    } catch (error) {
      console.error('Error checking setup status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDismiss = () => {
    setDismissed(true)
    localStorage.setItem('onboarding_banner_dismissed', 'true')
  }

  if (loading || dismissed || !isAuthenticated) {
    return null
  }

  // Check if user dismissed banner
  if (localStorage.getItem('onboarding_banner_dismissed') === 'true') {
    return null
  }

  // Show banner if API key or extension is missing
  if (hasApiKey && hasExtension) {
    return null
  }

  const missingItems = []
  if (!hasApiKey) missingItems.push('API Key')
  if (!hasExtension) missingItems.push('Browser Extension')

  return (
    <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-l-4 border-blue-500 rounded-lg p-4 mb-6 relative">
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 text-gray-400 hover:text-white transition-colors"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="flex items-start space-x-4">
        <div className="p-2 bg-blue-500/20 rounded-lg">
          <AlertCircle className="w-6 h-6 text-blue-400" />
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">
            Complete Your Setup
          </h3>
          <p className="text-gray-300 text-sm mb-3">
            To get the most out of Fuze, you're missing: <strong>{missingItems.join(' and ')}</strong>
          </p>

          <div className="flex flex-wrap gap-3">
            {!hasApiKey && (
              <button
                onClick={() => navigate('/profile')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2 text-sm"
              >
                <Key className="w-4 h-4" />
                <span>Add API Key</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}

            {!hasExtension && (
              <a
                href="/extension/chrome"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center space-x-2 text-sm"
              >
                <Download className="w-4 h-4" />
                <span>Install Extension</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            )}

            <button
              onClick={() => {
                localStorage.setItem('show_onboarding', 'true')
                window.location.reload()
              }}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
            >
              Show Setup Guide
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingBanner


