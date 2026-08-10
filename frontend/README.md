# Frontend

Vue 3 + Vite single-page app for the TTRPG Campaign Manager.

## Commands

```bash
npm install       # install dependencies
npm run dev       # start the dev server on http://localhost:5173
npm run build     # production build into dist/
npm run preview   # serve the production build on http://localhost:4173
npm test          # run the unit tests once (Vitest)
npm run test:watch  # run the tests in watch mode
npm run lint      # check with ESLint (eslint-plugin-vue)
npm run lint:fix  # auto-fix ESLint issues
npm run format    # format all files with Prettier
npm run format:check  # verify formatting without writing
```

## Linting & formatting

ESLint (flat config, `eslint.config.js`) uses `eslint-plugin-vue`'s recommended
rules for `.vue` and JS files. Prettier owns formatting; `@vue/eslint-config-prettier`
disables any ESLint rules that would conflict with it. Prettier settings live in
`.prettierrc.json`.

The dev (5173) and preview (4173) ports match the origins allowed by the API's
CORS configuration (`CORS_ORIGINS`, see `app/common/security/cors.py`) — the API
is a separate origin, so that list is what lets the session cookie work at all.

## Structure

```
frontend/
  index.html                       # Vite entry point
  vite.config.js                   # Vite + Vitest config
  scripts/
    vendor-fonts.mjs               # re-download the self-hosted webfonts
    check-contrast.mjs             # WCAG AA check over the theme's colour pairs
  src/
    main.js                        # app bootstrap + PrimeVue plugin + router
    App.vue                        # the persistent shell around <RouterView>
    router/
      index.js                     # router instance, scroll behaviour, title
      routes.js                    # the route table
    views/
      HomeView.vue                 # / — the campaign chooser, and the create dialog
      CampaignSettingsView.vue     # /campaigns/:id/settings — editing and deleting one
      SpikeView.vue                # SPIKE: design-direction judgement surface
      StyleguideView.vue           # /styleguide — every token and component
      NotFoundView.vue             # catch-all
    assets/
      base.css                     # element defaults, prose, ornament
      fonts.css                    # @font-face for the self-hosted families
      fonts/                       # woff2, latin + latin-ext subsets
    api/
      http.js                      # the transport: one request, no auth state
      client.js                    # what features call: token + refresh-on-401
      sso.js                       # where "Continue with Discord" goes, and back
    stores/
      auth.js                      # current user, in-memory access token
      theme.js                     # theme state, persisted
      campaigns.js                 # the campaigns you own, and the three writes
      sources.js                   # the sources you own, read-only
      currentCampaign.js           # the remembered campaign — storage, not a store
    design-system/
      preset.js                    # composes the three layers into the preset
      tokens/
        primitives.js              # raw ramps and scales, no meaning, no imports
        semantic.js                # roles, the two schemes, app tokens
        components.js              # per-component overrides
    components/
      AppShell.vue                 # top bar + context sidebar + content area
      AppNav.vue                   # the nav list, shared by sidebar and drawer
      CampaignTitle.vue            # the campaign name at the head of its own nav
      CampaignForm.vue             # the campaign fields, for both creating and editing
      BareLayout.vue               # chrome for the pages above any campaign
      ChromeActions.vue            # who you are, and the account menu, in both bars
      domain/                      # stat block, read-aloud, dice, entity tags
    content/
      sample.js                    # sample copy for the spike
```

## Design system

The visual direction is settled (issue #23). Two surfaces exercise it:

- **`/styleguide`** — the living reference: every token in both schemes, and
  every component we own or override. Start here. **Dev only** — see below.
- **`/campaigns/:campaignId/sessions` (`SpikeView.vue`)** — one realistic page
  of prep notes, for judging type, palette and ornament _in context_ rather than
  in a grid. It stands in for session notes until that context exists; its
  counts come from `content/sample.js` and are invented.

### Token layers

`design-system/preset.js` composes three layers under `tokens/`, and each layer
may only reach downwards:

| layer      | file                   | holds                                                 |
| ---------- | ---------------------- | ----------------------------------------------------- |
| primitives | `tokens/primitives.js` | raw ramps and scales, no meaning, no imports          |
| semantic   | `tokens/semantic.js`   | roles, the two schemes, app-owned `grimoire.*` tokens |
| components | `tokens/components.js` | per-component overrides, referencing semantic tokens  |

Two rules that are load-bearing:

- **Never reference a primitive from a component override.** Go through the
  semantic layer, so a ramp change never has to be chased into component files.
- **Never collapse `LIGHT_ROLES` / `DARK_ROLES` into shared numeric indices.**
  The schemes walk the ramp in _opposite_ directions — parchment top-down,
  candlelight bottom-up. Collapsing them is what produced the light-on-light
  dark theme bug during the spike.

`tokens/primitives.js` is deliberately import-free so plain Node tooling can
read it; `scripts/check-contrast.mjs` imports it directly.

### Elevation

**There is no elevation scale, and that is a decision rather than an omission.**
A printed page has no z-axis: depth here comes from rules (`.rule-double`,
`.rule-fleuron`), borders (`--p-content-border-color`) and the chrome/content
split — dark leather against parchment. Every in-page `shadow` in the preset is
explicitly `none`, overriding Aura's defaults on `card`, `formField` and both
focus rings.

**There is no density scale either, since #79.** Comfortable is the only
spacing, so `--space-*` has one definition rather than two. The 44px touch
floors dotted around the components look like they were density workarounds and
are not: they are a touch guideline, set in absolute pixels precisely so no
change to the spacing scale can quietly lower them.

Shadows survive only where something genuinely floats above the page — drawer,
popover, menu — and those are the `overlay.*` tokens in `tokens/semantic.js`.
**They are tinted warm, and that is not decoration.** Aura ships them as pure
black at 10%; this palette never reaches pure black, so a neutral shadow reads
grey-blue against parchment — a hole in the page rather than a raised edge.
`OVERLAY_SHADOW` and `MODAL_SHADOW` warm them to the ink at the bottom of the
ramp. #79's account menu was the first overlay in the app and is what put the
question on screen; anything floating that is added later should read those
tokens rather than inventing a shadow.

Some things worth knowing before touching any of it:

- **PrimeVue is pinned to v4** (`4.5.5`, MIT). v5 relicensed to a commercial
  model and renders a license banner without a key. Don't bump the major
  without deciding that question.
- **Everything colour-bearing reads a `--p-*` token.** No component hardcodes a
  hex. A theme switch is a token swap.
- **`app` wins over `primevue` in the cascade**, which is what lets `base.css`
  override component styles without specificity games — and is also a trap.
  `<Button as="router-link">` renders an `<a>`, so the anchor rule claims it and
  paints a primary button's label in the same accent as its background: a solid
  block with invisible text. `a.p-button` reverts colour and decoration to the
  primevue layer. jsdom does not do layered cascade, so no unit test can catch
  this class of bug — it is found by looking.
- **Two themes**: `candlelight` (dark, the default) and `parchment` (light),
  driven by a `.theme-candlelight` class on `<html>`. The default is
  deliberately _not_ tied to `prefers-color-scheme`.
- **Contrast is checked, not eyeballed**: `node scripts/check-contrast.mjs`
  verifies every foreground/background pair against WCAG AA in both themes and
  exits non-zero on failure. Run it after any palette change.
- **Fonts are self-hosted**, no CDN — Cinzel (display), Alegreya (body),
  IBM Plex Mono (dice and stat lines), latin + latin-ext only, all OFL.
  Regenerate with `node scripts/vendor-fonts.mjs`.
- **Ornament is token-gated**: a `.no-ornament` class on any ancestor turns off
  textures and rules.

### Routing

`vue-router` in history mode. Conventions, set in `router/routes.js`:

- every route is **named**; link and navigate by name, never by a hand-built path
- the landing route is eagerly imported, everything else is **lazy**, so the
  initial bundle carries only what the first paint needs
- **`/styleguide` is dev only.** Its route is behind an `import.meta.env.DEV`
  literal, which the bundler substitutes at build time, so the branch and its
  dynamic import are dropped entirely: the view is not shipped, no chunk is
  emitted, and `/styleguide` falls through to the catch-all in a production
  build. Keep that condition a bare literal — putting it behind a variable or a
  function parameter defeats the elimination and the chunk comes back.
- every route sets `meta.title`, which `router/index.js` turns into the document
  title
- `meta.layout` names the chrome `App.vue` wraps the view in: `auth` for the
  signed-out column, `bare` for the pages above any campaign. Saying nothing
  gets the campaign shell, which is what all but a handful want
- the catch-all stays **last**

`App.vue` holds the shell and renders `<RouterView>` inside it, so the top bar
and sidebar are not torn down on navigation.

### Where a signed-in visitor lands

`/` is a **chooser**, not a page inside the campaign frame (#59). `AppNav`'s
Campaign section is meaningless before a campaign is picked, so home sits
outside `AppShell` in `BareLayout` — `meta.layout: 'bare'`, the third value
beside `auth` and saying nothing.

The campaign id lives **in the path** (`/campaigns/:campaignId/...`).
`localStorage` holds only the campaign to open by default, under
`grimoire.campaign`. That is a knowing contradiction of #14, which put
`active_campaign_id` on `users` — a column cut from #44 and still unbuilt. It
moves server-side the day multi-device continuity matters.

The rule for `/` is one line, in `enterRememberedCampaign`:

> a remembered id? go there. otherwise, show the chooser.

The two exceptions — just signed in, just left a campaign — are **not** special
cases in that guard. They work because the id is cleared at those moments, in
four places, and between them they are every point a session starts or stops
being one person's:

| where             | why it is not covered by the others                                   |
| ----------------- | --------------------------------------------------------------------- |
| `auth.clear()`    | logout, and every failed refresh — a session ending                   |
| `auth.logIn()`    | an expired session never calls logout; that person meets a login form |
| `SsoCallbackView` | a provider sign-in arrives through `boot()`, which must _not_ forget  |
| the campaign chip | leaving would otherwise bounce straight back in                       |

Two consequences worth keeping:

- **Do not "fix" this with a flag.** A `skipAutoEnter` boolean is the obvious
  shape and it desynchronises on the first page reload. The clearing rule cannot.
- **`boot()` must never forget.** A cold open with a live refresh cookie is the
  case the whole feature exists for. The SSO callback is the one sign-in that
  also arrives through `boot()`, which is why it clears explicitly.

### The top bar: where you are on the left, who you are on the right

#79 collapsed a bar that had accumulated one control per decision — six of them,
none of which said who was signed in. What is left is a label and a menu.

**Where you are is a label; what you can do is a menu.** That split is the whole
shape of it, and it is why the campaign's name and the campaign's actions live
in different places rather than together.

- **`ChromeActions.vue` is the one menu** — everything you can do: switch theme,
  and inside a campaign its settings and closing it, then sign out. Shared by
  `AppShell` and `BareLayout` so the two bars cannot drift apart; the campaign
  arrives as a prop rather than by forking the component. The username is the
  trigger itself rather than a name beside one: one control, carrying
  `aria-haspopup`, `aria-expanded` and a focus ring because it is pressable.
- **The campaign items are added, not dimmed.** They exist only when there is a
  campaign. A disabled item reads as broken rather than as not-yet-available —
  the argument #59 made for the sidebar.
- **`CampaignTitle.vue` is a label and nothing else.** No border, no chevron,
  nothing to press, `cursor: default`. It sits at the head of the nav it names,
  in the sidebar and in the drawer — below 900px the drawer is the only place
  the campaign is named at all. The tag it replaced looked pressable and mostly
  was not, which is the worst of both.
- **Its tooltip is the only place the description appears in the chrome.** A
  15rem column is narrower than a lot of campaign names, so the name ellipsises
  and the popup carries the whole of it, with the description under it. The
  ellipsis is visual only — CSS truncation does not shorten the accessible name,
  so nothing is hidden from a screen reader by a hover-only affordance. The
  `tooltip` directive is registered in `main.js`; `tokens/components.js` already
  had tokens for it.
- **The theme item reads "Switch theme"**, not the name of the theme it would
  switch to. Naming the destination needs no state indicator, which is the
  argument for it, but it reads as a place among a list of verbs. The icon
  carries the direction — a sun in candlelight, a moon in parchment.
- **`aria-expanded` is flipped on click, not from the menu's `show` event.**
  PrimeVue emits that from the overlay's transition hooks, so it arrives after
  the animation — and the attribute describes what the button just did, not what
  an animation has finished doing. Focus returns to the trigger on close.

Two recorded decisions changed here, and both were rewritten rather than deleted:

- **#25 said sign out must hold its place at every width.** That was written when
  the alternative was folding it away as the bar narrowed. It is in the menu now:
  one tap further, but present on every route and at every width, and no longer a
  44px icon beside another 44px icon — which is how a thumb aiming at the theme
  toggle ends a session. The reasoning lives in `ChromeActions.vue`.
- **Search is gone entirely** — field, toggle and collapsed row. Nothing was ever
  behind it, a placeholder since the spike, and a control that does nothing is a
  promise the app does not keep.

Below 640px the ladder is one rung long — the wordmark goes, and the username
caps at 8rem in `ChromeActions`. The campaign is not on this row to compete for
it any more.

### Creating is a dialog; editing is a page

The two are shaped differently on purpose, and the difference is not
inconsistency:

- **Creating stays the `Dialog` on the chooser** (#59). It is short, it is never
  resumed, and nobody reloads half way through — and an empty state whose
  primary action navigates away is a worse answer than one that resolves where
  you are.
- **Editing is `/campaigns/:campaignId/settings`** (#49). An edit _is_
  interrupted, reloaded, bookmarked and opened in a second tab, and a modal
  survives none of those.

Both render `CampaignForm.vue`, so the two cannot drift apart.

The settings page is reached from the **cog on the campaign chip** in
`AppShell`'s top bar, beside the name it changes — by the time you want to
rename a campaign you are inside it, so the chooser carries no entry point of its
own and stays a screen for choosing a table. If that bar ends up carrying more
controls than it can, #79 owns the crowding.

Three things that go with all this:

- **`CampaignForm.vue` owns the form and nothing else.** The caller makes the
  call and hands back whatever it threw, through `error`. That is what lets
  creating navigate into the new campaign and editing stay put, without the
  shared component knowing that either happens.
- **Every write sends both fields.** `PUT /campaigns/{id}` is a full
  replacement, not a patch: a description left out of the body is cleared. A
  form that emitted only what changed would wipe the description of every
  campaign anyone renamed.
- **The empty-name check is not duplication of the API's 422.** `CampaignCreate.name`
  is a bare `str`, so the backend answers 422 for a name that is _missing_ and
  accepts one that is blank — the client check is the only thing between someone
  and a nameless campaign. A 422 is placed against the field named in its `loc`;
  pydantic's own wording is not shown, because it is written for whoever wrote
  the request.

Deleting lives on that same settings page, behind the campaign's name typed out.
It is not on the chooser, which is the screen people land on straight after
signing in, and it is not a dialog: `CampaignService.delete` takes every
character at the table with it and the API offers no undo, so the confirmation
has to be one that muscle memory cannot satisfy.

`currentCampaign.js` is deliberately import-free and is not a Pinia store:
`stores/auth.js` has to clear it, and it cannot import a store that imports
`api/client.js`, which imports the auth store.

## State and the API

Pinia is the single state pattern; there is no second way to hold shared state.
Stores live in `src/stores/`, and `installTheme()` still runs from `main.js`
before mount so the theme class is on `<html>` before first paint.

### Talking to the API

Two modules, and the split between them is load-bearing:

| module          | what it does                                                       |
| --------------- | ------------------------------------------------------------------ |
| `api/http.js`   | builds and sends one request; knows nothing about who is signed in |
| `api/client.js` | attaches the access token, and renews it on a 401                  |

**Feature stores call `request` from `client.js`.** The auth store is the one
exception: signing in, refreshing and signing out go straight to `apiFetch`, so
a refresh can never be intercepted by the 401 handling that exists to serve it.
That is what stops it looping.

**The API host is runtime configuration, not part of the build.** `index.html`
loads `/config.js` before the app, and that file sets
`window.__CONFIG__ = { apiUrl }`. `api/http.js` reads it once at import.

| where         | where `/config.js` comes from                       | from                                         |
| ------------- | --------------------------------------------------- | -------------------------------------------- |
| production    | `/opt/dnd/config/config.js`, aliased by nginx       | whatever configures the host                 |
| dev / preview | the `dev-runtime-config` plugin in `vite.config.js` | `VITE_API_URL`, else `http://localhost:8000` |

Vite substitutes `VITE_*` at **build** time, so a host in the bundle makes the
artifact correct in exactly one environment and silently wrong in every other —
which is how a build once shipped calling `localhost:8000`. Nothing in `dist/`
names a host now, so the same artifact deploys anywhere and moving the API is one
line on the server.

**No deploy step writes it.** It sits outside `/opt/dnd/frontend-dist`, which the
deploy replaces wholesale, so it is host state rather than something every deploy
has to restore — and it is the first thing that should become an Ansible task
rather than a step to translate.

Three things follow, and all three are load-bearing:

- **It fails closed.** A production build that finds no `apiUrl` throws at import
  rather than falling back to localhost. A fallback there would be the original
  bug again, in production, silently. The error names the file and where it
  lives, because that is the only clue anyone will get.
- **`/config.js` must not be cached.** It carries no content hash, unlike
  everything under `/assets/`, so `nginx/lastdawn.fr.conf` serves it `no-cache`.
  Without that a browser can keep pointing at yesterday's API host.
- **The script tag is deliberately not a module.** It has to have run before the
  app's first import; `type="module"` defers it and it would not have.

### Sessions

The backend issues a short access token in the response body and a long-lived
refresh token in an `httpOnly` cookie (#35). Three things follow, all of which
are easy to undo by accident:

- **Nothing is persisted by the auth store.** The access token lives in memory
  only. A reload restores the session from the cookie, so there is no
  long-lived credential on disk for an XSS to reach. Don't add `localStorage`
  here — the reason it looks like it needs it is the reason it must not have it.
- **Every request sends `credentials: 'include'`.** The API is a different origin
  in every environment — `api.lastdawn.fr` from `lastdawn.fr`, `:8000` from
  `:5173` — so without it the cookie is neither stored nor sent, and every
  session ends at the first reload.
- **Refreshes are serialised, per tab and across tabs.** The backend rotates the
  refresh token on every use and treats a re-presented one as a leak, revoking
  the whole session. So two refreshes racing do not waste a request — they sign
  the user out. `stores/auth.js` holds one in-flight promise per tab and takes a
  Web Lock across them; both are covered by tests, and neither is optional.

The first render waits on `auth.ready`, which the boot refresh flips when it
settles either way. Rendering earlier means a returning user sees a signed-out
app for a moment before it corrects itself.

## Testing

Tests use [Vitest](https://vitest.dev/) with a `jsdom` environment and
[@vue/test-utils](https://test-utils.vuejs.org/) for mounting components. Test
files live next to the component they cover as `*.test.js`.
