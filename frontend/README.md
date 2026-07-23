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
    main.js                        # app bootstrap + PrimeVue plugin
    App.vue                        # SPIKE: design-direction judgement surface
    assets/
      base.css                     # element defaults, prose, ornament
      fonts.css                    # @font-face for the self-hosted families
      fonts/                       # woff2, latin + latin-ext subsets
    design-system/
      preset.js                    # the theme: primitives -> roles -> schemes
      useTheme.js                  # theme + density state, persisted
    components/
      AppShell.vue                 # top bar + context sidebar + content area
      domain/                      # stat block, read-aloud, dice, entity tags
    content/
      sample.js                    # sample copy for the spike
```

## Design system (spike — issue #23)

The visual direction is still being iterated on. `src/App.vue` is not a real
screen: it is one realistic page of prep notes used to judge type, palette and
ornament in context. Tweak `src/design-system/preset.js` and look at that page.

Some things worth knowing before touching it:

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

The three-layer token split, the `/styleguide` route, and per-component tests
described in issue #23 come _after_ the direction is settled — see the issue.

## Testing

Tests use [Vitest](https://vitest.dev/) with a `jsdom` environment and
[@vue/test-utils](https://test-utils.vuejs.org/) for mounting components. Test
files live next to the component they cover as `*.test.js`.
