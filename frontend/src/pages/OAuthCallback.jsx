import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Supabase may return tokens in hash or query params depending on environment/flow.
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
        const queryParams = new URLSearchParams(window.location.search)
        const access_token = hashParams.get('access_token') || queryParams.get('access_token')
        const oauthError = hashParams.get('error_description') || queryParams.get('error_description')

        if (oauthError) {
          setError(`OAuth error: ${oauthError}`)
          return
        }

        if (!access_token) {
          setError('No access token found in redirect URL. Please try Google sign-in again.')
          return
        }

        // Strip token fragment from URL as early as possible to avoid PWA/history quirks on Android.
        if (window.location.hash || window.location.search) {
          window.history.replaceState({}, document.title, '/oauth/callback')
        }

        // Send the Supabase access token to our backend to exchange for local session
        const res = await api.post('/api/auth/supabase-oauth', { access_token })
        const { access_token: localAccessToken, user } = res.data

        if (!localAccessToken) {
          setError('Authentication failed: no token returned')
          return
        }

        // Set local token and redirect
        localStorage.setItem('token', localAccessToken)
        if (user) {
          localStorage.setItem('user', JSON.stringify(user))
        }
        // Update axios default header for immediate use
        api.defaults.headers.common['Authorization'] = `Bearer ${localAccessToken}`

        // Fetch user profile to ensure user data is loaded before navigation
        try {
          await api.get('/api/profile')
          console.log('Profile fetched successfully after OAuth')
        } catch (profileErr) {
          console.error('Failed to fetch profile after OAuth:', profileErr)
          // Continue anyway - AuthContext will handle it
        }

        // Dispatch custom event to notify app of login (and hydrate AuthContext immediately)
        window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: { user } }))

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
      } catch (err) {
        console.error('OAuth callback error', err)
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
