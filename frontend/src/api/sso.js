import { API_URL } from './http.js'
import { safeRedirect } from '../router/redirect.js'

/*
 * Signing in through a provider, from the browser's side.
 *
 * There is very little of it, and that is the point of the arrangement: the
 * whole exchange happens between the API and Discord, and the SPA's part is to
 * leave, come back, and pick up the session that is waiting for it in a cookie.
 * Nothing here handles a token, because no token ever reaches this side of it.
 */

/*
 * Where "Continue with Discord" goes. A real navigation, never a fetch: the
 * consent screen has to be a page the person can read at Discord's own address,
 * and Discord refuses to be framed. That is why it is an anchor in the template
 * rather than a click handler.
 */
export const DISCORD_SIGN_IN_URL = `${API_URL}/auth/discord/authorize`

/*
 * The same for Google (#36). Two constants rather than a `signInUrl(provider)`
 * helper: there are two of them, they are used once each, and a function would
 * accept a provider name this app does not offer.
 */
export const GOOGLE_SIGN_IN_URL = `${API_URL}/auth/google/authorize`

// Session-scoped and tab-scoped, like the thing it stands for. It exists for the
// length of one round trip and should not outlive the tab that started it.
const DESTINATION_KEY = 'ttrpg.sso.destination'

/*
 * Remember where the guard was trying to send someone.
 *
 * The round trip leaves this origin entirely, so `?redirect=` on the login URL
 * does not survive it — without this, following a deep link while signed out
 * would send you to Discord and drop you at the home page, having forgotten what
 * you clicked. sessionStorage is the only thing that spans a full page load.
 *
 * Guarded because storage is not always there: Safari in private mode and any
 * page with storage disabled throw on access. Losing the destination is a dull
 * failure — you land on the home page — and it must not be the reason a sign-in
 * cannot start.
 */
export function rememberDestination(target) {
  try {
    sessionStorage.setItem(DESTINATION_KEY, safeRedirect(target))
  } catch {
    // Nothing to do and nothing worth saying. See above.
  }
}

/*
 * Where to land, once and once only.
 *
 * Removed as it is read, so a later sign-in in the same tab cannot inherit a
 * destination somebody chose ten minutes ago. Passed through `safeRedirect`
 * again on the way out rather than trusting what was stored: this is a value
 * that originally came from a query string, and it is about to be handed to the
 * router.
 */
export function takeDestination() {
  try {
    const stored = sessionStorage.getItem(DESTINATION_KEY)
    sessionStorage.removeItem(DESTINATION_KEY)
    return safeRedirect(stored)
  } catch {
    return safeRedirect(null)
  }
}
