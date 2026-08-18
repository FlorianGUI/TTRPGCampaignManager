import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import ToastService from 'primevue/toastservice'
import 'primeicons/primeicons.css'
import './assets/base.css'
import App from './App.vue'
import { createAppRouter } from './router/index.js'
import Grimoire from './design-system/preset.js'
import { installTheme } from './stores/theme.js'
import { useAuthStore } from './stores/auth.js'

const app = createApp(App)

// Pinia first: installTheme() and the auth store below both read stores, and a
// store cannot be used before its pinia is installed.
app.use(createPinia())
app.use(createAppRouter())

app.use(PrimeVue, {
  theme: {
    preset: Grimoire,
    options: {
      // Class-driven rather than prefers-color-scheme alone, so the toggle wins.
      darkModeSelector: '.theme-candlelight',
      // `app` last means src/assets/base.css overrides component styles without
      // needing higher specificity.
      cssLayer: { name: 'primevue', order: 'primevue, app' },
    },
  },
  ripple: false,
})

/*
 * The only directive the app registers. `tooltip` already has tokens in
 * `tokens/components.js` — they were written before anything used them — and
 * the campaign name in the sidebar is the first thing that does.
 */
app.directive('tooltip', Tooltip)

/*
 * What `useWriteFailure` speaks through. A service rather than a component here:
 * it is the queue, and the one `<Toast />` that renders it lives in App.vue —
 * installing this without that would be a queue nobody reads (#111).
 */
app.use(ToastService)

installTheme()

/*
 * Restore the session before anything renders. This is not awaited: `boot()`
 * flips the store's `ready` flag when it settles and App.vue holds the first
 * render until then, which keeps the mount synchronous and puts the waiting in
 * one place rather than two.
 */
useAuthStore().boot()

app.mount('#app')
