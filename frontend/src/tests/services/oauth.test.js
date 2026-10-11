import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '../../services/api'
import { completeOAuth, OAUTH_MODES } from '../../services/oauth'

const markPending = (mode = OAUTH_MODES.SIGN_IN, ageMs = 0) =>
  localStorage.setItem('fuze_oauth_pending', JSON.stringify({ mode, at: Date.now() - ageMs }))

describe('Google OAuth completion', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('refuses a token this browser did not ask for (login CSRF)', async () => {
    const post = vi.spyOn(api, 'post')
    const result = await completeOAuth({ accessToken: 'attacker-token' })
    expect(result).toMatchObject({ status: 'error', code: 'unexpected_redirect' })
    expect(post).not.toHaveBeenCalled()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('refuses a stale sign-in attempt', async () => {
    markPending(OAUTH_MODES.SIGN_IN, 11 * 60 * 1000)
    const post = vi.spyOn(api, 'post')
    expect((await completeOAuth({ accessToken: 't' })).status).toBe('error')
    expect(post).not.toHaveBeenCalled()
  })

  it('exchanges the token and stores the session it started', async () => {
    markPending()
    vi.spyOn(api, 'post').mockResolvedValue({
      data: { user: { id: 7, email: 'a@b.c' }, access_token: 'a1', refresh_token: 'r1' },
    })
    const result = await completeOAuth({ accessToken: 'supa' })
    expect(api.post).toHaveBeenCalledWith('/api/auth/supabase-oauth', { access_token: 'supa' })
    expect(result.status).toBe('signed_in')
    expect(JSON.parse(localStorage.getItem('user'))).toMatchObject({ id: 7, token: 'a1', refresh_token: 'r1' })
    expect(localStorage.getItem('fuze_oauth_pending')).toBeNull()
  })

  it('reports an existing password account instead of signing in', async () => {
    markPending()
    vi.spyOn(api, 'post').mockRejectedValue({
      response: { status: 409, data: { error: 'account_link_required', message: 'Sign in with your password' } },
    })
    const result = await completeOAuth({ accessToken: 'supa' })
    expect(result).toMatchObject({ status: 'error', code: 'account_link_required' })
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('links Google to the signed-in account in link mode', async () => {
    markPending(OAUTH_MODES.LINK)
    vi.spyOn(api, 'post').mockResolvedValue({ data: {} })
    const result = await completeOAuth({ accessToken: 'supa' })
    expect(api.post).toHaveBeenCalledWith('/api/auth/link-oauth', { access_token: 'supa' })
    expect(result.status).toBe('linked')
  })
})
