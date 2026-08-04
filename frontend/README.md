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
CORS configuration (`CORS_ORIGINS`, see `app/common/security/cors.py`).

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
    stores/
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

## Testing

Tests use [Vitest](https://vitest.dev/) with a `jsdom` environment and
[@vue/test-utils](https://test-utils.vuejs.org/) for mounting components. Test
files live next to the component they cover as `*.test.js`.
