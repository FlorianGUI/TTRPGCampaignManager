import { describe, it, expect, afterEach, vi } from 'vitest'
import { API_URL, ApiError, apiFetch } from './http.js'

function respond(status, body, headers = {}) {
  return {
    ok: status < 400,
    status,
    headers: new Headers(headers),
    json: async () => {
      if (body === undefined) throw new SyntaxError('Unexpected end of JSON input')
      return body
    },
  }
}

function spyFetch(response = respond(200, {})) {
  return vi.fn(async () => response)
}

describe('apiFetch', () => {
  it('sends the path against the configured base URL', async () => {
    const fetch = spyFetch()

    await apiFetch('/users/me', { fetch })

    expect(fetch).toHaveBeenCalledWith(`${API_URL}/users/me`, expect.anything())
  })

  it('always sends credentials, so the refresh cookie travels', async () => {
    /*
     * Not a precaution. The API is a different origin everywhere it runs, so
     * without this the browser neither stores the cookie nor sends it back —
     * and every session would end at the first reload.
     */
    const fetch = spyFetch()

    await apiFetch('/users/me', { fetch })

    expect(fetch.mock.calls[0][1].credentials).toBe('include')
  })

  it('attaches the bearer token when there is one', async () => {
    const fetch = spyFetch()

    await apiFetch('/users/me', { token: 'a-token', fetch })

    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer a-token')
  })

  it('sends no Authorization header when there is no token', async () => {
    const fetch = spyFetch()

    await apiFetch('/users/refresh', { method: 'POST', fetch })

    expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })

  it('sends a JSON body as JSON', async () => {
    const fetch = spyFetch(respond(201, {}))

    await apiFetch('/users/register', { method: 'POST', json: { username: 'aragorn' }, fetch })

    const [, init] = fetch.mock.calls[0]
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe('{"username":"aragorn"}')
  })

  it('form-encodes a form body, which login alone needs', async () => {
    const fetch = spyFetch()

    await apiFetch('/users/login', {
      method: 'POST',
      form: { username: 'aragorn', password: 'strider 123' },
      fetch,
    })

    const [, init] = fetch.mock.calls[0]
    expect(init.headers['Content-Type']).toBe('application/x-www-form-urlencoded')
    expect(init.body).toBe('username=aragorn&password=strider+123')
  })

  it('returns the parsed body', async () => {
    const fetch = spyFetch(respond(200, { username: 'aragorn' }))

    expect(await apiFetch('/users/me', { fetch })).toEqual({ username: 'aragorn' })
  })

  it('returns null for a 204, which is what logout answers', async () => {
    const fetch = spyFetch(respond(204))

    expect(await apiFetch('/users/logout', { method: 'POST', fetch })).toBeNull()
  })

  it('throws an ApiError carrying the status a form can key on', async () => {
    const fetch = spyFetch(respond(409, { detail: 'Username already exists' }))

    const error = await apiFetch('/users/register', { method: 'POST', fetch }).catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.detail).toBe('Username already exists')
  })

  it('still throws a usable error when the body is not JSON at all', async () => {
    /* A proxy's error page, or an empty body. Neither should surface as a
     * SyntaxError from somewhere inside the client. */
    const fetch = spyFetch(respond(502))

    const error = await apiFetch('/users/me', { fetch }).catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(502)
    expect(error.detail).toBeNull()
    expect(error.message).toContain('502')
  })

  it('carries Retry-After, which is the only header a page can act on', async () => {
    /* The backend sends it and `cors.py` exposes it across origins for exactly
     * this; dropping it here made both of those pointless (#68). */
    const fetch = spyFetch(respond(429, { detail: 'Too many requests.' }, { 'Retry-After': '42' }))

    const error = await apiFetch('/users/refresh', { method: 'POST', fetch }).catch((e) => e)

    expect(error.retryAfter).toBe(42)
  })

  it('has no wait to report when the response does not say', async () => {
    const fetch = spyFetch(respond(409, { detail: 'Username already exists' }))

    const error = await apiFetch('/users/register', { method: 'POST', fetch }).catch((e) => e)

    expect(error.retryAfter).toBeNull()
  })

  it('reports no wait rather than a wrong one when the header is a date', async () => {
    /*
     * `Retry-After` may legally be an HTTP-date, and nothing here can act on
     * one. `Number('Wed, 21 Oct 2015 07:28:00 GMT')` is NaN — the danger is
     * a parse that quietly produces a number instead.
     */
    const headers = { 'Retry-After': 'Wed, 21 Oct 2015 07:28:00 GMT' }
    const fetch = spyFetch(respond(429, { detail: 'Too many requests.' }, headers))

    const error = await apiFetch('/users/refresh', { method: 'POST', fetch }).catch((e) => e)

    expect(error.retryAfter).toBeNull()
  })
})

/*
 * The base URL is decided once, when the module is first imported, so each of
 * these has to import it fresh against a different environment. `resetModules`
 * is what makes that possible — without it the second case would keep the first
 * one's answer.
 */
describe('API_URL', () => {
  afterEach(() => {
    delete globalThis.__CONFIG__
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  async function freshApiUrl() {
    vi.resetModules()
    return (await import('./http.js')).API_URL
  }

  it('takes the host the server put in window.__CONFIG__', async () => {
    globalThis.__CONFIG__ = { apiUrl: 'https://api.lastdawn.fr' }

    expect(await freshApiUrl()).toBe('https://api.lastdawn.fr')
  })

  it('falls back to the local API in development, where there is no deploy to write one', async () => {
    vi.stubEnv('DEV', true)

    expect(await freshApiUrl()).toBe('http://localhost:8000')
  })

  it('refuses to start a production build with no config, rather than guessing', async () => {
    /*
     * The whole point of the change, and the one case that can only go wrong in
     * production. Falling back to localhost here would be the original bug
     * again: every visitor's browser calling their own machine, silently, and
     * only once it is deployed.
     */
    vi.stubEnv('DEV', false)

    await expect(freshApiUrl()).rejects.toThrow(/config\.js/)
  })
})
