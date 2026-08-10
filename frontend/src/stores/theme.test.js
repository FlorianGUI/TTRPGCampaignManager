import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { DARK_CLASS, THEME_STORAGE_KEY, installTheme, useThemeStore } from './theme.js'

/*
 * The cases this had before Pinia (#34), against the store instead of
 * module-level refs. They no longer need vi.resetModules(): the state
 * initialiser runs when the store is first used, so a fresh pinia per test is
 * enough to re-read a freshly seeded localStorage.
 *
 * The density case went with density itself (#79) rather than being rewritten —
 * there is one scale now, and a test asserting that a class is never added would
 * be testing the absence of a feature.
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
