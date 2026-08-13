import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  COLLAPSED_STORAGE_KEY,
  forgetCollapsed,
  readCollapsed,
  rememberCollapsed,
} from './collapsedNarrative.js'

/*
 * Which acts a game master has shut. A view preference, per person and per
 * device — the API has no column for it and must not grow one.
 */

describe('the collapse memory', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.restoreAllMocks())

  it('remembers nothing to begin with', () => {
    expect(readCollapsed('c-1')).toEqual(new Set())
  })

  it('remembers what was shut, and hands it back as a set', () => {
    // A set, because the only questions a template asks are "is this one shut"
    // and "shut this one" — `includes` on every row of a long outline is the
    // wrong shape for both.
    rememberCollapsed('c-1', new Set(['a-1', 'a-2']))

    expect(readCollapsed('c-1')).toEqual(new Set(['a-1', 'a-2']))
  })

  it('keeps campaigns apart', () => {
    /*
     * Collapsing Act I of one campaign says nothing about another, and a single
     * shared set would have them contradicting each other on every navigation.
     */
    rememberCollapsed('c-1', new Set(['a-1']))
    rememberCollapsed('c-2', new Set(['a-9']))

    expect(readCollapsed('c-1')).toEqual(new Set(['a-1']))
    expect(readCollapsed('c-2')).toEqual(new Set(['a-9']))
  })

  it('leaves nothing behind when everything is expanded again', () => {
    // Otherwise the key accumulates one empty entry per campaign anyone opens.
    rememberCollapsed('c-1', new Set(['a-1']))

    rememberCollapsed('c-1', new Set())

    expect(JSON.parse(localStorage.getItem(COLLAPSED_STORAGE_KEY))).toEqual({})
  })

  it('forgets a campaign that is gone', () => {
    rememberCollapsed('c-1', new Set(['a-1']))
    rememberCollapsed('c-2', new Set(['a-9']))

    forgetCollapsed('c-1')

    expect(readCollapsed('c-1')).toEqual(new Set())
    expect(readCollapsed('c-2')).toEqual(new Set(['a-9']))
  })

  it('treats a key written by something else as absent', () => {
    // An older shape, or another app on the same origin. Reasoning about it is
    // worse than starting again with everything expanded.
    localStorage.setItem(COLLAPSED_STORAGE_KEY, '"not an object"')

    expect(readCollapsed('c-1')).toEqual(new Set())
  })

  it('treats unreadable storage as nothing remembered', () => {
    /*
     * Safari in private mode and any page with storage disabled throw on the
     * property, not merely on the call. Forgetting which acts were shut is a
     * dull failure and must never be why the app fails to start.
     */
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })

    expect(readCollapsed('c-1')).toEqual(new Set())
  })

  it('carries on when storage refuses a write', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })

    expect(() => rememberCollapsed('c-1', new Set(['a-1']))).not.toThrow()
    expect(() => forgetCollapsed('c-1')).not.toThrow()
  })
})
