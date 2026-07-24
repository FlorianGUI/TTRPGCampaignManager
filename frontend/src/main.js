import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import 'primeicons/primeicons.css'
import './assets/base.css'
import App from './App.vue'
import { createAppRouter } from './router/index.js'
import Grimoire from './design-system/preset.js'
import { installTheme } from './design-system/useTheme.js'

const app = createApp(App)

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
