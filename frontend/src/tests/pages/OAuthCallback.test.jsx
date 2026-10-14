import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router'

const completeOAuth = vi.fn()
vi.mock('../../services/oauth', () => ({
  completeOAuth: (...a) => completeOAuth(...a),
  readOAuthRedirect: () => ({ accessToken: 'tok', error: null }),
}))

import OAuthCallback from '../../pages/OAuthCallback'

const Where = () => {
  const l = useLocation()
  return <div data-testid="where">{l.pathname + l.search}</div>
}

const renderCallback = () =>
  render(
    <MemoryRouter initialEntries={['/oauth/callback']}>
      <Routes>
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>
  )

describe('after Google sign-in', () => {
  beforeEach(() => {
    completeOAuth.mockReset()
    sessionStorage.clear()
  })

  it('goes back to the shared link the user was saving', async () => {
    completeOAuth.mockResolvedValue({ status: 'signed_in', redirect: '/share?url=https%3A%2F%2Fe.com&title=T&text=body' })
    const { findByTestId } = renderCallback()
    expect((await findByTestId('where')).textContent).toBe('/share?url=https%3A%2F%2Fe.com&title=T&text=body')
  })

  it('goes to the dashboard when there was nowhere else to go', async () => {
    completeOAuth.mockResolvedValue({ status: 'signed_in', redirect: null })
    const { findByTestId } = renderCallback()
    expect((await findByTestId('where')).textContent).toBe('/dashboard')
  })

  it('never follows an off-site destination', async () => {
    completeOAuth.mockResolvedValue({ status: 'signed_in', redirect: 'https://evil.tld/phish' })
    const { findByTestId } = renderCallback()
    expect((await findByTestId('where')).textContent).toBe('/dashboard')
  })
})
