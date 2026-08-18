import { describe, it, expect } from 'vitest'
import { en } from './en.js'
import { fr } from './fr.js'

/*
 * The two catalogues, checked against each other.
 *
 * This is the "something fails loudly when they drift" half of #87. A key added
 * to one and forgotten in the other is the ordinary way a translation rots, and
 * it is invisible until somebody browsing in French meets the one English
 * sentence left — or, worse, meets `login.submit` written on a button.
 *
 * It reads the catalogues rather than a list of keys, so it needs no
 * maintenance: adding copy in both places passes, adding it in one fails.
 */

const placeholdersIn = (message) =>
  [...message.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort()

describe('the catalogues', () => {
  it('hold the same keys', () => {
    // Sorted rather than compared as sets, so the failure names the missing key
    // instead of only saying the lengths differ.
    expect(Object.keys(fr).sort()).toEqual(Object.keys(en).sort())
  })

  it('say something for every key', () => {
    for (const [catalogue, name] of [
      [en, 'en'],
      [fr, 'fr'],
    ]) {
      for (const [key, message] of Object.entries(catalogue)) {
        expect(typeof message, `${name}: ${key}`).toBe('string')
        expect(message.trim(), `${name}: ${key}`).not.toBe('')
      }
    }
  })

  it('fill in the same placeholders', () => {
    /*
     * A translation that drops `{provider}` renders a sentence with a hole in
     * it, and one that invents `{name}` renders `{name}` on screen — `t` throws
     * for the second, which is a runtime error nobody sees until they browse in
     * French. Both are caught here instead.
     */
    for (const key of Object.keys(en)) {
      expect(placeholdersIn(fr[key]), key).toEqual(placeholdersIn(en[key]))
    }
  })
})
