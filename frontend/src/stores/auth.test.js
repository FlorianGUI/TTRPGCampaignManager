import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth.js'
import { API_URL, ApiError } from '../api/http.js'

/*
 * These drive the real transport against a stubbed `fetch`, rather than mocking
 * api/http.js. The method, the encoding and `credentials: 'include'` are part of
 * what this store has to get right — a mock at the module boundary would assert
 * that we called our own function.
 */

function respond(status, body) {
  return {
    ok: status < 400,
    status,
    json: async () => body ?? {},
  }
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
      globalThis.fetch = vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      })
      const auth = useAuthStore()

      await auth.boot()

      expect(auth.ready).toBe(true)
      expect(auth.isSignedIn).toBe(false)
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
})
