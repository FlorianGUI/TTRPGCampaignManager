/*
 * The transport, and nothing else: it builds a request, sends it, and turns a
 * failure into something a caller can branch on. It knows no auth state.
 *
 * That separation is what stops the refresh logic in `client.js` from calling
 * itself. The auth store signs in, refreshes and signs out through here
 * directly, so those three calls can never be intercepted by the very 401
 * handling they exist to serve.
 */

// Relative, and that is the point: the API is reached at a same-origin /api,
// which nginx proxies in production and the Vite server proxies in development.
// A relative base means no API host is baked into the bundle, so the artifact CI
// builds is correct wherever it is served — the failure mode being avoided is a
// deploy that ships a build carrying the wrong host, which breaks only in
// production and only for everyone.
//
// VITE_API_URL still overrides it, for pointing a local build at an API
// somewhere else. Nothing in CI sets it, and production must not.
export const API_URL = import.meta.env.VITE_API_URL ?? '/api'

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `Request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    // FastAPI's `detail`: a string for the errors we raise, an array of field
    // problems for a 422. Kept as it arrived — a form keys off `status` for
    // everything we currently need, and inventing a shape here would be
    // inventing one the backend does not promise.
    this.detail = detail
  }
}

async function detailOf(response) {
  try {
    return (await response.json()).detail ?? null
  } catch {
    // An error page, an empty body, a proxy in a bad mood.
    return null
  }
}

/**
 * Send one request. Returns the parsed body, `null` for a 204, or throws
 * `ApiError`.
 *
 * `credentials: 'include'` outlives the same-origin proxy that made it
 * redundant. Same-origin would carry the refresh cookie under the default
 * `same-origin` policy anyway, but `include` is also correct there, and it is
 * the difference between working and silently ending every session at the first
 * reload the moment VITE_API_URL points somewhere else. The backend answers with
 * `allow_credentials=True` against an explicit origin list, which is what makes
 * that legal when it happens.
 */
export async function apiFetch(
  path,
  { method = 'GET', json, form, token, fetch = globalThis.fetch } = {},
) {
  const headers = {}
  let body

  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  }

  if (form !== undefined) {
    // The one endpoint that takes this is POST /users/login, and it stays that
    // way deliberately: it is FastAPI's OAuth2 password flow, which is what
    // keeps Swagger's Authorize button signing in against the real endpoint
    // (#33). Everything else in the API is JSON. Don't "fix" it.
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    body = new URLSearchParams(form).toString()
  }

  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body,
    credentials: 'include',
  })

  if (!response.ok) throw new ApiError(response.status, await detailOf(response))
  if (response.status === 204) return null

  return response.json()
}
