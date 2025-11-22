import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Share2, ExternalLink, Loader2, CheckCircle2, XCircle, Globe } from 'lucide-react'
import Button from '../components/Button'

const ShareHandler = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading } = useAuth()
  
  const [sharedUrl, setSharedUrl] = useState('')
  const [sharedTitle, setSharedTitle] = useState('')
  const [sharedText, setSharedText] = useState('')
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [previewData, setPreviewData] = useState(null)
  const [extracting, setExtracting] = useState(false)

  // Extract URL from text if it contains a URL
  const extractUrlFromText = (text) => {
    if (!text) return ''
    
    // Try to find URL in text using regex
    // Updated regex to handle:
    // - Standard URLs (http://, https://)
    // - LinkedIn URLs with special characters and encoding
    // - URLs with query parameters and fragments
    // - URLs at end of text (no trailing space)
    const urlRegex = /(https?:\/\/[^\s\)]+)/g
    const matches = text.match(urlRegex)
    
    if (matches && matches.length > 0) {
      // Return the first URL found, but clean it up
      let url = matches[0]
      
      // Remove trailing punctuation that might have been captured
      url = url.replace(/[.,;:!?]+$/, '')
      
      // Remove closing parentheses if URL was in parentheses
      if (url.endsWith(')') && !url.includes('(')) {
        url = url.slice(0, -1)
      }
      
      return url
    }
    
    // Also check for LinkedIn shortened links (lnkd.in)
    const linkedInShortRegex = /(https?:\/\/lnkd\.in\/[^\s\)]+)/g
    const linkedInMatches = text.match(linkedInShortRegex)
    if (linkedInMatches && linkedInMatches.length > 0) {
      return linkedInMatches[0].replace(/[.,;:!?)]+$/, '')
    }
    
    return ''
  }

  // Extract shared data from URL parameters
  useEffect(() => {
    let url = searchParams.get('url') || ''
    const title = searchParams.get('title') || ''
    const text = searchParams.get('text') || ''

    // Debug: Log what we're receiving (only in dev)
    if (import.meta.env.DEV) {
      console.log('ShareHandler - Received params:', { url, title, text })
    }

    // If no URL in url parameter, try to extract from text
    // This handles cases where LinkedIn sends URL in text field
    if (!url && text) {
      const extractedUrl = extractUrlFromText(text)
      if (extractedUrl) {
        url = extractedUrl
        if (import.meta.env.DEV) {
          console.log('ShareHandler - Extracted URL from text:', url)
        }
      }
    }

    // If still no URL, check if text itself is a URL
    if (!url && text && (text.startsWith('http://') || text.startsWith('https://'))) {
      url = text.trim()
      // Remove trailing punctuation
      url = url.replace(/[.,;:!?)]+$/, '')
    }

    // Additional check: Sometimes LinkedIn sends the URL as the title
    if (!url && title && (title.startsWith('http://') || title.startsWith('https://'))) {
      url = title.trim().replace(/[.,;:!?)]+$/, '')
    }

    // Final check: Try to extract from title if it contains a URL
    if (!url && title) {
      const extractedFromTitle = extractUrlFromText(title)
      if (extractedFromTitle) {
        url = extractedFromTitle
      }
    }

    setSharedUrl(url)
    setSharedTitle(title)
    setSharedText(text)

    // Set basic preview immediately
    if (url) {
      setPreviewData({
        title: title || 'Untitled',
        description: text || '',
        url: url,
        quality_score: 0
      })
    } else if (import.meta.env.DEV) {
      console.warn('ShareHandler - No URL found in any parameter:', { url, title, text })
    }
  }, [searchParams])

  // Extract detailed preview once authenticated
  useEffect(() => {
    if (isAuthenticated && sharedUrl && !extracting) {
      extractPreview(sharedUrl)
    }
  }, [isAuthenticated, sharedUrl])

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login?redirect=/share' + (sharedUrl ? `?url=${encodeURIComponent(sharedUrl)}` : ''))
    }
  }, [isAuthenticated, authLoading, navigate, sharedUrl])

  const extractPreview = async (url) => {
    if (!url || !isAuthenticated) return

    setExtracting(true)
    setError('')

    try {
      // Try to extract content preview from the URL
      const response = await api.post('/api/bookmarks/extract-url', { url })
      
      if (response.data.success) {
        setPreviewData({
          title: response.data.title || sharedTitle || 'Untitled',
          description: response.data.description || sharedText || '',
          url: url,
          quality_score: response.data.quality_score || 0
        })
      } else {
        // Fallback to basic preview
        setPreviewData({
          title: sharedTitle || 'Untitled',
          description: sharedText || '',
          url: url,
          quality_score: 0
        })
      }
    } catch (err) {
      console.error('Preview extraction failed:', err)
      // Fallback to basic preview
      setPreviewData({
        title: sharedTitle || 'Untitled',
        description: sharedText || '',
        url: url,
        quality_score: 0
      })
    } finally {
      setExtracting(false)
    }
  }

  const handleSave = async () => {
    if (!sharedUrl) {
      setError('No URL provided to save')
      return
    }

    if (!isAuthenticated) {
      navigate('/login?redirect=/share?url=' + encodeURIComponent(sharedUrl))
      return
    }

    setSaving(true)
    setError('')

    try {
      const bookmarkData = {
        url: sharedUrl,
        title: previewData?.title || sharedTitle || '',
        description: previewData?.description || sharedText || ''
      }

      const response = await api.post('/api/bookmarks', bookmarkData)

      if (response.data) {
        setSuccess(true)
        // Redirect to bookmarks page after 2 seconds
        setTimeout(() => {
          navigate('/bookmarks')
        }, 2000)
      }
    } catch (err) {
      console.error('Save failed:', err)
      setError(err.response?.data?.message || err.message || 'Failed to save bookmark. Please try again.')
      setSaving(false)
    }
  }

  const handleCancel = () => {
    navigate('/dashboard')
  }

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0F0F1E]">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  // Show error if no URL provided
  if (!sharedUrl && !authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0F0F1E] p-4">
        <div className="max-w-md w-full bg-gradient-to-br from-[#1a1a2e] to-[#252540] rounded-2xl p-8 border border-cyan-500/20">
          <div className="text-center">
            <XCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
            <h1 className="text-2xl font-bold text-white mb-2">No Content to Share</h1>
            <p className="text-gray-400 mb-6">
              No URL was provided. Please share a link from another app.
            </p>
            <Button onClick={handleCancel} variant="primary">
              Go to Dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F0F1E] p-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-gradient-to-br from-[#1a1a2e] to-[#252540] rounded-2xl p-6 md:p-8 border border-cyan-500/20 shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-cyan-500/20 rounded-lg">
              <Share2 className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Share to Fuze</h1>
              <p className="text-gray-400 text-sm">Save this content to your bookmarks</p>
            </div>
          </div>

          {/* Success Message */}
          {success && (
            <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
              <div>
                <p className="text-green-400 font-medium">Bookmark saved successfully!</p>
                <p className="text-green-400/70 text-sm">Redirecting to bookmarks...</p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3">
              <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-red-400">{error}</p>
            </div>
          )}

          {/* Preview Card */}
          {previewData && (
            <div className="mb-6 p-5 bg-[#0F0F1E] rounded-xl border border-gray-700">
              {extracting ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-cyan-400 mr-3" />
                  <span className="text-gray-400">Extracting content...</span>
                </div>
              ) : (
                <>
                  <div className="flex items-start gap-3 mb-4">
                    <Globe className="w-5 h-5 text-cyan-400 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-white mb-2 line-clamp-2">
                        {previewData.title}
                      </h3>
                      {previewData.description && (
                        <p className="text-gray-400 text-sm line-clamp-3 mb-3">
                          {previewData.description}
                        </p>
                      )}
                      <a
                        href={previewData.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1"
                      >
                        <ExternalLink className="w-4 h-4" />
                        <span className="truncate">{previewData.url}</span>
                      </a>
                    </div>
                  </div>
                  
                  {previewData.quality_score > 0 && (
                    <div className="text-xs text-gray-500">
                      Content quality: {Math.round(previewData.quality_score * 10)}/10
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* URL Display (if no preview) */}
          {!previewData && !extracting && sharedUrl && (
            <div className="mb-6 p-5 bg-[#0F0F1E] rounded-xl border border-gray-700">
              <div className="flex items-start gap-3">
                <Globe className="w-5 h-5 text-cyan-400 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-400 text-sm mb-2">URL to save:</p>
                  <a
                    href={sharedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-400 hover:text-cyan-300 text-sm break-all flex items-center gap-1"
                  >
                    <ExternalLink className="w-4 h-4 flex-shrink-0" />
                    <span className="break-all">{sharedUrl}</span>
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {!success && (
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                onClick={handleSave}
                disabled={saving || extracting || !sharedUrl}
                variant="primary"
                className="flex-1"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Saving...
                  </>
                ) : (
                  'Save Bookmark'
                )}
              </Button>
              <Button
                onClick={handleCancel}
                disabled={saving}
                variant="secondary"
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p className="text-blue-400 text-sm text-center">
            <strong>Tip:</strong> You can share links from any app to Fuze. The content will be automatically extracted and saved to your bookmarks.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ShareHandler

