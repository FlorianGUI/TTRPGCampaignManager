import { describe, it, expect, afterEach } from 'vitest'
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

  describe('the popup', () => {
    it('carries the name and the description, one per line', async () => {
      // The description is the line the game master wrote to recognise the
      // table by, and the sidebar has nowhere to show it.
      const text = await hover(mountTitle())

      expect(text.textContent).toBe('The Hollow Crown\nA kingdom with no heir.')
      // Without pre-line the two would run together into a sentence that says
      // neither.
      expect(text.getAttribute('style')).toContain('pre-line')
    })

    it('is just the name when there is no description', async () => {
      const text = await hover(mountTitle({ campaign: { ...campaign, description: null } }))

      // Rather than a stray blank line under it.
      expect(text.textContent).toBe('The Hollow Crown')
    })
  })
})
