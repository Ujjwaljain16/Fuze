/**
 * The installable-app pieces: what Android needs to install the PWA (and so list it in the share sheet), how the
 * share target is declared, and that the service worker is never cached like an asset.
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

const FRONTEND = path.resolve(__dirname, '..', '..')
const read = (...p) => fs.readFileSync(path.join(FRONTEND, ...p), 'utf8')
const manifest = JSON.parse(read('public', 'manifest.json'))
const vercel = JSON.parse(read('vercel.json'))

/** Width and height from a PNG's IHDR chunk, or null when the file is not a PNG. */
const pngSize = (file) => {
  const buf = fs.readFileSync(file)
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  if (buf.length < 24 || !buf.subarray(0, 8).equals(signature)) return null
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) }
}

describe('manifest', () => {
  it('is installable: a name, a start URL inside its scope, standalone display, theme colours', () => {
    expect(manifest.name && manifest.short_name).toBeTruthy()
    expect(manifest.display).toBe('standalone')
    expect(manifest.scope).toBe('/')
    expect(manifest.start_url.startsWith(manifest.scope)).toBe(true)
    expect(manifest.id).toBe('/')
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i)
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it('has real PNG icons at 192 and 512, and a separate maskable one', () => {
    const pngs = manifest.icons.filter((i) => i.type === 'image/png')
    for (const size of ['192x192', '512x512']) {
      expect(pngs.some((i) => i.sizes === size && i.purpose === 'any')).toBe(true)
    }
    expect(pngs.some((i) => i.sizes === '512x512' && i.purpose === 'maskable')).toBe(true)
    expect(manifest.icons.every((i) => i.purpose !== 'any maskable')).toBe(true)   // one purpose per icon
  })

  it('points every icon at a file that exists, and the PNGs are the size they claim', () => {
    for (const icon of manifest.icons) {
      const file = path.join(FRONTEND, 'public', icon.src)
      expect(fs.existsSync(file), icon.src).toBe(true)
      if (icon.type === 'image/png') {
        const [w, h] = icon.sizes.split('x').map(Number)
        expect(pngSize(file), icon.src).toEqual({ width: w, height: h })
      }
    }
  })

  it('gives iOS a PNG home-screen icon', () => {
    const html = read('index.html')
    expect(html).toMatch(/<link rel="apple-touch-icon" href="\/icons\/apple-touch-icon\.png"/)
    expect(pngSize(path.join(FRONTEND, 'public', 'icons', 'apple-touch-icon.png'))).toEqual({ width: 180, height: 180 })
  })
})

describe('share target (the phone share sheet)', () => {
  it('opens /share with the shared title, text and url as query parameters', () => {
    expect(manifest.share_target).toEqual({
      action: '/share',
      method: 'GET',
      enctype: 'application/x-www-form-urlencoded',
      params: { title: 'title', text: 'text', url: 'url' },
    })
    expect(manifest.share_target.action.startsWith(manifest.scope)).toBe(true)
  })

  it('is served by the app: /share is rewritten to the single-page app, not a 404', () => {
    const rewrite = new RegExp(`^${vercel.rewrites[0].source}$`)
    expect(rewrite.test('/share')).toBe(true)
    expect(rewrite.test('/icons/icon-192.png')).toBe(false)     // real files are served as files
  })
})

describe('caching headers', () => {
  const rulesFor = (pathname) =>
    vercel.headers.filter((h) => new RegExp(`^${h.source}$`).test(pathname))
  const cacheControl = (pathname) => {
    let value
    for (const rule of rulesFor(pathname)) {            // a later matching rule overrides an earlier one
      const header = rule.headers.find((h) => h.key === 'Cache-Control')
      if (header) value = header.value
    }
    return value
  }

  it('never caches the service worker or the manifest, whatever other rules match them', () => {
    expect(cacheControl('/sw.js')).toBe('public, max-age=0, must-revalidate')
    expect(cacheControl('/manifest.json')).toBe('public, max-age=0, must-revalidate')
  })

  it('still caches hashed assets and icons for a year', () => {
    expect(cacheControl('/assets/index-abc123.js')).toMatch(/immutable/)
    expect(cacheControl('/icons/icon-192.png')).toMatch(/immutable/)
  })
})

describe('service worker', () => {
  const sw = read('public', 'sw.js')

  it('keeps pages network-first and never touches API calls', () => {
    expect(sw).toMatch(/request\.mode === 'navigate'/)
    expect(sw).toMatch(/url\.pathname\.startsWith\('\/api\/'\)/)
  })

  it("does not store each visited address (a shared link arrives as /share?url=...) in the cache", () => {
    const navigation = sw.slice(sw.indexOf('async function handleNavigationRequest'), sw.indexOf('async function handleStaticAssetRequest'))
    expect(navigation).toMatch(/cache\.put\('\/index\.html'/)
    expect(navigation).not.toMatch(/cache\.put\(request/)
  })

  it('has its version stamped in at build time', () => {
    expect(sw).toMatch(/const CACHE_VERSION = '__BUILD_HASH__'/)
  })
})
