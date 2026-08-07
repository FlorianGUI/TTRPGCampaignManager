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
 *  - `meta.public: true` marks the handful of routes a signed-out visitor may
 *    reach. Everything else is behind the guard, so forgetting the flag fails
 *    closed — a new page is private until it says otherwise
 *  - `meta.layout: 'auth'` asks App.vue for the bare chrome instead of the
 *    campaign shell
 */
export const routes = [
  {
    path: '/',
    name: 'home',
    component: SpikeView,
    meta: { title: 'Session notes' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Sign in', public: true, layout: 'auth' },
  },
  {
    path: '/signup',
    name: 'signup',
    component: () => import('../views/SignupView.vue'),
    meta: { title: 'Create an account', public: true, layout: 'auth' },
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { title: 'Reset your password', public: true, layout: 'auth' },
  },
  /*
   * Where a reset link lands, and public for the same reason /verify-email is:
   * whoever follows it is by definition unable to sign in.
   */
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('../views/ResetPasswordView.vue'),
    meta: { title: 'Choose a new password', public: true, layout: 'auth' },
  },
  /*
   * Where a verification link lands. Public because the common case is opening
   * the mail on a phone that has never signed in — a guard here would turn a
   * working link into a login prompt (#38).
   */
  {
    path: '/verify-email',
    name: 'verify-email',
    component: () => import('../views/VerifyEmailView.vue'),
    meta: { title: 'Confirm your address', public: true, layout: 'auth' },
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
