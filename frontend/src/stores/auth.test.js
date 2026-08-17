import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth.js'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from './currentCampaign.js'
import { API_URL, ApiError } from '../api/http.js'

/*
 * These drive the real transport against a stubbed `fetch`, rather than mocking
 * api/http.js. The method, the encoding and `credentials: 'include'` are part of
 * what this store has to get right — a mock at the module boundary would assert
 * that we called our own function.
 */

function respond(status, body, headers = {}) {
  return {
    ok: status < 400,
    status,
    // A real `Response` always has these, and the transport reads `Retry-After`
    // off a 429 (#68) — a stub without them would be a stub of something else.
    headers: new Headers(headers),
    json: async () => body ?? {},
  }
}

// What a `fetch` that never reached the server does: it rejects, and with a
// `TypeError` rather than anything the API could have sent. That is the whole
// difficulty — it does not arrive as an `ApiError` at all.
function unreachable() {
  globalThis.fetch = vi.fn(async () => {
    throw new TypeError('Failed to fetch')
  })
}

const A_SESSION = respond(200, { access_token: 'fresh-token', token_type: 'bearer' })
const A_USER = respond(200, { id: 'u-1', username: 'aragorn', email: 'aragorn@gondor.test' })

/*
 * A fake API, keyed by "METHOD /path". Every call is recorded in order.
 *
 * The key drops the base, so routes read as the API's own paths rather than the
 * /api prefix nginx and the dev server proxy under — that prefix is deployment,
 * not something these tests have an opinion about.
 */
function serve(routes) {
  const calls = []
  globalThis.fetch = vi.fn(async (url, init = {}) => {
    const key = `${init.method ?? 'GET'} ${url.slice(API_URL.length)}`
    calls.push(key)
    const handler = routes[key]
    if (!handler) throw new Error(`no route for ${key}`)
    return typeof handler === 'function' ? handler() : handler
  })
  return calls
}

function countOf(calls, key) {
  return calls.filter((call) => call === key).length
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete globalThis.fetch
  })

  describe('boot', () => {
    it('restores the session from the refresh cookie alone', async () => {
      serve({ 'POST /users/refresh': A_SESSION, 'GET /users/me': A_USER })
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.isSignedIn).toBe(true)
      expect(auth.user.username).toBe('aragorn')
      expect(auth.token).toBe('fresh-token')
      expect(auth.ready).toBe(true)
    })

    it('sends no bearer token on the way in, because there is not one yet', async () => {
      /* The whole point of booting from a cookie: on a cold load the tab holds
       * nothing, and the credential is the one thing script cannot read. */
      serve({ 'POST /users/refresh': A_SESSION, 'GET /users/me': A_USER })

      await useAuthStore().boot()

      expect(globalThis.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()
      expect(globalThis.fetch.mock.calls[0][1].credentials).toBe('include')
    })

    it('boots signed out when there is no session to restore', async () => {
      /* A first-time visitor, and equally anyone thirty days after signing in:
       * the refresh window is absolute, so this is ordinary rather than an error. */
      const calls = serve({ 'POST /users/refresh': respond(401, { detail: 'Could not renew' }) })
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.isSignedIn).toBe(false)
      expect(auth.ready).toBe(true)
      expect(countOf(calls, 'GET /users/me')).toBe(0)
    })

    it('becomes ready even when the network is down', async () => {
      /* `ready` gates the first render, so anything that leaves it false leaves
       * the app on a blank page for good. */
      unreachable()
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.ready).toBe(true)
      expect(auth.isSignedIn).toBe(false)
    })

    it('does not settle as signed out when it never got an answer', async () => {
      /*
       * The failure this issue is about (#68). `boot()` runs on every page load,
       * so treating a failed request as a verdict means opening the app during a
       * deploy — or on a wifi handover, or waking a laptop — signs you out while
       * a perfectly good thirty-day cookie sits in the browser. The guard reads
       * "not signed in" as a redirect to /login, so `reachable` is what stands
       * between a ten-second outage and everyone having to sign in again.
       */
      unreachable()
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.reachable).toBe(false)
    })

    it('settles as signed out on a 401, which is an answer', async () => {
      serve({ 'POST /users/refresh': respond(401, { detail: 'Could not renew the session' }) })
      const auth = useAuthStore()

      await auth.boot()

      // Not the "we could not ask" case: the server said no, and the login page
      // is where this person belongs.
      expect(auth.reachable).toBe(true)
      expect(auth.isSignedIn).toBe(false)
    })

    it('keeps the session on a 502, which is nginx rather than the API', async () => {
      /* The same situation as a dead network, arriving through a different
       * branch: it is what a proxy answers while the backend is being replaced. */
      serve({ 'POST /users/refresh': respond(502) })
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.reachable).toBe(false)
    })

    it('asks again when told to, and boots properly the second time', async () => {
      /* The retry behind the "cannot reach the server" panel. Anything less
       * leaves a client that has to be reloaded to recover from a blip. */
      let reachableNow = false
      globalThis.fetch = vi.fn(async (url) => {
        if (!reachableNow) throw new TypeError('Failed to fetch')
        return String(url).endsWith('/users/refresh') ? A_SESSION : A_USER
      })
      const auth = useAuthStore()
      await auth.boot()

      reachableNow = true
      await auth.retryBoot()

      expect(auth.reachable).toBe(true)
      expect(auth.isSignedIn).toBe(true)
    })
  })

  describe('renew', () => {
    it('holds one refresh for every caller that asks while it is in flight', async () => {
      /*
       * The bug this slice is most likely to write. Rotation means the second
       * and third requests present a token that has already been spent, which
       * the backend reads as a leak and answers by revoking the session — so
       * the naive version does not waste requests, it signs the user out.
       */
      let release
      const calls = serve({
        'POST /users/refresh': () => new Promise((resolve) => (release = () => resolve(A_SESSION))),
      })
      const auth = useAuthStore()

      const all = Promise.all([auth.renew(), auth.renew(), auth.renew()])
      release()
      await all

      expect(countOf(calls, 'POST /users/refresh')).toBe(1)
    })

    it('asks again once the previous refresh has settled', async () => {
      const calls = serve({ 'POST /users/refresh': A_SESSION })
      const auth = useAuthStore()

      await auth.renew()
      await auth.renew()

      expect(countOf(calls, 'POST /users/refresh')).toBe(2)
    })

    it('takes a cross-tab lock when the browser has one', async () => {
      /*
       * Per-tab single-flight cannot see another tab, and two tabs restored
       * together at browser start will both send the same cookie. Web Locks
       * serialise them, so the second refreshes the already-rotated cookie
       * instead of replaying the spent one.
       */
      const request = vi.fn(async (name, run) => run())
      Object.defineProperty(navigator, 'locks', { value: { request }, configurable: true })
      serve({ 'POST /users/refresh': A_SESSION })

      await useAuthStore().renew()

      expect(request).toHaveBeenCalledWith('ttrpg.auth.refresh', expect.any(Function))
      delete navigator.locks
    })

    it('still refreshes where Web Locks are unavailable', async () => {
      /* Older Safari, and any non-secure context. jsdom has no locks either,
       * which is why every other case here exercises this path. */
      expect(navigator.locks).toBeUndefined()
      serve({ 'POST /users/refresh': A_SESSION })
      const auth = useAuthStore()

      await auth.renew()

      expect(auth.token).toBe('fresh-token')
    })

    it('clears the session when the refresh is refused', async () => {
      serve({ 'POST /users/refresh': respond(401, { detail: 'Could not renew the session' }) })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'stale-token'

      const error = await auth.renew().catch((e) => e)

      expect(error).toBeInstanceOf(ApiError)
      expect(error.status).toBe(401)
      expect(auth.isSignedIn).toBe(false)
      expect(auth.token).toBeNull()
    })

    /*
     * The four ways a refresh can fail, and what each one means for the session
     * (#68). Three of them used to end it; only one should.
     */
    it('keeps the session when the request never reached the server', async () => {
      /*
       * "We could not ask" is not "the answer was no". A `fetch` rejection is not
       * even an `ApiError` — the transport only builds one from a response — so
       * before this it sailed through the same catch as a 401 and cost the user
       * a session they still had.
       */
      unreachable()
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'stale-token'

      const error = await auth.renew().catch((e) => e)

      expect(error).toBeInstanceOf(TypeError)
      expect(auth.user).toEqual({ username: 'aragorn' })
      expect(auth.token).toBe('stale-token')
    })

    it('keeps the session on a 5xx, which is the same situation with a status', async () => {
      /* nginx answering while the backend restarts. It arrives as an `ApiError`,
       * which is the only reason it needs saying separately. */
      serve({ 'POST /users/refresh': respond(503) })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'stale-token'

      const error = await auth.renew().catch((e) => e)

      expect(error.status).toBe(503)
      expect(auth.isSignedIn).toBe(true)
      expect(auth.token).toBe('stale-token')
    })

    it('ends the session on a 429, revoking it server-side first', async () => {
      /*
       * The emergency stop, and it has to be a real one. Clearing locally alone
       * would leave the refresh cookie alive: once the window passed, a reload
       * would sign this person back in without a password and nobody would have
       * started over.
       */
      const calls = serve({
        'POST /users/refresh': respond(
          429,
          { detail: 'Too many requests from here.' },
          { 'Retry-After': '42' },
        ),
        'POST /users/logout': respond(204),
      })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'stale-token'

      const error = await auth.renew().catch((e) => e)

      expect(error.status).toBe(429)
      expect(calls).toEqual(['POST /users/refresh', 'POST /users/logout'])
      expect(auth.isSignedIn).toBe(false)
      expect(auth.token).toBeNull()
    })

    it('keeps the server sentence and the wait, for the login page to show', async () => {
      serve({
        'POST /users/refresh': respond(
          429,
          { detail: 'Too many requests from here.' },
          { 'Retry-After': '42' },
        ),
        'POST /users/logout': respond(204),
      })
      const auth = useAuthStore()

      await auth.renew().catch(() => {})

      // The sentence is the server's — copy about limits belongs where the
      // limits are — and the wait is what stops the reader retrying at once.
      expect(auth.signedOutReason).toEqual({
        message: 'Too many requests from here.',
        retryAfter: 42,
      })
    })

    it('still stops, and still explains, when the logout call fails too', async () => {
      /* A soft stop beats a stuck client: the alternative is somebody who cannot
       * leave, still holding a cookie the server is refusing to talk about. */
      serve({
        'POST /users/refresh': respond(429, { detail: 'Too many requests from here.' }),
        'POST /users/logout': respond(429, { detail: 'Too many requests from here.' }),
      })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'stale-token'

      await auth.renew().catch(() => {})

      expect(auth.isSignedIn).toBe(false)
      expect(auth.signedOutReason.message).toBe('Too many requests from here.')
    })

    it('hands the reason over once, so it explains one arrival at the login page', async () => {
      serve({
        'POST /users/refresh': respond(429, { detail: 'Too many requests from here.' }),
        'POST /users/logout': respond(204),
      })
      const auth = useAuthStore()

      await auth.renew().catch(() => {})

      expect(auth.takeSignedOutReason().message).toBe('Too many requests from here.')
      // Left in place it would greet whoever opens the login page next week
      // with an explanation of a session that ended long ago.
      expect(auth.takeSignedOutReason()).toBeNull()
    })
  })

  describe('logIn', () => {
    it('signs in with a form-encoded body', async () => {
      /* The one endpoint that is not JSON, and deliberately so: it is FastAPI's
       * OAuth2 password flow, which keeps Swagger's Authorize button working. */
      serve({ 'POST /users/login': A_SESSION, 'GET /users/me': A_USER })
      const auth = useAuthStore()

      await auth.logIn('aragorn', 'strider123')

      const [, init] = globalThis.fetch.mock.calls[0]
      expect(init.headers['Content-Type']).toBe('application/x-www-form-urlencoded')
      expect(init.body).toBe('username=aragorn&password=strider123')
      expect(auth.isSignedIn).toBe(true)
    })

    it('surfaces bad credentials for the form to show, and stays signed out', async () => {
      serve({ 'POST /users/login': respond(401, { detail: 'Incorrect username or password' }) })
      const auth = useAuthStore()

      const error = await auth.logIn('aragorn', 'wrong').catch((e) => e)

      expect(error.status).toBe(401)
      expect(auth.isSignedIn).toBe(false)
    })
  })

  describe('register', () => {
    it('signs the new account in, with no second call', async () => {
      serve({
        'POST /users/register': respond(201, { access_token: 'fresh-token' }),
        'GET /users/me': A_USER,
      })
      const auth = useAuthStore()

      await auth.register('aragorn', 'aragorn@gondor.test', 'strider123')

      const [, init] = globalThis.fetch.mock.calls[0]
      expect(init.headers['Content-Type']).toBe('application/json')
      expect(auth.isSignedIn).toBe(true)
    })

    it('surfaces a taken username as a 409 the username field can key on', async () => {
      serve({ 'POST /users/register': respond(409, { detail: 'Username already exists' }) })

      const error = await useAuthStore()
        .register('aragorn', 'a@b.test', 'strider123')
        .catch((e) => e)

      expect(error.status).toBe(409)
    })
  })

  describe('logOut', () => {
    it('revokes server-side before clearing anything locally', async () => {
      /* Clearing only the client would leave a working refresh cookie behind,
       * which is the one way to log out that does not log you out. */
      const calls = serve({ 'POST /users/logout': respond(204) })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }
      auth.token = 'a-token'

      await auth.logOut()

      expect(calls).toEqual(['POST /users/logout'])
      expect(auth.isSignedIn).toBe(false)
      expect(auth.token).toBeNull()
    })

    it('clears local state even if the call never lands', async () => {
      globalThis.fetch = vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      })
      const auth = useAuthStore()
      auth.user = { username: 'aragorn' }

      await auth.logOut().catch(() => {})

      expect(auth.isSignedIn).toBe(false)
    })
  })

  /*
   * The remembered campaign is the one thing this store leaves on disk (#59).
   * Everything else has always been memory-only, which is why these are worth
   * asserting rather than assuming: the failure mode is not an error message,
   * it is the app quietly opening somebody else's campaign.
   */
  describe('the remembered campaign', () => {
    beforeEach(() => {
      forgetCurrentCampaign()
    })

    it('is forgotten when a session ends', async () => {
      serve({ 'POST /users/logout': respond(204) })
      rememberCurrentCampaign('c-1')

      await useAuthStore().logOut()

      expect(readCurrentCampaign()).toBeNull()
    })

    it('is forgotten when somebody signs in', async () => {
      serve({ 'POST /users/login': A_SESSION, 'GET /users/me': A_USER })
      rememberCurrentCampaign('c-1')

      await useAuthStore().logIn('aragorn', 'a-password')

      /*
       * Not covered by the logout case: the refresh window is absolute and does
       * not slide, so a session that simply expires never calls logout. That
       * person meets a login form, and without this they would be dropped into
       * a campaign that may not be theirs.
       */
      expect(readCurrentCampaign()).toBeNull()
    })

    it('is forgotten when a refresh fails, which is a session ending too', async () => {
      serve({ 'POST /users/refresh': respond(401) })
      rememberCurrentCampaign('c-1')

      await useAuthStore().boot()

      expect(readCurrentCampaign()).toBeNull()
    })

    it('survives a boot that could not reach the API at all', async () => {
      /* Forgetting it here would be the sign-out showing through by another
       * route: the session was never ended, so nothing about it should be. */
      unreachable()
      rememberCurrentCampaign('c-1')

      await useAuthStore().boot()

      expect(readCurrentCampaign()).toBe('c-1')
    })

    it('survives a boot that restores the session, which is the whole point', async () => {
      serve({ 'POST /users/refresh': A_SESSION, 'GET /users/me': A_USER })
      rememberCurrentCampaign('c-1')

      await useAuthStore().boot()

      // A cold open with a live cookie is the case that should land you back
      // where you were. Clearing here would make the feature do nothing.
      expect(readCurrentCampaign()).toBe('c-1')
    })
  })
})
