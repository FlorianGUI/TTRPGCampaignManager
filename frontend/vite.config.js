import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

/*
 * `/config.js` in development, standing in for the file the deploy writes on the
 * server. index.html asks for it in both places, so development exercises the
 * same boot sequence production does — a missing config.js is then a broken dev
 * server rather than a surprise only production can discover.
 *
 * VITE_API_URL is honoured here, and only here: it configures this dev-server
 * response, never the bundle. That is the distinction the whole arrangement
 * rests on — the host is something the environment says at runtime, not
 * something the build remembers.
 */
function devRuntimeConfig(apiUrl) {
  const body = `window.__CONFIG__ = ${JSON.stringify({ apiUrl })}\n`

  // The braces matter: `middlewares.use` returns the connect app, which is
  // itself a function, and Vite treats a function returned from these hooks as a
  // post-hook to call later — with no arguments, which crashes on startup.
  return {
    name: 'dev-runtime-config',
    configureServer(server) {
      server.middlewares.use('/config.js', serve)
    },
    configurePreviewServer(server) {
      server.middlewares.use('/config.js', serve)
    },
  }

  function serve(_request, response) {
    response.setHeader('Content-Type', 'application/javascript')
    response.setHeader('Cache-Control', 'no-cache')
    response.end(body)
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // loadEnv rather than process.env: Vite reads .env files into import.meta.env
  // for the client and leaves process.env alone, so a VITE_API_URL sitting in
  // .env.local — which is what .env.example tells you to write — would be
  // invisible here otherwise.
  const env = loadEnv(mode, import.meta.dirname, 'VITE_')

  return {
    plugins: [vue(), devRuntimeConfig(env.VITE_API_URL || 'http://localhost:8000')],
    server: {
      port: 5173,
    },
    preview: {
      port: 4173,
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
  }
})
