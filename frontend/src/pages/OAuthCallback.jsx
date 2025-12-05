import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Supabase returns tokens in the URL hash fragment
        const hash = window.location.hash.substring(1) // remove leading '#'
        const params = new URLSearchParams(hash)
        const access_token = params.get('access_token')

        if (!access_token) {
          setError('No access token found in redirect URL')
          return
        }

        // Send the Supabase access token to our backend to exchange for local session
        const res = await api.post('/api/auth/supabase-oauth', { access_token })
        const { access_token: localAccessToken } = res.data

        if (!localAccessToken) {
          setError('Authentication failed: no token returned')
          return
        }

        // Set local token and redirect
        localStorage.setItem('token', localAccessToken)
        // Update axios default header for immediate use
        api.defaults.headers.common['Authorization'] = `Bearer ${localAccessToken}`

        // Fetch user profile to ensure user data is loaded before navigation
        await api.get('/api/profile')

        // Dispatch custom event to notify app of login (triggers API key check)
        window.dispatchEvent(new CustomEvent('userLoggedIn'))

        // Small delay to let event propagate and AuthContext to update
        await new Promise(resolve => setTimeout(resolve, 200))

        // Navigate to dashboard (user data is now loaded)
        navigate('/dashboard', { replace: true })
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
