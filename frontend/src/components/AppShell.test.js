import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import AppShell from './AppShell.vue'
import AppNav from './AppNav.vue'

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

function mountShell() {
  return mount(AppShell, {
    props: { sections, active: 'Session notes' },
    // A fresh pinia per mount: the shell reads the theme store for its toggles.
    global: { plugins: [PrimeVue, createPinia()] },
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
})
