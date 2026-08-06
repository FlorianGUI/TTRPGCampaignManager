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

The dev (5173) and preview (4173) ports both proxy `/api` to the API on 8000, so
the browser only ever talks to one origin — see **State and the API** below. They
remain in the API's `CORS_ORIGINS` (`app/common/security/cors.py`) for anything
that calls it directly, which the app itself no longer does.

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
    stores/
      auth.js                      # current user, in-memory access token
      theme.js                     # theme + density state, persisted
    design-system/
      preset.js                    # composes the three layers into the preset
      tokens/
        primitives.js              # raw ramps and scales, no meaning, no imports
        semantic.js                # roles, the two schemes, app tokens
        components.js              # per-component overrides
    components/
      AppShell.vue                 # top bar + context sidebar + content area
      AppNav.vue                   # the nav list, shared by sidebar and drawer
      domain/                      # stat block, read-aloud, dice, entity tags
    content/
      sample.js                    # sample copy for the spike
```

## Design system

The visual direction is settled (issue #23). Two surfaces exercise it:

- **`/styleguide`** — the living reference: every token in both schemes, and
  every component we own or override. Start here. **Dev only** — see below.
- **`/` (`SpikeView.vue`)** — one realistic page of prep notes, for judging
  type, palette and ornament _in context_ rather than in a grid.

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
- the catch-all stays **last**

`App.vue` holds the shell and renders `<RouterView>` inside it, so the top bar
and sidebar are not torn down on navigation.

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

**The API is same-origin, at `/api`.** Nothing in the bundle names a host: nginx
proxies `/api` to the API in production (`nginx/lastdawn.fr.conf`) and
`vite.config.js` does the same in dev and preview. That is deliberate — Vite
substitutes `VITE_*` at **build** time, so any host in there makes the artifact
correct in exactly one environment and silently wrong in the others. `.env.example`
documents `VITE_API_URL` as an override for pointing a local build elsewhere;
CI does not set it, and production must not.

Two things follow, and both are load-bearing:

- **The proxy strips the prefix.** `/api/users/login` reaches the backend as
  `/users/login`, so the backend stays unaware it sits behind a prefix and
  `api.lastdawn.fr` keeps serving identical paths for Swagger.
- **So the refresh cookie's path has to be rewritten.** The backend scopes it
  `Path=/users`; a browser that received it from `/api/users` would store it and
  then never send it. `proxy_cookie_path` in nginx and `cookiePathRewrite` in
  `vite.config.js` are the same fix on both sides. Remove either and the session
  ends at the first reload, with nothing failing loudly.

### Sessions

The backend issues a short access token in the response body and a long-lived
refresh token in an `httpOnly` cookie (#35). Three things follow, all of which
are easy to undo by accident:

- **Nothing is persisted by the auth store.** The access token lives in memory
  only. A reload restores the session from the cookie, so there is no
  long-lived credential on disk for an XSS to reach. Don't add `localStorage`
  here — the reason it looks like it needs it is the reason it must not have it.
- **Every request sends `credentials: 'include'`.** Same-origin `/api` would
  carry the cookie without it, but it costs nothing there and is the difference
  between working and losing every session at the first reload as soon as
  `VITE_API_URL` points at another origin.
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
