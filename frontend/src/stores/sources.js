import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
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
 */
export const useSourcesStore = defineStore('sources', () => {
  const items = ref([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref(null)

  // Same reasoning as the campaigns store: `source_repository.py` has no
  // `order_by` either, so the order is decided here until it needs to be a
  // query. #50 owns whether that stays true once the Library view lands.
  const sorted = computed(() =>
    [...items.value].sort((a, b) => a.title.localeCompare(b.title, undefined, { numeric: true })),
  )

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

  return { items, sorted, loading, loaded, error, ensureLoaded, reload }
})
