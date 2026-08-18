/*
 * What the app says, and which language it says it in.
 *
 * `t(key)` rather than a Vue plugin and a `$t` global: a plain function is
 * imported where it is used, which means ESLint sees a typo'd import, a test
 * needs no plugin installed to render copy, and the store and the router — two
 * places that have no component around them — reach it the same way a template
 * does.
 *
 * **Module state, and no reactivity.** The locale is decided once, from the
 * browser, before the app mounts (see `main.js`), and nothing can change it
 * afterwards because there is no switcher (#87). A `ref` here would buy
 * re-rendering that nothing ever triggers, at the price of every call site
 * having to unwrap it.
 */
import { en } from './en.js'
import { fr } from './fr.js'
import { FALLBACK_LOCALE, SUPPORTED_LOCALES } from './locale.js'

export { FALLBACK_LOCALE, SUPPORTED_LOCALES, browserLanguages, resolveLocale } from './locale.js'

const CATALOGUES = { en, fr }

let locale = FALLBACK_LOCALE

export function currentLocale() {
  return locale
}

/*
 * Speak this language from here on, and say so in the document.
 *
 * `<html lang>` matters as much as the words do: it is what a screen reader
 * picks a voice from, what a browser offers to translate against, and what CSS
 * hyphenation and quotation marks key off. `index.html` ships `lang="en"` for
 * the moment before this runs; this is what makes it true.
 *
 * An unsupported locale falls back rather than throwing. This is called with
 * whatever the browser said, and a browser is not a caller we can correct.
 */
export function setLocale(next) {
  locale = SUPPORTED_LOCALES.includes(next) ? next : FALLBACK_LOCALE

  if (typeof document !== 'undefined') document.documentElement.lang = locale

  return locale
}

/*
 * A key, and the values its placeholders take.
 *
 * **It throws rather than returning the key.** A missing key rendering its own
 * name is the failure #87 names: `login.submit` on a button looks like copy
 * somebody forgot to write and reads as broken to everyone but the person who
 * could fix it. Throwing is loud where loud is cheap — the catalogues are
 * checked against each other by a test, and every component test renders real
 * copy, so an unknown key cannot reach a build without failing something first.
 *
 * French falls back to English for a key it lacks, which the parity test means
 * cannot happen; it is here so that adding a third language is a catalogue that
 * can be filled in over time rather than one that has to be complete before it
 * can be shipped.
 */
export function t(key, values) {
  const message = CATALOGUES[locale][key] ?? CATALOGUES[FALLBACK_LOCALE][key]

  if (message === undefined) throw new Error(`No copy for "${key}"`)

  return values ? fill(message, values, key) : message
}

function fill(message, values, key) {
  return message.replaceAll(/\{(\w+)\}/g, (placeholder, name) => {
    // A placeholder with nothing to put in it would render as `{provider}` on
    // screen — the same silent nonsense as a missing key, and worth the same
    // noise. `in` rather than a falsy check: 0 is a value.
    if (!(name in values)) throw new Error(`No "${name}" for "${key}"`)

    return values[name]
  })
}

/*
 * A date, in the reader's language.
 *
 * Nothing renders one yet — #78 gave records a created and updated time and no
 * screen shows them. It is here rather than waiting because the first date to
 * appear is the one that decides the habit, and `toLocaleDateString()` with no
 * locale reads the *operating system's*, which is not what the rest of the app
 * is speaking.
 */
export function formatDate(value, options = { dateStyle: 'long' }) {
  return new Intl.DateTimeFormat(locale, options).format(new Date(value))
}
