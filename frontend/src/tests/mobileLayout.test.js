/**
 * Phone layout guards. Each of these was a real bug found by opening the app at 375px:
 *  - desktop sidebar offsets applied on phones too, squeezing every page into a ~100px column;
 *  - a Tailwind 3 copy of the gradient classes overrode Tailwind 4's, so gradient buttons had no background;
 *  - hover-only actions (Tailwind 4 hovers only where a device can hover) never appeared on a phone.
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

const SRC = path.resolve(__dirname, '..')
const read = (...p) => fs.readFileSync(path.join(SRC, ...p), 'utf8')

/** Top-level rules and @media blocks of a stylesheet, as {media: string|null, selector, body}. */
const parseCss = (css) => {
  const rules = []
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const walk = (text, media) => {
    let i = 0
    while (i < text.length) {
      const open = text.indexOf('{', i)
      if (open === -1) break
      const head = text.slice(i, open).trim()
      let depth = 1
      let j = open + 1
      while (j < text.length && depth > 0) {
        if (text[j] === '{') depth++
        else if (text[j] === '}') depth--
        j++
      }
      const body = text.slice(open + 1, j - 1)
      if (head.startsWith('@media')) walk(body, head.replace(/^@media\s*/, ''))
      else if (!head.startsWith('@')) rules.push({ media: media || null, selector: head, body })
      i = j
    }
  }
  walk(clean, null)
  return rules
}

describe('the sidebar takes no space on a phone', () => {
  const rules = parseCss(read('App.css'))
  const sidebarOffsets = rules.filter((r) =>
    /data-sidebar-collapsed="(true|false)"\]\s+\.(main-content|navbar)/.test(r.selector) && /margin-left|left:/.test(r.body))

  it('has desktop offsets for the content and the navbar', () => {
    expect(sidebarOffsets.length).toBeGreaterThan(0)
  })

  it('applies every one of them only above the phone breakpoint (901px and up)', () => {
    for (const rule of sidebarOffsets) {
      expect(rule.media, rule.selector).toMatch(/min-width:\s*901px/)
    }
  })

  it('forces no margin on the content at phone widths', () => {
    const phone = rules.filter((r) => r.media && /max-width:\s*900px/.test(r.media) && r.selector === '.main-content')
    expect(phone.some((r) => /margin-left:\s*0\s*!important/.test(r.body))).toBe(true)
  })

  it('uses the same breakpoint as the JavaScript that chooses the drawer', async () => {
    const { MOBILE_BREAKPOINT } = await import('../utils/breakpoints')
    expect(MOBILE_BREAKPOINT).toBe(900)
  })
})

describe('gradients come from Tailwind', () => {
  it('does not redefine the gradient utilities (a Tailwind 3 copy broke every gradient button under Tailwind 4)', () => {
    for (const file of ['components/sidebar-styles.css', 'App.css', 'index.css']) {
      const selectors = parseCss(read(file)).map((r) => r.selector)
      expect(selectors.filter((s) => /^\.(bg-gradient-to-|from-|to-|via-)/.test(s)), file).toEqual([])
    }
  })
})

describe('hover-only actions', () => {
  it('stay visible on devices that cannot hover', () => {
    const rule = parseCss(read('App.css')).find((r) => r.selector === '.touch-visible')
    expect(rule && rule.media).toMatch(/hover:\s*none/)
    expect(rule.body).toMatch(/opacity:\s*1/)
  })

  it('every action that appears only on hover is marked touch-visible', () => {
    const offenders = []
    for (const file of ['pages/Bookmarks.jsx', 'pages/Dashboard.jsx', 'pages/Projects.jsx']) {
      for (const line of read(file).split('\n')) {
        // decorative overlays (absolute inset-0) may stay hover-only; a button or an action group may not
        if (line.includes('opacity-0 group-hover:opacity-100') && !line.includes('absolute inset-0') && !line.includes('touch-visible')) {
          offenders.push(`${file}: ${line.trim().slice(0, 80)}`)
        }
      }
    }
    expect(offenders).toEqual([])
  })
})
