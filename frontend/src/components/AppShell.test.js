import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import AppShell from './AppShell.vue'
import AppNav from './AppNav.vue'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from '../stores/currentCampaign.js'

const router = { push: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
}))

/*
 * Covers the small-screen navigation contract from issue #25: below the
 * sidebar breakpoint the nav has to stay *reachable*, not merely hidden. The
 * breakpoint itself is CSS and isn't asserted here — jsdom has no layout.
 */

const sections = [
  {
    label: 'Campaign',
    context: 'campaign',
    items: [{ label: 'Session notes', icon: 'pi-file-edit', count: 14 }],
  },
]

const campaign = { id: 'c-1', name: 'The Hollow Crown', description: null }

function mountShell(props = {}) {
  // A fresh pinia per mount: the shell's action cluster reads the theme store
  // for its toggles and the auth store for signing out. setActivePinia as well
  // as the plugin, so a test can reach the same store the component will.
  const pinia = createPinia()
  setActivePinia(pinia)

  return mount(AppShell, {
    props: { sections, active: 'Session notes', ...props },
    global: { plugins: [PrimeVue, pinia] },
  })
}

/* matchMedia is not implemented in jsdom; the shell listens to it on setup. */
function stubMatchMedia() {
  const listeners = new Set()

  window.matchMedia = vi.fn(() => ({
    matches: false,
    addEventListener: (_, fn) => listeners.add(fn),
    removeEventListener: (_, fn) => listeners.delete(fn),
  }))

  return listeners
}

describe('AppShell', () => {
  beforeEach(() => {
    stubMatchMedia()
  })

  it('renders the same nav in the sidebar and, once open, in the drawer', async () => {
    const wrapper = mountShell()

    expect(wrapper.findAllComponents(AppNav)).toHaveLength(1)

    await wrapper.get('.shell__nav-toggle').trigger('click')

    expect(wrapper.findAllComponents(AppNav)).toHaveLength(2)
  })

  it('keeps the drawer closed until the nav toggle is pressed', async () => {
    const wrapper = mountShell()
    const drawer = wrapper.findComponent({ name: 'Drawer' })

    expect(drawer.props('visible')).toBe(false)

    await wrapper.get('.shell__nav-toggle').trigger('click')

    expect(drawer.props('visible')).toBe(true)
  })

  it('closes the drawer once a destination is chosen', async () => {
    const wrapper = mountShell()
    await wrapper.get('.shell__nav-toggle').trigger('click')

    const drawerNav = wrapper.findAllComponents(AppNav)[1]
    drawerNav.vm.$emit('navigate', sections[0].items[0])
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent({ name: 'Drawer' }).props('visible')).toBe(false)
  })

  it('closes the drawer when the viewport grows past the sidebar breakpoint', async () => {
    const listeners = stubMatchMedia()
    const wrapper = mountShell()
    await wrapper.get('.shell__nav-toggle').trigger('click')

    listeners.forEach((fn) => fn({ matches: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent({ name: 'Drawer' }).props('visible')).toBe(false)
  })

  it('reveals the collapsed search row from the search toggle', async () => {
    const wrapper = mountShell()

    expect(wrapper.find('#shell-search-row').exists()).toBe(false)

    await wrapper.get('.shell__search-toggle').trigger('click')

    expect(wrapper.find('#shell-search-row').exists()).toBe(true)
  })

  /*
   * The other half of putting home outside this shell (#59). Without a way
   * back, the chooser is reachable only by signing out — and signing out is not
   * a way back.
   */
  describe('the campaign chip', () => {
    beforeEach(() => {
      router.push.mockClear()
      forgetCurrentCampaign()
    })

    it('is absent until there is a campaign to name', () => {
      expect(mountShell().find('.shell__campaign').exists()).toBe(false)
    })

    it('names the campaign it will leave, for anyone not looking at the icon', () => {
      const wrapper = mountShell({ campaign })

      expect(wrapper.get('.shell__campaign-name').text()).toBe('The Hollow Crown')
      expect(wrapper.get('.shell__campaign-leave').attributes('aria-label')).toBe(
        'Leave The Hollow Crown',
      )
    })

    it('forgets the campaign on the way out, so / shows the chooser', async () => {
      rememberCurrentCampaign(campaign.id)
      const wrapper = mountShell({ campaign })

      await wrapper.get('.shell__campaign-leave').trigger('click')

      /*
       * Both halves matter. Navigating without forgetting would send you to a
       * `/` that redirects straight back into the campaign you just left — an
       * exit that cannot be used.
       */
      expect(readCurrentCampaign()).toBeNull()
      expect(router.push).toHaveBeenCalledWith({ name: 'home' })
    })
  })
})
