import { ApiError, apiFetch } from './http.js'
import { useAuthStore } from '../stores/auth.js'

/*
 * The client every feature store calls. It attaches the access token and, when
 * one has expired, renews it and tries again — once.
 *
 * With a 15-minute access token that second path is the normal course of a
 * session rather than an exception, which is why it lives here instead of in
 * each caller. The store's `renew` is single-flight, so a screenful of requests
 * expiring together produces one refresh between them.
 *
 * The auth store's own four calls do not come through here: signing in,
 * refreshing and signing out go straight to `apiFetch`, so a refresh can never
 * be intercepted by the 401 handling that exists to serve it. That is what
 * keeps this from looping.
 */
export async function request(path, options = {}) {
  const auth = useAuthStore()

  try {
    return await apiFetch(path, { ...options, token: auth.token })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error

    // Renewing throws if the session is genuinely over, having cleared the
    // store on its way out. Letting that propagate is deliberate: the caller
    // gets one 401 and the app is signed out, rather than a second round of
    // retries against a session that no longer exists.
    await auth.renew()

    return apiFetch(path, { ...options, token: auth.token })
  }
}

export { ApiError, API_URL } from './http.js'
