/*
 * The transport, and nothing else: it builds a request, sends it, and turns a
 * failure into something a caller can branch on. It knows no auth state.
 *
 * That separation is what stops the refresh logic in `client.js` from calling
 * itself. The auth store signs in, refreshes and signs out through here
 * directly, so those three calls can never be intercepted by the very 401
 * handling they exist to serve.
 */

/*
 * Where the API lives, read at runtime rather than compiled in.
 *
 * `config.js` is written on the server at deploy time from an environment
 * variable there, and `index.html` loads it before this module runs. Vite would
 * otherwise substitute a host at build time, which makes the artifact correct in
 * exactly one environment — the bug that shipped a bundle calling
 * localhost:8000. Nothing in the bundle names a host now, so the same dist/ is
 * deployable anywhere and moving the API is an env var and a restart.
 *
 * It fails closed. A production build with no config has nothing sensible to
 * fall back to: falling back to localhost would reintroduce exactly the failure
 * this exists to prevent, and it would do it silently, in production, for
 * everyone. Better to refuse to start and say why.
 */
function resolveApiUrl() {
  const configured = globalThis.__CONFIG__?.apiUrl

  if (configured) return configured

  if (import.meta.env.DEV) return 'http://localhost:8000'

  throw new Error(
    'No apiUrl in window.__CONFIG__. /config.js is written by the deploy from ' +
      'FRONTEND_API_URL on the server — it is missing, empty, or was not served.',
  )
}

export const API_URL = resolveApiUrl()

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
 * `credentials: 'include'` is not optional and is not a precaution. The API is a
 * different origin in every environment — `api.lastdawn.fr` from `lastdawn.fr`,
 * `:8000` from `:5173` — so without it the browser neither stores the refresh
 * cookie nor sends it back, and every session ends at the first reload. The
 * backend answers with `allow_credentials=True` against an explicit origin list,
 * which is what makes that legal.
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
