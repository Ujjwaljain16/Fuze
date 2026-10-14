import { describe, it, expect } from 'vitest'
import { buildSharePath, loginPathForShare, MAX_SHARED_TEXT } from '../../utils/shareRedirect'
import { getSafeInternalRedirect } from '../../utils/urlSafety'

/** What the login page reads back: the `redirect` parameter of /login?..., then the params of that share path. */
const readBack = (loginPath) => {
  const redirect = new URL(loginPath, 'http://localhost').searchParams.get('redirect')
  return { redirect, shared: new URL(redirect, 'http://localhost').searchParams }
}

describe('buildSharePath', () => {
  it('carries the url, title and text', () => {
    const path = buildSharePath({ url: 'https://lnkd.in/p/abc', title: 'Amazon OA', text: 'Great post' })
    const params = new URL(path, 'http://x').searchParams
    expect(path.startsWith('/share?')).toBe(true)
    expect([params.get('url'), params.get('title'), params.get('text')]).toEqual(['https://lnkd.in/p/abc', 'Amazon OA', 'Great post'])
  })

  it('leaves out what was not shared, and is just /share when nothing was', () => {
    expect(buildSharePath({ url: 'https://example.com' })).toBe('/share?url=https%3A%2F%2Fexample.com')
    expect(buildSharePath({})).toBe('/share')
    expect(buildSharePath()).toBe('/share')
  })

  it('caps a very long text so the address stays usable', () => {
    const params = new URL(buildSharePath({ text: 'x'.repeat(MAX_SHARED_TEXT + 500) }), 'http://x').searchParams
    expect(params.get('text')).toHaveLength(MAX_SHARED_TEXT)
  })
})

describe('loginPathForShare', () => {
  it('survives the round trip through the login redirect, whatever characters the share holds', () => {
    const shared = {
      url: 'https://www.linkedin.com/feed/update/urn:li:activity:7?utm_source=share&utm_medium=android#frag',
      title: 'Amazon OA: "Secure Maximum Deliveries" & more',
      text: 'Line one\nLine two with ? & = # % and emoji \u{1F44B} and ünïcode',
    }
    const { shared: params } = readBack(loginPathForShare(shared))
    expect(params.get('url')).toBe(shared.url)
    expect(params.get('title')).toBe(shared.title)
    expect(params.get('text')).toBe(shared.text)
  })

  it('is one login parameter: an "&" in the share never becomes a parameter of the login page', () => {
    const login = new URL(loginPathForShare({ url: 'https://e.com/?a=1&b=2', title: 't', text: 'x&y' }), 'http://localhost')
    expect([...login.searchParams.keys()]).toEqual(['redirect'])
  })

  it('is accepted by the login page as a same-app redirect, with the query intact', () => {
    const { redirect } = readBack(loginPathForShare({ url: 'https://e.com/a', title: 'T', text: 'body' }))
    expect(getSafeInternalRedirect(redirect)).toBe(redirect)
    expect(redirect.startsWith('/share?')).toBe(true)
  })

  it('goes to plain /share when nothing was shared', () => {
    expect(readBack(loginPathForShare({})).redirect).toBe('/share')
  })
})
