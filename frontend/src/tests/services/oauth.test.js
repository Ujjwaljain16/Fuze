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


describe('Google OAuth remembers where the user was going', () => {
  const pending = () => JSON.parse(localStorage.getItem('fuze_oauth_pending'))

  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co')
    // startGoogleOAuth navigates away; keep the test page where it is
    Object.defineProperty(window, 'location', { value: { origin: 'http://localhost', href: 'http://localhost/login' }, writable: true })
  })

  it('stores a same-app destination with the pending sign-in', async () => {
    const { startGoogleOAuth } = await import('../../services/oauth')
    startGoogleOAuth(OAUTH_MODES.SIGN_IN, '/share?url=https%3A%2F%2Fe.com&title=T&text=body')
    expect(pending().redirect).toBe('/share?url=https%3A%2F%2Fe.com&title=T&text=body')
  })

  it('never stores an off-site or malformed destination', async () => {
    const { startGoogleOAuth } = await import('../../services/oauth')
    for (const bad of ['https://evil.tld/x', '//evil.tld', '/\\evil.tld', 'javascript:alert(1)', '', null, undefined]) {
      startGoogleOAuth(OAUTH_MODES.SIGN_IN, bad)
      expect(pending().redirect, String(bad)).toBeUndefined()
    }
  })

  it('hands the destination back after a successful sign-in, and checks it again', async () => {
    localStorage.setItem('fuze_oauth_pending', JSON.stringify({ mode: OAUTH_MODES.SIGN_IN, at: Date.now(), redirect: '/share?url=x' }))
    vi.spyOn(api, 'post').mockResolvedValue({ data: { user: { id: 1 }, access_token: 'a', refresh_token: 'r' } })
    expect(await completeOAuth({ accessToken: 'supa' })).toMatchObject({ status: 'signed_in', redirect: '/share?url=x' })

    // something tampered with storage: an off-site value is dropped
    localStorage.setItem('fuze_oauth_pending', JSON.stringify({ mode: OAUTH_MODES.SIGN_IN, at: Date.now(), redirect: 'https://evil.tld' }))
    expect((await completeOAuth({ accessToken: 'supa' })).redirect).toBeNull()
  })

  it('has no destination when there was none', async () => {
    markPending()
    vi.spyOn(api, 'post').mockResolvedValue({ data: { user: { id: 1 } } })
    expect((await completeOAuth({ accessToken: 'supa' })).redirect).toBeNull()
  })
})
