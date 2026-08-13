/*
 * Which acts and sequences a game master has shut, per campaign.
 *
 * Deliberately import-free and deliberately not a Pinia store, for the reasons
 * `currentCampaign.js` gives: this is storage, not state anyone else reasons
 * about, and keeping it here means the dependency runs one way and stays boring.
 *
 * **The API has no `collapsed` column and must not grow one.** Whether an act is
 * shut is a per-person, per-device view preference rather than a fact about the
 * campaign — under #31 two game masters at the same table would fight over a
 * stored one, and neither would be wrong. It is also the sort of thing that
 * would quietly turn every expand into a write.
 *
 * Keyed by campaign, because collapsing Act I of one campaign says nothing about
 * another, and a single shared set would have them contradicting each other on
 * every navigation.
 *
 * Every access is guarded the same way `theme.js` and `currentCampaign.js` guard
 * theirs: Safari in private mode and any page with storage disabled throw on the
 * property, not merely on the call. Forgetting which acts were shut is a dull
 * failure and must never be the reason the app fails to start.
 */

export const COLLAPSED_STORAGE_KEY = 'grimoire.collapsed'

function readAll() {
  try {
    const stored = JSON.parse(localStorage.getItem(COLLAPSED_STORAGE_KEY) ?? '{}')
    // Anything but an object means the key was written by something else, or by
    // an older shape. Treat it as absent rather than reasoning about it.
    return stored && typeof stored === 'object' && !Array.isArray(stored) ? stored : {}
  } catch {
    return {}
  }
}

/*
 * A Set rather than the stored array, because the only questions a template asks
 * are "is this one shut" and "shut this one" — and `includes` on every row of a
 * two-hundred-scene outline is the wrong shape for both.
 */
export function readCollapsed(campaignId) {
  const ids = readAll()[campaignId]
  return new Set(Array.isArray(ids) ? ids : [])
}

export function rememberCollapsed(campaignId, ids) {
  try {
    const all = readAll()

    // An empty set removes the campaign's entry rather than storing `[]`. A game
    // master who expands everything should leave nothing behind, and the key
    // should not accumulate one entry per campaign they have ever opened.
    if (ids.size) all[campaignId] = [...ids]
    else delete all[campaignId]

    localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(all))
  } catch {
    // Non-fatal: this session still works, it just will not remember.
  }
}

/*
 * For when a campaign goes. Nothing calls this yet — deleting a campaign
 * navigates away and the entry is harmless — but it is here so the key does not
 * become the one place a deleted campaign lives on.
 */
export function forgetCollapsed(campaignId) {
  try {
    const all = readAll()
    delete all[campaignId]
    localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(all))
  } catch {
    // Nothing to do. See above.
  }
}
