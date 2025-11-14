import { useState, useEffect } from 'react'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import { Key, Eye, EyeOff, CheckCircle, XCircle, Trash2, TestTube, ExternalLink, TrendingUp, Shield, Zap } from 'lucide-react'

const ApiKeyManager = () => {
  const { success, error } = useToast()
  const [apiKey, setApiKey] = useState('')
  const [apiKeyName, setApiKeyName] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [status, setStatus] = useState(null)
  const [usage, setUsage] = useState(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      const response = await api.get('/api/user/api-key/status')
      if (response.data) {
        setStatus(response.data)
        if (response.data.has_api_key) {
          setApiKeyName(response.data.api_key_name || 'My API Key')
        }
      }
    } catch (err) {
      console.error('Error loading API key status:', err)
    }
  }

  const loadUsage = async () => {
    try {
      const response = await api.get('/api/user/api-key/usage')
      if (response.data) {
        setUsage(response.data)
      }
    } catch (err) {
      console.error('Error loading usage:', err)
    }
  }

  const handleSave = async (e) => {
    e.preventDefault()
    
    if (!apiKey.trim()) {
      error('Please enter your API key')
      return
    }

    if (!apiKey.startsWith('AIza') || apiKey.length < 30) {
      error('Invalid API key format. Gemini keys start with "AIza" and are at least 30 characters.')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/api/user/api-key', {
        api_key: apiKey.trim(),
        api_key_name: apiKeyName.trim() || 'My API Key'
      })

      if (response.data) {
        success('API key saved successfully!')
        setApiKey('')
        setApiKeyName('')
        loadStatus()
        loadUsage()
        
        // Trigger a custom event for onboarding modal to update
        window.dispatchEvent(new CustomEvent('apiKeyAdded'))
      }
    } catch (err) {
      console.error('Error saving API key:', err)
      if (err.response?.data?.error) {
        error(err.response.data.error)
      } else {
        error('Failed to save API key. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const response = await api.post('/api/user/api-key/test')
      
      if (response.data?.valid) {
        success('API key is valid and working!')
      } else {
        error(response.data?.message || 'API key test failed')
      }
    } catch (err) {
      console.error('Error testing API key:', err)
      error('Failed to test API key. Please try again.')
    } finally {
      setTesting(false)
    }
  }

  const handleRemove = async () => {
    if (!confirm('Are you sure you want to remove your API key? AI features will use the default key.')) {
      return
    }

    setLoading(true)
    try {
      const response = await api.delete('/api/user/api-key')
      
      if (response.data) {
        success('API key removed successfully')
        setApiKey('')
        setApiKeyName('')
        setStatus(null)
        setUsage(null)
        loadStatus()
      }
    } catch (err) {
      console.error('Error removing API key:', err)
      error('Failed to remove API key. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (status?.has_api_key) {
      loadUsage()
    }
  }, [status])

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Key className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">Gemini API Key</h3>
            <p className="text-sm text-gray-400">Use your own API key for better performance</p>
          </div>
        </div>
        {status?.has_api_key && (
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm flex items-center space-x-1">
            <CheckCircle className="w-4 h-4" />
            <span>Active</span>
          </span>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            API Key
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIzaSy..."
              maxLength={100}
              className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-12"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
            >
              {showKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your free API key from{' '}
            <a
              href="https://makersuite.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 inline-flex items-center space-x-1"
            >
              <span>Google AI Studio</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Key Name (Optional)
          </label>
          <input
            type="text"
            value={apiKeyName}
            onChange={(e) => setApiKeyName(e.target.value)}
            placeholder="My Personal Key"
            className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex space-x-3">
          <button
            type="submit"
            disabled={loading || !apiKey.trim()}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Key className="w-4 h-4" />
                <span>Save API Key</span>
              </>
            )}
          </button>

          {status?.has_api_key && (
            <>
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                {testing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Testing...</span>
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    <span>Test</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleRemove}
                disabled={loading}
                className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                <Trash2 className="w-4 h-4" />
                <span>Remove</span>
              </button>
            </>
          )}
        </div>
      </form>

      {status?.has_api_key && usage && (
        <div className="mt-6 pt-6 border-t border-gray-800">
          <h4 className="text-sm font-medium text-gray-300 mb-4 flex items-center space-x-2">
            <TrendingUp className="w-4 h-4" />
            <span>Usage Statistics</span>
          </h4>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Daily</span>
                <span className="text-white">
                  {usage.usage_stats?.requests_today || 0} / {usage.limits?.requests_per_day || 1500}
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, ((usage.usage_stats?.requests_today || 0) / (usage.limits?.requests_per_day || 1500)) * 100)}%`
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Monthly</span>
                <span className="text-white">
                  {usage.usage_stats?.requests_this_month || 0} / {usage.limits?.requests_per_month || 45000}
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, ((usage.usage_stats?.requests_this_month || 0) / (usage.limits?.requests_per_month || 45000)) * 100)}%`
                  }}
                />
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div className="flex items-start space-x-2">
              <Shield className="w-4 h-4 text-blue-400 mt-0.5" />
              <div className="text-xs text-gray-300">
                <p className="font-medium text-blue-400 mb-1">Why use your own key?</p>
                <ul className="space-y-1 text-gray-400">
                  <li>• No rate limit conflicts with other users</li>
                  <li>• You control your own API usage and costs</li>
                  <li>• Better performance and reliability</li>
                  <li>• Free tier: 15/min, 1,500/day, 45,000/month</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {!status?.has_api_key && (
        <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
          <div className="flex items-start space-x-2">
            <Zap className="w-4 h-4 text-yellow-400 mt-0.5" />
            <div className="text-xs text-gray-300">
              <p className="font-medium text-yellow-400 mb-1">No API key configured</p>
              <p className="text-gray-400">
                You're currently using the default shared API key. Add your own key for better performance and no rate limit conflicts.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ApiKeyManager

