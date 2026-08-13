import { describe, it, expect, beforeEach, vi } from 'vitest'
import { h } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import AppShell from './AppShell.vue'
import AppNav from './AppNav.vue'
import CampaignTitle from './CampaignTitle.vue'
import ChromeActions from './ChromeActions.vue'

const router = { push: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
  /*
   * The campaign's name is a link into the structure now (#88), and it renders a
   * `custom` RouterLink so it can own the anchor it measures. The stub has to
   * hand the slot the same three values the real one does, or the title renders
   * nothing at all and every assertion below fails for the wrong reason.
   */
  RouterLink: {
    props: { to: { type: [String, Object], required: true }, custom: Boolean },
    setup(props, { slots }) {
      const slotProps = { href: '/stub', navigate: () => {}, isActive: false }
      return () => (props.custom ? slots.default(slotProps) : h('a', slots.default?.(slotProps)))
    },
  },
}))

// The sidebar reads the campaign's tree on every campaign route. This suite is
// about the shell's layout, so the request is stubbed rather than answered.
vi.mock('../api/client.js', () => ({ request: vi.fn(() => new Promise(() => {})) }))

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

  /*
   * The campaign is named in the sidebar now, at the head of the navigation it
   * belongs to, rather than as a tag in a bar that is about the app. What it
   * does when opened is covered where it lives, in CampaignMenu.test.js.
   */
  describe('naming the campaign', () => {
    it('puts the name at the head of the sidebar, not in the top bar', () => {
      const wrapper = mountShell({ campaign })

      expect(wrapper.get('.shell__sidebar').findComponent(CampaignTitle).exists()).toBe(true)
      expect(wrapper.get('.shell__bar').findComponent(CampaignTitle).exists()).toBe(false)
    })

    it('hands it the campaign it was given', () => {
      expect(mountShell({ campaign }).findComponent(CampaignTitle).props('campaign')).toEqual(
        campaign,
      )
    })

    it('says nothing at all when there is no campaign', () => {
      // Absent rather than an empty heading: on a route above any campaign
      // there is no name to give.
      expect(mountShell().findComponent(CampaignTitle).exists()).toBe(false)
    })

    it('travels into the drawer, which is the only place it is named on a phone', async () => {
      const wrapper = mountShell({ campaign })
      await wrapper.get('.shell__nav-toggle').trigger('click')

      // The sidebar is hidden below 900px, so a name that stayed behind in it
      // would leave the campaign unnamed exactly where the drawer exists to
      // help.
      expect(wrapper.findAllComponents(CampaignTitle)).toHaveLength(2)
    })
  })

  it('hands the campaign to the account menu, which is what grows its items', () => {
    // A prop rather than a second component: ChromeActions exists so the
    // chooser's bar and the campaign's bar cannot drift apart, and the campaign
    // is the only thing that differs between them.
    expect(mountShell({ campaign }).findComponent(ChromeActions).props('campaign')).toEqual(
      campaign,
    )
  })

  it('passes nothing on when there is no campaign', () => {
    expect(mountShell().findComponent(ChromeActions).props('campaign')).toBeNull()
  })

  /*
   * #79 took the search field, its toggle and the collapsed row out. Nothing was
   * ever behind them — a placeholder since the spike — and a control that does
   * nothing costs more than the space it takes: it is a promise the app does not
   * keep.
   */
  it('offers no search, since there is nothing behind it to find', () => {
    const wrapper = mountShell({ campaign })

    expect(wrapper.find('#shell-search-row').exists()).toBe(false)
    expect(wrapper.find('.shell__search-toggle').exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'InputText' }).exists()).toBe(false)
  })
})
