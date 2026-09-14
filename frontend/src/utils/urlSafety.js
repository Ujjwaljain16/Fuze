/**
 * Guards against javascript:/data:/vbscript: URLs being rendered as clickable
 * <a href> links for bookmark/content URLs sourced from user input (manual
 * save, bulk import, the browser extension, LinkedIn scraping, etc.).
 *
 * The access token lives in localStorage (see AuthContext/api.js), so any
 * link that renders an attacker-controlled `javascript:` URL as a real href
 * is a stored-XSS-to-account-takeover path the moment a user clicks it.
 * Always render bookmark/result URLs through getSafeHref() instead of the
 * raw field.
 */
const SAFE_PROTOCOLS = new Set(['http:', 'https:']);

export function isSafeUrl(url) {
  if (!url || typeof url !== 'string') return false;
  try {
    const parsed = new URL(url, window.location.origin);
    return SAFE_PROTOCOLS.has(parsed.protocol);
  } catch {
    return false;
  }
}

export function getSafeHref(url) {
  return isSafeUrl(url) ? url : '#';
}

/**
 * Validate a post-login "?redirect=" target is a same-app relative path,
 * never an absolute/protocol-relative URL -- otherwise a crafted
 * "/login?redirect=https://evil.tld" (or "//evil.tld") link could send a
 * freshly-authenticated user off-site (open redirect), and a login flow is
 * exactly the kind of link people click from an email/DM without looking
 * closely. Falls back to `fallback` (default "/dashboard") for anything else.
 */
export function getSafeInternalRedirect(target, fallback = '/dashboard') {
  if (!target || typeof target !== 'string') return fallback;
  // Must start with a single '/' and not '//' or '/\' (both browser-normalize
  // to a protocol-relative URL, i.e. an external host).
  if (!/^\/(?!\/|\\)/.test(target)) return fallback;
  return target;
}
