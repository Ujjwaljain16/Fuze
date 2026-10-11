import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { completeOAuth, readOAuthRedirect } from '../services/oauth'

const EXCHANGE_LOCK_KEY = 'oauth_exchange_in_progress'

export default function OAuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)
  const [errorCode, setErrorCode] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      if (sessionStorage.getItem(EXCHANGE_LOCK_KEY) === '1') {
        return
      }
      sessionStorage.setItem(EXCHANGE_LOCK_KEY, '1')

      const redirect = readOAuthRedirect()
      // Strip the token from the address bar and history before doing anything else.
      if (window.location.hash || window.location.search) {
        window.history.replaceState({}, document.title, '/oauth/callback')
      }

      try {
        const result = await completeOAuth(redirect)
        if (result.status === 'linked') {
          navigate('/profile?google=connected', { replace: true })
          return
        }
        if (result.status === 'error') {
          setErrorCode(result.code)
          setError(result.message)
          return
        }

        navigate('/dashboard', { replace: true })
        // Mobile/PWA fallback: if SPA navigation doesn't take effect, force location redirect.
        setTimeout(() => {
          if (window.location.pathname === '/oauth/callback') {
            window.location.replace('/dashboard')
          }
        }, 700)
      } finally {
        sessionStorage.removeItem(EXCHANGE_LOCK_KEY)
      }
    }

    handleCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center p-8 max-w-md">
        {error ? (
          <div>
            <h2 className="text-xl font-semibold mb-2">
              {errorCode === 'account_link_required' ? 'You already have an account' : 'Authentication Error'}
            </h2>
            <p className="text-sm text-red-400">{error}</p>
            <div className="mt-4">
              <a href="/login" className="text-cyan-400">
                {errorCode === 'account_link_required' ? 'Sign in with your password' : 'Return to login'}
              </a>
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
