import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSourcesStore } from './sources.js'
import { ApiError } from '../api/http.js'

const request = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))

const PHB = { id: 's-1', title: "Player's Handbook" }
const MM = { id: 's-2', title: 'Monster Manual' }

describe('the sources store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  /*
   * The one thing about this endpoint that is easy to get wrong and expensive
   * to discover: a source belongs to the person, not the table. Threading a
   * selected campaign into this call would scope a library to whichever game
   * happened to be open (#50).
   */
  it('asks for the whole library, with no campaign in the call', async () => {
    request.mockResolvedValue([PHB, MM])

    await useSourcesStore().ensureLoaded()

    expect(request).toHaveBeenCalledWith('/sources/')
  })

  it('sorts by title, because the API does not', async () => {
    request.mockResolvedValue([PHB, MM])
    const sources = useSourcesStore()

    await sources.ensureLoaded()

    expect(sources.sorted.map((s) => s.title)).toEqual(['Monster Manual', "Player's Handbook"])
  })

  it('loads once however many callers ask', async () => {
    request.mockResolvedValue([PHB])
    const sources = useSourcesStore()

    await Promise.all([sources.ensureLoaded(), sources.ensureLoaded()])

    expect(request).toHaveBeenCalledTimes(1)
  })

  it('goes back for a fresh list when asked to reload', async () => {
    request.mockResolvedValue([PHB])
    const sources = useSourcesStore()
    await sources.ensureLoaded()

    await sources.reload()

    expect(request).toHaveBeenCalledTimes(2)
  })

  /*
   * Home asks for campaigns and sources together. One of them being unreachable
   * is not a reason to blank the other — the campaign list is the point of the
   * screen and it should survive a library having a bad day.
   */
  it('fails on its own, without throwing at whoever asked', async () => {
    request.mockRejectedValue(new ApiError(500, null))
    const sources = useSourcesStore()

    await expect(sources.ensureLoaded()).resolves.toBeUndefined()

    expect(sources.error).toBeInstanceOf(ApiError)
    expect(sources.loaded).toBe(false)
    expect(sources.items).toEqual([])
  })
})
