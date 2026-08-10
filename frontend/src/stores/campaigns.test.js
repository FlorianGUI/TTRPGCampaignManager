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
   * The order is the API's. `campaign_repository.py` orders by id — arbitrary
   * but fixed, which is what a grid of cards found by position needs. Re-sorting
   * here would mean two places decide the order and only one of them survives
   * the day this list is paged.
   */
  it('keeps the order the API sent, without a second opinion about it', async () => {
    request.mockResolvedValue([HOLLOW, SALT])

    const campaigns = useCampaignsStore()
    await campaigns.ensureLoaded()

    expect(campaigns.items.map((c) => c.name)).toEqual(['The Hollow Crown', 'Salt & Ashes'])
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

  describe('updating', () => {
    async function loaded() {
      request.mockResolvedValue([HOLLOW, SALT])
      const campaigns = useCampaignsStore()
      await campaigns.ensureLoaded()
      request.mockReset()

      return campaigns
    }

    it('PUTs both fields, because the API replaces rather than patches', async () => {
      const campaigns = await loaded()
      request.mockResolvedValue({ ...HOLLOW, name: 'The Hollow Throne' })

      await campaigns.update('c-1', {
        name: 'The Hollow Throne',
        description: 'A kingdom with no heir.',
      })

      /*
       * `PUT /campaigns/{id}` is a full replacement: a description left out of
       * the body is cleared, not kept. Sending only what changed would wipe the
       * description of every campaign anyone renamed.
       */
      expect(request).toHaveBeenCalledWith('/campaigns/c-1', {
        method: 'PUT',
        json: { name: 'The Hollow Throne', description: 'A kingdom with no heir.' },
      })
    })

    it('puts the row it gets back where the old one was', async () => {
      const campaigns = await loaded()
      const renamed = { ...HOLLOW, name: 'The Hollow Throne' }
      request.mockResolvedValue(renamed)

      await campaigns.update('c-1', { name: 'The Hollow Throne', description: 'x' })

      // In place: the order is the API's, and moving a renamed campaign to the
      // end of the chooser would be this store having an opinion about it.
      expect(campaigns.items).toEqual([renamed, SALT])
    })

    it('sends null rather than an empty description', async () => {
      const campaigns = await loaded()
      request.mockResolvedValue(SALT)

      await campaigns.update('c-2', { name: 'Salt & Ashes', description: '' })

      expect(request).toHaveBeenCalledWith(
        '/campaigns/c-2',
        expect.objectContaining({ json: { name: 'Salt & Ashes', description: null } }),
      )
    })

    it('lets a failure reach the form rather than parking it in `error`', async () => {
      const campaigns = await loaded()
      request.mockRejectedValue(new ApiError(404, 'Campaign not found'))

      await expect(campaigns.update('c-1', { name: 'x', description: '' })).rejects.toThrow(
        ApiError,
      )

      // `error` belongs to the list. Painting the whole chooser as broken
      // because one edit was refused would be the wrong screen saying so.
      expect(campaigns.error).toBeNull()
      expect(campaigns.items).toEqual([HOLLOW, SALT])
    })
  })

  describe('deleting', () => {
    async function loaded() {
      request.mockResolvedValue([HOLLOW, SALT])
      const campaigns = useCampaignsStore()
      await campaigns.ensureLoaded()
      request.mockReset()

      return campaigns
    }

    it('asks the API, then drops it from the list without refetching', async () => {
      const campaigns = await loaded()
      request.mockResolvedValue(null)

      await campaigns.remove('c-1')

      expect(request).toHaveBeenCalledWith('/campaigns/c-1', { method: 'DELETE' })
      // A 204 has nothing to say, and the one row that changed is the one we
      // just named. Reloading here would also race the navigation that follows.
      expect(request).toHaveBeenCalledTimes(1)
      expect(campaigns.items).toEqual([SALT])
    })

    it('keeps the campaign when the API refuses to delete it', async () => {
      const campaigns = await loaded()
      request.mockRejectedValue(new ApiError(404, 'Campaign not found'))

      await expect(campaigns.remove('c-1')).rejects.toThrow(ApiError)

      // Removing it locally on a failure would show it gone until the next
      // reload brought it back — the worst of both answers.
      expect(campaigns.items).toEqual([HOLLOW, SALT])
    })
  })
})
