import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCampaignsStore } from './campaigns.js'
import { ApiError } from '../api/http.js'

const request = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))

const HOLLOW = { id: 'c-1', name: 'The Hollow Crown', description: 'A kingdom with no heir.' }
const SALT = { id: 'c-2', name: 'Salt & Ashes', description: null }

describe('the campaigns store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('asks the API for the list, and does not filter it again', async () => {
    request.mockResolvedValue([HOLLOW, SALT])
    const campaigns = useCampaignsStore()

    await campaigns.ensureLoaded()

    // Filtering by owner here would be a second, weaker answer to a question
    // `GET /campaigns/` has already settled server-side.
    expect(request).toHaveBeenCalledWith('/campaigns/')
    expect(campaigns.items).toEqual([HOLLOW, SALT])
    expect(campaigns.loaded).toBe(true)
  })

  /*
   * `campaign_repository.py` has no `order_by`, so the API's order is whatever
   * Postgres has and can change after any update. A grid of cards found by
   * position must not reshuffle between visits.
   */
  it('sorts by name, because the API does not', async () => {
    request.mockResolvedValue([HOLLOW, SALT])

    const campaigns = useCampaignsStore()
    await campaigns.ensureLoaded()

    expect(campaigns.sorted.map((c) => c.name)).toEqual(['Salt & Ashes', 'The Hollow Crown'])
  })

  it('orders numbered campaigns the way a person would', async () => {
    request.mockResolvedValue([
      { id: 'a', name: 'Arc 10' },
      { id: 'b', name: 'Arc 2' },
    ])

    const campaigns = useCampaignsStore()
    await campaigns.ensureLoaded()

    expect(campaigns.sorted.map((c) => c.name)).toEqual(['Arc 2', 'Arc 10'])
  })

  it('loads once however many callers ask', async () => {
    request.mockResolvedValue([HOLLOW])
    const campaigns = useCampaignsStore()

    // The route guard and the view both ask on the way into `/`, and App.vue
    // asks again for the top bar's chip. One request between them.
    await Promise.all([campaigns.ensureLoaded(), campaigns.ensureLoaded()])
    await campaigns.ensureLoaded()

    expect(request).toHaveBeenCalledTimes(1)
  })

  it('goes back for a fresh list when asked to reload', async () => {
    request.mockResolvedValue([HOLLOW])
    const campaigns = useCampaignsStore()
    await campaigns.ensureLoaded()

    request.mockResolvedValue([HOLLOW, SALT])
    await campaigns.reload()

    expect(request).toHaveBeenCalledTimes(2)
    expect(campaigns.items).toHaveLength(2)
  })

  it('finds a campaign by id, and says so plainly when it cannot', async () => {
    request.mockResolvedValue([HOLLOW, SALT])
    const campaigns = useCampaignsStore()
    await campaigns.ensureLoaded()

    expect(campaigns.byId('c-2')).toEqual(SALT)
    expect(campaigns.byId('c-gone')).toBeNull()
  })

  describe('when the request fails', () => {
    it('keeps the failure rather than throwing it at a route guard', async () => {
      request.mockRejectedValue(new ApiError(503, null))
      const campaigns = useCampaignsStore()

      // A guard and a template are the two callers, and neither has anywhere to
      // put a rejected promise.
      await expect(campaigns.ensureLoaded()).resolves.toBeUndefined()
      expect(campaigns.error).toBeInstanceOf(ApiError)
    })

    it('stays un-loaded, so the empty state is never shown for a dropped connection', async () => {
      request.mockRejectedValue(new ApiError(503, null))
      const campaigns = useCampaignsStore()

      await campaigns.ensureLoaded()

      /*
       * "no campaigns yet" and "could not ask" look identical in the data and
       * mean opposite things. `loaded` is what tells them apart — telling a
       * game master with three campaigns to start their first one is the kind
       * of lie that makes a page feel broken.
       */
      expect(campaigns.loaded).toBe(false)
      expect(campaigns.items).toEqual([])
    })
  })

  describe('creating', () => {
    it('sends the name and description, and keeps the row it gets back', async () => {
      request.mockResolvedValue(HOLLOW)
      const campaigns = useCampaignsStore()

      const created = await campaigns.create({
        name: 'The Hollow Crown',
        description: 'A kingdom.',
      })

      expect(request).toHaveBeenCalledWith('/campaigns/', {
        method: 'POST',
        json: { name: 'The Hollow Crown', description: 'A kingdom.' },
      })
      expect(created).toEqual(HOLLOW)
      // The response is the created row, so refetching would be asking the API
      // to repeat itself.
      expect(campaigns.items).toEqual([HOLLOW])
    })

    it('sends null rather than an empty description', async () => {
      request.mockResolvedValue(SALT)

      await useCampaignsStore().create({ name: 'Salt & Ashes', description: '' })

      expect(request).toHaveBeenCalledWith(
        '/campaigns/',
        expect.objectContaining({ json: { name: 'Salt & Ashes', description: null } }),
      )
    })

    it('counts as loaded, so a first campaign does not leave the empty state up', async () => {
      request.mockResolvedValue(HOLLOW)
      const campaigns = useCampaignsStore()

      await campaigns.create({ name: 'The Hollow Crown', description: '' })

      expect(campaigns.loaded).toBe(true)
    })

    it('lets a failure reach the form, which is the only thing that can explain it', async () => {
      request.mockRejectedValue(new ApiError(422, null))

      await expect(useCampaignsStore().create({ name: 'x', description: '' })).rejects.toThrow(
        ApiError,
      )
    })
  })
})
