import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/*
 * The API, same-origin, exactly as nginx serves it in production
 * (nginx/lastdawn.fr.conf). Development that talked to :8000 directly would be
 * testing a topology we do not ship: no proxy, and CORS in the path.
 *
 * `cookiePathRewrite` is the one line here that is not a convenience. The
 * backend sets the refresh cookie `Path=/users`, because that is where it lives
 * behind the proxy — but the browser sees it arrive from /api/users and would
 * never send it back to a path it was not scoped to. Without this the session
 * ends at the first reload, and only the browser can tell you so.
 */
const apiProxy = {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
    cookiePathRewrite: { '/users': '/api/users' },
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    port: 4173,
    proxy: apiProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
