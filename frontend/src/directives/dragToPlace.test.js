import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent, h, withDirectives } from 'vue'
import { mount } from '@vue/test-utils'
import { placementFor, revert, vDragToPlace } from './dragToPlace.js'

/*
 * What can honestly be tested, and what cannot.
 *
 * jsdom lays nothing out, so there is no pointer, no hit-testing and no drag to
 * simulate — a test that drove SortableJS end to end here would be asserting
 * that a mock moved a node (#109 says as much). So this covers the two halves
 * that are ours:
 *
 * - the arithmetic: given a row sitting between these two, what `place` body
 *   does that describe? Pure, over a document jsdom builds perfectly well.
 * - the wiring: given SortableJS reports a drop, do we compute that body, hand
 *   the DOM back to Vue, and call out exactly once?
 *
 * The gesture itself — that a drag feels right, that the placeholder lands where
 * the eye expects, that a long outline scrolls — is checked by hand and written
 * up in the PR. Nothing below should be read as covering it.
 */

const rows = (...ids) => {
  const list = document.createElement('ol')

  for (const id of ids) {
    const item = document.createElement('li')
    item.dataset.id = id
    item.dataset.kind = id.startsWith('a') ? 'act' : id.startsWith('q') ? 'sequence' : 'scene'
    list.append(item)
  }

  return list
}

const at = (list, index) => list.children[index]

describe('the placement a drop describes', () => {
  it('anchors to the row it now sits below', () => {
    const list = rows('s-1', 's-2', 's-3')

    expect(placementFor(at(list, 2))).toEqual({
      item: { id: 's-3', kind: 'scene' },
      parent: null,
      after: { id: 's-2', kind: 'scene' },
    })
  })

  it('reads the top of a list as a destination, not as a missing anchor', () => {
    // `null` is "put it first", and the API takes it as such. Distinct from
    // "cannot be placed", which is not a thing a drop can express.
    const list = rows('s-1', 's-2')

    expect(placementFor(at(list, 0)).after).toBeNull()
  })

  it('anchors to a row of another kind, which is the whole of #101', () => {
    /* A sibling group is everything under one parent. A scene dropped below the
     * sequence above it is an ordinary move, and the anchor names its kind. */
    const list = rows('q-1', 's-1')

    expect(placementFor(at(list, 1)).after).toEqual({ id: 'q-1', kind: 'sequence' })
  })

  it('takes the parent from the list it landed in, not from the row', () => {
    /*
     * The difference between a reorder and a reparent, and the reason the parent
     * is not read off the record: mid-drop the row still carries the parentage it
     * had before it was picked up.
     */
    const list = rows('s-1')
    list.dataset.parentId = 'a-1'
    list.dataset.parentKind = 'act'

    expect(placementFor(at(list, 0)).parent).toEqual({ id: 'a-1', kind: 'act' })
  })

  it('calls a list with no parent the campaign', () => {
    // A real place rather than a fallback: a scene needs no act to belong to.
    expect(placementFor(at(rows('s-1'), 0)).parent).toBeNull()
  })
})

describe('handing the DOM back', () => {
  /*
   * SortableJS moves real nodes; Vue believes its own vnode tree. Restoring the
   * element before anything else is what stops the next render patching against
   * a shape it never made — the bug being avoided is `insertBefore` throwing on
   * a node that has quietly moved.
   */
  it('puts a row dragged downwards back where it started', () => {
    const list = rows('s-1', 's-2', 's-3')
    const moved = at(list, 0)
    list.append(moved) // as if dropped at the end

    revert(moved, list, 0)

    expect([...list.children].map((row) => row.dataset.id)).toEqual(['s-1', 's-2', 's-3'])
  })

  it('puts a row dragged upwards back where it started', () => {
    const list = rows('s-1', 's-2', 's-3')
    const moved = at(list, 2)
    list.prepend(moved)

    revert(moved, list, 2)

    expect([...list.children].map((row) => row.dataset.id)).toEqual(['s-1', 's-2', 's-3'])
  })

  it('brings a row back out of the list it was dropped into', () => {
    const from = rows('s-1', 's-2')
    const to = rows('s-9')
    const moved = at(from, 1)
    to.append(moved)

    revert(moved, from, 1)

    expect([...from.children].map((row) => row.dataset.id)).toEqual(['s-1', 's-2'])
    expect([...to.children].map((row) => row.dataset.id)).toEqual(['s-9'])
  })
})

/*
 * The directive, with SortableJS stood in for. The library is not what is under
 * test — our handlers are, and this is the only way to call them without a
 * pointer.
 */
const created = vi.hoisted(() => [])

vi.mock('sortablejs', () => ({
  default: {
    create: (el, options) => {
      created.push({ el, options })
      return { destroy: vi.fn() }
    },
  },
}))

function harness(options, items) {
  const Harness = defineComponent({
    props: { options: { type: Object, required: true }, items: { type: Array, required: true } },
    render() {
      return withDirectives(
        h(
          'ol',
          this.items.map((row) =>
            h('li', {
              key: row.id,
              'data-id': row.id,
              'data-kind': row.kind,
              'data-shut': row.shut || undefined,
              'data-accepts': row.accepts,
            }),
          ),
        ),
        [[vDragToPlace, this.options]],
      )
    },
  })

  const wrapper = mount(Harness, { props: { options, items } })

  return { wrapper, sortable: created.at(-1) }
}

const ITEMS = [
  { id: 's-1', kind: 'scene' },
  { id: 's-2', kind: 'scene' },
  { id: 's-3', kind: 'scene' },
]

describe('the directive', () => {
  beforeEach(() => {
    created.length = 0
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('writes what the list is onto the list, so a drop can read it back', () => {
    /* A drop can land in a list other than the one it started in, so the answer
     * has to be legible from the target element rather than held in the closure
     * of whichever instance the drag began in. */
    const { sortable } = harness(
      { parent: { id: 'a-1', kind: 'act' }, accepts: ['sequence', 'scene'] },
      ITEMS,
    )

    expect(sortable.el.dataset.parentId).toBe('a-1')
    expect(sortable.el.dataset.parentKind).toBe('act')
    expect(sortable.el.dataset.accepts).toBe('sequence scene')
  })

  it('leaves a campaign-level list saying it has no parent', () => {
    const { sortable } = harness({ parent: null, accepts: ['act', 'scene'] }, ITEMS)

    expect(sortable.el.dataset.parentId).toBeUndefined()
  })

  it('refuses a kind the target list cannot hold', () => {
    /*
     * The tree's shape, enforced while dragging rather than after dropping: the
     * placeholder never appears in a list that will not have the row, so an
     * illegal move is refused visibly instead of being accepted and undone.
     */
    const { sortable } = harness({ parent: null, accepts: ['scene'] }, ITEMS)
    const to = { el: sortable.el }
    const anAct = Object.assign(document.createElement('li'), {})
    anAct.dataset.kind = 'act'
    const aScene = document.createElement('li')
    aScene.dataset.kind = 'scene'

    expect(sortable.options.group.put(to, null, anAct)).toBe(false)
    expect(sortable.options.group.put(to, null, aScene)).toBe(true)
  })

  it('reports the drop and hands the DOM back, in that order', () => {
    const onDrop = vi.fn()
    const { sortable } = harness({ parent: null, accepts: ['scene'], onDrop }, ITEMS)
    const list = sortable.el
    const moved = at(list, 0)

    // What SortableJS leaves behind: the row is already at the end.
    list.append(moved)
    sortable.options.onEnd({ item: moved, from: list, to: list, oldIndex: 0, newIndex: 2 })

    expect(onDrop).toHaveBeenCalledWith({
      item: { id: 's-1', kind: 'scene' },
      parent: null,
      after: { id: 's-3', kind: 'scene' },
    })
    // Back where Vue believes it is, so the tree from the response redraws
    // against the shape it rendered.
    expect([...list.children].map((row) => row.dataset.id)).toEqual(['s-1', 's-2', 's-3'])
  })

  it('says nothing when a row is dropped where it was', () => {
    // Picked up and put back is not a move, and a request for it would renumber
    // a sibling list for nothing.
    const onDrop = vi.fn()
    const { sortable } = harness({ parent: null, accepts: ['scene'], onDrop }, ITEMS)
    const list = sortable.el

    sortable.options.onEnd({
      item: at(list, 1),
      from: list,
      to: list,
      oldIndex: 1,
      newIndex: 1,
    })

    expect(onDrop).not.toHaveBeenCalled()
  })

  describe('springing a shut row open', () => {
    const shutAct = () => {
      const row = document.createElement('li')
      row.dataset.id = 'a-1'
      row.dataset.kind = 'act'
      row.dataset.shut = 'true'
      row.dataset.accepts = 'sequence scene'
      return row
    }

    const dragged = (kind) => {
      const row = document.createElement('li')
      row.dataset.kind = kind
      return row
    }

    it('opens one held under the pointer, rather than dropping in blind', () => {
      vi.useFakeTimers()
      const onSpringOpen = vi.fn()
      const { sortable } = harness({ parent: null, accepts: ['scene'], onSpringOpen }, ITEMS)

      sortable.options.onMove({ related: shutAct(), dragged: dragged('scene') })
      vi.advanceTimersByTime(600)

      expect(onSpringOpen).toHaveBeenCalledWith('a-1')
    })

    it('waits, so passing over an act on the way somewhere else does not open it', () => {
      vi.useFakeTimers()
      const onSpringOpen = vi.fn()
      const { sortable } = harness({ parent: null, accepts: ['scene'], onSpringOpen }, ITEMS)
      const scene = dragged('scene')

      sortable.options.onMove({ related: shutAct(), dragged: scene })
      vi.advanceTimersByTime(200)
      sortable.options.onMove({ related: at(sortable.el, 0), dragged: scene })
      vi.advanceTimersByTime(600)

      expect(onSpringOpen).not.toHaveBeenCalled()
    })

    it('does not open a row that would refuse the drop anyway', () => {
      // Springing an act open to reveal a list that cannot hold an act is an
      // animation that helps nobody.
      vi.useFakeTimers()
      const onSpringOpen = vi.fn()
      const { sortable } = harness({ parent: null, accepts: ['act'], onSpringOpen }, ITEMS)

      sortable.options.onMove({ related: shutAct(), dragged: dragged('act') })
      vi.advanceTimersByTime(600)

      expect(onSpringOpen).not.toHaveBeenCalled()
    })

    it('leaves an open row alone', () => {
      vi.useFakeTimers()
      const onSpringOpen = vi.fn()
      const { sortable } = harness({ parent: null, accepts: ['scene'], onSpringOpen }, ITEMS)
      const open = shutAct()
      delete open.dataset.shut

      sortable.options.onMove({ related: open, dragged: dragged('scene') })
      vi.advanceTimersByTime(600)

      expect(onSpringOpen).not.toHaveBeenCalled()
    })
  })
})
