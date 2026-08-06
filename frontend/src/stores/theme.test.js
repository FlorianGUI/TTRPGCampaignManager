import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import {
  COMPACT_CLASS,
  DARK_CLASS,
  DENSITY_STORAGE_KEY,
  THEME_STORAGE_KEY,
  installTheme,
  useThemeStore,
} from './theme.js'

/*
 * The same six cases this had before Pinia (#34), against the store instead of
 * module-level refs. They no longer need vi.resetModules(): the state
 * initialiser runs when the store is first used, so a fresh pinia per test is
 * enough to re-read a freshly seeded localStorage.
 */

describe('theme store', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    setActivePinia(createPinia())
  })

  it('defaults to candlelight when nothing is stored', () => {
    expect(useThemeStore().theme).toBe('candlelight')
  })

  it('restores the stored theme over the default', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'parchment')

    expect(useThemeStore().theme).toBe('parchment')
  })

  it('ignores a stored value that is not a known theme', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'neon')

    expect(useThemeStore().theme).toBe('candlelight')
  })

  it('puts the dark class on the root and persists the choice', async () => {
    const store = useThemeStore()
    installTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true)

    store.toggleTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(false)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('parchment')
  })

  it('toggles density independently of the theme', async () => {
    const store = useThemeStore()
    installTheme()
    await nextTick()

    expect(document.documentElement.classList.contains(COMPACT_CLASS)).toBe(false)

    store.toggleDensity()
    await nextTick()

    expect(store.density).toBe('compact')
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

    const store = useThemeStore()
    installTheme()
    await nextTick()

    expect(store.theme).toBe('candlelight')
    expect(document.documentElement.classList.contains(DARK_CLASS)).toBe(true)

    vi.restoreAllMocks()
  })
})
