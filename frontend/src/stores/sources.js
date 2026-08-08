import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '../api/client.js'

/*
 * The sources a game master owns — books, magazine issues, their own notes.
 *
 * **Not campaign-scoped.** `GET /sources/` takes no campaign because a source
 * belongs to the person, not the table, and every campaign can see all of them.
 * Do not thread a selected campaign into this call; the fact that home shows
 * sources beside campaigns is precisely because the two sit at the same level.
 *
 * Read-only for now. Adding and editing is #51, and the Library view is #50 —
 * home only lists what is there and links onwards.
 *
 * The order comes from `source_repository.py`, which orders by id. Whether a
 * library wants to be alphabetical by title is #50's question, and it is a
 * question for the query rather than for this file.
 */
export const useSourcesStore = defineStore('sources', () => {
  const items = ref([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref(null)

  let inflight = null

  function ensureLoaded() {
    inflight ??= load()
    return inflight
  }

  function reload() {
    inflight = null
    return ensureLoaded()
  }

  /*
   * Fails on its own. Home asks for campaigns and sources together, and one of
   * them being unreachable is not a reason to blank the other — the campaign
   * list is the point of the screen and it should survive a library that is
   * having a bad day.
   */
  async function load() {
    loading.value = true

    try {
      items.value = await request('/sources/')
      error.value = null
      loaded.value = true
    } catch (failure) {
      error.value = failure
    } finally {
      loading.value = false
    }
  }

  return { items, loading, loaded, error, ensureLoaded, reload }
})
