/*
 * Which campaign the app opens on its own, and nothing else about it.
 *
 * Deliberately import-free, and deliberately not a Pinia store. `stores/auth.js`
 * has to clear this whenever a session begins or ends, and it cannot import a
 * store that imports `api/client.js`, because that module imports the auth store
 * — a cycle for the sake of one string. Keeping the storage here means the
 * dependency runs one way and stays boring.
 *
 * #14 decided this belonged on `users` as `active_campaign_id`. That column was
 * cut from #44 and is still unbuilt, so #59 keeps the value on the client and
 * says so out loud. The contradiction is smaller than it reads: the campaign id
 * lives in the URL, so this only supplies a *default* for `/`. Campaign pages
 * are bookmarkable, and two tabs can sit in two campaigns — neither of which the
 * server-side column would have given us.
 *
 * It is cleared in four places, and between them they are every moment a session
 * starts or stops being one person's: `logIn`, `logOut`, the SSO callback, and
 * the exit control in the top bar. That is what lets `/` decide with a single
 * rule — a remembered id means go there, no id means show the chooser — with no
 * flag to keep in step and nothing a page reload can desynchronise.
 */

export const CAMPAIGN_STORAGE_KEY = 'grimoire.campaign'

/*
 * Every access is guarded the same way `stores/theme.js` guards its own: Safari
 * in private mode and any page with storage disabled throw on the property, not
 * merely on the call. Forgetting where you were is a dull failure and must never
 * be the reason the app fails to start.
 */
export function readCurrentCampaign() {
  try {
    return localStorage.getItem(CAMPAIGN_STORAGE_KEY) || null
  } catch {
    return null
  }
}

export function rememberCurrentCampaign(id) {
  try {
    localStorage.setItem(CAMPAIGN_STORAGE_KEY, id)
  } catch {
    // Non-fatal: this session still works, it just will not resume itself.
  }
}

export function forgetCurrentCampaign() {
  try {
    localStorage.removeItem(CAMPAIGN_STORAGE_KEY)
  } catch {
    // Nothing to do. See above.
  }
}
