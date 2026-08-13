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
  </span>
</template>

<style scoped>
.move {
  flex: none;
}
</style>
