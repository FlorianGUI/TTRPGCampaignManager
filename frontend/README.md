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
      HomeView.vue                 # / — the campaign chooser
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
      theme.js                     # theme + density state, persisted
      campaigns.js                 # the campaigns you own, and creating one
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
      BareLayout.vue               # chrome for the pages above any campaign
      ChromeActions.vue            # density + theme + sign out, shared by both bars
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
split — dark leather against parchment. Every `shadow` in the preset is
explicitly `none`, overriding Aura's defaults on `card`, `formField` and both
focus rings.

Shadows survive only where something genuinely floats above the page — drawer,
popover, menu — and those come from PrimeVue's overlay tokens. If that stops
being enough, add the ramp to `tokens/semantic.js` and tint it warm; the palette
never reaches pure black, so a neutral shadow reads cold against it.

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
