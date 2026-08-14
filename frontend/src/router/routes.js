import HomeView from '../views/HomeView.vue'
import { useCampaignsStore } from '../stores/campaigns.js'
import { forgetCurrentCampaign, readCurrentCampaign } from '../stores/currentCampaign.js'

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
 *  - `meta.layout` names the chrome App.vue should wrap the view in: `auth` for
 *    the signed-out column, `bare` for the pages above any campaign. Saying
 *    nothing gets the campaign shell, which is what all but a handful want
 */

/*
 * Go straight into the campaign you were last in, if there is one.
 *
 * This is the whole of the "where do I land" rule from #59, and it is one line
 * of logic on purpose: a remembered id means go there, no id means show the
 * chooser. The two exceptions people asked for — just signed in, just left a
 * campaign — are not special cases here. They are handled by *clearing* the id
 * at those moments (`logIn`, `logOut`, the SSO callback, the exit chip), which
 * is why a page reload cannot desynchronise this and there is no flag to keep
 * in step.
 *
 * The list is fetched before deciding rather than after. The chooser needs it
 * anyway, `ensureLoaded` is single-flight, and it is what separates "this
 * campaign is gone" from "this campaign is not mine" — both of which arrive as
 * an id that is simply not in the list.
 */
export async function enterRememberedCampaign() {
  const campaignId = readCurrentCampaign()
  if (!campaignId) return true

  const campaigns = useCampaignsStore()
  await campaigns.ensureLoaded()

  /*
   * Could not ask. Keep the id and show the chooser, which renders the failure
   * and offers a retry — forgetting here would punish a dropped connection by
   * losing a preference that is probably still correct.
   */
  if (!campaigns.loaded) return true

  // Deleted, or belonging to whoever used this browser last. Either way it is
  // not a campaign this user can open, and it should not be tried again.
  if (!campaigns.byId(campaignId)) {
    forgetCurrentCampaign()
    return true
  }

  /*
   * The structure, which is where the chooser's own cards go. Being returned to
   * the campaign you left should put you where choosing it would have — landing
   * somewhere else depending on whether you clicked a card or were remembered
   * here is the kind of difference that reads as a bug.
   *
   * `replace`, so Back from the campaign does not land on a `/` that bounces
   * straight here again — an entry no one can ever get past.
   */
  return { name: 'campaign-structure', params: { campaignId }, replace: true }
}

export const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    beforeEnter: enterRememberedCampaign,
    meta: { title: 'Your campaigns', layout: 'bare' },
  },
  /*
   * Inside a campaign. The id is in the path rather than only in storage, so a
   * campaign page can be bookmarked and two tabs can sit in two campaigns —
   * neither of which `active_campaign_id` on `users` would have given us (#14).
   *
   * `SpikeView` stands in for session notes until that context exists. It is no
   * longer the landing route, which is what #59 set out to fix: its counts come
   * from `content/sample.js` and are invented.
   *
   * Nothing links here any more — opening a campaign goes to its structure — so
   * the route is reachable by URL and by nothing else. Left standing rather than
   * deleted because #52 is the context that will fill it, and a path that has
   * been bookmarked should not start answering 404 in the meantime.
   */
  {
    path: '/campaigns/:campaignId/sessions',
    name: 'campaign-sessions',
    component: () => import('../views/SpikeView.vue'),
    meta: { title: 'Session notes' },
  },
  /*
   * The campaign's shape: acts, sequences and scenes as one outline (#88).
   *
   * An ordinary campaign route wearing the ordinary campaign shell — no
   * `meta.layout`, because the page splitting is a page's business and the shell
   * knows nothing about it. Reached from the campaign's name in the sidebar,
   * which is now a control rather than a label.
   */
  {
    path: '/campaigns/:campaignId/structure',
    name: 'campaign-structure',
    component: () => import('../views/StructureView.vue'),
    meta: { title: 'Structure' },
  },
  /*
   * One act, sequence or scene, each on its own page (#88).
   *
   * Three routes rather than one with a kind in the path: they are three
   * resources with three ids, and the API already spells them out that way. It
   * also means a scene's page carries only what a scene needs — a body and a
   * stepper — rather than a view branching three ways on every render.
   *
   * Nothing here is carried alongside the tree. Getting back is the breadcrumb,
   * which always starts at Structure, and the sidebar; moving sideways is the
   * previous/next stepper at the foot of a scene.
   */
  {
    path: '/campaigns/:campaignId/acts/:actId',
    name: 'campaign-act',
    component: () => import('../views/ActView.vue'),
    meta: { title: 'Act' },
  },
  {
    path: '/campaigns/:campaignId/sequences/:sequenceId',
    name: 'campaign-sequence',
    component: () => import('../views/SequenceView.vue'),
    meta: { title: 'Sequence' },
  },
  {
    path: '/campaigns/:campaignId/scenes/:sceneId',
    name: 'campaign-scene',
    component: () => import('../views/SceneView.vue'),
    meta: { title: 'Scene' },
  },
  /*
   * Editing one, and the only place it can be deleted. Reached from the cog in
   * the top bar, beside the campaign it belongs to — which is why it needs no
   * entry point on the chooser: you are already in the campaign you want to
   * rename.
   *
   * No `meta.layout`, so it wears the campaign shell and the top bar names the
   * campaign being edited — the chip and the form read the same id from the path
   * and cannot disagree about which campaign this is.
   *
   * Creating stays a dialog on the chooser (#59). Editing is the one that is
   * interrupted, reloaded and bookmarked, and it is the only one that needed a
   * route it could survive those in.
   */
  {
    path: '/campaigns/:campaignId/settings',
    name: 'campaign-settings',
    component: () => import('../views/CampaignSettingsView.vue'),
    meta: { title: 'Campaign settings' },
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
   * Where a provider sign-in comes back to (#39). The API sets the refresh
   * cookie and redirects here with nothing in the URL but, when it went wrong,
   * an error code — so this page refreshes, loads the user and moves on.
   *
   * Public, and it has to be rather than merely happens to be. On the failure
   * path there is no session, so the guard would send an error code off to the
   * login page and swallow the one thing this page exists to say.
   */
  {
    path: '/auth/callback',
    name: 'sso-callback',
    component: () => import('../views/SsoCallbackView.vue'),
    meta: { title: 'Signing you in', public: true, layout: 'auth' },
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
