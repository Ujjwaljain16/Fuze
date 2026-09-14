import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        if (sessionStorage.getItem('oauth_exchange_in_progress') === '1') {
          return
        }

        // Only read tokens/errors from the URL fragment (#), never the query
        // string (?) -- a query-string token would be sent to the server in
        // the request line and leak via Referer headers to any third-party
        // resource loaded on this page before it's stripped.
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
        const access_token = hashParams.get('access_token')
        const oauthError = hashParams.get('error_description')

        // Strip the fragment from the URL/history immediately, before any
        // branching (including the error paths below) -- avoids leaving a
        // token or error detail sitting in browser history either way.
        if (window.location.hash || window.location.search) {
          window.history.replaceState({}, document.title, '/oauth/callback')
        }

        if (oauthError) {
          setError(`OAuth error: ${oauthError}`)
          return
        }

        if (!access_token) {
          setError('No access token found in redirect URL. Please try Google sign-in again.')
          return
        }

        // Send the Supabase access token to our backend to exchange for local session
        const res = await api.post('/api/auth/supabase-oauth', { access_token })
        
        const { user, access_token: backendToken } = res.data || {}

        const fullUser = {
          ...(user || {}),
          ...(backendToken ? { token: backendToken, access_token: backendToken } : {})
        }

        // Set user profile in localStorage (with access token attached for Authorization header)
        if (user) {
          localStorage.setItem('user', JSON.stringify(fullUser))
        }

        // Fetch user profile to ensure user data is loaded before navigation
        try {
          await api.get('/api/profile')
        } catch {
          // Continue anyway - AuthContext will handle it
        }

        // Dispatch custom event to notify app of login (and hydrate AuthContext immediately)
        window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: { user: fullUser } }))

        // Small delay to let event propagate and AuthContext to update
        await new Promise(resolve => setTimeout(resolve, 300))

        // Navigate using router first
        navigate('/dashboard', { replace: true })

        // Mobile/PWA fallback: if SPA navigation doesn't take effect, force location redirect.
        setTimeout(() => {
          if (window.location.pathname === '/oauth/callback') {
            window.location.replace('/dashboard')
          }
        }, 700)
      } catch {
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
