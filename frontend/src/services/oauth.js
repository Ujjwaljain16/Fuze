import api from './api'

// Google sign-in goes through Supabase's implicit flow: Supabase redirects back with
// #access_token=... and we exchange that for our own session.
//
// A redirect is only accepted if this browser started it. Without that check anyone could
// send a victim a link carrying the attacker's token (…/#access_token=…) and silently sign
// the victim into the attacker's account, where whatever they save is visible to the attacker.
const PENDING_KEY = 'fuze_oauth_pending'
const PENDING_MAX_AGE_MS = 10 * 60 * 1000

export const OAUTH_MODES = { SIGN_IN: 'signin', LINK: 'link' }

export const startGoogleOAuth = (mode = OAUTH_MODES.SIGN_IN) => {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || window.__env?.VITE_SUPABASE_URL
  if (!supabaseUrl) {
    throw new Error('Supabase is not configured for OAuth')
  }
  // localStorage (not sessionStorage): mobile/PWA flows can come back in another tab.
  localStorage.setItem(PENDING_KEY, JSON.stringify({ mode, at: Date.now() }))
  const redirectTo = encodeURIComponent(window.location.origin + '/oauth/callback')
  window.location.href = `${supabaseUrl.replace(/\/$/, '')}/auth/v1/authorize?provider=google&redirect_to=${redirectTo}`
}

const takePending = () => {
  let pending = null
  try {
    pending = JSON.parse(localStorage.getItem(PENDING_KEY) || 'null')
  } catch {
    pending = null
  }
  localStorage.removeItem(PENDING_KEY)
  if (!pending || typeof pending.at !== 'number' || Date.now() - pending.at > PENDING_MAX_AGE_MS) {
    return null
  }
  return pending
}

// Tokens are only read from the fragment: a query-string token would be sent to servers
// in the request line and leak through Referer headers.
export const readOAuthRedirect = () => {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  return { accessToken: params.get('access_token'), error: params.get('error_description') }
}

export const hasOAuthRedirect = () => {
  const { accessToken, error } = readOAuthRedirect()
  return Boolean(accessToken || error)
}

/**
 * Finish a Google redirect. Resolves to one of:
 *   { status: 'signed_in', user }           new session stored
 *   { status: 'linked' }                    Google connected to the signed-in account
 *   { status: 'error', code, message }      nothing changed
 */
export const completeOAuth = async ({ accessToken, error }) => {
  const pending = takePending()
  if (error) {
    return { status: 'error', code: 'provider_error', message: `Google sign-in failed: ${error}` }
  }
  if (!accessToken) {
    return { status: 'error', code: 'missing_token', message: 'No access token found. Please try Google sign-in again.' }
  }
  if (!pending) {
    return {
      status: 'error',
      code: 'unexpected_redirect',
      message: 'This sign-in was not started from this browser. Use "Continue with Google" to sign in.',
    }
  }

  try {
    if (pending.mode === OAUTH_MODES.LINK) {
      await api.post('/api/auth/link-oauth', { access_token: accessToken })
      return { status: 'linked' }
    }
    const res = await api.post('/api/auth/supabase-oauth', { access_token: accessToken })
    const { user, access_token: token, refresh_token: refreshToken } = res.data || {}
    const fullUser = {
      ...(user || {}),
      ...(token ? { token, access_token: token } : {}),
      ...(refreshToken ? { refresh_token: refreshToken } : {}),
    }
    localStorage.setItem('user', JSON.stringify(fullUser))
    window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: { user: fullUser } }))
    return { status: 'signed_in', user: fullUser }
  } catch (err) {
    const data = err.response?.data || {}
    return {
      status: 'error',
      code: data.error || 'oauth_failed',
      message: data.message || 'Google sign-in failed. Please try again.',
    }
  }
}
