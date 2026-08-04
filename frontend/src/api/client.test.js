import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { request } from './client.js'
import { useAuthStore } from '../stores/auth.js'

function respond(status, body) {
  return { ok: status < 400, status, json: async () => body ?? {} }
}

/*
 * Routes answer from a queue, so one path can give a different answer the
 * second time — which is the whole subject here: a request that 401s, then
 * succeeds once the token behind it has been renewed.
 */
function serve(routes) {
  const calls = []
  globalThis.fetch = vi.fn(async (url, init = {}) => {
    const key = `${init.method ?? 'GET'} ${new URL(url).pathname}`
    calls.push({ key, token: init.headers.Authorization })
    const answers = routes[key]
    if (!answers) throw new Error(`no route for ${key}`)
    return answers.length > 1 ? answers.shift() : answers[0]
  })
  return calls
}

function countOf(calls, key) {
  return calls.filter((call) => call.key === key).length
}

describe('request', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete globalThis.fetch
  })

  it('attaches the access token the store is holding', async () => {
    const calls = serve({ 'GET /campaigns/': [respond(200, [])] })
    useAuthStore().token = 'a-token'

    await request('/campaigns/')

    expect(calls[0].token).toBe('Bearer a-token')
  })

  it('renews an expired token and retries, so the caller never sees the 401', async () => {
    /*
     * With a 15-minute access token this is the ordinary course of a session
     * rather than an exception, which is why it lives here and not in callers.
     */
    const calls = serve({
      'GET /campaigns/': [
        respond(401, { detail: 'Could not validate credentials' }),
        respond(200, ['a campaign']),
      ],
      'POST /users/refresh': [respond(200, { access_token: 'fresh-token' })],
    })
    const auth = useAuthStore()
    auth.token = 'expired-token'

    expect(await request('/campaigns/')).toEqual(['a campaign'])

    expect(calls.map((call) => call.key)).toEqual([
      'GET /campaigns/',
      'POST /users/refresh',
      'GET /campaigns/',
    ])
    expect(calls[2].token).toBe('Bearer fresh-token')
  })

  it('renews once for a screenful of requests that expire together', async () => {
    /*
     * Four panels loading at once all 401 at the same moment. Rotation makes
     * the naive version worse than wasteful: three of those refreshes would
     * present an already-spent token, which revokes the session.
     */
    const calls = serve({
      'GET /campaigns/': [respond(401), respond(200, [])],
      'GET /sources/': [respond(401), respond(200, [])],
      'GET /users/me': [respond(401), respond(200, {})],
      'POST /users/refresh': [respond(200, { access_token: 'fresh-token' })],
    })
    useAuthStore().token = 'expired-token'

    await Promise.all([request('/campaigns/'), request('/sources/'), request('/users/me')])

    expect(countOf(calls, 'POST /users/refresh')).toBe(1)
  })

  it('gives up after one retry rather than looping', async () => {
    const calls = serve({
      'GET /campaigns/': [respond(401)],
      'POST /users/refresh': [respond(200, { access_token: 'fresh-token' })],
    })
    useAuthStore().token = 'expired-token'

    const error = await request('/campaigns/').catch((e) => e)

    expect(error.status).toBe(401)
    expect(countOf(calls, 'POST /users/refresh')).toBe(1)
    expect(countOf(calls, 'GET /campaigns/')).toBe(2)
  })

  it('signs the app out when the session is genuinely over', async () => {
    const calls = serve({
      'GET /campaigns/': [respond(401)],
      'POST /users/refresh': [respond(401, { detail: 'Could not renew the session' })],
    })
    const auth = useAuthStore()
    auth.user = { username: 'aragorn' }
    auth.token = 'expired-token'

    const error = await request('/campaigns/').catch((e) => e)

    expect(error.status).toBe(401)
    expect(auth.isSignedIn).toBe(false)
    // The failed request is not tried a second time — there is nothing left to
    // try it with, and retrying is how a redirect loop starts.
    expect(countOf(calls, 'GET /campaigns/')).toBe(1)
  })

  it('leaves every other failure alone', async () => {
    /* A 404 means "not there, or not yours" — the API will not say which (#41).
     * It is an answer, not an expired token, and refreshing would tell us
     * nothing new. */
    const calls = serve({ 'GET /campaigns/nope': [respond(404, { detail: 'Campaign not found' })] })
    useAuthStore().token = 'a-token'

    const error = await request('/campaigns/nope').catch((e) => e)

    expect(error.status).toBe(404)
    expect(countOf(calls, 'POST /users/refresh')).toBe(0)
  })
})
