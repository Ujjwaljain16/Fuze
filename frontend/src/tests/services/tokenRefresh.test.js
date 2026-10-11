import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { refreshTokenIfNeeded } from '../../services/api'

const jwtExpiringIn = (seconds) => {
  const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds }))
  return `header.${payload}.signature`
}

describe('token refresh', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('does not refresh while the access token is still valid', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, token: jwtExpiringIn(3600), refresh_token: 'r1' }))
    const post = vi.spyOn(axios, 'post')
    await refreshTokenIfNeeded()
    expect(post).not.toHaveBeenCalled()
  })

  it('sends the refresh token (not the access token) and stores the rotated pair', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, token: jwtExpiringIn(30), refresh_token: 'r1' }))
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { access_token: 'a2', refresh_token: 'r2' } })

    await refreshTokenIfNeeded()

    expect(post).toHaveBeenCalledTimes(1)
    expect(post.mock.calls[0][0]).toMatch(/\/api\/auth\/refresh$/)
    expect(post.mock.calls[0][2].headers).toEqual({ Authorization: 'Bearer r1' })
    const stored = JSON.parse(localStorage.getItem('user'))
    expect(stored).toMatchObject({ id: 1, token: 'a2', access_token: 'a2', refresh_token: 'r2' })
  })

  it('falls back to the cookie when a session has no stored refresh token', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, token: jwtExpiringIn(0) }))
    const post = vi.spyOn(axios, 'post').mockResolvedValue({ data: { access_token: 'a2', refresh_token: 'r2' } })
    await refreshTokenIfNeeded()
    expect(post.mock.calls[0][2]).toMatchObject({ withCredentials: true, headers: {} })
  })
})
