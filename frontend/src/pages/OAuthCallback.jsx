import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  console.log('[OAuth] OAuthCallback component RENDERED at URL:', window.location.href)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        if (sessionStorage.getItem('oauth_exchange_in_progress') === '1') {
          return
        }

        console.log('[OAuth] Callback initiated, URL:', window.location.href)
        
        // Supabase may return tokens in hash or query params depending on environment/flow.
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
        const queryParams = new URLSearchParams(window.location.search)
        const access_token = hashParams.get('access_token') || queryParams.get('access_token')
        const oauthError = hashParams.get('error_description') || queryParams.get('error_description')

        console.log('[OAuth] Token source - hash:', !!hashParams.get('access_token'), 'query:', !!queryParams.get('access_token'))
        console.log('[OAuth] Token extracted:', !!access_token, 'Error found:', !!oauthError)

        if (oauthError) {
          console.error('[OAuth] OAuth error detected:', oauthError)
          setError(`OAuth error: ${oauthError}`)
          return
        }

        if (!access_token) {
          console.error('[OAuth] No access token found in URL')
          setError('No access token found in redirect URL. Please try Google sign-in again.')
          return
        }

        console.log('[OAuth] Token found, token length:', access_token.length)

        // Strip token fragment from URL as early as possible to avoid PWA/history quirks on Android.
        if (window.location.hash || window.location.search) {
          console.log('[OAuth] Clearing URL hash/query')
          window.history.replaceState({}, document.title, '/oauth/callback')
        }

        // Send the Supabase access token to our backend to exchange for local session
        console.log('[OAuth] Calling /api/auth/supabase-oauth...')
        const res = await api.post('/api/auth/supabase-oauth', { access_token })
        console.log('[OAuth] API response received, status:', res.status)
        
        const { access_token: localAccessToken, user } = res.data

        if (!localAccessToken) {
          console.error('[OAuth] No local token returned from backend')
          setError('Authentication failed: no token returned')
          return
        }

        console.log('[OAuth] Local token received, setting localStorage...')

        // Set local token and redirect
        localStorage.setItem('token', localAccessToken)
        if (user) {
          console.log('[OAuth] Setting user in localStorage:', user.id)
          localStorage.setItem('user', JSON.stringify(user))
        }
        // Update axios default header for immediate use
        api.defaults.headers.common['Authorization'] = `Bearer ${localAccessToken}`

        // Fetch user profile to ensure user data is loaded before navigation
        try {
          console.log('[OAuth] Fetching profile...')
          await api.get('/api/profile')
          console.log('[OAuth] Profile fetched successfully')
        } catch (profileErr) {
          console.error('[OAuth] Failed to fetch profile:', profileErr)
          // Continue anyway - AuthContext will handle it
        }

        // Dispatch custom event to notify app of login (and hydrate AuthContext immediately)
        console.log('[OAuth] Dispatching userLoggedIn event...')
        window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: { user } }))

        // Small delay to let event propagate and AuthContext to update
        await new Promise(resolve => setTimeout(resolve, 300))

        // Navigate using router first
        console.log('[OAuth] Navigating to /dashboard...')
        navigate('/dashboard', { replace: true })

        // Mobile/PWA fallback: if SPA navigation doesn't take effect, force location redirect.
        setTimeout(() => {
          if (window.location.pathname === '/oauth/callback') {
            console.log('[OAuth] Fallback: forcing location.replace to /dashboard')
            window.location.replace('/dashboard')
          }
        }, 700)
      } catch (err) {
        console.error('[OAuth] Fatal error in callback:', err.message)
        console.error('[OAuth] Error details:', {
          status: err.response?.status,
          data: err.response?.data,
          stack: err.stack
        })
        setError('OAuth sign-in failed. Please try again.')
      }
    }

    handleCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center p-8">
        {error ? (
          <div>
            <h2 className="text-xl font-semibold mb-2">Authentication Error</h2>
            <p className="text-sm text-red-400">{error}</p>
            <div className="mt-4">
              <a href="/login" className="text-cyan-400">Return to login</a>
            </div>
          </div>
        ) : (
          <div>
            <h2 className="text-xl font-semibold mb-2">Signing you in...</h2>
            <p className="text-sm text-gray-400">Completing authentication, you will be redirected shortly.</p>
          </div>
        )}
      </div>
    </div>
  )
}
