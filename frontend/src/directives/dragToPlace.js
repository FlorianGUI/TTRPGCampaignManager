import Sortable from 'sortablejs'

/*
 * Dragging a row of the outline to where it belongs.
 *
 * **An accelerator over the ⋮ menu, never a replacement for it** (#109). Drag is
 * the obvious gesture for an outline and the one thing a keyboard and a screen
 * reader cannot do, so the menu stays — WCAG 2.2 **2.5.7 Dragging Movements**
 * asks that anything achievable by dragging also be achievable with a single
 * pointer and no drag, and the menu is what makes that true. A change here that
 * breaks the menu is a regression however good the drag feels.
 *
 * SortableJS directly rather than through `vuedraggable`, because that wrapper's
 * whole model is two-way binding a list — and this list is not ours. The tree
 * comes from the server and `place` answers with the new one, so a drop *reports*
 * and the response redraws. Nothing here mutates the outline.
 *
 * ## The DOM is handed back before anything is asked of the API
 *
 * SortableJS moves real nodes; Vue believes its own vnode tree. Left alone, the
 * next render patches against a DOM that has silently changed shape, which is how
 * a reorder turns into `insertBefore` failing on a node that is no longer where
 * Vue left it. So `onEnd` puts the element back exactly where it started before
 * calling anything — the same thing `vuedraggable` does, and the reason a drop
 * looks like it "snaps back" for the instant before the new tree arrives.
 *
 * ## Everything it needs is on the elements
 *
 * The list carries what it is (`data-parent-id`, `data-parent-kind`) and what it
 * may hold (`data-accepts`); each row carries `data-id` and `data-kind`. A drop
 * can land in a *different* list than it started in, so reading the answer off
 * the DOM is what lets one function work it out without two directive instances
 * having to talk to each other. It also makes the arithmetic a pure function over
 * a document, which is the one part of a drag that can honestly be tested (#109).
 */

const GROUP = 'outline'

/* Long enough that a press is a press. Rows are links: without a delay every
 * click on the way to a scene is a one-pixel drag, and every drag starts by
 * following the link it grabbed. `touchStartThreshold` gives the other half —
 * a finger that moves first is scrolling, and the drag never begins. */
const HOLD_MS = 200
const MOVE_TOLERANCE = 6

/* Spring-loaded, like every file manager: hold over a shut act and it opens, so
 * the drop lands in a list you can see rather than in one you are told about
 * afterwards. Its children appear *below* the row under the pointer, so nothing
 * moves out from under you. */
const SPRING_MS = 600

/*
 * What the animation is worth to someone who has asked for less of it: nothing.
 * Read per drag rather than once, so a preference changed mid-session is honoured
 * without a reload, and guarded because jsdom has no `matchMedia`.
 */
function animationMs() {
  return globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ? 0 : 150
}

const kindsOf = (element) => (element?.dataset?.accepts ?? '').split(' ').filter(Boolean)

const refers = (element) =>
  element?.dataset?.id ? { id: element.dataset.id, kind: element.dataset.kind } : null

/**
 * The `place` body a dropped row describes, read from where it now sits.
 *
 * `after` is the row immediately above it in its new list, and `null` at the top
 * — which is a destination rather than a missing argument. The parent comes from
 * the list rather than from the row, because a drop into another list is a
 * reparent and the row's own data is still the old truth.
 */
export function placementFor(item) {
  const list = item.parentElement

  return {
    item: refers(item),
    parent: list.dataset.parentId
      ? { id: list.dataset.parentId, kind: list.dataset.parentKind }
      : null,
    after: refers(item.previousElementSibling),
  }
}

/**
 * Put the element back where Vue still believes it is.
 *
 * Removed first, so the index counts the same slots it did before the drag: with
 * the row taken out, `children[oldIndex]` is whatever it was originally in front
 * of, and `null` at the end of the list.
 */
export function revert(item, from, oldIndex) {
  item.remove()
  from.insertBefore(item, from.children[oldIndex] ?? null)
}

/*
 * The list describes itself on itself.
 *
 * Written here rather than spelled out in the template beside the directive,
 * because they would be the same two facts twice and the pair that drifted would
 * be found by a row landing under the wrong parent.
 */
function describe(el, { parent, accepts }) {
  el.dataset.accepts = accepts.join(' ')

  if (parent) {
    el.dataset.parentId = parent.id
    el.dataset.parentKind = parent.kind
  } else {
    delete el.dataset.parentId
    delete el.dataset.parentKind
  }
}

export const vDragToPlace = {
  mounted(el, binding) {
    const state = { options: binding.value, spring: null, over: null }
    el.__dragToPlace = state
    describe(el, binding.value)

    function cancelSpring() {
      clearTimeout(state.spring)
      state.spring = null
      state.over = null
    }

    /*
     * A shut row the pointer is resting on, and only if it could hold what is
     * being dragged — springing open an act to reveal a list that would refuse
     * the drop is an animation that helps nobody.
     */
    function considerSpringing(related, dragged) {
      const shut = related?.dataset?.shut === 'true'
      const holds = shut && kindsOf(related).includes(dragged?.dataset?.kind)
      const id = holds ? related.dataset.id : null

      if (id === state.over) return
      cancelSpring()
      if (!id) return

      state.over = id
      state.spring = setTimeout(() => state.options.onSpringOpen?.(id), SPRING_MS)
    }

    state.sortable = Sortable.create(el, {
      group: {
        name: GROUP,
        pull: true,
        /*
         * The tree's shape, asked of the list being dropped into: the campaign
         * takes acts, sequences and scenes; an act takes sequences and scenes; a
         * sequence takes scenes. Refusing here is what makes an illegal drop
         * *visible* — the placeholder never appears in a list that will not have
         * it, rather than the drop being accepted and then undone (#109).
         *
         * A cycle is impossible as a consequence rather than as a rule: no list
         * inside an act accepts an act, and none inside a sequence accepts a
         * sequence, so nothing can be dropped into its own descendants.
         */
        put: (to, _from, dragged) => kindsOf(to.el).includes(dragged.dataset.kind),
      },
      delay: HOLD_MS,
      delayOnTouchOnly: false,
      touchStartThreshold: MOVE_TOLERANCE,
      animation: animationMs(),
      /*
       * SortableJS's own drag rather than the browser's.
       *
       * Native HTML5 dragging is desktop-only — on touch the library falls back
       * to this anyway — so leaving it on means two gestures to reason about and
       * only one of them ever seen on a phone. It also stops the native drag of
       * the row's link competing for the same press, which is a fight the link
       * wins by handing the browser a URL to drag instead of a row.
       *
       * The ghost is ours to style, which is what `.sortable-drag` and
       * `.sortable-ghost` are for below.
       */
      forceFallback: true,
      fallbackTolerance: MOVE_TOLERANCE,
      /*
       * The controls in the row are pressed, not dragged. `preventOnFilter` off,
       * or filtering swallows the very click it was protecting.
       */
      filter: 'button, input',
      preventOnFilter: false,
      onMove: (evt) => {
        considerSpringing(evt.related, evt.dragged)
        return true
      },
      onEnd: (evt) => {
        cancelSpring()

        const { item, from, to, oldIndex, newIndex } = evt
        // Where it landed, read while it is still there.
        const placement = placementFor(item)

        revert(item, from, oldIndex)

        if (from === to && oldIndex === newIndex) return

        state.options.onDrop?.(placement)
      },
    })
  },

  /*
   * The binding is a fresh object every render, so the handlers have to be read
   * at event time rather than captured at mount. Keeping the latest here is what
   * stops a drop calling into a closure over a campaign the page has left.
   */
  updated(el, binding) {
    if (!el.__dragToPlace) return

    el.__dragToPlace.options = binding.value
    describe(el, binding.value)
  },

  unmounted(el) {
    clearTimeout(el.__dragToPlace?.spring)
    el.__dragToPlace?.sortable?.destroy()
    delete el.__dragToPlace
  },
}
