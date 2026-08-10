import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ChromeActions from './ChromeActions.vue'
import { useAuthStore } from '../stores/auth.js'
import { useThemeStore } from '../stores/theme.js'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from '../stores/currentCampaign.js'

/*
 * The cluster shared by both top bars, which #79 turned from three icon buttons
 * into a named trigger and a menu. It exists so the chooser's bar and the
 * campaign's bar cannot drift apart — a test that only ever mounted one of them
 * would not notice if they did.
 *
 * Everything you can *do* is here, the campaign's actions included. What is not
 * is the campaign's name: that is a label, and it lives at the head of the nav
 * it names (CampaignTitle).
 */

const router = { push: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
}))

const campaign = { id: 'c-1', name: 'The Hollow Crown', description: null }

function mountActions(props = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { id: 'u-1', username: 'aragorn' }

  return mount(ChromeActions, {
    props,
    // The menu is an overlay and teleports to the body, which would put every
    // item outside the wrapper.
    global: { plugins: [PrimeVue, pinia], stubs: { teleport: true } },
  })
}

/* Opens the menu and hands back the rendered items. */
async function openMenu(wrapper) {
  await wrapper.get('.chrome-actions__trigger').trigger('click')
  await flushPromises()

  return wrapper.findAll('.p-menu-item-link')
}

function labels(items) {
  return items.map((item) => item.text())
}

/* The item whose label starts with the given text, so a test names what it
 * clicks rather than counting positions. */
function item(items, label) {
  return items.find((entry) => entry.text().startsWith(label))
}

describe('ChromeActions', () => {
  beforeEach(() => {
    router.push.mockClear()
    forgetCurrentCampaign()
  })

  describe('the trigger', () => {
    it('says who is signed in, which is what the old bar never did', () => {
      expect(mountActions().get('.chrome-actions__trigger').text()).toContain('aragorn')
    })

    it('announces itself as a menu, since the name is the control', () => {
      const trigger = mountActions().get('.chrome-actions__trigger')

      expect(trigger.attributes('aria-haspopup')).toBe('menu')
      expect(trigger.attributes('aria-expanded')).toBe('false')
      expect(trigger.attributes('aria-controls')).toBe('chrome-actions-menu')
    })

    it('reports itself expanded once the menu is open', async () => {
      const wrapper = mountActions()

      await openMenu(wrapper)

      expect(wrapper.get('.chrome-actions__trigger').attributes('aria-expanded')).toBe('true')
    })
  })

  describe('above any campaign', () => {
    it('offers the theme and signing out, and nothing about a campaign', async () => {
      // What `BareLayout` mounts: on the chooser there is no campaign to close
      // and none to settle.
      const items = await openMenu(mountActions())

      expect(labels(items)).toEqual(['Switch theme', 'Sign out'])
    })

    it('leaves the campaign items out rather than dimming them', async () => {
      const items = await openMenu(mountActions())

      /*
       * #59 argued this for the sidebar and it holds here: a disabled item
       * reads as broken rather than as not-yet-available. There is nothing to
       * grey out — there is no campaign.
       */
      expect(item(items, 'Close campaign')).toBeUndefined()
      expect(item(items, 'Campaign settings')).toBeUndefined()
    })
  })

  describe('inside a campaign', () => {
    it('grows the two campaign items, above the separator and sign out', async () => {
      const items = await openMenu(mountActions({ campaign }))

      expect(labels(items)).toEqual([
        'Switch theme',
        'Campaign settings',
        'Close campaign',
        'Sign out',
      ])
    })

    it('goes to the settings for the campaign it was given', async () => {
      const items = await openMenu(mountActions({ campaign }))

      await item(items, 'Campaign settings').trigger('click')

      expect(router.push).toHaveBeenCalledWith({
        name: 'campaign-settings',
        params: { campaignId: 'c-1' },
      })
    })

    it('forgets the campaign on the way out, so / shows the chooser', async () => {
      rememberCurrentCampaign('c-1')
      const items = await openMenu(mountActions({ campaign }))

      await item(items, 'Close campaign').trigger('click')

      /*
       * Both halves matter, and they are unchanged from the chip's ×.
       * Navigating without forgetting would send you to a `/` that redirects
       * straight back into the campaign you just left — an exit that cannot be
       * used.
       */
      expect(readCurrentCampaign()).toBeNull()
      expect(router.push).toHaveBeenCalledWith({ name: 'home' })
    })
  })

  describe('the theme item', () => {
    it('is an action rather than a destination', async () => {
      const wrapper = mountActions()
      const theme = useThemeStore()

      const items = await openMenu(wrapper)
      await item(items, 'Switch theme').trigger('click')

      expect(theme.theme).toBe('parchment')
    })

    it('keeps its wording once flipped, and lets the icon carry the direction', async () => {
      const wrapper = mountActions()
      useThemeStore().toggleTheme()

      const items = await openMenu(wrapper)

      // In a list of verbs — switch, sign out — naming the destination would be
      // the odd one out. Which way it goes is the icon's job.
      expect(item(items, 'Switch theme')).toBeDefined()
      expect(labels(items)).not.toContain('Candlelight theme')
    })
  })

  describe('signing out', () => {
    it('revokes the session server-side, then returns to the login page', async () => {
      const wrapper = mountActions()
      const auth = useAuthStore()
      const logOut = vi.spyOn(auth, 'logOut').mockResolvedValue()

      const items = await openMenu(wrapper)
      await item(items, 'Sign out').trigger('click')
      await flushPromises()

      /*
       * Through the store, which calls POST /users/logout before clearing.
       * Clearing locally alone would leave a working refresh cookie behind —
       * the one way to log out that does not log you out (#35).
       */
      expect(logOut).toHaveBeenCalled()
      expect(router.push).toHaveBeenCalledWith({ name: 'login' })
    })

    it('is present on every route, which is the part of #25 that still holds', async () => {
      /*
       * #25 decided sign out must not fold away as the bar narrows. It is
       * behind a trigger now rather than beside the theme toggle, but it is in
       * the menu whether or not there is a campaign — what changed is the
       * number of taps, not whether it is reachable.
       */
      expect(labels(await openMenu(mountActions()))).toContain('Sign out')
      expect(labels(await openMenu(mountActions({ campaign })))).toContain('Sign out')
    })

    it('is last, below the separator, so a slip lands on something recoverable', async () => {
      const items = await openMenu(mountActions({ campaign }))

      expect(labels(items).at(-1)).toBe('Sign out')
    })
  })
})
