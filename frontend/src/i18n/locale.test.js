import { describe, it, expect, vi, afterEach } from 'vitest'
import { browserLanguages, resolveLocale, FALLBACK_LOCALE } from './locale.js'

/*
 * Which language the browser is asking for. English is not a preference here,
 * it is what is left when nothing matched — so most of this is about the ways a
 * language tag arrives looking like something else.
 */

describe('resolveLocale', () => {
  it('matches on the primary subtag, so every French is French', () => {
    expect(resolveLocale(['fr'])).toBe('fr')
    expect(resolveLocale(['fr-CA'])).toBe('fr')
    expect(resolveLocale(['fr-BE'])).toBe('fr')
  })

  it('reads a tag however it is cased', () => {
    // BCP 47 says the comparison is case-insensitive, and a browser is not a
    // caller that can be asked to be consistent.
    expect(resolveLocale(['FR-fr'])).toBe('fr')
  })

  it('falls back to English for anything else', () => {
    expect(resolveLocale(['en-GB'])).toBe(FALLBACK_LOCALE)
    expect(resolveLocale(['de-DE'])).toBe(FALLBACK_LOCALE)
    expect(resolveLocale([])).toBe(FALLBACK_LOCALE)
    expect(resolveLocale([''])).toBe(FALLBACK_LOCALE)
  })

  it('takes the first language it can speak, not the first one listed', () => {
    // Someone reading Breton first and French second is served French rather
    // than English, which is the whole reason the list is walked.
    expect(resolveLocale(['br', 'fr-FR', 'en'])).toBe('fr')
  })
})

describe('browserLanguages', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('is the browser’s whole preference list', () => {
    vi.stubGlobal('navigator', { languages: ['fr-CA', 'en'], language: 'fr-CA' })

    expect(browserLanguages()).toEqual(['fr-CA', 'en'])
  })

  it('falls back to the single language on a browser that has no list', () => {
    vi.stubGlobal('navigator', { language: 'fr' })

    expect(browserLanguages()).toEqual(['fr'])
  })

  it('is empty where there is no navigator at all', () => {
    // Not a browser: the module is imported by tests and could be imported by a
    // build step, and neither is a reason to throw.
    vi.stubGlobal('navigator', undefined)

    expect(browserLanguages()).toEqual([])
  })
})
