/**
 * Where a signed-out share goes after sign-in. The phone's share sheet opens /share?title=...&text=...&url=...;
 * if the user is not signed in yet, all three must survive the trip through the login page (including a Google
 * sign-in), not just the link: the shared text is what makes a post searchable when the page itself cannot be read.
 */

// A URL has a practical length limit (and a login redirect carries it twice over); a shared post's text can be long.
export const MAX_SHARED_TEXT = 2000

/** "/share?url=...&title=...&text=..." with only the parts that exist. */
export const buildSharePath = ({ url, title, text } = {}) => {
  const params = new URLSearchParams()
  if (url) params.set('url', url)
  if (title) params.set('title', title)
  if (text) params.set('text', String(text).slice(0, MAX_SHARED_TEXT))
  const query = params.toString()
  return query ? `/share?${query}` : '/share'
}

/**
 * "/login?redirect=<the share path, encoded as one value>". The share path has its own "?" and "&", so it has to be
 * encoded whole: left raw, "&title=..." would be read as another parameter of the login page.
 */
export const loginPathForShare = (shared) => `/login?redirect=${encodeURIComponent(buildSharePath(shared))}`
