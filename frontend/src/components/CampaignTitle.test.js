import { describe, it, expect, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import CampaignTitle from './CampaignTitle.vue'

/*
 * The campaign's name at the head of its own navigation — a label, not a
 * control. What you can do to a campaign is in the account menu; this only says
 * where you are.
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
 * Only `<p>` is affected, and the tooltip's own popup is a `<div>`.
 */
function measuring({ name, column }) {
  Object.defineProperty(HTMLParagraphElement.prototype, 'scrollWidth', {
    configurable: true,
    get: () => name,
  })
  Object.defineProperty(HTMLParagraphElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => column,
  })
}

function mountTitle(props = {}) {
  return mount(CampaignTitle, {
    props: { campaign, ...props },
    // The directive is registered in main.js, which tests do not run.
    global: { plugins: [PrimeVue], directives: { tooltip: Tooltip } },
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
    delete HTMLParagraphElement.prototype.scrollWidth
    delete HTMLParagraphElement.prototype.clientWidth
  })

  it('names the campaign you are in', () => {
    expect(mountTitle().text()).toBe('The Hollow Crown')
  })

  it('is not a control', () => {
    const wrapper = mountTitle()

    /*
     * The tag this replaced looked pressable and mostly was not, which is the
     * worst of both. Nothing here presses: no button, no link, and no
     * aria-haspopup promising a menu that lives in the top bar.
     */
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.get('.campaign-title').attributes('aria-haspopup')).toBeUndefined()
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
