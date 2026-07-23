import { ref, watchEffect } from 'vue'

/*
 * Theme + density state, driven by classes on <html>.
 *
 * Candlelight (dark) is the default and we deliberately do NOT fall back to
 * prefers-color-scheme: the dark theme is the designed default (issue #23 —
 * tables get played in dim rooms), so a light-mode OS shouldn't silently opt
 * users into parchment. Only an explicit toggle switches it, and that choice
 * persists.
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

function preferredTheme() {
  return read(THEME_STORAGE_KEY, THEMES) ?? 'candlelight'
}

export const theme = ref(preferredTheme())
export const density = ref(read(DENSITY_STORAGE_KEY, DENSITIES) ?? 'comfortable')

export function toggleTheme() {
  theme.value = theme.value === 'candlelight' ? 'parchment' : 'candlelight'
}

export function toggleDensity() {
  density.value = density.value === 'comfortable' ? 'compact' : 'comfortable'
}

/* Wires the refs to <html>. Called once from main.js. */
export function installTheme(root = document.documentElement) {
  watchEffect(() => {
    root.classList.toggle(DARK_CLASS, theme.value === 'candlelight')
    write(THEME_STORAGE_KEY, theme.value)
  })

  watchEffect(() => {
    root.classList.toggle(COMPACT_CLASS, density.value === 'compact')
    write(DENSITY_STORAGE_KEY, density.value)
  })
}

export function useTheme() {
  return { theme, density, toggleTheme, toggleDensity }
}
