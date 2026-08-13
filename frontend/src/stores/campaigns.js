import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '../api/client.js'
import { forgetCollapsed } from './collapsedNarrative.js'

/*
 * The campaigns a game master owns.
 *
 * `GET /campaigns/` is filtered server-side by owner, so nothing here filters
 * again — a client-side owner check would be a second, weaker answer to a
 * question the API has already settled.
 *
 * The order is the API's too, for the same reason. `campaign_repository.py`
 * orders by id: arbitrary but fixed, which is the property a grid of cards
 * needs. Re-sorting here would mean two places decide the order and only one of
 * them survives paging.
 *
 * There is no aggregate "dashboard" endpoint and this does not fetch one.
 * Campaigns and sources are two calls because they are two collections; folding
 * them together would put a screen's layout into the API's shape.
 *
 * The list is also the app's answer to "is this campaign mine?". A campaign
 * belonging to someone else 404s exactly as one that does not exist, so an id
 * absent from here is the same absence either way — which is what lets the route
 * guard, the top bar's chip and the edit form all read `byId` rather than each
 * inventing a way to ask.
 */
export const useCampaignsStore = defineStore('campaigns', () => {
  const items = ref([])
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref(null)

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
   * The three writes. None of them reloads the list: every one answers with the
   * row it changed (or, for a delete, with nothing left to say), so refetching
   * would be asking the API to repeat itself — and would race the navigation
   * that follows each of them.
   *
   * They all reject rather than parking the failure in `error` the way `load`
   * does. That field belongs to the list: a form has somewhere to put a rejected
   * promise and needs the status to say *which* field the API objected to, and
   * painting the whole chooser as broken because one edit was refused would be
   * the wrong screen showing the wrong thing.
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

  /*
   * `PUT /campaigns/{id}` is a full replacement, not a patch: a description left
   * out of the body is cleared rather than kept. So both fields are always sent,
   * and the form that calls this is loaded with the current values for the same
   * reason — an edit that only touches the name must still carry the description
   * it did not touch, or saving a name silently wipes the description.
   */
  async function update(id, { name, description }) {
    const campaign = await request(`/campaigns/${id}`, {
      method: 'PUT',
      json: { name, description: description || null },
    })

    // Only ever reached through a loaded list — the edit form is rendered from
    // `byId` — so a miss here would mean editing something not in the list, and
    // appending it would put a row on the chooser by way of a failed lookup.
    const at = items.value.findIndex((c) => c.id === id)
    if (at !== -1) items.value[at] = campaign

    return campaign
  }

  /*
   * Takes the characters at the table with it — the cascade is `CampaignService`'s
   * (see its `delete`), which is why the confirmation that guards this one is a
   * typed name rather than a dialog dismissed by reflex.
   */
  async function remove(id) {
    await request(`/campaigns/${id}`, { method: 'DELETE' })

    items.value = items.value.filter((campaign) => campaign.id !== id)
    // The campaign is gone, so which of its acts were shut is not a preference
    // any more — it is the one place a deleted campaign would live on.
    forgetCollapsed(id)
  }

  return { items, loading, loaded, error, ensureLoaded, reload, byId, create, update, remove }
})
