import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiFetch } from '../api/http.js'

/*
 * Who is signed in, and the access token that proves it.
 *
 * The access token is held in memory and nowhere else. It used to be destined
 * for localStorage — the reason was surviving a reload — but the refresh cookie
 * from #35 does that job better and cannot be read by script at all. So there is
 * no long-lived credential on disk for an XSS to steal, and this store persists
 * nothing. The browser holds the only durable part of a session.
 *
 * Everything here talks to `apiFetch` rather than to `request` in api/client.js,
 * deliberately: that wrapper answers a 401 by refreshing, and a refresh call
 * that did the same would recurse.
 */

const REFRESH_LOCK = 'ttrpg.auth.refresh'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(null)
  // False until the boot refresh has resolved one way or the other. The first
  // render waits on it, or a returning user watches the login page flash before
  // being sent back where they were.
  const ready = ref(false)

  const isSignedIn = computed(() => user.value !== null)

  // One in-flight refresh per tab. Four requests can hit a 401 together — with
  // a 15-minute access token this is routine, not an edge case — and rotation
  // means the naive version does not merely send four requests: three of them
  // present a token that has already been spent, which the backend reads as a
  // leak and answers by revoking the whole session. The user is signed out by
  // their own client.
  let renewal = null

  function clear() {
    user.value = null
    token.value = null
  }

  /*
   * Serialise refreshes across tabs as well as within one.
   *
   * The per-tab promise above cannot see another tab, and two tabs restored
   * together at browser start will both send the same cookie before either
   * response lands — whichever loses is a replay, and both tabs get signed out.
   * Web Locks are cross-tab and are the smallest thing that closes it.
   *
   * Note what the waiting tab does when its turn comes: it refreshes too, and
   * that is correct rather than wasteful. The cookie is browser state, so by
   * then it holds the token the first tab rotated *to* — a valid one. It cannot
   * skip its own refresh instead, because the token the other tab received went
   * into that tab's memory, where this one cannot reach it.
   *
   * Falls back to the per-tab promise where the API is missing: older Safari,
   * and any non-secure context.
   */
  function serialised(run) {
    if (!globalThis.navigator?.locks) return run()
    return navigator.locks.request(REFRESH_LOCK, run)
  }

  async function renewOnce() {
    try {
      const session = await apiFetch('/users/refresh', { method: 'POST' })
      token.value = session.access_token
      return session.access_token
    } catch (error) {
      // The session is over — expired, revoked, replayed or never there. All
      // four arrive as one 401 by design, and there is nothing to distinguish.
      clear()
      throw error
    }
  }

  function renew() {
    if (renewal) return renewal
    renewal = serialised(renewOnce).finally(() => {
      renewal = null
    })
    return renewal
  }

  async function loadUser() {
    user.value = await apiFetch('/users/me', { token: token.value })
  }

  /*
   * Restore the session, if there is one to restore.
   *
   * A 401 here is the ordinary signed-out case rather than an error: it is what
   * a first-time visitor gets, and what anyone gets thirty days after signing
   * in, since the refresh window is absolute and does not slide. Either way the
   * app boots signed out, which is a state it has to handle regardless.
   *
   * Idempotent, and it returns the same promise to everyone who asks. Two
   * callers want it now — main.js starts it before mount, and the route guard
   * has to wait for it before it can tell a signed-out visitor from one whose
   * session simply has not come back yet. Without that, the first navigation
   * races the refresh and sends a signed-in user to the login page.
   */
  let booting = null

  function boot() {
    booting ??= (async () => {
      try {
        await renew()
        await loadUser()
      } catch {
        clear()
      } finally {
        ready.value = true
      }
    })()

    return booting
  }

  async function logIn(username, password) {
    // Form-encoded, not JSON — see the note in api/http.js.
    const session = await apiFetch('/users/login', { method: 'POST', form: { username, password } })
    token.value = session.access_token
    await loadUser()
  }

  async function register(username, email, password) {
    // Registering signs you in (#33), so there is no login call chained onto
    // this one and one failure point instead of two. A 409 is a taken username
    // and belongs on that field; it propagates for the form to place.
    const session = await apiFetch('/users/register', {
      method: 'POST',
      json: { username, email, password },
    })
    token.value = session.access_token
    await loadUser()
  }

  async function logOut() {
    try {
      // Revokes server-side and clears the cookie. Answers 204 whether or not
      // there was a session, so there is no failure to handle — but clearing
      // locally without calling this would leave a working refresh cookie
      // behind, which is the one way to log out that does not log you out.
      await apiFetch('/users/logout', { method: 'POST' })
    } finally {
      clear()
    }
  }

  return { user, token, ready, isSignedIn, boot, renew, logIn, register, logOut, clear }
})
