/**
 * A share opened while signed out: the title and text, not only the link, must reach the login page, and the page
 * must not redirect before it has read what was shared.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router'

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: false, loading: false }),
}))
vi.mock('../../services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import ShareHandler from '../../pages/ShareHandler'
import { getSafeInternalRedirect } from '../../utils/urlSafety'

const LoginProbe = () => {
  const location = useLocation()
  return <div data-testid="login-search">{location.search}</div>
}

const openShare = (query) =>
  render(
    <MemoryRouter initialEntries={[`/share?${query}`]}>
      <Routes>
        <Route path="/share" element={<ShareHandler />} />
        <Route path="/login" element={<LoginProbe />} />
      </Routes>
    </MemoryRouter>
  )

const redirectOf = async () => {
  const search = (await screen.findByTestId('login-search')).textContent
  return new URLSearchParams(search).get('redirect')
}

describe('a share opened while signed out', () => {
  it('sends the title and text to the login page along with the link', async () => {
    const query = new URLSearchParams({
      url: 'https://lnkd.in/p/gemNZe47', title: 'Amazon OA SDE I Intern', text: 'Help needed with this problem\nthanks',
    }).toString()
    openShare(query)

    const redirect = await redirectOf()
    const shared = new URL(redirect, 'http://localhost').searchParams
    expect(shared.get('url')).toBe('https://lnkd.in/p/gemNZe47')
    expect(shared.get('title')).toBe('Amazon OA SDE I Intern')
    expect(shared.get('text')).toBe('Help needed with this problem\nthanks')
    expect(getSafeInternalRedirect(redirect)).toBe(redirect)
  })

  it('finds the link in the shared text when the url field is empty, and still keeps the text', async () => {
    openShare(new URLSearchParams({ text: 'Check this out https://lnkd.in/p/abc123' }).toString())

    const shared = new URL(await redirectOf(), 'http://localhost').searchParams
    expect(shared.get('url')).toBe('https://lnkd.in/p/abc123')
    expect(shared.get('text')).toBe('Check this out https://lnkd.in/p/abc123')
  })

  it('does not send a blank redirect before it has read what was shared', async () => {
    openShare(new URLSearchParams({ url: 'https://example.com/a', title: 'T' }).toString())
    const redirect = await redirectOf()
    expect(redirect).not.toBe('/share')
    expect(new URL(redirect, 'http://localhost').searchParams.get('url')).toBe('https://example.com/a')
  })
})
