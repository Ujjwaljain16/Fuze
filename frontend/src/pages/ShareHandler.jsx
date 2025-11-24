import { useState, useEffect, useRef } from 'react'
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
  const extractedUrlRef = useRef(null) // Track which URL we've already extracted
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsSmallMobile(window.innerWidth <= 480)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Extract URL from text if it contains a URL
  const extractUrlFromText = (text) => {
    if (!text) return ''
    
    // Try to find URL in text using regex
    // Updated regex to handle:
    // - Standard URLs (http://, https://)
    // - LinkedIn URLs with special characters (urn:li:activity) and encoding
    // - URLs with query parameters, fragments, and encoded characters (%3A, %28, etc.)
    // - URLs at end of text (no trailing space)
    // - URLs with colons in path (like urn:li:activity)
    // Match until we hit whitespace, closing paren without opening, or end of string
    const urlRegex = /(https?:\/\/[^\s)]+(?:\?[^\s)]*)?(?:&[^\s)]*)*)/g
    const matches = text.match(urlRegex)
    
    if (matches && matches.length > 0) {
      // Return the first URL found, but clean it up
      let url = matches[0]
      
      // For LinkedIn feed/update URLs, they can be very long with encoded params
      // Make sure we capture the full URL including all query parameters
      if (url.includes('linkedin.com') && url.includes('urn:li:activity')) {
        // For LinkedIn activity URLs, try to get the complete URL
        // They can have very long encoded query strings
        const linkedInFullMatch = text.match(/https?:\/\/[^\s)]+urn:li:activity[^\s)]*/)
        if (linkedInFullMatch && linkedInFullMatch[0].length > url.length) {
          url = linkedInFullMatch[0]
        }
      }
      
      // Remove trailing punctuation that might have been captured (but keep URL-encoded chars)
      // Only remove if it's actual punctuation, not part of the URL encoding
      url = url.replace(/[.,;!?]+$/, '')
      
      // Remove closing parentheses if URL was in parentheses (but not if it's part of encoding like %29)
      if (url.endsWith(')') && !url.includes('(') && !url.includes('%29')) {
        url = url.slice(0, -1)
      }
      
      return url
    }
    
    // Also check for LinkedIn shortened links (lnkd.in)
    const linkedInShortRegex = /(https?:\/\/lnkd\.in\/[^\s)]+)/g
    const linkedInMatches = text.match(linkedInShortRegex)
    if (linkedInMatches && linkedInMatches.length > 0) {
      return linkedInMatches[0].replace(/[.,;:!?)]+$/, '')
    }
    
    // Special handling for LinkedIn feed/update URLs that might be split across lines or have special formatting
    const linkedInFeedRegex = /https?:\/\/www\.linkedin\.com\/feed\/update\/[^\s)]+/
    const linkedInFeedMatch = text.match(linkedInFeedRegex)
    if (linkedInFeedMatch && linkedInFeedMatch.length > 0) {
      let feedUrl = linkedInFeedMatch[0]
      // Try to extend the match to include the full query string
      const extendedMatch = text.match(new RegExp(feedUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[^\\s)]*'))
      if (extendedMatch) {
        feedUrl = extendedMatch[0].replace(/[.,;!?)]+$/, '')
      }
      return feedUrl
    }
    
    return ''
  }

  // Extract shared data from URL parameters
  useEffect(() => {
    let url = searchParams.get('url') || ''
    const title = searchParams.get('title') || ''
    const text = searchParams.get('text') || ''

    // Debug: Log what we're receiving (only in dev)
    // Logging removed for production

    // If no URL in url parameter, try to extract from text
    // This handles cases where LinkedIn sends URL in text field
    if (!url && text) {
      const extractedUrl = extractUrlFromText(text)
      if (extractedUrl) {
        url = extractedUrl
      }
    }

    // If still no URL, check if text itself is a URL
    if (!url && text && (text.startsWith('http://') || text.startsWith('https://'))) {
      url = text.trim()
      // For LinkedIn feed URLs, they can be very long - don't truncate
      // Only remove trailing punctuation if it's clearly not part of the URL
      if (!url.includes('urn:li:activity') && !url.includes('%3A')) {
        url = url.replace(/[.,;:!?)]+$/, '')
      }
    }

    // Additional check: Sometimes LinkedIn sends the URL as the title
    if (!url && title && (title.startsWith('http://') || title.startsWith('https://'))) {
      url = title.trim()
      if (!url.includes('urn:li:activity') && !url.includes('%3A')) {
        url = url.replace(/[.,;:!?)]+$/, '')
      }
    }

    // Final check: Try to extract from title if it contains a URL
    if (!url && title) {
      const extractedFromTitle = extractUrlFromText(title)
      if (extractedFromTitle) {
        url = extractedFromTitle
      }
    }

    // Special handling: Check if any parameter contains a LinkedIn feed URL pattern
    // LinkedIn saved posts sometimes send the URL in unexpected places
    if (!url) {
      const allParams = [url, title, text].join(' ')
      const linkedInPattern = /https?:\/\/www\.linkedin\.com\/feed\/update\/urn:li:activity[^\s)]+/
      const linkedInMatch = allParams.match(linkedInPattern)
      if (linkedInMatch) {
        url = linkedInMatch[0]
        // Try to get the full URL including all query parameters
        const fullMatch = allParams.match(new RegExp(linkedInMatch[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[^\\s)]*'))
        if (fullMatch && fullMatch[0].length > url.length) {
          url = fullMatch[0]
        }
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
      console.warn('ShareHandler - No URL found in any parameter:', { 
        url, 
        title, 
        text,
        'Try extracting manually': extractUrlFromText(text || title || '')
      })
    }
  }, [searchParams])

  // Extract detailed preview once authenticated
  useEffect(() => {
    // Only extract if:
    // 1. User is authenticated
    // 2. We have a URL
    // 3. We're not currently extracting
    // 4. We haven't already extracted this URL
    if (isAuthenticated && sharedUrl && !extracting && extractedUrlRef.current !== sharedUrl) {
      extractedUrlRef.current = sharedUrl // Mark this URL as being extracted
      extractPreview(sharedUrl)
    }
    // Note: We intentionally don't include extracting in deps to prevent re-triggering
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, sharedUrl])

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login?redirect=/share' + (sharedUrl ? `?url=${encodeURIComponent(sharedUrl)}` : ''))
    }
  }, [isAuthenticated, authLoading, navigate, sharedUrl])

  const extractPreview = async (url) => {
    if (!url || !isAuthenticated) {
      // Reset ref if extraction can't proceed
      if (extractedUrlRef.current === url) {
        extractedUrlRef.current = null
      }
      return
    }

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
      // Keep the ref set so we don't extract again for the same URL
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

      // Use quick-save endpoint for immediate response
      const response = await api.post('/api/bookmarks/quick-save', bookmarkData)

      if (response.data) {
        setSuccess(true)
        
        // Try to return user to previous app (where they shared from)
        // This works for PWA share targets
        setTimeout(() => {
          // Try to close the window (works if opened as share target)
          if (window.history.length > 1) {
            // If we have history, go back
            window.history.back()
          } else {
            // Otherwise, try to close (may not work if not opened by share)
            window.close()
            // Fallback: navigate to dashboard if close doesn't work
            setTimeout(() => {
              navigate('/dashboard')
            }, 500)
          }
        }, 1000) // Show success message for 1 second before returning
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
        <Loader2 className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} animate-spin text-cyan-400`} />
      </div>
    )
  }

  // Show error if no URL provided
  if (!sharedUrl && !authLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center bg-[#0F0F1E] ${isMobile ? 'p-4' : 'p-4'}`}>
        <div className={`max-w-md w-full bg-gradient-to-br from-[#1a1a2e] to-[#252540] rounded-2xl ${isMobile ? 'p-6' : 'p-8'} border border-cyan-500/20`}>
          <div className="text-center">
            <XCircle className={`${isMobile ? 'w-12 h-12' : 'w-16 h-16'} mx-auto ${isMobile ? 'mb-3' : 'mb-4'} text-red-400`} />
            <h1 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-1.5' : 'mb-2'}`}>No Content to Share</h1>
            <p className={`text-gray-400 ${isMobile ? 'mb-4 text-sm' : 'mb-6'}`}>
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
    <div className={`min-h-screen bg-[#0F0F1E] ${isMobile ? 'p-3' : 'p-4'}`}>
      <div className="max-w-2xl mx-auto">
        <div className={`bg-gradient-to-br from-[#1a1a2e] to-[#252540] rounded-2xl ${isMobile ? 'p-4' : 'p-6 md:p-8'} border border-cyan-500/20 shadow-2xl`}>
          {/* Header */}
          <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'gap-3'} ${isMobile ? 'mb-4' : 'mb-6'}`}>
            <div className={`${isMobile ? 'p-2' : 'p-3'} bg-cyan-500/20 rounded-lg`}>
              <Share2 className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
            </div>
            <div>
              <h1 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white`}>Share to Fuze</h1>
              <p className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>Save this content to your bookmarks</p>
            </div>
          </div>

          {/* Success Message */}
          {success && (
            <div className={`${isMobile ? 'mb-4 p-3' : 'mb-6 p-4'} bg-green-500/10 border border-green-500/20 rounded-lg flex items-center ${isSmallMobile ? 'gap-2' : 'gap-3'}`}>
              <CheckCircle2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-green-400 flex-shrink-0`} />
              <div>
                <p className={`text-green-400 font-medium ${isMobile ? 'text-sm' : ''}`}>Bookmark saved successfully!</p>
                <p className={`text-green-400/70 ${isMobile ? 'text-xs' : 'text-sm'}`}>Processing content in background. Returning to previous app...</p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className={`${isMobile ? 'mb-4 p-3' : 'mb-6 p-4'} bg-red-500/10 border border-red-500/20 rounded-lg flex items-center ${isSmallMobile ? 'gap-2' : 'gap-3'}`}>
              <XCircle className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-red-400 flex-shrink-0`} />
              <p className={`text-red-400 ${isMobile ? 'text-sm' : ''}`}>{error}</p>
            </div>
          )}

          {/* Preview Card */}
          {previewData && (
            <div className={`${isMobile ? 'mb-4 p-3' : 'mb-6 p-5'} bg-[#0F0F1E] rounded-xl border border-gray-700`}>
              {extracting ? (
                <div className={`flex items-center justify-center ${isMobile ? 'py-6' : 'py-8'}`}>
                  <Loader2 className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} animate-spin text-cyan-400 ${isMobile ? 'mr-2' : 'mr-3'}`} />
                  <span className={`text-gray-400 ${isMobile ? 'text-sm' : ''}`}>Extracting content...</span>
                </div>
              ) : (
                <>
                  <div className={`flex items-start ${isSmallMobile ? 'gap-2' : 'gap-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
                    <Globe className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 mt-1 flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white ${isMobile ? 'mb-1.5' : 'mb-2'} line-clamp-2`}>
                        {previewData.title}
                      </h3>
                      {previewData.description && (
                        <p className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'} line-clamp-3 ${isMobile ? 'mb-2' : 'mb-3'}`}>
                          {previewData.description}
                        </p>
                      )}
                      <a
                        href={previewData.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`text-cyan-400 hover:text-cyan-300 ${isMobile ? 'text-xs' : 'text-sm'} flex items-center ${isSmallMobile ? 'gap-0.5' : 'gap-1'}`}
                      >
                        <ExternalLink className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} flex-shrink-0`} />
                        <span className="truncate">{previewData.url}</span>
                      </a>
                    </div>
                  </div>
                  
                  {previewData.quality_score > 0 && (
                    <div className={`${isMobile ? 'text-xs' : 'text-xs'} text-gray-500`}>
                      Content quality: {Math.round(previewData.quality_score * 10)}/10
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* URL Display (if no preview) */}
          {!previewData && !extracting && sharedUrl && (
            <div className={`${isMobile ? 'mb-4 p-3' : 'mb-6 p-5'} bg-[#0F0F1E] rounded-xl border border-gray-700`}>
              <div className={`flex items-start ${isSmallMobile ? 'gap-2' : 'gap-3'}`}>
                <Globe className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 mt-1 flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-gray-400 ${isMobile ? 'text-xs mb-1.5' : 'text-sm mb-2'}`}>URL to save:</p>
                  <a
                    href={sharedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`text-cyan-400 hover:text-cyan-300 ${isMobile ? 'text-xs' : 'text-sm'} break-all flex items-center ${isSmallMobile ? 'gap-0.5' : 'gap-1'}`}
                  >
                    <ExternalLink className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} flex-shrink-0`} />
                    <span className="break-all">{sharedUrl}</span>
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {!success && (
            <div className={`flex ${isSmallMobile ? 'flex-col' : 'flex-col sm:flex-row'} ${isMobile ? 'gap-2' : 'gap-3'}`}>
              <Button
                onClick={handleSave}
                disabled={saving || extracting || !sharedUrl}
                variant="primary"
                className="flex-1"
              >
                {saving ? (
                  <>
                    <Loader2 className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} animate-spin ${isMobile ? 'mr-1.5' : 'mr-2'}`} />
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
        <div className={`${isMobile ? 'mt-4 p-3' : 'mt-6 p-4'} bg-cyan-500/10 border border-cyan-500/20 rounded-lg`}>
          <p className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'} text-center`}>
            <strong>Tip:</strong> You can share links from any app to Fuze. The content will be automatically extracted and saved to your bookmarks.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ShareHandler

