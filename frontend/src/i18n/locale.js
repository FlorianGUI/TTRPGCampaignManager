/*
 * Which language the app speaks, decided from the browser and nothing else.
 *
 * No switcher, and that is #87's decision rather than an omission: a chosen
 * language is a preference, and a preference needs somewhere to live per account
 * — which is a conversation about the user record, not about copy. The browser
 * already carries an answer that every other site respects, so we respect it too.
 *
 * Matched on the primary subtag, so `fr-CA` and `fr-BE` are French. Anything
 * that is not French is English: a fallback rather than a guess, because a
 * half-recognised locale would render an empty catalogue.
 */

export const FALLBACK_LOCALE = 'en'

/* The catalogues that exist. `i18n/index.js` imports them; this is the list of
   what may be asked for, kept here so the resolution below has no imports. */
export const SUPPORTED_LOCALES = [FALLBACK_LOCALE, 'fr']

/*
 * What the browser says it reads, most preferred first.
 *
 * `navigator.languages` rather than `navigator.language` alone: the first is the
 * whole preference list, and someone whose browser is set to Breton then French
 * should be read French rather than English. `language` is the fallback for the
 * older shape, and an empty list is a browser that said nothing.
 */
export function browserLanguages() {
  if (typeof navigator === 'undefined') return []

  return navigator.languages?.length ? [...navigator.languages] : [navigator.language ?? '']
}

export function resolveLocale(tags = browserLanguages()) {
  for (const tag of tags) {
    // Case-folded, because a tag is whatever the browser wrote: `FR-fr` is
    // French, and BCP 47 says the comparison is case-insensitive.
    const primary = String(tag).toLowerCase().split('-')[0]

    if (SUPPORTED_LOCALES.includes(primary)) return primary
  }

  return FALLBACK_LOCALE
}
