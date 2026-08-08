import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { request } from '../api/client.js'

/*
 * The campaigns a game master owns.
 *
 * `GET /campaigns/` is filtered server-side by owner, so nothing here filters
 * again — a client-side owner check would be a second, weaker answer to a
 * question the API has already settled.
 *
 * There is no aggregate "dashboard" endpoint and this does not fetch one.
 * Campaigns and sources are two calls because they are two collections; folding
 * them together would put a screen's layout into the API's shape.
 */
export const useCampaignsStore = defineStore('campaigns', () => {
  const items = ref([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref(null)

  /*
   * Sorted here rather than in the view, because more than one screen wants the
   * same order and disagreeing about it would be worse than either choice.
   *
   * `campaign_repository.py` has no `order_by`, so the API returns rows in
   * whatever order Postgres has them in — which can change after any update. A
   * grid of cards found by position must not reshuffle between visits, so the
   * order is decided on this side until there is a reason to page the list, at
   * which point it has to move into the query.
   */
  const sorted = computed(() =>
    [...items.value].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
  )

  /*
   * One load per page load, shared by everyone who asks.
   *
   * Two callers want it at once on a campaign page: the view, and App.vue
   * resolving the name for the top bar's chip. Single-flight so that is one
   * request rather than two, in the same shape `auth.boot()` uses.
   *
   * It never rejects. Callers are a route guard and a template, and neither has
   * anywhere to put a thrown error — the failure belongs in `error` where the
   * page can render it and the guard can tell "not yours" from "could not ask".
   */
  let inflight = null

  function ensureLoaded() {
    inflight ??= load()
    return inflight
  }

  function reload() {
    inflight = null
    return ensureLoaded()
  }

  async function load() {
    loading.value = true

    try {
      items.value = await request('/campaigns/')
      error.value = null
      loaded.value = true
    } catch (failure) {
      error.value = failure
      // Left un-loaded on purpose: `loaded` is what the empty state waits for,
      // and a failed request must not be mistaken for an account with no
      // campaigns. Those two look identical and mean opposite things.
    } finally {
      loading.value = false
    }
  }

  function byId(id) {
    return items.value.find((campaign) => campaign.id === id) ?? null
  }

  /*
   * Creating is #49's subject; what lives here is the one call the empty state
   * needs to not be a dead end. The new campaign is pushed onto the list rather
   * than triggering a reload — the response is the created row, so refetching
   * would be asking the API to repeat itself.
   */
  async function create({ name, description }) {
    const campaign = await request('/campaigns/', {
      method: 'POST',
      json: { name, description: description || null },
    })

    items.value.push(campaign)
    loaded.value = true

    return campaign
  }

  return { items, sorted, loading, loaded, error, ensureLoaded, reload, byId, create }
})
