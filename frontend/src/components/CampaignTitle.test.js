import { describe, it, expect, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import { createRouter, createMemoryHistory } from 'vue-router'
import CampaignTitle from './CampaignTitle.vue'

/*
 * The campaign's name at the head of its own navigation, and the way into its
 * structure (#88).
 *
 * It was deliberately not a control until now, and the test below that asserted
 * so has been rewritten rather than deleted. #79's objection was to a thing that
 * *invited* a click and answered with nothing; the name has somewhere to go now,
 * so the objection is met by giving it a destination and the affordances that
 * promise one, rather than by taking the affordances away.
 */

const campaign = { id: 'c-1', name: 'The Hollow Crown', description: 'A kingdom with no heir.' }

/* The title observes its own box, to notice the column changing width; jsdom has
 * no ResizeObserver. Not a fact about this component, only about the
 * environment. */
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

/*
 * jsdom lays nothing out — every element is 0 wide — so whether the name is
 * ellipsised has to be stated rather than produced. These are the two numbers
 * the component compares: what the name needs, and what the column gives it.
 * Only `<a>` is affected, and the tooltip's own popup is a `<div>`.
 */
function measuring({ name, column }) {
  Object.defineProperty(HTMLAnchorElement.prototype, 'scrollWidth', {
    configurable: true,
    get: () => name,
  })
  Object.defineProperty(HTMLAnchorElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => column,
  })
}

/*
 * A real router rather than a stub, because the point of this component now is
 * where it goes: a stubbed RouterLink would let the destination be wrong and the
 * test still pass.
 */
function routerWith(structure = '/campaigns/:campaignId/structure') {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: structure, name: 'campaign-structure', component: { template: '<div />' } },
    ],
  })
}

function mountTitle(props = {}, router = routerWith()) {
  return mount(CampaignTitle, {
    props: { campaign, ...props },
    // The directive is registered in main.js, which tests do not run.
    global: { plugins: [PrimeVue, router], directives: { tooltip: Tooltip } },
  })
}

/*
 * Hovers the name and reads the popup out of the document — the tooltip is
 * appended to the body, so it is nowhere inside the wrapper, and it is shown a
 * tick after the event rather than during it.
 */
async function hover(wrapper) {
  // The measurement is taken on mount, so the first render is always the one
  // made before it — settle that before hovering, as a hand would.
  await flushPromises()

  await wrapper.get('.campaign-title').trigger('mouseenter')
  await flushPromises()
  await new Promise((resolve) => setTimeout(resolve, 0))

  return document.querySelector('.p-tooltip-text')
}

describe('CampaignTitle', () => {
  /* The tooltip is appended to the body and outlives its component, so without
   * this a later test reads the previous one's popup. */
  afterEach(() => {
    document.querySelectorAll('.p-tooltip').forEach((el) => el.remove())
    delete HTMLAnchorElement.prototype.scrollWidth
    delete HTMLAnchorElement.prototype.clientWidth
  })

  it('names the campaign you are in', () => {
    expect(mountTitle().text()).toBe('The Hollow Crown')
  })

  it('goes to the campaign structure, which is what earns it a click', async () => {
    /*
     * The rewrite of "is not a control". #79 refused an affordance because there
     * was nothing behind it; this asserts there is, so the two cannot both be
     * true and a future reader is not left choosing between them.
     */
    const wrapper = mountTitle()

    expect(wrapper.get('a').attributes('href')).toBe('/campaigns/c-1/structure')
  })

  it('still promises no menu', () => {
    // It navigates. It does not open anything — what you can *do* to a campaign
    // is still the account menu's, which #79 settled and #88 does not touch.
    expect(mountTitle().get('.campaign-title').attributes('aria-haspopup')).toBeUndefined()
  })

  it('says so when you are already looking at the structure', async () => {
    const router = routerWith()
    await router.push({ name: 'campaign-structure', params: { campaignId: 'c-1' } })
    await router.isReady()

    const wrapper = mountTitle({}, router)

    expect(wrapper.get('a').attributes('aria-current')).toBe('page')
  })

  it('does not claim to be the page you are on when you are elsewhere', () => {
    expect(mountTitle().get('a').attributes('aria-current')).toBeUndefined()
  })

  it('does not truncate the accessible name, only the visible one', () => {
    // CSS ellipsis is what shortens this in a 15rem column; the text itself
    // stays whole, so a screen reader reads the campaign's real name.
    expect(
      mountTitle({ campaign: { ...campaign, name: 'A Name Far Too Long For A Sidebar' } }).text(),
    ).toBe('A Name Far Too Long For A Sidebar')
  })

  describe('the popup, when the name does not fit the column', () => {
    beforeEach(() => measuring({ name: 400, column: 240 }))

    it('carries the whole name, which is all it carries', async () => {
      const text = await hover(mountTitle())

      /*
       * The rest of the name is the one thing the column is not showing, and so
       * the only thing a popup can add. The description is not in here and is
       * not in the chrome at all — it is held for #31, where it introduces a
       * table to someone who has not sat at it.
       */
      expect(text.textContent).toBe('The Hollow Crown')
    })
  })

  describe('the popup, when the name fits', () => {
    beforeEach(() => measuring({ name: 240, column: 240 }))

    it('does not appear at all', async () => {
      /*
       * Nothing is ellipsised, so a popup would repeat a line you are already
       * reading — which teaches you it is not worth waiting for, and then the
       * time it does carry the rest of a long name is the time you have stopped
       * hovering. An empty value is how PrimeVue is told to unbind it.
       */
      expect(await hover(mountTitle())).toBeNull()
    })
  })

  it('answers again when the campaign is renamed', async () => {
    // A rename does not resize the element — it is a block in a fixed column —
    // so the observer never fires and the measurement has to be retaken.
    measuring({ name: 240, column: 240 })
    const wrapper = mountTitle()

    measuring({ name: 400, column: 240 })
    await wrapper.setProps({ campaign: { ...campaign, name: 'A Name Far Too Long' } })

    expect((await hover(wrapper)).textContent).toBe('A Name Far Too Long')
  })
})
