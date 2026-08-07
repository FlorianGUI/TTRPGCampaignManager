/*
 * Where to send someone after they sign in.
 *
 * The destination arrives in a query string, which means it arrives from
 * whoever wrote the link — and a login page that redirects wherever it is told
 * is an open redirect: a link to our own domain that deposits the visitor,
 * freshly signed in and trusting, on someone else's page.
 *
 * So this allows exactly one shape: a path on this app. Anything else, and
 * anything malformed, falls back to the landing page. That is a dull failure,
 * which is the correct one — the worst case is a user who ends up at / rather
 * than the page they wanted.
 */
const FALLBACK = '/'

export function safeRedirect(target, fallback = FALLBACK) {
  if (typeof target !== 'string' || target === '') return fallback

  // A single leading slash. Two of anything — "//host" or the backslash forms
  // browsers quietly normalise into them — is a protocol-relative URL pointing
  // at another origin, which is the whole attack.
  if (target[0] !== '/') return fallback
  if (target[1] === '/' || target[1] === '\\') return fallback

  return target
}

export default safeRedirect
