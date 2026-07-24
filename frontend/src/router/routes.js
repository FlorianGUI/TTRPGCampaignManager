import SpikeView from '../views/SpikeView.vue'

/*
 * Route table, kept apart from the router instance so it can be imported by
 * tests without creating a router.
 *
 * Conventions for routes added later:
 *  - every route is named; link and navigate by name, never by hand-built path
 *  - the landing route for a section is eagerly imported, everything else is
 *    lazy, so the initial bundle only carries what the first paint needs
 *  - the catch-all stays last
 */
export const routes = [
  {
    path: '/',
    name: 'home',
    component: SpikeView,
    meta: { title: 'Session notes' },
  },
  /*
   * Dev-only. `import.meta.env.DEV` is substituted with a literal at build
   * time, so this whole branch — and with it the dynamic import — is dropped
   * from the production bundle rather than merely hidden: the view is not
   * shipped, not code-split into a chunk, and /styleguide falls through to the
   * catch-all in a deployed build.
   *
   * Keep the condition as a bare `import.meta.env.DEV` literal. Hiding it
   * behind a variable or a parameter defeats the static elimination and the
   * chunk comes back.
   */
  ...(import.meta.env.DEV
    ? [
        {
          path: '/styleguide',
          name: 'styleguide',
          component: () => import('../views/StyleguideView.vue'),
          meta: { title: 'Styleguide' },
        },
      ]
    : []),
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: 'Not found' },
  },
]

export default routes
