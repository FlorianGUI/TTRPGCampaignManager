<script setup>
/*
 * Moving a record: one step up, one step down, or somewhere else entirely.
 *
 * **Controls rather than drag, and that is the order deliberately.** Drag is the
 * obvious gesture for an outline and it is the one thing a keyboard and a screen
 * reader cannot do — so a drag-only reorder is a feature half the ways in cannot
 * reach. This works with a keyboard because it is buttons, works on a phone
 * because it is buttons, and drag can be added over it later as an enhancement
 * rather than as the only way.
 *
 * It also maps one-to-one onto the endpoint. `PUT .../placement` takes a parent
 * and an `after` anchor, which is exactly "up", "down" and "into" — where a drag
 * would first have to translate a drop position into an anchor id.
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
import { anchorForStep, parentsFor, useStructureStore } from '../../stores/structure.js'

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
const picking = ref(false)
const chosen = ref(null)
const moving = ref(false)

const up = computed(() => anchorForStep(props.siblings, props.node.id, 'up'))
const down = computed(() => anchorForStep(props.siblings, props.node.id, 'down'))

const parents = computed(() =>
  parentsFor(structure.treeFor(props.campaignId), props.kind, props.node.id),
)

/*
 * A step keeps the parent it already has. Only the anchor changes, so the body
 * has to carry the current parentage rather than omitting it — omitting a parent
 * is how a record gets moved to the campaign, which is not what a step means.
 */
function stepTo(after) {
  return move({
    ...(props.kind !== 'act' && { act_id: props.node.act_id ?? null }),
    ...(props.kind === 'scene' && { sequence_id: props.node.sequence_id ?? null }),
    after,
  })
}

async function move(placement) {
  moving.value = true
  try {
    await structure.place(props.campaignId, props.kind, props.node.id, placement)
  } finally {
    moving.value = false
  }
}

async function moveInto() {
  if (!chosen.value) return

  // Appended to the new parent — `after: null` would put it first, and arriving
  // at the top of a list you did not choose the position in is more surprising
  // than arriving at the end of it.
  const { act_id, sequence_id } = chosen.value
  const last = lastIn(act_id, sequence_id)

  await move({
    ...(props.kind !== 'act' && { act_id }),
    ...(props.kind === 'scene' && { sequence_id }),
    after: last,
  })

  picking.value = false
  chosen.value = null
}

/* The id of whatever currently sits last in the destination, or null if empty. */
function lastIn(actId, sequenceId) {
  const tree = structure.treeFor(props.campaignId)
  const family =
    props.kind === 'sequence'
      ? tree.sequences.filter((s) => s.act_id === actId)
      : tree.scenes.filter((s) => s.act_id === actId && s.sequence_id === sequenceId)

  const ordered = [...family].sort((a, b) => a.position - b.position || a.id.localeCompare(b.id))
  const last = ordered.filter((record) => record.id !== props.node.id).at(-1)

  return last?.id ?? null
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
  ...(props.kind === 'act'
    ? []
    : [
        { separator: true },
        {
          label: 'Move into…',
          icon: 'pi pi-sign-in',
          command: () => {
            picking.value = true
          },
        },
      ]),
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
      :aria-label="`Move ${node.title}`"
      aria-haspopup="true"
      @click="menu.toggle($event)"
    />
    <Menu ref="menu" :model="items" popup />

    <Dialog
      v-model:visible="picking"
      modal
      :header="`Move ${node.title}`"
      :style="{ width: 'min(28rem, 92vw)' }"
    >
      <p class="move__hint">
        It goes to the end of whatever you choose. The campaign is a place in its own right — a
        scene does not need an act to belong to.
      </p>

      <Select
        v-model="chosen"
        class="move__select"
        :options="parents"
        option-label="label"
        placeholder="Choose where it goes"
      />

      <template #footer>
        <Button label="Cancel" text severity="secondary" @click="picking = false" />
        <Button label="Move" :disabled="!chosen" :loading="moving" @click="moveInto" />
      </template>
    </Dialog>
  </span>
</template>

<style scoped>
.move {
  flex: none;
}

.move__hint {
  margin: 0 0 var(--space-4);
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
}

.move__select {
  width: 100%;
}
</style>
