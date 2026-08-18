<script setup>
/*
 * Stepping a record one place up or down among its siblings.
 *
 * **Every kind of move, and only moves.** Reparenting lived here, moved to the
 * edit form, and has come back — the split that settled is between *what a record
 * says* and *where it sits*: the form owns the first and this owns the second. An
 * edit form that could also move something meant a rename and a reorganisation
 * shared one Save button, and only one of those is undone by doing it again.
 *
 * Controls rather than drag, deliberately. Drag is the obvious gesture for an
 * outline and the one thing a keyboard and a screen reader cannot do, so a
 * drag-only reorder is a feature half the ways in cannot reach. This is buttons:
 * it works with a keyboard, works on a phone, and drag can be added over it later
 * as an enhancement rather than as the only way.
 *
 * The ends of a list are disabled rather than hidden: a control that appears and
 * disappears as a row moves is harder to aim at than one that greys out, and the
 * menu would change height under the pointer.
 */
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Menu from 'primevue/menu'
import Select from 'primevue/select'
import {
  anchorForStep,
  lastUnder,
  parentsFor,
  titleOf,
  useStructureStore,
} from '../../stores/structure.js'
import { useWriteFailure } from '../../composables/useWriteFailure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  kind: { type: String, required: true },
  node: { type: Object, required: true },
  // The rows this one sits among, in order, as `{ kind, node }` entries. Computed
  // by whoever renders the row, because only they know which list this is. Since
  // #101 a group spans kinds, so each entry has to name its own — an anchor is an
  // id *and* a kind.
  siblings: { type: Array, required: true },
})

const structure = useStructureStore()

/*
 * Every write below is a menu command with no form behind it, so a refusal has
 * nowhere of its own to appear. `finally` was tidying the spinner and letting
 * the rejection past it, which left a row that did not move and said nothing
 * (#111). The three `catch`es below are all that was missing.
 */
const { failed } = useWriteFailure()

const menu = ref(null)
const moving = ref(false)
const confirming = ref(false)
const removing = ref(false)
const picking = ref(false)
const chosen = ref(null)

const parents = computed(() =>
  parentsFor(structure.treeFor(props.campaignId), props.kind, props.node.id),
)

/*
 * Reparenting appends. Arriving at the top of a list whose order you did not
 * choose is more surprising than arriving at the end of it — and an omitted
 * anchor means the top, which is the difference `lastUnder` exists to hold.
 */
async function moveInto() {
  if (!chosen.value) return

  const { act_id, sequence_id } = chosen.value
  moving.value = true

  try {
    await structure.place(props.campaignId, props.kind, props.node.id, {
      parent: parentRef(act_id, sequence_id),
      after: lastUnder(structure.treeFor(props.campaignId), props.kind, {
        actId: act_id,
        sequenceId: sequence_id,
        excluding: props.node.id,
      }),
    })
    // Inside the `try`, so a refused move leaves the dialog open with the
    // destination still chosen — the gesture is one press from being retried
    // rather than one that has to be found and made again.
    picking.value = false
    chosen.value = null
  } catch {
    failed()
  } finally {
    moving.value = false
  }
}

/*
 * What deleting this actually costs, said plainly in the confirmation.
 *
 * Nothing inside it is lost: the API rehomes children to the nearest surviving
 * parent, because cascading is the answer #80 ruled out. So the dialog explains
 * where things go rather than asking anyone to be sure — a warning that
 * overstates the danger is one people learn to click through, and then it is
 * there for the delete that really is dangerous.
 *
 * That is also why this is an ordinary confirmation and not the typed-name gate
 * the campaign delete uses: closing a table takes every sheet and every scene at
 * it with no undo, and removing an act takes a heading.
 */
const consequence = computed(
  () =>
    ({
      act: 'Its sequences and scenes move to the campaign. Nothing in it is deleted.',
      sequence: 'Its scenes move to the act above it. Nothing in it is deleted.',
      scene: 'The scene and everything written in it goes.',
    })[props.kind],
)

async function remove() {
  removing.value = true

  try {
    await structure.deleteNode(props.campaignId, props.kind, props.node.id)
    confirming.value = false
  } catch {
    // The confirmation stays open, which is the honest thing for it to do: the
    // record is still there, so a dialog that closed would be saying otherwise.
    failed()
  } finally {
    removing.value = false
  }
}

const up = computed(() => anchorForStep(props.siblings, props.node.id, 'up'))
const down = computed(() => anchorForStep(props.siblings, props.node.id, 'down'))

/*
 * The one shape the endpoint takes: a parent, or null for the campaign. Kept in
 * one place because both gestures below build it, and a sequence naming a
 * sequence is the mistake it exists to make unwritable.
 */
function parentRef(actId, sequenceId) {
  if (sequenceId) return { id: sequenceId, kind: 'sequence' }
  if (actId) return { id: actId, kind: 'act' }
  return null
}

/*
 * A step keeps the parent it already has. Only the anchor changes, so the body
 * carries the current parentage rather than omitting it — omitting a parent is
 * how a record is moved to the campaign, which is not what a step means.
 */
async function stepTo(after) {
  moving.value = true

  try {
    await structure.place(props.campaignId, props.kind, props.node.id, {
      parent: parentRef(props.node.act_id ?? null, props.node.sequence_id ?? null),
      after,
    })
  } catch {
    // Nothing to undo: `place` writes the tree from the response, so a refused
    // step never moved the row on screen in the first place. What was missing
    // was only saying so.
    failed()
  } finally {
    moving.value = false
  }
}

const items = computed(() => [
  {
    label: 'Move up',
    icon: 'pi pi-arrow-up',
    disabled: up.value === undefined,
    command: () => stepTo(up.value),
  },
  {
    label: 'Move down',
    icon: 'pi pi-arrow-down',
    disabled: down.value === undefined,
    command: () => stepTo(down.value),
  },
  ...(parents.value.length
    ? [
        {
          label: 'Move into…',
          icon: 'pi pi-sign-in',
          command: () => {
            picking.value = true
          },
        },
      ]
    : []),
  { separator: true },
  {
    label: 'Delete',
    icon: 'pi pi-trash',
    // The one item here that cannot be undone by doing it again.
    class: 'move__delete',
    command: () => {
      confirming.value = true
    },
  },
])
</script>

<template>
  <span class="move">
    <!-- Square, like `AddChild` beside it — see the note there. -->
    <Button
      text
      size="small"
      icon="pi pi-ellipsis-v"
      :loading="moving"
      :aria-label="`Move ${titleOf(node, kind)}`"
      aria-haspopup="true"
      @click="menu.toggle($event)"
    />
    <Menu ref="menu" :model="items" popup />

    <Dialog
      v-model:visible="picking"
      modal
      :header="`Move ${titleOf(node, kind)}`"
      :style="{ width: 'min(28rem, 92vw)' }"
    >
      <p class="move__consequence">
        It goes to the end of whatever you choose. The campaign is a place in its own right — a
        scene does not need an act to belong to.
      </p>

      <Select
        v-model="chosen"
        class="move__parent"
        :options="parents"
        option-label="label"
        placeholder="Choose where it goes"
      />

      <template #footer>
        <Button label="Cancel" text severity="secondary" @click="picking = false" />
        <Button label="Move" :disabled="!chosen" :loading="moving" @click="moveInto" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="confirming"
      modal
      :header="`Delete ${titleOf(node, kind)}?`"
      :style="{ width: 'min(28rem, 92vw)' }"
    >
      <p class="move__consequence">{{ consequence }}</p>

      <template #footer>
        <Button label="Cancel" text severity="secondary" @click="confirming = false" />
        <Button label="Delete" severity="danger" :loading="removing" @click="remove" />
      </template>
    </Dialog>
  </span>
</template>

<style scoped>
.move {
  flex: none;
}

/*
 * The focus ring hugs the button rather than floating off it.
 *
 * The global ring is 2px at 2px offset — right on a text field, and heavy on a
 * 28px circle, where the halo ends up wider than the icon inside it and reads as
 * a selection rather than a cursor position. Same thickness and same colour, so
 * it is no less visible and still clears the 3:1 that WCAG 1.4.11 asks of a focus
 * indicator; only the offset goes.
 *
 * Scoped rather than changed in `semantic.js`, because the token is right for
 * everything it was written for. `AddChild` carries the same rule — the two
 * sit beside each other in every row and must not disagree about this.
 */
.move :deep(.p-button):focus-visible {
  outline-offset: 0;
}

.move__consequence {
  margin: 0 0 var(--space-4);
  color: var(--p-text-muted-color);
}

.move__parent {
  width: 100%;
}
</style>
