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
  src/
    main.js                        # app bootstrap
    App.vue                        # root component
    components/
      HelloWorld.vue               # sample component
      HelloWorld.test.js           # component unit test
```

## Testing

Tests use [Vitest](https://vitest.dev/) with a `jsdom` environment and
[@vue/test-utils](https://test-utils.vuejs.org/) for mounting components. Test
files live next to the component they cover as `*.test.js`.
