import { describe, it, expect } from 'vitest'
import { unreadableNote } from '../../utils/unreadableBookmark'

describe('unreadableNote', () => {
  it('says LinkedIn forbids automated reading, for a lnkd.in short link and for linkedin.com', () => {
    for (const url of ['https://lnkd.in/p/gemNZe47', 'https://www.linkedin.com/posts/someone_x-activity-1']) {
      const note = unreadableNote({ url, has_content: false, scrape_status: 'DISALLOWED' })
      expect(note).toMatch(/^LinkedIn doesn't allow automated reading/)
      expect(note).toMatch(/extension/)          // and what to do about it
      expect(note).toMatch(/notes/)
    }
  })

  it('is generic for another site that blocks automated reading', () => {
    expect(unreadableNote({ url: 'https://example.com/a', has_content: false, scrape_status: 'DISALLOWED' }))
      .toMatch(/^This site doesn't allow automated reading/)
  })

  it('explains a failed read', () => {
    expect(unreadableNote({ url: 'https://example.com/a', has_content: false, scrape_status: 'FAILED' }))
      .toMatch(/may need a login/)
  })

  it('says nothing when the page was read, or the status is not a refusal or failure', () => {
    expect(unreadableNote({ url: 'https://lnkd.in/x', has_content: true, scrape_status: 'DISALLOWED' })).toBeNull()
    expect(unreadableNote({ url: 'https://example.com', has_content: false, scrape_status: 'PENDING' })).toBeNull()
    expect(unreadableNote({ url: 'https://example.com', has_content: false, scrape_status: 'SUCCESS' })).toBeNull()
    expect(unreadableNote({ url: 'https://example.com', has_content: false })).toBeNull()
    expect(unreadableNote(null)).toBeNull()
  })

  it('does not take a lookalike host for LinkedIn', () => {
    expect(unreadableNote({ url: 'https://notlinkedin.com/x', has_content: false, scrape_status: 'DISALLOWED' }))
      .toMatch(/^This site/)
  })

  it('copes with a URL that does not parse', () => {
    expect(unreadableNote({ url: 'not a url', has_content: false, scrape_status: 'DISALLOWED' })).toMatch(/^This site/)
  })
})
