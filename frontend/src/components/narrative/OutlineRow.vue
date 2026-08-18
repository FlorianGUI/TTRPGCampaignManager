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
import { toPlainText } from '../../markdown/toPlainText.js'
import { useWriteFailure } from '../../composables/useWriteFailure.js'

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
const { failed } = useWriteFailure()

const name = computed(() => titleOf(props.node, props.kind))

/*
 * What the description says, without what it is written in. A row is a list
 * cell, and the third projection exists for exactly this: `**bold**` and
 * `:npc[Fen Warden]` are characters an author typed, never ones a reader should
 * meet (#132). The act's own page renders the same field properly, one click
 * away, which is where there is room for it.
 *
 * Reduced rather than rendered inline, which is the other way to stop printing
 * syntax. A markdown link in here would come out indistinguishable from the
 * title's link beside it — `.row__main a` strips both of colour and underline
 * so a row reads as text — and two destinations with one appearance is worse
 * than no emphasis. Reduction cannot introduce a second target.
 *
 * An empty result drops the paragraph, so a description that is only markup
 * leaves no blank line behind.
 */
const summary = computed(() => toPlainText(props.node.description))

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
/*
 * Marking a scene off, from the outline.
 *
 * A full replacement like every other write here, and safe to send the body back
 * unchanged because the tree does not carry it — the scene's own record does, and
 * that is what is being echoed. `saveNode` refetches the tree, so the act's
 * progress dot above catches up in the same round trip.
 */
async function cycle(status) {
  try {
    const scene =
      (await structure.ensureNode(props.campaignId, 'scene', props.node.id)) ??
      structure.nodeFor('scene', props.node.id)

    await structure.saveNode(props.campaignId, 'scene', props.node.id, {
      title: props.node.title,
      body: scene?.body ?? '',
      status,
    })
  } catch {
    /*
     * Nothing to put back. `SceneStatus` is drawn from `node.status` off the
     * tree and holds no state of its own, so the dot never changed — it simply
     * did not move, which is indistinguishable from a click that missed (#111).
     */
    failed()
  }
}

async function commit() {
  if (!props.renaming) return

  const title = draft.value.trim()
  if (title && title !== props.node.title) {
    try {
      await structure.saveNode(props.campaignId, props.kind, props.node.id, {
        title,
        ...(props.kind === 'scene' ? { body: '', status: 'planned' } : { description: '' }),
      })
    } catch {
      /*
       * The row goes back to the title the tree still holds, which for a row
       * added moments ago is no title at all. That is the truth of it: the name
       * was not written, and leaving the typed one on screen would be the outline
       * showing something the campaign does not contain.
       */
      failed()
    }
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
      <!--
        The title and the controls are one line, which is what holds them level
        with each other. The description belongs under that line rather than
        beside it, so it sits outside and moves nothing.
      -->
      <div class="row__line">
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
          <!--
            `draggable="false"` because the row itself is the drag surface
            (#109) and an anchor is natively draggable: without this the browser
            starts dragging the *link* — a URL, with its own ghost image — and
            the row never moves.
          -->
          <RouterLink
            v-else
            :to="to"
            draggable="false"
            :class="{ 'row__title--unnamed': !node.title?.trim() }"
            >{{ name }}</RouterLink
          >
        </component>

        <!-- Where a new record lands is read before it is added. -->
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
          <SceneStatus v-else-if="kind === 'scene'" :status="node.status" @cycle="cycle" />

          <MoveControl :campaign-id="campaignId" :kind="kind" :node="node" :siblings="siblings" />
        </span>
      </div>

      <p v-if="summary" class="row__description">{{ summary }}</p>
    </div>
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
  flex: 1;
  min-width: 0;
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
 * Rows read as text and behave as links. Like the contents table, colour is the
 * hover cue; underlines turn a long outline into a page of rules.
 */
.row__main a {
  color: inherit;
  text-decoration: none;
}

.row__main a:hover {
  color: var(--p-primary-color);
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
 * Controls centred on the title, by sharing its line rather than by being
 * aligned to it.
 *
 * They are empty boxes, and an empty box's baseline is its bottom edge — so the
 * row's `baseline` hung them off their own height. Invisible while the status
 * mark was a 10px dot; six pixels of drift once it grew to a 24px hit area,
 * which took the move menu up with it and left the add button behind.
 *
 * Neither alignment on the row itself would do. `center` drops the controls
 * between the title and the description below it, and a fixed height computed
 * off the type scale is wrong for exactly the rows that are set smaller: a scene
 * title is an inline box, so its line box comes from the block's strut and not
 * from its own `line-height`. Sharing the line asks the browser for that height
 * instead of restating it.
 */
.row__line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
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
