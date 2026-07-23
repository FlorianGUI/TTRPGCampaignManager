import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { COMPACT_CLASS, DARK_CLASS, DENSITY_STORAGE_KEY, THEME_STORAGE_KEY } from './useTheme.js'

/*
 * The module reads localStorage at import time, so each case re-imports it
 * against a freshly seeded store.
 */
async function loadTheme() {
  vi.resetModules()
  return import('./useTheme.js')
}

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
  })

  it('defaults to candlelight when nothing is stored', async () => {
    const { theme } = await loadTheme()

    expect(theme.value).toBe('candlelight')
  })

  it('restores the stored theme over the default', async () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'parchment')

    const { theme } = await loadTheme()

    expect(theme.value).toBe('parchment')
  })

  it('ignores a stored value that is not a known theme', async () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'neon')

    const { theme } = await loadTheme()

    expect(theme.value).toBe('candlelight')
  })

  it('puts the dark class on the root and persists the choice', async () => {
    const { installTheme, toggleTheme } = await loadTheme()
    installTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true)

    toggleTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(false)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('parchment')
  })

  it('toggles density independently of the theme', async () => {
    const { installTheme, toggleDensity, density } = await loadTheme()
    installTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(COMPACT_CLASS)).toBe(false)

    toggleDensity()
    await nextTick()

    expect(density.value).toBe('compact')
    expect(document.documentElement.classList.contains(COMPACT_CLASS)).toBe(true)
    expect(localStorage.getItem(DENSITY_STORAGE_KEY)).toBe('compact')
  })

  it('still applies the theme when storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage disabled')
    })

    const { installTheme, theme } = await loadTheme()
    installTheme()
    await nextTick()

    expect(theme.value).toBe('candlelight')
    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true)

    vi.restoreAllMocks()
  })
})
