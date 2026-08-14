import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { actProgress, scenesUnder, useStructureStore } from './structure.js'

const request = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))

const ACT_I = { id: 'a-1', title: 'Act I — Water Rising', description: '', position: 1024 }
const ACT_II = { id: 'a-2', title: 'Act II — The War', description: '', position: 2048 }
const CAUSEWAY = {
  id: 'q-1',
  title: 'The Causeway',
  act_id: 'a-1',
  description: '',
  position: 1024,
}

const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

const TREE = {
  acts: [ACT_I, ACT_II],
  sequences: [CAUSEWAY],
  scenes: [
    scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1', status: 'done' }),
    scene('s-2', 'Interlude', 2048, { act_id: 'a-1' }),
    scene('s-3', 'Session zero', 1536, { status: 'done' }),
  ],
}

describe('the structure store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('asks for the whole tree in one request', async () => {
    request.mockResolvedValue(TREE)
    const structure = useStructureStore()

    await structure.ensureLoaded('c-1')

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/')
    expect(structure.treeFor('c-1')).toEqual(TREE)
  })

  it('asks once however many callers there are', async () => {
    // The sidebar and the page both want this on a structure route, and that
    // should be one request rather than two.
    request.mockResolvedValue(TREE)
    const structure = useStructureStore()

    await Promise.all([structure.ensureLoaded('c-1'), structure.ensureLoaded('c-1')])

    expect(request).toHaveBeenCalledTimes(1)
  })

  it('keeps campaigns apart', async () => {
    /*
     * Two tabs can sit in two campaigns — #59 put the id in the path for exactly
     * that — so a single slot would have them overwriting each other's tree.
     */
    request
      .mockResolvedValueOnce(TREE)
      .mockResolvedValueOnce({ acts: [], sequences: [], scenes: [] })
    const structure = useStructureStore()

    await structure.ensureLoaded('c-1')
    await structure.ensureLoaded('c-2')

    expect(structure.treeFor('c-1').acts).toHaveLength(2)
    expect(structure.treeFor('c-2').acts).toHaveLength(0)
  })

  it('asks again when told to reload', async () => {
    request.mockResolvedValue(TREE)
    const structure = useStructureStore()
    await structure.ensureLoaded('c-1')

    await structure.reload('c-1')

    expect(request).toHaveBeenCalledTimes(2)
  })

  it('parks a failure rather than throwing it at a template', async () => {
    request.mockRejectedValue(new Error('nope'))
    const structure = useStructureStore()

    await structure.ensureLoaded('c-1')

    expect(structure.error).toBeInstanceOf(Error)
    /*
     * Not an empty tree. A campaign nobody has written in yet and one we could
     * not ask about look identical once both are `{ acts: [] }`, and they want
     * opposite screens.
     */
    expect(structure.treeFor('c-1')).toBeNull()
  })

  describe('the campaign’s own children', () => {
    beforeEach(async () => {
      request.mockResolvedValue(TREE)
      await useStructureStore().ensureLoaded('c-1')
    })

    it('lists acts and campaign-level scenes together, in position order', () => {
      const children = useStructureStore().childrenOf('c-1')

      expect(children.map((c) => [c.kind, c.node.title])).toEqual([
        ['act', 'Act I — Water Rising'],
        ['scene', 'Session zero'],
        ['act', 'Act II — The War'],
      ])
    })

    it('leaves out scenes that belong to something', () => {
      // A scene inside an act or a sequence is not the campaign's own child, and
      // showing it at depth one would say it was.
      const titles = useStructureStore()
        .childrenOf('c-1')
        .map((c) => c.node.title)

      expect(titles).not.toContain('Arrival at dusk')
      expect(titles).not.toContain('Interlude')
    })

    it('has nothing to list for a campaign it has not loaded', () => {
      expect(useStructureStore().childrenOf('c-unknown')).toEqual([])
    })
  })
})

describe('an act’s progress', () => {
  it('counts scenes inside its sequences as well as its own', () => {
    /*
     * The act is what a game master sees progress on; a sequence is a grouping
     * inside it rather than a boundary around it.
     */
    expect(scenesUnder(TREE, ACT_I).map((s) => s.id)).toEqual(['s-1', 's-2'])
  })

  it('is ongoing when some are done and some are not', () => {
    expect(actProgress(TREE, ACT_I)).toEqual({ total: 2, played: 1, label: 'ongoing', fill: 50 })
  })

  it('is not started when nothing has been played', () => {
    const tree = { ...TREE, scenes: [scene('s-9', 'Not yet', 1024, { act_id: 'a-2' })] }

    expect(actProgress(tree, ACT_II).label).toBe('not started')
  })

  it('is finished when nothing is still planned', () => {
    // Skipped counts as resolved: a scene that was cut is not still waiting.
    const tree = {
      ...TREE,
      scenes: [
        scene('s-9', 'Played', 1024, { act_id: 'a-2', status: 'done' }),
        scene('s-10', 'Cut', 2048, { act_id: 'a-2', status: 'skipped' }),
      ],
    }

    expect(actProgress(tree, ACT_II).label).toBe('finished')
  })

  it('is empty when the act has no scenes, which is not the same as not started', () => {
    /*
     * An act with nothing in it has not been *written*, which is a different
     * problem from written and unplayed — and it is the one a game master can
     * act on, so it must not be flattened into the same grey dot.
     */
    expect(actProgress(TREE, ACT_II)).toEqual({ total: 0, played: 0, label: 'empty', fill: 0 })
  })
})
