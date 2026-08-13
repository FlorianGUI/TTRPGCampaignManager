import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import MoveControl from './MoveControl.vue'
import { anchorForStep, parentsFor, useStructureStore } from '../../stores/structure.js'

const request = vi.hoisted(() => vi.fn())

vi.mock('../../api/client.js', () => ({ request }))

/* PrimeVue's Select and Menu read matchMedia on mount; jsdom has none. */
window.matchMedia ??= () => ({ matches: false, addEventListener() {}, removeEventListener() {} })

const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

const ACT = { id: 'a-1', title: 'Act I', description: '', position: 1024 }
const CAUSEWAY = {
  id: 'q-1',
  title: 'The Causeway',
  description: '',
  act_id: 'a-1',
  position: 1024,
}

const TREE = {
  acts: [ACT],
  sequences: [CAUSEWAY],
  scenes: [
    scene('s-1', 'One', 1024, { sequence_id: 'q-1' }),
    scene('s-2', 'Two', 2048, { sequence_id: 'q-1' }),
    scene('s-3', 'Three', 3072, { sequence_id: 'q-1' }),
  ],
}

const SIBLINGS = TREE.scenes

async function render({ node = SIBLINGS[2], kind = 'scene', siblings = SIBLINGS } = {}) {
  request.mockResolvedValue(TREE)

  // One pinia, shared: the component reads the tree this loads, and mounting
  // with a fresh one would leave it looking at an empty store.
  const pinia = createPinia()
  setActivePinia(pinia)
  await useStructureStore().ensureLoaded('c-1')

  const wrapper = mount(MoveControl, {
    props: { campaignId: 'c-1', kind, node, siblings },
    global: { plugins: [PrimeVue, pinia] },
  })
  await flushPromises()
  return wrapper
}

/* The menu is a popup, so its items are read off the model rather than the DOM. */
const items = (wrapper) => wrapper.findComponent({ name: 'Menu' }).props('model')
const item = (wrapper, label) => items(wrapper).find((entry) => entry.label === label)

describe('stepping one place', () => {
  /*
   * The arithmetic is not symmetrical, which is why it is a function with a test
   * rather than an expression in a template.
   */
  const siblings = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]

  it('moving down lands after the neighbour it passed', () => {
    expect(anchorForStep(siblings, 'a', 'down')).toBe('b')
  })

  it('moving up lands after the record two above, not the one above', () => {
    // The one directly above is the neighbour being passed; anchoring to it
    // would put the record straight back where it started.
    expect(anchorForStep(siblings, 'c', 'up')).toBe('a')
  })

  it('moving up from second means the top of the list', () => {
    // `null` is a destination — the head — and distinct from "cannot move".
    expect(anchorForStep(siblings, 'b', 'up')).toBeNull()
  })

  it('says nothing at the ends', () => {
    expect(anchorForStep(siblings, 'a', 'up')).toBeUndefined()
    expect(anchorForStep(siblings, 'c', 'down')).toBeUndefined()
  })

  it('says nothing for a record that is not in the list', () => {
    expect(anchorForStep(siblings, 'z', 'up')).toBeUndefined()
  })
})

describe('the parents a record may take', () => {
  it('offers the campaign first, because it is a place and not a fallback', () => {
    // #80's skippable levels: a scene on the campaign is as legitimate as one
    // three levels down.
    expect(parentsFor(TREE, 'scene', 's-1')[0]).toEqual({
      label: 'The campaign',
      act_id: null,
      sequence_id: null,
    })
  })

  it('offers a scene both acts and sequences', () => {
    expect(parentsFor(TREE, 'scene', 's-1').map((o) => o.label)).toEqual([
      'The campaign',
      'Act I',
      'The Causeway',
    ])
  })

  it('never offers a sequence another sequence, because there is no column for it', () => {
    expect(parentsFor(TREE, 'sequence', 'q-1').map((o) => o.label)).toEqual([
      'The campaign',
      'Act I',
    ])
  })

  it('offers an act nothing, since the campaign is its only possible parent', () => {
    expect(parentsFor(TREE, 'act', 'a-1')).toEqual([])
  })

  it('never offers a record itself', () => {
    expect(parentsFor(TREE, 'scene', 's-1').some((o) => o.sequence_id === 'q-1')).toBe(true)
    expect(parentsFor(TREE, 'sequence', 'q-1').some((o) => o.sequence_id === 'q-1')).toBe(false)
  })
})

describe('the move control', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('greys out the ends rather than hiding them', async () => {
    /*
     * A control that appears and disappears as a row moves is harder to aim at
     * than one that greys out, and the menu would change height under the
     * pointer mid-click.
     */
    const wrapper = await render({ node: SIBLINGS[0] })

    expect(item(wrapper, 'Move up').disabled).toBe(true)
    expect(item(wrapper, 'Move down').disabled).toBe(false)
  })

  it('sends the parent it already has, so a step is not a reparent', async () => {
    const wrapper = await render({ node: SIBLINGS[2] })

    request.mockClear()
    request.mockResolvedValue(TREE)
    await item(wrapper, 'Move up').command()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/scenes/s-3/placement', {
      method: 'PUT',
      json: { act_id: null, sequence_id: 'q-1', after: 's-1' },
    })
  })

  it('asks the tree again, because a placement can renumber siblings too', async () => {
    const wrapper = await render({ node: SIBLINGS[2] })

    request.mockClear()
    request.mockResolvedValue(TREE)
    await item(wrapper, 'Move up').command()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/')
  })

  it('offers reordering and nothing else', async () => {
    /*
     * Reparenting moved to the edit form on each record's own page — a game
     * master looks for "which act is this in" where they look for everything
     * else about it, and two ways to do one thing is one too many.
     */
    const wrapper = await render({ node: SIBLINGS[0] })

    expect(items(wrapper).map((entry) => entry.label)).toEqual(['Move up', 'Move down'])
  })

  it('names the row it moves, so the button is not one of forty called “Move”', async () => {
    const wrapper = await render({ node: SIBLINGS[0] })

    expect(wrapper.get('button').attributes('aria-label')).toBe('Move One')
  })
})
