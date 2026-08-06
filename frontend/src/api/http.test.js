import { describe, it, expect, vi } from 'vitest'
import { API_URL, ApiError, apiFetch } from './http.js'

function respond(status, body) {
  return {
    ok: status < 400,
    status,
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

  // Skipped for anyone who has deliberately overridden the base in .env.local;
  // CI has no such file, which is the run that matters here.
  it.skipIf(import.meta.env.VITE_API_URL)(
    'defaults to a same-origin base, so no API host is baked into the build',
    () => {
      /*
       * The guard on the one thing here that fails only in production: a base
       * URL carrying a scheme and host is a bundle correct in exactly one
       * environment, and silently wrong in every other.
       */
      expect(API_URL).toBe('/api')
    },
  )

  it('always sends credentials, so the refresh cookie travels', async () => {
    /*
     * Same-origin would send the cookie without this, but the base URL is
     * overridable: point VITE_API_URL at another host and the browser stops
     * storing or returning the cookie, ending every session at the first
     * reload.
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
})
