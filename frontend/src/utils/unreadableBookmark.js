/**
 * Why a bookmark has no page text, in words the user can act on. A page Fuze could not read used to show up as
 * a bare "Untitled" bookmark with nothing to say what happened or what to do.
 *
 * Returns null for a bookmark that has its text, or whose reading has not finished or failed in some other way.
 */

const SITES = [
  { match: (host) => host === 'linkedin.com' || host.endsWith('.linkedin.com') || host === 'lnkd.in', name: 'LinkedIn' },
]

const hostOf = (url) => {
  try {
    return new URL(url).hostname.toLowerCase()
  } catch {
    return ''
  }
}

const WHAT_TO_DO = "Open the page and save it with the Fuze extension while you are looking at it, or paste the text into the notes."

export const unreadableNote = (bookmark) => {
  if (!bookmark || bookmark.has_content) return null

  if (bookmark.scrape_status === 'DISALLOWED') {
    const host = hostOf(bookmark.url)
    const site = SITES.find((s) => s.match(host))
    const who = site ? site.name : 'This site'
    return `${who} doesn't allow automated reading, so Fuze couldn't read this page. ${WHAT_TO_DO}`
  }
  if (bookmark.scrape_status === 'FAILED') {
    return `Fuze couldn't read this page; it may need a login or may be gone. ${WHAT_TO_DO}`
  }
  return null
}
