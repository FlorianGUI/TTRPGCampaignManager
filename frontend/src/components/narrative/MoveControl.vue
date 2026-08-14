<script setup>
/*
 * Stepping a record one place up or down among its siblings.
 *
 * **Reordering only.** Changing which act or sequence something sits in used to
 * live here too, and moved to the edit form on its own page: a game master looks
 * for "which act is this in" where they look for everything else about it, and
 * two ways to do one thing is one too many. What is left is the move whose
 * neighbours are on screen — which is exactly the move that belongs in a list.
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
import { anchorForStep, titleOf, useStructureStore } from '../../stores/structure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  kind: { type: String, required: true },
  node: { type: Object, required: true },
  // The records this one sits among, in order. Computed by whoever renders the
  // row, because only they know which list this is — a scene's siblings are the
  // scenes of its own parent, not of the campaign.
  siblings: { type: Array, required: true },
})

const structure = useStructureStore()

const menu = ref(null)
const moving = ref(false)
const confirming = ref(false)
const removing = ref(false)

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
  } finally {
    removing.value = false
  }
}

const up = computed(() => anchorForStep(props.siblings, props.node.id, 'up'))
const down = computed(() => anchorForStep(props.siblings, props.node.id, 'down'))

/*
 * A step keeps the parent it already has. Only the anchor changes, so the body
 * carries the current parentage rather than omitting it — omitting a parent is
 * how a record is moved to the campaign, which is not what a step means.
 */
async function stepTo(after) {
  moving.value = true

  try {
    await structure.place(props.campaignId, props.kind, props.node.id, {
      ...(props.kind !== 'act' && { act_id: props.node.act_id ?? null }),
      ...(props.kind === 'scene' && { sequence_id: props.node.sequence_id ?? null }),
      after,
    })
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
    <Button
      text
      rounded
      size="small"
      icon="pi pi-ellipsis-v"
      :loading="moving"
      :aria-label="`Move ${titleOf(node, kind)}`"
      aria-haspopup="true"
      @click="menu.toggle($event)"
    />
    <Menu ref="menu" :model="items" popup />

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

.move__consequence {
  margin: 0;
  color: var(--p-text-muted-color);
}
</style>
