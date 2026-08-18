import { describe, it, expect } from 'vitest'
import { primevueLocale } from './primevue.js'

/*
 * PrimeVue's own copy. Its components emit strings none of which pass through
 * `t` — a dialog's close button, an empty `Select` — so this is what stops them
 * being the English underneath a French page.
 */

describe('primevueLocale', () => {
  it('hands PrimeVue nothing for English, which is already its default', () => {
    // An empty object merges to exactly the library's defaults. A copy of them
    // here would be a second English that could fall behind the first.
    expect(primevueLocale('en')).toEqual({})
  })

  it('translates what the app’s components can actually say', () => {
    const locale = primevueLocale('fr')

    // The close button on every Dialog and Drawer in the app.
    expect(locale.aria.close).toBe('Fermer')
    expect(locale.emptyMessage).toBe('Aucune option disponible')
  })

  it('asks for nothing on a language it has no words for', () => {
    expect(primevueLocale('de')).toEqual({})
  })
})
