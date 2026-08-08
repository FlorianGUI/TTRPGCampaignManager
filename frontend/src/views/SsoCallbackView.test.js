import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import SsoCallbackView from './SsoCallbackView.vue'
import { useAuthStore } from '../stores/auth.js'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from '../stores/currentCampaign.js'

const router = { replace: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
}))

function landOn(query = '') {
  window.history.replaceState({}, '', `/auth/callback${query}`)
}

async function mountView() {
  const view = mount(SsoCallbackView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })
  await flushPromises()
  return view
}

function signedIn() {
  const auth = useAuthStore()
  vi.spyOn(auth, 'boot').mockImplementation(async () => {
    auth.user = { id: 'u-1', username: 'aragorn' }
    auth.ready = true
  })
  return auth
}

function signedOut() {
  const auth = useAuthStore()
  vi.spyOn(auth, 'boot').mockImplementation(async () => {
    auth.ready = true
  })
  return auth
}

describe('SsoCallbackView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    router.replace.mockClear()
    sessionStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('picks up the session the callback left in a cookie and moves on', async () => {
    const auth = signedIn()
    landOn()

    await mountView()

    expect(auth.boot).toHaveBeenCalled()
    expect(router.replace).toHaveBeenCalledWith('/')
  })

  it('waits for the boot refresh rather than starting a second one', async () => {
    /*
     * main.js already started one on this page load. A second would not merely
     * be wasteful: rotation means whichever loses that race presents a spent
     * token, which the API reads as a leak and answers by revoking the session —
     * so the user would be signed out by their own client, on arrival.
     */
    const auth = signedIn()
    vi.spyOn(auth, 'renew')
    landOn()

    await mountView()

    expect(auth.renew).not.toHaveBeenCalled()
  })

  it('returns to the page the guard interrupted before the round trip', async () => {
    signedIn()
    sessionStorage.setItem('ttrpg.sso.destination', '/library?q=owlbear')
    landOn()

    await mountView()

    expect(router.replace).toHaveBeenCalledWith('/library?q=owlbear')
  })

  it('lands on the home page when nothing was stashed', async () => {
    signedIn()
    landOn()

    await mountView()

    expect(router.replace).toHaveBeenCalledWith('/')
  })

  it('explains a cancelled sign-in instead of looking broken', async () => {
    signedIn()
    landOn('?error=cancelled&provider=discord')

    const view = await mountView()

    expect(view.text()).toContain('Sign-in cancelled')
    expect(router.replace).not.toHaveBeenCalled()
  })

  it('names the provider it actually was', async () => {
    /*
     * The page cannot know on its own: the round trip left this origin, so the
     * button that started it is two navigations ago. The API says which, and
     * "Google did not answer" beats "the provider did not answer".
     */
    signedIn()
    landOn('?error=provider-unavailable&provider=google')

    const view = await mountView()

    expect(view.text()).toContain('Google did not answer')
    expect(view.text()).not.toContain('Discord')
  })

  it('names Discord when it was Discord', async () => {
    signedIn()
    landOn('?error=provider-unavailable&provider=discord')

    const view = await mountView()

    expect(view.text()).toContain('Discord did not answer')
    expect(view.text()).not.toContain('Google')
  })

  it('will not put an unknown provider name into its own copy', async () => {
    /*
     * The value arrives in a URL, so it is whatever someone typed. Interpolating
     * it raw would let a crafted link write our error page for us — the sentence
     * would carry attacker-chosen text under our own heading.
     */
    signedIn()
    landOn('?error=provider-unavailable&provider=Definitely+Your+Bank')

    const view = await mountView()

    expect(view.text()).toContain('the provider did not answer')
    expect(view.text()).not.toContain('Your Bank')
  })

  it('copes with no provider named at all', async () => {
    signedIn()
    landOn('?error=cancelled')

    const view = await mountView()

    expect(view.text()).toContain('the provider')
  })

  it('does not refresh at all when the callback reported an error', async () => {
    const auth = signedIn()
    landOn('?error=cancelled')

    await mountView()

    expect(auth.boot).not.toHaveBeenCalled()
  })

  it('says what to do about an address Discord has not confirmed', async () => {
    signedIn()
    landOn('?error=unverified-email&provider=discord')

    const view = await mountView()

    expect(view.text()).toContain('Discord has not confirmed your address')
    expect(view.text()).toContain('Confirm it with Discord')
  })

  it('explains the one case a person has to fix from the other side', async () => {
    /*
     * `email-in-use` is the account-linking refusal, and it is the only error
     * here with a route out that is not "try again": sign in with the password,
     * confirm the address, and the link becomes safe.
     */
    signedIn()
    landOn('?error=email-in-use&provider=google')

    const view = await mountView()

    expect(view.text()).toContain('Sign in with your password')
  })

  it('has something to say about a code it has never seen', async () => {
    signedIn()
    landOn('?error=something-invented')

    const view = await mountView()

    expect(view.text()).toContain('Something went wrong')
  })

  it('reports a session that did not survive the trip rather than hanging', async () => {
    signedOut()
    landOn()

    const view = await mountView()

    expect(view.text()).toContain('The sign-in did not stick')
    expect(router.replace).not.toHaveBeenCalled()
  })

  it('always offers a way back to the sign-in page', async () => {
    signedIn()
    landOn('?error=provider-unavailable')

    const view = await mountView()

    expect(view.find('router-link-stub').exists()).toBe(true)
  })

  it('announces the failure to a screen reader', async () => {
    signedIn()
    landOn('?error=cancelled')

    const view = await mountView()

    expect(view.find('[role="alert"]').exists()).toBe(true)
  })

  it('takes the error code out of the address bar', async () => {
    /*
     * Noise on a URL somebody may bookmark or share — and a stale code shown
     * again after a reload would be a lie about the sign-in they just tried.
     */
    signedIn()
    landOn('?error=cancelled')

    await mountView()

    expect(window.location.search).toBe('')
  })

  /*
   * A provider sign-in is a sign-in, and it has to forget the last campaign the
   * way `logIn` does — but it never calls it. The session arrives through
   * `boot()`, which is the same call a returning visitor's cold open makes, so
   * the difference can only be drawn here (#59).
   */
  describe('the remembered campaign', () => {
    beforeEach(() => {
      forgetCurrentCampaign()
    })

    it('is forgotten, so a shared browser does not open the last person’s game', async () => {
      signedIn()
      landOn()
      rememberCurrentCampaign('c-1')

      await mountView()

      expect(readCurrentCampaign()).toBeNull()
    })

    it('is left alone when the sign-in failed', async () => {
      signedOut()
      landOn('?error=cancelled')
      rememberCurrentCampaign('c-1')

      await mountView()

      // Nothing happened. Nobody new is signed in, and taking someone's place
      // away because Discord said no would be a second failure on top of the
      // one this page is here to explain.
      expect(readCurrentCampaign()).toBe('c-1')
    })
  })
})
