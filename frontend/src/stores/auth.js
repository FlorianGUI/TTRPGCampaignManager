import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, apiFetch } from '../api/http.js'
import { forgetCurrentCampaign } from './currentCampaign.js'

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
  /*
   * Whether the last boot got an answer at all — which is a different question
   * from whether the answer was yes.
   *
   * `ready` alone cannot say it: a boot that settles signed-out looks identical
   * to one that never reached the API, and the guard turns "not signed in" into
   * a redirect to /login. That is how a deploy window, a wifi handover or a
   * laptop waking up used to sign people out while their cookie was perfectly
   * good (#68). False here means nobody has been judged yet.
   */
  const reachable = ref(true)
  /*
   * Why the session ended, when it ended for a reason worth explaining.
   *
   * Only the 429 stop sets it, and the sentence is the server's own — copy about
   * limits belongs where the limits are, and those sentences are written to be
   * safe to display (#63). A field rather than a query parameter: the redirect
   * is client-side so this survives it, and `?reason=` would be a URL anyone
   * could forge into showing a message that never happened.
   */
  const signedOutReason = ref(null)

  const isSignedIn = computed(() => user.value !== null)

  // One in-flight refresh per tab. Four requests can hit a 401 together — with
  // a 15-minute access token this is routine, not an edge case — and rotation
  // means the naive version does not merely send four requests: three of them
  // present a token that has already been spent, which the backend reads as a
  // leak and answers by revoking the whole session. The user is signed out by
  // their own client.
  let renewal = null

  /*
   * `forgetCurrentCampaign` as well as the in-memory pair, because the remembered
   * campaign is the one thing this store leaves on disk. It is only a uuid, but
   * it is a uuid that decides where the *next* person to open this browser lands
   * — and "the app opened someone else's campaign" is not a sentence anyone
   * should have to hear. Everything else here has always been memory-only, which
   * is why this is the one line that needs saying out loud (#35).
   */
  function clear() {
    user.value = null
    token.value = null
    forgetCurrentCampaign()
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

  /*
   * Which failed refreshes are answers about the session, and which are not.
   *
   * - 401: the cookie is finished — expired, revoked, replayed or never there.
   *   All four arrive as one 401 by design and there is nothing to tell apart.
   * - 429: the emergency stop. Traffic that trips a limit as loose as the
   *   global one is outside anything a browser on a timer does, so the session
   *   ends and whoever is behind it starts over (#68).
   *
   * Everything else is not an answer. A `fetch` rejection is not even an
   * `ApiError` — `http.js` only builds one from a response — and a 502 while the
   * backend restarts is one that arrived from nginx rather than from the API.
   * Neither is evidence about the session, and "we could not ask" must not cost
   * anyone theirs.
   */
  function endsTheSession(error) {
    return error instanceof ApiError && (error.status === 401 || error.status === 429)
  }

  /*
   * The 429 stop, made real.
   *
   * Clearing locally would be a soft stop: the refresh cookie would survive, and
   * once the window passed a reload would sign the user back in without a
   * password — nobody would have started over. So the client revokes the session
   * itself. Logout carries the same cookie and counts against its own bucket, so
   * it should get through while refresh is throttled.
   *
   * If it does not — a 429 of its own, or the network is simply gone — clear
   * anyway and show the same message. A soft stop beats a client that cannot
   * leave.
   *
   * `apiFetch` rather than `request` from api/client.js, for the reason this
   * whole store avoids that wrapper: it answers a 401 by refreshing, and a
   * refresh is what we are in the middle of failing.
   */
  async function stopHard(error) {
    try {
      await apiFetch('/users/logout', { method: 'POST' })
    } catch {
      // Deliberately swallowed: see above.
    } finally {
      clear()
      // After `clear`, which does not touch this — the reason has to outlive the
      // sign-out it explains, all the way to the login page.
      signedOutReason.value = {
        // Only the server's sentence. `detail` is an array on a 422 and can be
        // null on a body we could not read; neither is something to print at
        // someone, and inventing a replacement here would be writing copy about
        // limits in the one place that knows nothing about them.
        message: typeof error.detail === 'string' ? error.detail : null,
        retryAfter: error.retryAfter,
      }
    }
  }

  async function renewOnce() {
    try {
      const session = await apiFetch('/users/refresh', { method: 'POST' })
      token.value = session.access_token
      return session.access_token
    } catch (error) {
      // The 429 has work to do before clearing — see `stopHard`. The other end
      // of a session only has to be forgotten. Everything else is left alone,
      // and the caller gets the failure to deal with as its own.
      if (error instanceof ApiError && error.status === 429) await stopHard(error)
      else if (endsTheSession(error)) clear()

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
   * A failure that is not an answer — no network, a 502 from nginx mid-deploy —
   * must not settle as signed-out, because the guard reads that as a redirect to
   * /login. This runs on every page load, so treating it as a verdict meant
   * "open the app at a bad moment and you are signed out", holding a perfectly
   * good thirty-day cookie. It settles as `reachable = false` instead, and the
   * app says so rather than pretending to know (#68).
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
        reachable.value = true
      } catch (error) {
        // `renewOnce` has already ended the session in the two cases where that
        // is the right answer; this is here for a failure further along, and to
        // be the one place the difference is written down.
        if (endsTheSession(error)) clear()
        else reachable.value = false
      } finally {
        ready.value = true
      }
    })()

    return booting
  }

  /*
   * Ask again, for a client that was told nothing the first time.
   *
   * `ready` deliberately stays true: the app is already showing the "cannot
   * reach the server" panel, and dropping back to the blank pre-boot screen
   * would take the explanation away at the moment someone acts on it.
   */
  function retryBoot() {
    booting = null
    return boot()
  }

  /*
   * The reason, once.
   *
   * Read-and-clear because it explains one arrival at the login page. Left in
   * place it would put the message up again the next time anyone simply
   * navigated there, about a session that ended days ago.
   */
  function takeSignedOutReason() {
    const reason = signedOutReason.value
    signedOutReason.value = null

    return reason
  }

  /*
   * Signing in ends whatever the last session remembered.
   *
   * Here rather than only in `logOut` because the two are not the same event:
   * the refresh window is absolute and does not slide, so a session that simply
   * expires never calls logout — that person meets a login form, and without
   * this they would be dropped straight into a campaign that may not be theirs.
   * It is also what makes `/` show the chooser after an explicit sign-in, which
   * is the behaviour #59 asked for, without a flag to carry across the redirect.
   */
  async function logIn(username, password) {
    // Form-encoded, not JSON — see the note in api/http.js.
    const session = await apiFetch('/users/login', { method: 'POST', form: { username, password } })
    token.value = session.access_token
    forgetCurrentCampaign()
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

  return {
    user,
    token,
    ready,
    reachable,
    signedOutReason,
    isSignedIn,
    boot,
    retryBoot,
    renew,
    logIn,
    register,
    logOut,
    clear,
    takeSignedOutReason,
  }
})
