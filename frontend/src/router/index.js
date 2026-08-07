import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes.js'
import { useAuthStore } from '../stores/auth.js'

export const APP_TITLE = 'TTRPG Campaign Manager'

export function createAppRouter(history = createWebHistory(import.meta.env.BASE_URL)) {
  const router = createRouter({
    history,
    routes,

    /*
     * The document is the scroller (issue #25), so the browser's own restoration
     * works — return `savedPosition` on back/forward and let it win.
     */
    scrollBehavior(to, from, savedPosition) {
      if (savedPosition) return savedPosition
      if (to.hash) return { el: to.hash, behavior: 'smooth' }
      return { top: 0 }
    },
  })

  /*
   * The guard. Private by default: a route is reachable signed out only if it
   * says `meta.public`, so a page added without thinking about auth is behind
   * the guard rather than in front of it.
   *
   * `await auth.boot()` is the part that is easy to leave out and impossible to
   * see missing in development, where the refresh returns before you can blink.
   * On a cold load the first navigation happens while that request is still in
   * flight, and a guard that read `isSignedIn` then would send every returning
   * user to the login page — on a slow connection, every time. boot() is
   * idempotent, so this waits for the one main.js already started rather than
   * making a second.
   *
   * The destination travels as `?redirect=`, and `replace: true` keeps the
   * guarded URL out of history — otherwise Back from the login page returns to
   * a page the visitor still cannot see, and bounces them straight here again.
   */
  router.beforeEach(async (to) => {
    if (to.meta.public) return true

    const auth = useAuthStore()
    if (!auth.ready) await auth.boot()

    if (auth.isSignedIn) return true

    return { name: 'login', query: { redirect: to.fullPath }, replace: true }
  })

  // The title is the only chrome outside the Vue tree, so it is set here rather
  // than in a component.
  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} — ${APP_TITLE}` : APP_TITLE
  })

  return router
}

export default createAppRouter
