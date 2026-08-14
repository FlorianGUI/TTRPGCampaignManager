<script setup>
/*
 * One line of the outline, whatever level it sits at.
 *
 * Extracted because the six places that used to draw a row had already drifted:
 * two of them had lost their links and their move control in an edit that only
 * caught the other four. A row is one thing and now looks like one.
 *
 * The trailing controls live in a fixed-width column so **every dot lands on the
 * same vertical line** down the page. Before, they followed whatever the title
 * ended at, which made a column of them read as scattered — and a dot you have
 * to hunt for is worse than a word, which was the point of using dots.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ActProgress from './ActProgress.vue'
import AddChild from './AddChild.vue'
import MoveControl from './MoveControl.vue'
import SceneStatus from './SceneStatus.vue'
import { titleOf, useStructureStore } from '../../stores/structure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  kind: { type: String, required: true },
  node: { type: Object, required: true },
  siblings: { type: Array, required: true },
  // An act's, and only an act's — a sequence is a grouping inside the scale a
  // game master judges progress at, not a scale of its own.
  progress: { type: Object, default: null },
  collapsible: { type: Boolean, default: false },
  shut: { type: Boolean, default: false },
  // A scene sitting where a sequence would, because it skips that level. Marked,
  // or at this indent it reads as a sequence with nothing in it.
  skipsLevel: { type: Boolean, default: false },
  // What may be written inside this one. Empty for a scene, which holds nothing.
  allowed: { type: Array, default: () => [] },
  // Freshly added and not yet named: the title is a focused field rather than
  // text, so adding and naming are one gesture.
  renaming: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'created', 'renamed', 'cancel-rename'])

const structure = useStructureStore()

const name = computed(() => titleOf(props.node, props.kind))

const draft = ref('')
const field = ref(null)

watch(
  () => props.renaming,
  async (on) => {
    if (!on) return

    draft.value = props.node.title
    // After the field exists, not before: the row is text until this flips.
    await nextTick()
    field.value?.focus()
  },
  { immediate: true },
)

/*
 * Saved as a full replacement, like every other write in this API. Safe to send
 * the empty fields alongside because this only ever runs on a record created
 * moments ago — an existing row is renamed on its own page, where the rest of it
 * is on screen to be replaced knowingly.
 */
async function commit() {
  if (!props.renaming) return

  const title = draft.value.trim()
  if (title && title !== props.node.title) {
    await structure.saveNode(props.campaignId, props.kind, props.node.id, {
      title,
      ...(props.kind === 'scene' ? { body: '', status: 'planned' } : { description: '' }),
    })
  }

  emit('renamed')
}

const ROUTES = { act: 'campaign-act', sequence: 'campaign-sequence', scene: 'campaign-scene' }
const PARAMS = { act: 'actId', sequence: 'sequenceId', scene: 'sceneId' }

const to = computed(() => ({
  name: ROUTES[props.kind],
  params: { campaignId: props.campaignId, [PARAMS[props.kind]]: props.node.id },
}))

/* Headings for the grouping levels, so the outline is a document outline too. */
const tag = computed(() => ({ act: 'h2', sequence: 'h3', scene: 'span' })[props.kind])
</script>

<template>
  <div class="row" :class="`row--${kind}`">
    <button
      v-if="collapsible"
      type="button"
      class="chevron"
      :aria-expanded="!shut"
      :aria-label="`${shut ? 'Expand' : 'Collapse'} ${name}`"
      @click="$emit('toggle', node.id)"
    >
      <i class="pi" :class="shut ? 'pi-chevron-right' : 'pi-chevron-down'" />
    </button>
    <span v-else class="chevron chevron--none" aria-hidden="true" />

    <span
      v-if="skipsLevel"
      class="row__skip"
      title="Attached to the act, skipping the sequence level"
      >↳</span
    >

    <div class="row__main">
      <component :is="tag" class="row__title" :class="`row__title--${kind}`">
        <input
          v-if="renaming"
          ref="field"
          v-model="draft"
          class="row__field"
          :aria-label="`Name this ${kind}`"
          :placeholder="`Name this ${kind}`"
          @keyup.enter="commit"
          @keyup.esc="$emit('cancel-rename')"
          @blur="commit"
        />
        <RouterLink v-else :to="to" :class="{ 'row__title--unnamed': !node.title?.trim() }">{{
          name
        }}</RouterLink>
      </component>
      <p v-if="node.description" class="row__description">{{ node.description }}</p>
    </div>

    <!-- Beside the name, so where a new record lands is read before it is added. -->
    <AddChild
      v-if="allowed.length"
      :campaign-id="campaignId"
      :allowed="allowed"
      :parent-name="name"
      :act-id="kind === 'act' ? node.id : null"
      :sequence-id="kind === 'sequence' ? node.id : null"
      @created="$emit('created', $event)"
    />

    <span class="row__meta">
      <ActProgress v-if="progress" :progress="progress" />
      <SceneStatus v-else-if="kind === 'scene'" :status="node.status" />

      <MoveControl :campaign-id="campaignId" :kind="kind" :node="node" :siblings="siblings" />
    </span>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--p-border-radius-sm);
}

.row:hover {
  background: var(--p-content-hover-background);
}

.row--act {
  padding-top: var(--space-4);
}

.row__main {
  flex: 1;
  min-width: 0;
}

.row__title {
  margin: 0;
  font-family: var(--grimoire-font-display);
  font-size: var(--step-0);
  line-height: 1.3;
}

.row__title--sequence {
  font-family: var(--grimoire-font-body);
  font-style: italic;
  font-weight: 400;
}

.row__title--scene {
  font-family: var(--grimoire-font-body);
  font-size: var(--step--1);
  font-weight: 400;
}

/*
 * Rows read as text and behave as links. The underline arrives on hover rather
 * than sitting under every row — a two-hundred-line outline with every title
 * underlined is a page of rules, not a table of contents.
 */
.row__main a {
  color: inherit;
  text-decoration: none;
}

.row__main a:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}

.row__main a:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

/* Present but unnamed, which is a state rather than a fault. */
.row__title--unnamed {
  color: var(--p-text-muted-color);
  font-style: italic;
}

/*
 * The title, editable in place. Sized and set like the text it replaces so the
 * row does not jump when it appears — a field that changes the line height is a
 * field that moves the row you were about to click.
 */
.row__field {
  width: 100%;
  max-width: 28rem;
  font: inherit;
  color: inherit;
  background: var(--p-content-background);
  border: 1px solid var(--p-primary-color);
  border-radius: var(--p-border-radius-sm);
  padding: 0 var(--space-2);
}

.row__field:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.row__description {
  margin: var(--space-1) 0 0;
  font-size: var(--step--1);
  font-style: italic;
  color: var(--p-text-muted-color);
}

.row__skip {
  color: var(--p-grimoire-rule-color);
  font-family: var(--grimoire-font-mono);
  flex: none;
}

/*
 * The fixed column that makes the dots a column. Anchored to the right rather
 * than given a width per child, so the dot and the move control stay aligned
 * without either needing to know the other's size.
 */
.row__meta {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  width: var(--outline-meta);
}

/*
 * A chevron, and a space exactly its size where there is nothing to collapse —
 * so titles at one level line up whether or not the row has children.
 */
.chevron {
  flex: none;
  width: 1.25rem;
  height: 1.25rem;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: var(--p-border-radius-sm);
  background: transparent;
  color: var(--p-navigation-item-icon-color);
  cursor: pointer;
  font-size: 0.7em;
}

.chevron:hover {
  color: var(--p-primary-color);
  background: var(--p-content-border-color);
}

.chevron:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.chevron--none {
  visibility: hidden;
}

/* Touch targets, in absolute pixels so no change to the spacing scale can lower them. */
@media (pointer: coarse) {
  .chevron {
    width: 44px;
    height: 44px;
  }
}
</style>
