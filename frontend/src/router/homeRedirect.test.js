import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { enterRememberedCampaign } from './routes.js'
import { useCampaignsStore } from '../stores/campaigns.js'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from '../stores/currentCampaign.js'
import { ApiError } from '../api/http.js'

const request = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))

/*
 * "Straight into the campaign you were in, unless you just signed in or just
 * left one" (#59).
 *
 * The interesting thing about this rule is what is *not* here: no flag, no
 * history state, no second route. The two exceptions are handled by clearing
 * the id at those moments — which is why the reload case below behaves, and why
 * this guard only has to answer one question.
 */

const HOLLOW = { id: 'c-1', name: 'The Hollow Crown', description: null }

describe('entering the remembered campaign', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
    forgetCurrentCampaign()
  })

  it('shows the chooser when there is nothing remembered', async () => {
    expect(await enterRememberedCampaign()).toBe(true)

    // And it does not go asking for a list it has no question about.
    expect(request).not.toHaveBeenCalled()
  })

  it('goes straight in when the remembered campaign is still there', async () => {
    request.mockResolvedValue([HOLLOW])
    rememberCurrentCampaign('c-1')

    expect(await enterRememberedCampaign()).toEqual({
      name: 'campaign-sessions',
      params: { campaignId: 'c-1' },
      // Or Back from the campaign lands on a `/` that bounces straight here
      // again — an entrance no one can get past.
      replace: true,
    })
  })

  describe('when the remembered campaign is not in the list', () => {
    beforeEach(() => {
      request.mockResolvedValue([HOLLOW])
      rememberCurrentCampaign('c-deleted')
    })

    it('shows the chooser', async () => {
      expect(await enterRememberedCampaign()).toBe(true)
    })

    it('forgets it, so it is not tried again on the next load', async () => {
      await enterRememberedCampaign()

      // Deleted, or belonging to whoever used this browser last. Either way it
      // is not a campaign this user can open.
      expect(readCurrentCampaign()).toBeNull()
    })
  })

  describe('when the list cannot be fetched', () => {
    beforeEach(() => {
      request.mockRejectedValue(new ApiError(503, null))
      rememberCurrentCampaign('c-1')
    })

    it('shows the chooser rather than entering a campaign it could not confirm', async () => {
      expect(await enterRememberedCampaign()).toBe(true)
    })

    it('keeps the id, because a dropped connection is not evidence of anything', async () => {
      await enterRememberedCampaign()

      // Forgetting here would punish a network blip by losing a preference that
      // is almost certainly still correct. The chooser renders the failure and
      // offers a retry instead.
      expect(readCurrentCampaign()).toBe('c-1')
    })
  })

  it('reuses the list the chooser is about to need', async () => {
    request.mockResolvedValue([HOLLOW])
    rememberCurrentCampaign('c-gone')

    await enterRememberedCampaign()
    await useCampaignsStore().ensureLoaded()

    expect(request).toHaveBeenCalledTimes(1)
  })
})
