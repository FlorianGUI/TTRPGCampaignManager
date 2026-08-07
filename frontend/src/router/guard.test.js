import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { createAppRouter } from './index.js'
import { useAuthStore } from '../stores/auth.js'

/*
 * The guard, driven through the real router rather than by calling it directly:
 * what matters is where a navigation ends up, and that is the router's answer
 * rather than the guard's return value.
 */

function respond(status, body) {
  return { ok: status < 400, status, json: async () => body ?? {} }
}

function router() {
  return createAppRouter(createMemoryHistory())
}

// jsdom has no scrollTo, and a real navigation calls it via scrollBehavior.
beforeAll(() => {
  window.scrollTo = vi.fn()
})

describe('the route guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete globalThis.fetch
  })

  it('sends a signed-out visitor to the login page', async () => {
    const auth = useAuthStore()
    auth.ready = true

    const r = router()
    await r.push('/')

    expect(r.currentRoute.value.name).toBe('login')
  })

  it('remembers where they were going, so it can be restored after signing in', async () => {
    const auth = useAuthStore()
    auth.ready = true

    const r = router()
    await r.push('/library?q=owlbear')

    expect(r.currentRoute.value.query.redirect).toBe('/library?q=owlbear')
  })

  it('lets a signed-in user through', async () => {
    const auth = useAuthStore()
    auth.ready = true
    auth.user = { id: 'u-1', username: 'aragorn' }

    const r = router()
    await r.push('/')

    expect(r.currentRoute.value.name).toBe('home')
  })

  it('lets anyone reach the login and sign-up pages', async () => {
    useAuthStore().ready = true

    const r = router()
    await r.push('/signup')

    expect(r.currentRoute.value.name).toBe('signup')
  })

  it('waits for the boot refresh before judging anyone', async () => {
    /*
     * The failure this exists to prevent: on a cold load the first navigation
     * happens while the refresh is still in flight, and a guard that read
     * isSignedIn right then would bounce a perfectly valid session to the login
     * page. Here the session only arrives once boot() has run — so if the guard
     * does not wait for it, this test lands on 'login'.
     */
    globalThis.fetch = vi.fn(async (url) =>
      String(url).endsWith('/users/refresh')
        ? respond(200, { access_token: 'fresh-token' })
        : respond(200, { id: 'u-1', username: 'aragorn' }),
    )

    const auth = useAuthStore()
    expect(auth.ready).toBe(false)

    const r = router()
    await r.push('/')

    expect(r.currentRoute.value.name).toBe('home')
    expect(auth.isSignedIn).toBe(true)
  })

  it('does not start a second refresh when one is already running', async () => {
    const fetch = vi.fn(async (url) =>
      String(url).endsWith('/users/refresh')
        ? respond(200, { access_token: 'fresh-token' })
        : respond(200, { id: 'u-1', username: 'aragorn' }),
    )
    globalThis.fetch = fetch

    const auth = useAuthStore()
    // main.js starts it before mount; the guard has to join that one rather
    // than send the cookie a second time — a replayed refresh token revokes the
    // whole session (#35), so a duplicate here signs the user out.
    const started = auth.boot()

    const r = router()
    await Promise.all([started, r.push('/')])

    const refreshes = fetch.mock.calls.filter(([url]) => String(url).endsWith('/users/refresh'))
    expect(refreshes).toHaveLength(1)
  })
})
