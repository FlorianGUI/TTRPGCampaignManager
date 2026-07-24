import { createRouter, createWebHistory } from 'vue-router'
import { routes } from './routes.js'

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

  // The title is the only chrome outside the Vue tree, so it is set here rather
  // than in a component.
  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} — ${APP_TITLE}` : APP_TITLE
  })

  return router
}

export default createAppRouter
