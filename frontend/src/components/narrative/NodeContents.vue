<script setup>
/*
 * What a grouping holds, as a list you can click straight through.
 *
 * A node page carries no tree beside it, so this is how an act reaches its own
 * scenes — the outline is one navigation away and going back to it to descend
 * one level is the journey this removes.
 *
 * Ordered by `position`, mixing sequences and scenes, because that is the order
 * the story goes in and separating them would put every scene written straight
 * onto an act after all its sequences regardless of where it belongs.
 */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import MoveControl from './MoveControl.vue'
import SceneStatus from './SceneStatus.vue'
import { useStructureStore } from '../../stores/structure.js'
import { vDragToPlace } from '../../directives/dragToPlace.js'
import { useWriteFailure } from '../../composables/useWriteFailure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  // Whose children these are: `{ id, kind }`, the act or sequence whose page
  // this is. The list cannot work it out from the rows — a scene knows its
  // parent, but an empty list would know nothing, and a drop has to name one.
  parent: { type: Object, required: true },
  children: { type: Array, required: true },
})

const to = (campaignId, { kind, node }) =>
  kind === 'sequence'
    ? { name: 'campaign-sequence', params: { campaignId, sequenceId: node.id } }
    : { name: 'campaign-scene', params: { campaignId, sceneId: node.id } }
import { titleOf } from '../../stores/structure.js'

const structure = useStructureStore()
const { failed } = useWriteFailure()

async function cycle(campaignId, node, status) {
  try {
    const scene =
      (await structure.ensureNode(campaignId, 'scene', node.id)) ??
      structure.nodeFor('scene', node.id)

    await structure.saveNode(campaignId, 'scene', node.id, {
      title: node.title,
      body: scene?.body ?? '',
      status,
    })
  } catch {
    // The same silence #111 closed in the outline, in the copy of this control
    // that lives on a node page. The dot is drawn from the tree and holds no
    // state, so a refused cycle simply does not move.
    failed()
  }
}

/*
 * Dragging here, the same as on the outline (#109) — the same directive, the
 * same `place` call, the same refusal.
 *
 * It can only ever *reorder*, and that is the page rather than a decision: this
 * is one list with no tree around it, so there is nowhere to drag *to*. Nothing
 * is collapsed here either, so nothing springs open. Reparenting stays where it
 * already was, in the ⋮ menu's "Move into…".
 */
const list = computed(() => ({
  parent: props.parent,
  accepts: props.parent.kind === 'act' ? ['sequence', 'scene'] : ['scene'],
  onDrop: dropped,
}))

async function dropped({ item, parent, after }) {
  try {
    await structure.place(props.campaignId, item.kind, item.id, { parent, after })
  } catch {
    failed()
  }
}
</script>

<template>
  <ul v-drag-to-place="list" class="contents">
    <li
      v-for="child in children"
      :key="child.node.id"
      class="contents__row"
      :data-id="child.node.id"
      :data-kind="child.kind"
    >
      <RouterLink class="contents__item" :to="to(campaignId, child)">
        <span
          class="contents__title"
          :class="{ 'contents__title--sequence': child.kind === 'sequence' }"
        >
          {{ titleOf(child.node, child.kind) }}
        </span>

        <span v-if="child.kind === 'sequence'" class="contents__kind">sequence</span>
      </RouterLink>

      <SceneStatus
        v-if="child.kind === 'scene'"
        :status="child.node.status"
        @cycle="cycle(campaignId, child.node, $event)"
      />

      <!--
        The same menu the outline carries, so a list of children behaves the same
        wherever it is read. Outside the link, not inside it: a control nested in
        an anchor is a control that navigates when it misses.
      -->
      <MoveControl
        :campaign-id="campaignId"
        :kind="child.kind"
        :node="child.node"
        :siblings="children"
      />
    </li>
  </ul>
</template>

<style scoped>
.contents {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
}

/*
 * Centred, not baseline-aligned. The status mark is an empty box, and an empty
 * box's baseline is its bottom edge — so once it grew to a 24px hit area it
 * carried the controls beside it several pixels above the title they belong to.
 * A row here is one line, so centring is the whole answer.
 */
.contents__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
}

.contents__row:last-child {
  border-bottom: 0;
}

/* The same three states the outline paints while a row is dragged — see the
   note there for why the shadow is the one place elevation is allowed. */
.contents .sortable-ghost > * {
  opacity: 0.25;
}

.contents .sortable-ghost {
  background: var(--p-content-hover-background);
  border-radius: var(--p-border-radius-sm);
}

.contents .sortable-drag {
  background: var(--p-content-background);
  border-radius: var(--p-border-radius-sm);
  box-shadow: var(--p-overlay-popover-shadow);
  cursor: grabbing;
}

.contents__row {
  cursor: grab;
}

.contents__row :is(button, input, a) {
  cursor: revert;
}

.contents__item {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  color: var(--p-text-color);
  text-decoration: none;
}

.contents__item:hover .contents__title {
  color: var(--p-primary-color);
}

.contents__item:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.contents__title {
  flex: 1;
  min-width: 0;
}

.contents__title--sequence {
  font-style: italic;
}

.contents__kind {
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}

@media (pointer: coarse) {
  .contents__item {
    min-height: 44px;
    align-items: center;
  }
}
</style>
