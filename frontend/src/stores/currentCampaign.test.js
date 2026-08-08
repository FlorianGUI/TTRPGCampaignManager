import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  CAMPAIGN_STORAGE_KEY,
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from './currentCampaign.js'

describe('the remembered campaign', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('remembers nothing until something is entered', () => {
    expect(readCurrentCampaign()).toBeNull()
  })

  it('survives a round trip through storage', () => {
    rememberCurrentCampaign('c-1')

    expect(readCurrentCampaign()).toBe('c-1')
    expect(localStorage.getItem(CAMPAIGN_STORAGE_KEY)).toBe('c-1')
  })

  it('forgets on request, which is what makes / show the chooser', () => {
    rememberCurrentCampaign('c-1')
    forgetCurrentCampaign()

    expect(readCurrentCampaign()).toBeNull()
  })

  it('reads an empty string as nothing remembered', () => {
    // An empty key is not a campaign id, and returning it would send the guard
    // looking for a campaign named "".
    localStorage.setItem(CAMPAIGN_STORAGE_KEY, '')

    expect(readCurrentCampaign()).toBeNull()
  })

  /*
   * Safari in private mode and any page with storage disabled throw on the
   * property itself, not merely on the call. Losing where you were is a dull
   * failure; it must never be the reason the app fails to start.
   */
  describe('when storage is not available', () => {
    let storage

    beforeEach(() => {
      storage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')

      Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        get() {
          throw new Error('SecurityError')
        },
      })
    })

    afterEach(() => {
      Object.defineProperty(globalThis, 'localStorage', storage)
    })

    it('reads as nothing remembered rather than throwing', () => {
      expect(readCurrentCampaign()).toBeNull()
    })

    it('writes and clears without throwing', () => {
      expect(() => rememberCurrentCampaign('c-1')).not.toThrow()
      expect(() => forgetCurrentCampaign()).not.toThrow()
    })
  })

  it('does not care what else is in storage', () => {
    // The theme store lives beside it under the same prefix; clearing one must
    // not disturb the other.
    localStorage.setItem('grimoire.theme', 'parchment')
    rememberCurrentCampaign('c-1')
    forgetCurrentCampaign()

    expect(localStorage.getItem('grimoire.theme')).toBe('parchment')
  })
})
