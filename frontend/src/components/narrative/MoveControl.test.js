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

// Entries, not bare records: since #101 a sibling group spans kinds, so each
// row has to name its own.
const SIBLINGS = TREE.scenes.map((node) => ({ kind: 'scene', node }))

async function render({ node = SIBLINGS[2].node, kind = 'scene', siblings = SIBLINGS } = {}) {
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

/* The dialog is teleported to the body, so it is nowhere inside the wrapper. */
const dialogText = () => document.body.textContent

/* The menu is a popup, so its items are read off the model rather than the DOM. */
const items = (wrapper) => wrapper.findComponent({ name: 'Menu' }).props('model')
const item = (wrapper, label) => items(wrapper).find((entry) => entry.label === label)

describe('stepping one place', () => {
  /*
   * The arithmetic is not symmetrical, which is why it is a function with a test
   * rather than an expression in a template.
   */
  const siblings = ['a', 'b', 'c'].map((id) => ({ kind: 'scene', node: { id } }))

  it('moving down lands after the neighbour it passed', () => {
    expect(anchorForStep(siblings, 'a', 'down')).toEqual({ id: 'b', kind: 'scene' })
  })

  it('moving up lands after the record two above, not the one above', () => {
    // The one directly above is the neighbour being passed; anchoring to it
    // would put the record straight back where it started.
    expect(anchorForStep(siblings, 'c', 'up')).toEqual({ id: 'a', kind: 'scene' })
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
    // The dialog outlives its component in the body; without this a later test
    // reads the previous one's copy.
    document.body.innerHTML = ''
  })

  it('greys out the ends rather than hiding them', async () => {
    /*
     * A control that appears and disappears as a row moves is harder to aim at
     * than one that greys out, and the menu would change height under the
     * pointer mid-click.
     */
    const wrapper = await render({ node: SIBLINGS[0].node })

    expect(item(wrapper, 'Move up').disabled).toBe(true)
    expect(item(wrapper, 'Move down').disabled).toBe(false)
  })

  it('sends the parent it already has, so a step is not a reparent', async () => {
    const wrapper = await render({ node: SIBLINGS[2].node })

    request.mockClear()
    request.mockResolvedValue(TREE)
    await item(wrapper, 'Move up').command()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/placement', {
      method: 'PUT',
      json: {
        item: { id: 's-3', kind: 'scene' },
        parent: { id: 'q-1', kind: 'sequence' },
        after: { id: 's-1', kind: 'scene' },
      },
    })
  })

  it('takes the new tree from the answer rather than asking again', async () => {
    /*
     * A placement can renumber a whole sibling list, so the old code refetched.
     * The endpoint now answers with the tree it just wrote (#111), which closes
     * the window where the screen showed an order it had guessed at.
     */
    const wrapper = await render({ node: SIBLINGS[2].node })

    request.mockClear()
    request.mockResolvedValue({ ...TREE, acts: [] })
    await item(wrapper, 'Move up').command()
    await flushPromises()

    expect(request).toHaveBeenCalledTimes(1)
    expect(useStructureStore().treeFor('c-1').acts).toEqual([])
  })

  it('owns every kind of move, and the deleting', async () => {
    /*
     * The split that settled: this menu is where a record *moves*, the edit form
     * is where it *says* things. One Save button covering both would have put a
     * rename and a reorganisation behind the same press.
     */
    const wrapper = await render({ node: SIBLINGS[0].node })

    expect(
      items(wrapper)
        .map((entry) => entry.label)
        .filter(Boolean),
    ).toEqual(['Move up', 'Move down', 'Move into…', 'Delete'])
  })

  it('offers an act nowhere to be moved into, the campaign being its only parent', async () => {
    const wrapper = await render({ node: ACT, kind: 'act', siblings: [{ kind: 'act', node: ACT }] })

    expect(item(wrapper, 'Move into…')).toBeUndefined()
  })

  it('appends after the destination’s last child, whatever kind it is', async () => {
    /*
     * Arriving at the top of a list whose order you did not choose is more
     * surprising than arriving at the end of it.
     *
     * The act holds a sequence, and the anchor is that sequence — a sibling group
     * is everything under one parent (#101), so appending a scene lands it below
     * the sequence rather than below the last *scene*, which is what the per-kind
     * lists used to answer.
     */
    const wrapper = await render({ node: SIBLINGS[0].node })
    item(wrapper, 'Move into…').command()
    await flushPromises()

    wrapper.vm.chosen = { label: 'Act I', act_id: 'a-1', sequence_id: null }
    request.mockClear()
    request.mockResolvedValue(TREE)
    await wrapper.vm.moveInto()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/placement', {
      method: 'PUT',
      json: {
        item: { id: 's-1', kind: 'scene' },
        parent: { id: 'a-1', kind: 'act' },
        after: { id: 'q-1', kind: 'sequence' },
      },
    })
  })

  it('asks before deleting, and says what it costs rather than warning', async () => {
    /*
     * Nothing inside is lost — the API rehomes children to the nearest surviving
     * parent. A dialog that overstated the danger would be one people learn to
     * click through, and then it is there for the delete that really is.
     */
    const wrapper = await render({ node: SIBLINGS[0].node })

    item(wrapper, 'Delete').command()
    await flushPromises()

    expect(dialogText()).toContain('The scene and everything written in it goes.')
    expect(request).not.toHaveBeenCalledWith(
      expect.stringContaining('/scenes/'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('says where an act’s children go, because they are not deleted with it', async () => {
    const wrapper = await render({ node: ACT, kind: 'act', siblings: [{ kind: 'act', node: ACT }] })

    item(wrapper, 'Delete').command()
    await flushPromises()

    expect(dialogText()).toContain('move to the campaign')
  })

  it('deletes once confirmed, then asks the tree again', async () => {
    const wrapper = await render({ node: SIBLINGS[0].node })
    item(wrapper, 'Delete').command()
    await flushPromises()

    request.mockClear()
    request.mockResolvedValue(TREE)
    await wrapper.vm.remove()
    await flushPromises()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/scenes/s-1', { method: 'DELETE' })
    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/')
  })

  it('names the row it moves, so the button is not one of forty called “Move”', async () => {
    const wrapper = await render({ node: SIBLINGS[0].node })

    expect(wrapper.get('button').attributes('aria-label')).toBe('Move One')
  })
})
