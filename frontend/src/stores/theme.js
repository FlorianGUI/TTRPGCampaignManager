import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

/*
 * Theme + density state, driven by classes on <html>.
 *
 * Candlelight (dark) is the default and we deliberately do NOT fall back to
 * prefers-color-scheme: the dark theme is the designed default (issue #23 —
 * tables get played in dim rooms), so a light-mode OS shouldn't silently opt
 * users into parchment. Only an explicit toggle switches it, and that choice
 * persists.
 *
 * This was module-level refs before Pinia arrived (#34). The behaviour is
 * unchanged and so are its tests; what moved is where the state is declared, so
 * the codebase has one answer to "where does state live" rather than two.
 */

export const THEME_STORAGE_KEY = 'grimoire.theme'
export const DENSITY_STORAGE_KEY = 'grimoire.density'

export const DARK_CLASS = 'theme-candlelight'
export const COMPACT_CLASS = 'density-compact'

const THEMES = ['candlelight', 'parchment']
const DENSITIES = ['comfortable', 'compact']

function read(key, allowed) {
  try {
    const stored = localStorage.getItem(key)
    return allowed.includes(stored) ? stored : null
  } catch {
    // Private mode / storage disabled — fall back to defaults.
    return null
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Non-fatal: the theme still applies for this session.
  }
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref(read(THEME_STORAGE_KEY, THEMES) ?? 'candlelight')
  const density = ref(read(DENSITY_STORAGE_KEY, DENSITIES) ?? 'comfortable')

  function toggleTheme() {
    theme.value = theme.value === 'candlelight' ? 'parchment' : 'candlelight'
  }

  function toggleDensity() {
    density.value = density.value === 'comfortable' ? 'compact' : 'comfortable'
  }

  return { theme, density, toggleTheme, toggleDensity }
})

/*
 * Wires the store to <html>. Called once from main.js, before mount, so the
 * class is on the element before first paint — a component-level watcher would
 * run after, and the app would flash the wrong theme on every load.
 */
export function installTheme(root = document.documentElement) {
  const store = useThemeStore()

  watchEffect(() => {
    root.classList.toggle(DARK_CLASS, store.theme === 'candlelight')
    write(THEME_STORAGE_KEY, store.theme)
  })

  watchEffect(() => {
    root.classList.toggle(COMPACT_CLASS, store.density === 'compact')
    write(DENSITY_STORAGE_KEY, store.density)
  })
}
