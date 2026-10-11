import { describe, it, expect } from 'vitest'
import { getSafeInternalRedirect, getSafeHref } from '../../utils/urlSafety'

describe('getSafeInternalRedirect', () => {
  it.each([
    '/dashboard',
    '/projects/42',
    '/bookmarks?tag=react#top',
    '/share?url=https%3A%2F%2Fexample.com',
  ])('keeps the in-app path %s', (target) => {
    expect(getSafeInternalRedirect(target)).toBe(target)
  })

  it.each([
    ['protocol-relative', '//evil.tld'],
    ['protocol-relative with path', '//evil.tld/dashboard'],
    ['backslash after slash', '/\\evil.tld'],
    ['double backslash', '\\\\evil.tld'],
    ['backslash then slash', '\\/evil.tld'],
    ['slash backslash slash', '/\\/evil.tld'],
    ['backslash later in the path', '/foo\\..\\..\\evil.tld'],
    ['tab between slashes', '/\t/evil.tld'],
    ['newline between slashes', '/\n/evil.tld'],
    ['carriage return between slashes', '/\r/evil.tld'],
    ['NUL byte', '/\u0000/evil.tld'],
    ['absolute https URL', 'https://evil.tld'],
    ['javascript URL', 'javascript:alert(1)'],
    ['data URL', 'data:text/html,<script>alert(1)</script>'],
    ['relative path', 'dashboard'],
    ['leading whitespace', ' //evil.tld'],
    ['empty string', ''],
  ])('falls back for %s', (_name, target) => {
    expect(getSafeInternalRedirect(target)).toBe('/dashboard')
  })

  it('falls back for non-strings and honours a custom fallback', () => {
    expect(getSafeInternalRedirect(null)).toBe('/dashboard')
    expect(getSafeInternalRedirect(undefined)).toBe('/dashboard')
    expect(getSafeInternalRedirect(['/x'])).toBe('/dashboard')
    expect(getSafeInternalRedirect('//evil.tld', '/')).toBe('/')
  })

  it('handles a redirect param exactly as URLSearchParams decodes it', () => {
    const decode = (query) => new URLSearchParams(query).get('redirect')
    expect(getSafeInternalRedirect(decode('redirect=%2F%5Cevil.tld'))).toBe('/dashboard')
    expect(getSafeInternalRedirect(decode('redirect=%2F%09%2Fevil.tld'))).toBe('/dashboard')
    expect(getSafeInternalRedirect(decode('redirect=%2F%2Fevil.tld'))).toBe('/dashboard')
    expect(getSafeInternalRedirect(decode('redirect=%2Fprojects%2F7'))).toBe('/projects/7')
  })
})

describe('getSafeHref', () => {
  it('allows http(s) and blocks script-bearing schemes', () => {
    expect(getSafeHref('https://example.com/a')).toBe('https://example.com/a')
    expect(getSafeHref('javascript:alert(1)')).toBe('#')
    expect(getSafeHref('data:text/html,hi')).toBe('#')
    expect(getSafeHref('')).toBe('#')
  })
})
