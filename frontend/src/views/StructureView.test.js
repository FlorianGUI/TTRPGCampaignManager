import { describe, it, expect, beforeEach, vi } from 'vitest'
import { h } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { PrimeVueToastSymbol } from 'primevue/usetoast'
import StructureView from './StructureView.vue'
import { COLLAPSED_STORAGE_KEY } from '../stores/collapsedNarrative.js'

const request = vi.hoisted(() => vi.fn())

/* A fake in place of the real service — see the note in `MoveControl.test.js`. */
const toast = { add: vi.fn() }

vi.mock('../api/client.js', () => ({ request }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { campaignId: 'c-1' } }),
  /*
   * Every row leads to its own page now (#88's PR 2). Stubbed as a plain anchor
   * carrying the resolved route name, so the assertions below can stay about the
   * shape of the outline while one test checks where a row actually goes.
   */
  RouterLink: {
    props: { to: { type: [String, Object], required: true } },
    setup:
      (props, { slots }) =>
      () =>
        h(
          'a',
          { 'data-to': props.to.name, 'data-id': Object.values(props.to.params ?? {})[1] },
          slots.default?.(),
        ),
  },
}))

const act = (id, title, position, description = '') => ({ id, title, description, position })
const sequence = (id, title, position, act_id = null) => ({
  id,
  title,
  description: '',
  act_id,
  position,
})
const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

const EMPTY = { acts: [], sequences: [], scenes: [] }

async function render(tree) {
  request.mockResolvedValue(tree)
  const wrapper = mount(StructureView, {
    global: { plugins: [PrimeVue, createPinia()], provide: { [PrimeVueToastSymbol]: toast } },
  })
  await flushPromises()
  return wrapper
}

/* Titles in the order they appear, whatever level they sit at. */
const outline = (wrapper) =>
  wrapper.findAllComponents({ name: 'OutlineRow' }).map((row) => row.props('node').title)

describe('the structure page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
    localStorage.clear()
  })

  it('says what an act is when the campaign is empty', async () => {
    // The first place the word appears, so the empty state teaches it rather
    // than only offering a button.
    const wrapper = await render(EMPTY)

    expect(wrapper.text()).toContain('act')
    expect(wrapper.find('.outline').exists()).toBe(false)
  })

  it('shows the tree in narrative order, whatever level things sit at', async () => {
    /*
     * Depth one interleaves acts and campaign-level scenes by position — a scene
     * written straight onto the campaign is not a leftover to be listed last.
     */
    const wrapper = await render({
      acts: [act('a-1', 'Act I', 2048)],
      sequences: [],
      scenes: [scene('s-1', 'Session zero', 1024)],
    })

    expect(outline(wrapper)).toEqual(['Session zero', 'Act I'])
  })

  it('nests a sequence inside its act, and a scene inside that', async () => {
    const wrapper = await render({
      acts: [act('a-1', 'Act I', 1024)],
      sequences: [sequence('q-1', 'The Causeway', 1024, 'a-1')],
      scenes: [scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1' })],
    })

    expect(outline(wrapper)).toEqual(['Act I', 'The Causeway', 'Arrival at dusk'])
  })

  it('keeps a scene that skips the sequence level in its place among the sequences', async () => {
    /*
     * The tree stores only the direct parent, so the page is the only thing that
     * can order a scene on the act against the sequences beside it.
     */
    const wrapper = await render({
      acts: [act('a-1', 'Act I', 1024)],
      sequences: [sequence('q-1', 'The Causeway', 2048, 'a-1')],
      scenes: [scene('s-1', 'Interlude', 1024, { act_id: 'a-1' })],
    })

    expect(outline(wrapper)).toEqual(['Act I', 'Interlude', 'The Causeway'])
  })

  it('teaches the word sequence in an empty act', async () => {
    // #88 asks for this explicitly: a game master who has not studied
    // screenwriting will not arrive already using it.
    const wrapper = await render({ acts: [act('a-1', 'Act III', 1024)], sequences: [], scenes: [] })

    expect(wrapper.get('.empty-slot').text()).toContain('sequence')
  })

  it('shows what an act says about itself', async () => {
    const wrapper = await render({
      acts: [act('a-1', 'Act I', 1024, 'The party earns the Wardens’ trust.')],
      sequences: [],
      scenes: [],
    })

    expect(wrapper.get('.row__description').text()).toBe('The party earns the Wardens’ trust.')
  })

  describe('collapsing', () => {
    const tree = {
      acts: [act('a-1', 'Act I', 1024)],
      sequences: [],
      scenes: [scene('s-1', 'Arrival at dusk', 1024, { act_id: 'a-1' })],
    }

    it('hides what is inside an act, and says so', async () => {
      const wrapper = await render(tree)

      await wrapper.get('.chevron').trigger('click')

      expect(outline(wrapper)).toEqual(['Act I'])
      expect(wrapper.get('.chevron').attributes('aria-expanded')).toBe('false')
    })

    it('remembers what was shut, per campaign, without asking the API', async () => {
      /*
       * A per-person, per-device view preference. Under #31 two game masters at
       * one table would fight over a stored one, and neither would be wrong.
       */
      const wrapper = await render(tree)

      await wrapper.get('.chevron').trigger('click')

      expect(JSON.parse(localStorage.getItem(COLLAPSED_STORAGE_KEY))).toEqual({ 'c-1': ['a-1'] })
    })

    it('opens shut on a campaign that was left that way', async () => {
      localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify({ 'c-1': ['a-1'] }))

      const wrapper = await render(tree)

      expect(outline(wrapper)).toEqual(['Act I'])
    })

    it('shuts and reopens everything at once', async () => {
      const wrapper = await render(tree)

      await wrapper.get('.structure__collapse').trigger('click')
      expect(outline(wrapper)).toEqual(['Act I'])

      await wrapper.get('.structure__collapse').trigger('click')
      expect(outline(wrapper)).toEqual(['Act I', 'Arrival at dusk'])
    })

    it('offers nothing to collapse when there is nothing that collapses', async () => {
      const wrapper = await render({ acts: [], sequences: [], scenes: [scene('s-1', 'One', 1024)] })

      expect(wrapper.find('.structure__collapse').exists()).toBe(false)
    })
  })

  describe('adding', () => {
    /* Every plus, and what it says may go inside the thing it sits beside. */
    const offers = (wrapper) =>
      wrapper.findAllComponents({ name: 'AddChild' }).map((c) => ({
        parent: c.props('parentName'),
        allowed: c.props('allowed'),
      }))

    it('offers an act and a scene on the campaign itself', async () => {
      /*
       * Both, always — a one-shot should never have to make an act it does not
       * want in order to write its first scene.
       */
      const wrapper = await render(EMPTY)

      expect(offers(wrapper)).toEqual([{ parent: 'the campaign', allowed: ['act', 'scene'] }])
    })

    it('offers a sequence and a scene inside an act', async () => {
      const wrapper = await render({ acts: [act('a-1', 'Act I', 1024)], sequences: [], scenes: [] })

      expect(offers(wrapper)).toContainEqual({ parent: 'Act I', allowed: ['sequence', 'scene'] })
    })

    it('offers a scene inside a sequence, and nothing at all inside a scene', async () => {
      // There is no level below a scene, so a scene's row carries no plus.
      const wrapper = await render({
        acts: [act('a-1', 'Act I', 1024)],
        sequences: [sequence('q-1', 'The Causeway', 1024, 'a-1')],
        scenes: [scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1' })],
      })

      expect(offers(wrapper)).toContainEqual({ parent: 'The Causeway', allowed: ['scene'] })
      expect(offers(wrapper).some((o) => o.parent === 'Arrival at dusk')).toBe(false)
    })

    it('says so when the plus is refused, rather than spinning and stopping', async () => {
      /*
       * A sequence's plus writes a scene with no dialog in the way, so a refused
       * add used to be a button that visibly did nothing at all (#111).
       */
      const wrapper = await render({
        acts: [act('a-1', 'Act I', 1024)],
        sequences: [sequence('q-1', 'The Causeway', 1024, 'a-1')],
        scenes: [],
      })

      toast.add.mockClear()
      request.mockRejectedValue(new Error('nope'))
      await wrapper.findAllComponents({ name: 'AddChild' }).at(-1).find('button').trigger('click')
      await flushPromises()

      expect(toast.add).toHaveBeenCalledTimes(1)
    })

    it('names an unnamed record rather than showing a blank row', async () => {
      /*
       * Adding is one click, so a record can exist before it has a title — and a
       * game master who presses Escape keeps it that way. A blank line would read
       * as a rendering fault.
       */
      const wrapper = await render({
        acts: [],
        sequences: [],
        scenes: [scene('s-1', '', 1024)],
      })

      expect(wrapper.text()).toContain('Untitled scene')
    })
  })

  /*
   * The move #110 was opened for, driven through the page rather than through
   * `anchorForStep`: an act holding one scene and one sequence, stepping the
   * scene past the sequence. It is the case the per-kind number lines could not
   * express — the anchor is a *sequence*, which used to answer 404 with "Scene
   * not found" and leave the row where it was, in silence.
   */
  it('steps a scene past the sequence beside it, and redraws in the new order', async () => {
    const INTERLUDE = scene('s-1', 'Interlude', 1024, { act_id: 'a-1' })
    const CAUSEWAY = sequence('q-1', 'The Causeway', 2048, 'a-1')
    const before = { acts: [act('a-1', 'Act I', 1024)], sequences: [CAUSEWAY], scenes: [INTERLUDE] }

    const wrapper = await render(before)
    expect(outline(wrapper)).toEqual(['Act I', 'Interlude', 'The Causeway'])

    const moves = wrapper.findAllComponents({ name: 'MoveControl' })
    const scenesMenu = moves
      .find((move) => move.props('node').id === 's-1')
      .findComponent({ name: 'Menu' })
    const down = scenesMenu.props('model').find((entry) => entry.label === 'Move down')

    // Offered rather than greyed out: the row below is of another kind, and the
    // arrow means "the next thing here", which is what the outline draws.
    expect(down.disabled).toBe(false)

    request.mockClear()
    request.mockResolvedValue({ ...before, scenes: [{ ...INTERLUDE, position: 3072 }] })
    await down.command()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/placement', {
      method: 'PUT',
      json: {
        item: { id: 's-1', kind: 'scene' },
        parent: { id: 'a-1', kind: 'act' },
        // The whole of it: an anchor of a different kind than the row moving.
        after: { id: 'q-1', kind: 'sequence' },
      },
    })
    expect(outline(wrapper)).toEqual(['Act I', 'The Causeway', 'Interlude'])
  })

  it('says so when marking a scene off is refused', async () => {
    /*
     * The status dot is drawn from the tree and holds no state of its own, so a
     * refused cycle leaves it exactly where it was — which is indistinguishable
     * from a click that missed until something says otherwise (#111).
     */
    const wrapper = await render({
      acts: [],
      sequences: [],
      scenes: [scene('s-1', 'Session zero', 1024)],
    })

    toast.add.mockClear()
    request.mockRejectedValue(new Error('nope'))
    await wrapper.get('.status__dot').trigger('click')
    await flushPromises()

    expect(toast.add).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Session zero')
  })

  it('still shows the load failure as a page message, not as a toast', async () => {
    /*
     * The two are different situations and keep different answers: a first load
     * that failed leaves nothing to look at and offers a retry in place of the
     * outline, while a refused write happens over a tree that is still true
     * (#111). This is the half that must not have been swept up in the change.
     */
    request.mockRejectedValue(new Error('nope'))
    const wrapper = mount(StructureView, {
      global: { plugins: [PrimeVue, createPinia()], provide: { [PrimeVueToastSymbol]: toast } },
    })
    toast.add.mockClear()
    await flushPromises()

    expect(wrapper.text()).toContain('could not be loaded')
    expect(toast.add).not.toHaveBeenCalled()
  })

  it('offers a retry rather than an empty campaign when the request fails', async () => {
    /*
     * A campaign nobody has written in and one that could not be asked about
     * look identical as empty trees, and they want opposite screens.
     */
    request.mockRejectedValue(new Error('nope'))
    const wrapper = mount(StructureView, {
      global: { plugins: [PrimeVue, createPinia()], provide: { [PrimeVueToastSymbol]: toast } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('could not be loaded')
    expect(wrapper.find('.structure__empty').exists()).toBe(false)
  })
})
