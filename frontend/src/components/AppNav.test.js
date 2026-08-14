import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppNav from './AppNav.vue'

/*
 * The heads of the sidebar's lists.
 *
 * A head looks like the items under it — same box, same hover, same way of
 * saying it is current — and stays a head by its small-caps and the rule beneath
 * it. That much is CSS and is not asserted here; what is asserted is the part
 * that decides whether any of it is reachable: a head is a control only where
 * the section has somewhere of its own to go.
 *
 * Which matters because the alternative was a link that goes nowhere. `Library`
 * has no page yet, and #79's objection to the campaign name applies just as well
 * to a category: a thing that invites a click and answers with nothing is worse
 * than a heading that never asked for one.
 */

function routerWith() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/library', name: 'library', component: { template: '<div />' } },
    ],
  })
}

function mountNav(sections) {
  const router = routerWith()
  const wrapper = mount(AppNav, {
    props: { sections },
    global: { plugins: [router] },
  })

  return { wrapper, router }
}

const LIBRARY = {
  label: 'Library',
  items: [{ label: 'Bestiary', icon: 'pi pi-eye', count: 318 }],
}

describe('a sidebar section head', () => {
  it('is a heading, not a control, where the section has nowhere to go', () => {
    const { wrapper } = mountNav([LIBRARY])
    const head = wrapper.get('.nav-section')

    expect(head.element.tagName).toBe('P')
    expect(head.text()).toBe('Library')
    expect(wrapper.find('a.nav-section').exists()).toBe(false)
  })

  it('is a link where the section does have one', async () => {
    const { wrapper, router } = mountNav([{ ...LIBRARY, to: { name: 'library' } }])
    const head = wrapper.get('a.nav-section')

    expect(head.attributes('href')).toBe('/library')

    await router.push('/library')
    await router.isReady()

    // The same way an item says it: `aria-current`, which the styling hangs off.
    expect(wrapper.get('a.nav-section').attributes('aria-current')).toBe('page')
  })

  it('is not current while its own page is not the one being read', async () => {
    const { wrapper, router } = mountNav([{ ...LIBRARY, to: { name: 'library' } }])

    await router.push('/')
    await router.isReady()

    expect(wrapper.get('a.nav-section').attributes('aria-current')).toBeUndefined()
  })

  it('carries the same label treatment whether or not it leads anywhere', () => {
    const plain = mountNav([LIBRARY]).wrapper.get('.nav-section')
    const linked = mountNav([{ ...LIBRARY, to: { name: 'library' } }]).wrapper.get('.nav-section')

    // One class pair, so the two cannot drift into looking like different things.
    for (const head of [plain, linked]) {
      expect(head.classes()).toContain('label-smallcaps')
      expect(head.classes()).toContain('nav-section')
    }
  })
})
