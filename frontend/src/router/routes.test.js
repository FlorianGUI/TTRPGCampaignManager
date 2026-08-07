import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { routes } from './routes.js'
import { createAppRouter, APP_TITLE } from './index.js'
import { useAuthStore } from '../stores/auth.js'

/*
 * Guards the routing conventions rather than the routes themselves: those will
 * churn as features land, but a route that loses its name or a catch-all that
 * stops being last breaks navigation everywhere at once.
 */

// jsdom has no scrollTo, and a real navigation calls it via scrollBehavior.
beforeAll(() => {
  window.scrollTo = vi.fn()
})

describe('routes', () => {
  it('names every route, so navigation never has to build a path by hand', () => {
    for (const route of routes) {
      expect(route.name, route.path).toBeTruthy()
    }
  })

  it('keeps the catch-all last, or it would swallow everything after it', () => {
    const catchAllIndex = routes.findIndex((r) => r.path.includes(':pathMatch'))

    expect(catchAllIndex).toBe(routes.length - 1)
  })

  it('lazy-loads everything except the landing route', () => {
    const [landing, ...rest] = routes

    expect(typeof landing.component).toBe('object')
    for (const route of rest) {
      expect(typeof route.component, route.name).toBe('function')
    }
  })

  it('registers the styleguide in dev and not in a production build', () => {
    // The route table is built from a literal the bundler substitutes, so this
    // tracks whichever mode the suite runs in rather than asserting a constant.
    const hasStyleguide = routes.some((r) => r.name === 'styleguide')

    expect(hasStyleguide).toBe(import.meta.env.DEV)
  })

  it('gives every route a title to build the document title from', () => {
    for (const route of routes) {
      expect(route.meta?.title, route.name).toBeTruthy()
    }
  })
})

describe('createAppRouter', () => {
  /*
   * Every route but /login and /signup is behind the guard now, and the guard
   * reads the auth store — so these need a pinia, and the ones that navigate
   * need someone signed in or they end up on the login page instead.
   */
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sets the document title from the matched route', async () => {
    const auth = useAuthStore()
    auth.ready = true
    auth.user = { id: 'u-1', username: 'aragorn' }

    const router = createAppRouter(createMemoryHistory())

    // not-found rather than styleguide: it is the one route present in every
    // build mode, so this doesn't depend on the dev-only gating above.
    await router.push('/no-such-page')
    await router.isReady()

    expect(document.title).toBe(`Not found — ${APP_TITLE}`)
  })

  it('resolves an unknown path to the not-found route rather than failing', () => {
    const router = createRouter({ history: createMemoryHistory(), routes })

    expect(router.resolve('/no-such-page').name).toBe('not-found')
  })

  it('scrolls to the top on a forward navigation and restores on back', () => {
    const router = createAppRouter(createMemoryHistory())
    const saved = { top: 420, left: 0 }

    expect(router.options.scrollBehavior({}, {}, saved)).toBe(saved)
    expect(router.options.scrollBehavior({ hash: '' }, {}, null)).toEqual({ top: 0 })
    expect(router.options.scrollBehavior({ hash: '#x' }, {}, null)).toEqual({
      el: '#x',
      behavior: 'smooth',
    })
  })
})
