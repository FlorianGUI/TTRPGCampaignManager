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
  {
    path: '/styleguide',
    name: 'styleguide',
    // Lazy: the reference is shipped so it is reachable in deployed
    // environments, but it is a big page nobody loads on first paint.
    component: () => import('../views/StyleguideView.vue'),
    meta: { title: 'Styleguide' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { title: 'Not found' },
  },
]

export default routes
