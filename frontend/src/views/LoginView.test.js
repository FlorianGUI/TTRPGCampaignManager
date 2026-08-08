import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import LoginView from './LoginView.vue'
import { ApiError } from '../api/http.js'
import { DISCORD_SIGN_IN_URL, takeDestination } from '../api/sso.js'
import { useAuthStore } from '../stores/auth.js'

const router = { replace: vi.fn() }
let query = {}

vi.mock('vue-router', () => ({
  useRouter: () => router,
  useRoute: () => ({ query }),
}))

// RouterLink resolves globally rather than by import, so the mock above does not
// cover it and it has to be stubbed here.
function mountView() {
  return mount(LoginView, { global: { plugins: [PrimeVue], stubs: { RouterLink: true } } })
}

async function submitWith(view, { username = 'aragorn', password = 'anduril' } = {}) {
  await view.find('#login-username').setValue(username)
  await view.find('#login-password').setValue(password)
  await view.find('form').trigger('submit')
  await Promise.resolve()
  await view.vm.$nextTick()
}

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    query = {}
    router.replace.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('signs in and lands on the app', async () => {
    const auth = useAuthStore()
    vi.spyOn(auth, 'logIn').mockResolvedValue()

    const view = mountView()
    await submitWith(view)

    expect(auth.logIn).toHaveBeenCalledWith('aragorn', 'anduril')
    expect(router.replace).toHaveBeenCalledWith('/')
  })

  it('returns to the page the guard interrupted', async () => {
    query = { redirect: '/library?q=owlbear' }
    vi.spyOn(useAuthStore(), 'logIn').mockResolvedValue()

    const view = mountView()
    await submitWith(view)

    expect(router.replace).toHaveBeenCalledWith('/library?q=owlbear')
  })

  it('ignores a redirect pointing off this app', async () => {
    query = { redirect: '//evil.example' }
    vi.spyOn(useAuthStore(), 'logIn').mockResolvedValue()

    const view = mountView()
    await submitWith(view)

    expect(router.replace).toHaveBeenCalledWith('/')
  })

  it('shows bad credentials on the page, not only in the console', async () => {
    vi.spyOn(useAuthStore(), 'logIn').mockRejectedValue(new ApiError(401, 'Incorrect credentials'))

    const view = mountView()
    await submitWith(view)

    const alert = view.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('do not match an account')
  })

  it('says nothing about which half was wrong', async () => {
    /*
     * The API answers 401 identically for an unknown username and a wrong
     * password, precisely so neither can be probed. A message here that named
     * one of them would give away what the backend refused to.
     */
    vi.spyOn(useAuthStore(), 'logIn').mockRejectedValue(new ApiError(401, 'Incorrect credentials'))

    const view = mountView()
    await submitWith(view)

    const text = view.find('[role="alert"]').text().toLowerCase()
    expect(text).not.toMatch(/username (is|was) |no such|unknown user|wrong password/)
  })

  it('passes on the rate limiter’s own words, which are written to be shown', async () => {
    const detail = 'Too many sign-in attempts from here. Try again shortly.'
    vi.spyOn(useAuthStore(), 'logIn').mockRejectedValue(new ApiError(429, detail))

    const view = mountView()
    await submitWith(view)

    expect(view.find('[role="alert"]').text()).toContain(detail)
  })

  it('stays usable after a failure, so a typo is not a dead end', async () => {
    const logIn = vi
      .spyOn(useAuthStore(), 'logIn')
      .mockRejectedValueOnce(new ApiError(401, 'Incorrect credentials'))
      .mockResolvedValueOnce()

    const view = mountView()
    await submitWith(view)
    await submitWith(view)

    expect(logIn).toHaveBeenCalledTimes(2)
    expect(router.replace).toHaveBeenCalledWith('/')
  })

  describe('continuing with Discord', () => {
    beforeEach(() => {
      sessionStorage.clear()
    })

    /*
     * jsdom tries to follow a real anchor and complains that it cannot navigate.
     * The handler still runs, which is what these assert on — this just stops the
     * default action it has no way to perform, and the noise that comes with it.
     */
    async function clickDiscord(view) {
      const link = view.find(`a[href="${DISCORD_SIGN_IN_URL}"]`)
      link.element.addEventListener('click', (event) => event.preventDefault())
      await link.trigger('click')
    }

    it('offers it as a link, not a fetch', () => {
      /*
       * The consent screen is a page at Discord's own address that the person
       * has to be able to read and trust. Discord refuses to be framed, and a
       * consent prompt nobody can see is not consent — so this is a top-level
       * navigation and must stay an anchor.
       */
      const link = mountView().find(`a[href="${DISCORD_SIGN_IN_URL}"]`)

      expect(link.exists()).toBe(true)
      expect(link.text()).toContain('Continue with Discord')
    })

    it('does not hand the destination a handle on this window, or our URL', () => {
      // Our URL carries `?redirect=`, which is nobody's business at Discord.
      const rel = mountView().find(`a[href="${DISCORD_SIGN_IN_URL}"]`).attributes('rel')

      expect(rel).toContain('noopener')
      expect(rel).toContain('noreferrer')
    })

    it('stashes where the guard was sending them, which the round trip would lose', async () => {
      query = { redirect: '/library?q=owlbear' }

      const view = mountView()
      await clickDiscord(view)

      expect(takeDestination()).toBe('/library?q=owlbear')
    })

    it('stashes nothing until the link is actually used', () => {
      query = { redirect: '/library' }

      mountView()

      expect(takeDestination()).toBe('/')
    })

    it('will not stash a destination pointing off this app', async () => {
      query = { redirect: '//evil.example' }

      const view = mountView()
      await clickDiscord(view)

      expect(takeDestination()).toBe('/')
    })
  })

  it('labels its fields and asks password managers for the right thing', () => {
    const view = mountView()

    expect(view.find('label[for="login-username"]').exists()).toBe(true)
    expect(view.find('label[for="login-password"]').exists()).toBe(true)
    expect(view.find('#login-password').attributes('type')).toBe('password')
    expect(view.find('#login-username').attributes('autocomplete')).toBe('username')
    expect(view.find('#login-password').attributes('autocomplete')).toBe('current-password')
  })
})
