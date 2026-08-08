import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ChromeActions from './ChromeActions.vue'
import { useAuthStore } from '../stores/auth.js'
import { useThemeStore } from '../stores/theme.js'

/*
 * The cluster shared by both top bars. These behaviours used to live in
 * AppShell's tests and moved here with the markup — the point of extracting it
 * was that the chooser's bar and the campaign's bar cannot drift apart, and a
 * test that only ever mounts one of them would not notice if they did.
 */

const router = { push: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
}))

function mountActions() {
  const pinia = createPinia()
  setActivePinia(pinia)

  return mount(ChromeActions, { global: { plugins: [PrimeVue, pinia] } })
}

describe('ChromeActions', () => {
  beforeEach(() => {
    router.push.mockClear()
  })

  describe('signing out', () => {
    it('revokes the session server-side, then returns to the login page', async () => {
      const wrapper = mountActions()
      const auth = useAuthStore()
      const logOut = vi.spyOn(auth, 'logOut').mockResolvedValue()

      await wrapper.get('.chrome-actions__sign-out').trigger('click')
      await wrapper.vm.$nextTick()

      /*
       * Through the store, which calls POST /users/logout before clearing.
       * Clearing locally alone would leave a working refresh cookie behind —
       * the one way to log out that does not log you out (#35).
       */
      expect(logOut).toHaveBeenCalled()
      expect(router.push).toHaveBeenCalledWith({ name: 'login' })
    })

    it('is reachable and labelled without relying on the icon', () => {
      expect(mountActions().get('.chrome-actions__sign-out').attributes('aria-label')).toBe(
        'Sign out',
      )
    })
  })

  describe('the toggles', () => {
    it('flips the theme, and says which way it is going', async () => {
      const wrapper = mountActions()
      const theme = useThemeStore()

      const button = wrapper.get('[aria-label="Switch to parchment theme"]')
      await button.trigger('click')

      expect(theme.theme).toBe('parchment')
      expect(wrapper.find('[aria-label="Switch to candlelight theme"]').exists()).toBe(true)
    })

    it('flips the density the same way', async () => {
      const wrapper = mountActions()
      const theme = useThemeStore()

      await wrapper.get('.chrome-actions__density').trigger('click')

      expect(theme.density).toBe('compact')
    })
  })
})
