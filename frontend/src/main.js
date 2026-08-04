import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import 'primeicons/primeicons.css'
import './assets/base.css'
import App from './App.vue'
import { createAppRouter } from './router/index.js'
import Grimoire from './design-system/preset.js'
import { installTheme } from './stores/theme.js'

const app = createApp(App)

// Pinia first: installTheme() reads a store, and a store cannot be used before
// its pinia is installed.
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

installTheme()

app.mount('#app')
