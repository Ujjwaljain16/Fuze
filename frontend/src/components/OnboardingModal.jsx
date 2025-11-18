import { useState, useEffect } from 'react'
import { X, Key, Download, CheckCircle, ArrowRight, ExternalLink, Sparkles, AlertCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'

const OnboardingModal = ({ onComplete, forceApiKey = false }) => {
  const { user } = useAuth()
  const [currentStep, setCurrentStep] = useState(1)
  const [hasApiKey, setHasApiKey] = useState(false)
  const [loading, setLoading] = useState(true)
  const [dontShowAgain, setDontShowAgain] = useState(false)

  useEffect(() => {
    checkApiKeyStatus()
    
    // Listen for API key added event
    const handleApiKeyAdded = () => {
      setHasApiKey(true)
      if (currentStep === 1) {
        setCurrentStep(2)
      }
    }
    
    window.addEventListener('apiKeyAdded', handleApiKeyAdded)
    return () => window.removeEventListener('apiKeyAdded', handleApiKeyAdded)
  }, [])

  const checkApiKeyStatus = async () => {
    try {
      const response = await api.get('/api/user/api-key/status')
      if (response.data?.has_api_key) {
        setHasApiKey(true)
        // Skip to extension step if API key is already set
        if (currentStep === 1) {
          setCurrentStep(2)
        }
      }
    } catch (error) {
      console.error('Error checking API key status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = () => {
    // If API key is required and not set, prevent skipping
    if (forceApiKey && !hasApiKey) {
      return // Don't allow skipping
    }

    if (dontShowAgain) {
      localStorage.setItem('onboarding_completed', 'true')
    }
    onComplete()
  }

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1)
    } else {
      handleSkip()
    }
  }

  useEffect(() => {
    // Re-check API key status when step changes
    if (currentStep === 1) {
      checkApiKeyStatus()
    }
  }, [currentStep])

  if (loading) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto relative">
        {/* Close Button - Hide when API key is required */}
        {!forceApiKey && (
          <button
            onClick={handleSkip}
            className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        )}

        {/* Progress Indicator */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-white">
              {forceApiKey ? 'Setup Required' : 'Welcome to Fuze! 🎉'}
            </h2>
            <span className="text-sm text-gray-400">
              {forceApiKey ? 'Complete setup to continue' : `Step ${currentStep} of 3`}
            </span>
          </div>
          {forceApiKey && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 mb-4">
              <div className="flex items-center space-x-2 text-amber-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>API key setup is required to access the platform</span>
              </div>
            </div>
          )}
          <div className="flex space-x-2">
            {[1, 2, 3].map((step) => (
              <div
                key={step}
                className={`h-2 flex-1 rounded-full transition-all ${
                  step <= currentStep ? 'bg-blue-500' : 'bg-gray-700'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="p-6">
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-blue-500/20 rounded-lg">
                  <Key className="w-8 h-8 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white">Set Up Your Gemini API Key</h3>
                  <p className="text-gray-400">Required for AI-powered features</p>
                </div>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 space-y-4">
                <p className="text-gray-300">
                  To use Fuze's AI features (content analysis, recommendations, etc.), you need a free Gemini API key.
                </p>
                
                <div className="space-y-3">
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Free Tier Available</p>
                      <p className="text-gray-400 text-sm">15 requests/minute, 1,500 requests/day</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">No Rate Limit Conflicts</p>
                      <p className="text-gray-400 text-sm">Your own quota, no sharing with others</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Better Performance</p>
                      <p className="text-gray-400 text-sm">Faster responses and more reliable</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-blue-500/20">
                  <a
                    href="https://makersuite.google.com/app/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-2 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    <span>Get your free API key from Google AI Studio</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>

              {hasApiKey ? (
                <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <p className="text-green-400">API key is set up! You're all set.</p>
                </div>
              ) : (
                <div className={`${forceApiKey ? 'bg-red-500/10 border border-red-500/20' : 'bg-yellow-500/10 border border-yellow-500/20'} rounded-lg p-4 space-y-3`}>
                  <p className={`${forceApiKey ? 'text-red-400' : 'text-yellow-400'} text-sm`}>
                    {forceApiKey ? (
                      <>🔐 API key setup is required to access the platform. Please add your API key in your profile.</>
                    ) : (
                      <>💡 You can add your API key later in Settings → Profile, but we recommend doing it now for the best experience.</>
                    )}
                  </p>
                  <button
                    className={`inline-flex items-center space-x-2 ${forceApiKey ? 'text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border-red-500/20 hover:border-red-500/30' : 'text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/20 hover:border-blue-500/30'} transition-colors text-sm px-4 py-3 rounded-lg border transition-all font-medium`}
                    onClick={() => {
                      // Close modal and navigate to profile with API key required flag
                      window.location.href = '/profile?api_key_required=true'
                    }}
                  >
                    <Key className="w-4 h-4" />
                    <span>{forceApiKey ? 'Add API Key (Required)' : 'Go to Profile to add API key'}</span>
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-purple-500/20 rounded-lg">
                  <Download className="w-8 h-8 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white">Install Browser Extension</h3>
                  <p className="text-gray-400">Save content from anywhere on the web</p>
                </div>
              </div>

              <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 space-y-4">
                <p className="text-gray-300">
                  The Fuze browser extension lets you save bookmarks, articles, and learning resources directly from any webpage.
                </p>

                <div className="space-y-3">
                  <div className="flex items-start space-x-3">
                    <Sparkles className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">One-Click Saving</p>
                      <p className="text-gray-400 text-sm">Save any webpage with a single click</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <Sparkles className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Automatic Content Extraction</p>
                      <p className="text-gray-400 text-sm">AI extracts key information automatically</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <Sparkles className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Smart Tagging</p>
                      <p className="text-gray-400 text-sm">Content is automatically categorized</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-purple-500/20 space-y-3">
                  <p className="text-white font-medium">Download for your browser:</p>
                  <div className="flex flex-wrap gap-3">
                    <a
                      href="/extension/chrome"
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center space-x-2"
                    >
                      <span>Chrome Extension</span>
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <a
                      href="/extension/firefox"
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors flex items-center space-x-2"
                    >
                      <span>Firefox Extension</span>
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                  <p className="text-gray-400 text-sm">
                    💡 Extension installation instructions will be shown after download
                  </p>
                </div>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-green-500/20 rounded-lg">
                  <Sparkles className="w-8 h-8 text-green-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white">You're All Set! 🚀</h3>
                  <p className="text-gray-400">Start exploring Fuze</p>
                </div>
              </div>

              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 space-y-4">
                <p className="text-gray-300">
                  Welcome to Fuze! Here's what you can do:
                </p>

                <div className="space-y-3">
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Save Bookmarks</p>
                      <p className="text-gray-400 text-sm">Save learning resources and articles</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Create Projects</p>
                      <p className="text-gray-400 text-sm">Organize your learning journey</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Get AI Recommendations</p>
                      <p className="text-gray-400 text-sm">Discover relevant content based on your goals</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-white font-medium">Analyze Content</p>
                      <p className="text-gray-400 text-sm">AI-powered insights for every bookmark</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                <p className="text-blue-400 text-sm">
                  💡 <strong>Tip:</strong> Don't forget to add your API key in Settings → Profile if you haven't already!
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-6 border-t border-gray-800 flex items-center justify-between">
          {/* Don't show again checkbox - Hide when API key is required */}
          {!forceApiKey && (
            <label className="flex items-center space-x-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => setDontShowAgain(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
              />
              <span>Don't show this again</span>
            </label>
          )}

          {/* API Key Required Warning */}
          {forceApiKey && !hasApiKey && (
            <div className="flex items-center space-x-2 text-sm text-amber-400">
              <AlertCircle className="w-4 h-4" />
              <span>API key setup is required to continue</span>
            </div>
          )}

          <div className="flex space-x-3">
            {currentStep > 1 && (
              <button
                onClick={() => setCurrentStep(currentStep - 1)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={currentStep === 3 ? handleSkip : handleNext}
              disabled={forceApiKey && !hasApiKey && currentStep === 3}
              className={`px-6 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
                forceApiKey && !hasApiKey && currentStep === 3
                  ? 'bg-gray-600 cursor-not-allowed text-gray-400'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              <span>
                {currentStep === 3
                  ? (forceApiKey && !hasApiKey ? 'Add API Key First' : 'Get Started')
                  : 'Next'
                }
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingModal

