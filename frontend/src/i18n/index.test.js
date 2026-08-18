import { describe, it, expect, afterEach } from 'vitest'
import { currentLocale, formatDate, setLocale, t } from './index.js'

/*
 * Looking copy up, and the language it is looked up in.
 *
 * The locale is module state, so every test that moves it puts it back: the
 * default is English and the rest of the suite reads its assertions in English.
 */

afterEach(() => setLocale('en'))

describe('the locale', () => {
  it('is English until the app says otherwise', () => {
    // What every other test file in the suite relies on without saying so:
    // nothing resolves the browser's language except `main.js`.
    expect(currentLocale()).toBe('en')
  })

  it('follows onto the document, so the page does not lie about what it speaks', () => {
    setLocale('fr')

    expect(document.documentElement.lang).toBe('fr')

    setLocale('en')

    expect(document.documentElement.lang).toBe('en')
  })

  it('falls back rather than throwing on a language we do not speak', () => {
    // It is called with whatever the browser said, and a browser cannot be
    // corrected — an app that failed to boot over a language tag would be worse
    // than one that speaks English.
    expect(setLocale('de')).toBe('en')
    expect(currentLocale()).toBe('en')
  })
})

describe('t', () => {
  it('says the thing', () => {
    expect(t('login.submit')).toBe('Sign in')

    setLocale('fr')

    expect(t('login.submit')).toBe('Se connecter')
  })

  it('fills placeholders in, wherever the language puts them', () => {
    expect(t('progress.spelled', { label: 'ongoing', played: 2, total: 6 })).toBe(
      'ongoing — 2 of 6 scenes played',
    )

    setLocale('fr')

    expect(t('progress.spelled', { label: 'en cours', played: 2, total: 6 })).toBe(
      'en cours — 2 scènes jouées sur 6',
    )
  })

  it('fills a placeholder that appears twice', () => {
    // `sso.email-in-use.detail` names the provider at both ends of the sentence.
    expect(t('sso.no-email.detail', { provider: 'Discord' })).toContain('Add an address to Discord')
  })

  it('throws for a key nobody wrote, rather than rendering the key', () => {
    /*
     * The failure #87 names: `login.submit` written across a button reads as
     * copy somebody forgot, and it reads that way to everyone except the person
     * who could fix it. Loud is cheap — every component test renders real copy,
     * so this cannot get past the suite.
     */
    expect(() => t('login.nothing')).toThrow('No copy for "login.nothing"')
  })

  it('throws for a placeholder with nothing to put in it', () => {
    expect(() => t('home.welcome', {})).toThrow('No "username" for "home.welcome"')
  })

  it('takes a value of zero, which is a value', () => {
    expect(t('login.wait.seconds', { count: 0 })).toBe('0 seconds')
  })
})

describe('formatDate', () => {
  /*
   * Nothing renders a date yet — #78 gave records their times and no screen
   * shows one. This is here so that the first screen to show one is already
   * speaking the app's language rather than the operating system's.
   */
  it('is written in the language the app is speaking', () => {
    // Pinned to UTC, or this asserts the runner's timezone as much as its
    // language — a date near midnight is a different day either side of one.
    const midsummer = '2026-06-24T10:30:00Z'
    const utc = { dateStyle: 'long', timeZone: 'UTC' }

    expect(formatDate(midsummer, utc)).toMatch(/June 24, 2026|24 June 2026/)

    setLocale('fr')

    expect(formatDate(midsummer, utc)).toBe('24 juin 2026')
  })
})
