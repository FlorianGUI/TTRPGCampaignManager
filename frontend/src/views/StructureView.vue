<script setup>
/*
 * The campaign's structure: acts, sequences and scenes, as one indented outline.
 *
 * An ordinary page in the content area, like the Bestiary or the settings — the
 * shell is untouched and no route here sets `meta.layout`. That was a decision
 * taken the hard way: earlier drafts had the sidebar widening into the tree and
 * handing its sections to the drawer, and every one of those made the app carry
 * state that belongs to a page.
 *
 * **Depth is indentation**, which is what makes the levels being skippable
 * visible rather than explained: a scene hanging off an act sits where a
 * sequence would, and one hanging off the campaign sits at the outermost edge.
 * Nothing is less valid than anything else — a campaign of scenes and no acts is
 * a working campaign.
 *
 * **Two ways to move a row, and one path to the API.** The ⋮ menu is the one
 * that must always work — it is what a keyboard and a screen reader use, and
 * WCAG 2.2's 2.5.7 asks that everything a drag can do be doable without one.
 * Dragging is laid over it (#109) and ends in the same `place` call, because two
 * gestures building their own request bodies would eventually disagree about
 * what a move means.
 */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import AddChild from '../components/narrative/AddChild.vue'
import OutlineRow from '../components/narrative/OutlineRow.vue'
import { actProgress, useStructureStore } from '../stores/structure.js'
import { useCampaignsStore } from '../stores/campaigns.js'
import { readCollapsed, rememberCollapsed } from '../stores/collapsedNarrative.js'
import { vDragToPlace } from '../directives/dragToPlace.js'
import { useWriteFailure } from '../composables/useWriteFailure.js'
import { t } from '../i18n/index.js'
import { toPlainText } from '../markdown/toPlainText.js'

const route = useRoute()
const structure = useStructureStore()
const campaigns = useCampaignsStore()

/*
 * The page is titled with the campaign, not with the word "Structure".
 *
 * The sidebar already says which campaign this is and the nav says which of its
 * pages — a heading repeating both told the reader nothing they had not just
 * read, and spent the largest type on the page saying it.
 */
const campaign = computed(() => campaigns.byId(campaignId.value))

/*
 * The row that was just added, and so is still being named. One at a time: a
 * second addition commits the first, which is what a text field losing focus
 * means everywhere else.
 */
const renaming = ref(null)

function added({ node }) {
  renaming.value = node.id
}

const campaignId = computed(() => route.params.campaignId)
const tree = computed(() => structure.treeFor(campaignId.value))

/*
 * Which acts and sequences are shut, remembered per campaign in `localStorage`.
 * The API has no opinion about it and must not grow one — see the module for
 * why a view preference stored server-side would be #31's problem.
 */
const collapsed = ref(new Set())

watch(
  campaignId,
  (id) => {
    collapsed.value = readCollapsed(id)
    structure.ensureLoaded(id)
  },
  { immediate: true },
)

function toggle(id) {
  // Replaced rather than mutated: a Set's contents are not reactive, so adding
  // to the existing one would change the data and leave the template showing
  // the old answer.
  const next = new Set(collapsed.value)
  next.has(id) ? next.delete(id) : next.add(id)
  collapsed.value = next
  rememberCollapsed(campaignId.value, next)
}

const isShut = (id) => collapsed.value.has(id)

/*
 * The campaign's own children, in position order: acts and any scene hanging off
 * the campaign itself, together. Sequences that skip the act level are here too
 * — unlike the sidebar, this page has room for all three kinds at one level, and
 * hiding them would make a sequence written straight onto the campaign
 * unreachable.
 */
const children = computed(() => {
  if (!tree.value) return []

  const { acts, sequences, scenes } = tree.value

  return [
    ...acts.map((node) => ({ kind: 'act', node })),
    ...sequences.filter((s) => s.act_id === null).map((node) => ({ kind: 'sequence', node })),
    ...scenes
      .filter((s) => s.act_id === null && s.sequence_id === null)
      .map((node) => ({ kind: 'scene', node })),
  ].sort((a, b) => a.node.position - b.node.position || a.node.id.localeCompare(b.node.id))
})

const sequencesIn = (act) => tree.value.sequences.filter((sequence) => sequence.act_id === act.id)

const scenesOn = (act) => tree.value.scenes.filter((scene) => scene.act_id === act.id)

const scenesIn = (sequence) =>
  tree.value.scenes.filter((scene) => scene.sequence_id === sequence.id)

/*
 * An act's children in one ordered list, so a scene written straight onto the act
 * keeps its place among the sequences rather than being listed after all of them.
 * The tree stores only the direct parent, so this is the only place that ordering
 * exists.
 */
const childrenOfAct = (act) =>
  [
    ...sequencesIn(act).map((node) => ({ kind: 'sequence', node })),
    ...scenesOn(act).map((node) => ({ kind: 'scene', node })),
  ].sort((a, b) => a.node.position - b.node.position || a.node.id.localeCompare(b.node.id))

const progressOf = (act) => actProgress(tree.value, act)

/*
 * The list a row sits in, which is what "up" and "down" mean for it.
 *
 * Every level passes its own, taken from the same array the rows were rendered
 * from — a scene inside a sequence moves among that sequence's scenes, and the
 * wrong list would anchor a step against something that is not a sibling and be
 * refused by the API for reasons nobody could see on screen.
 *
 * At each level the two kinds are ordered together, for the same reason the
 * outline renders them that way: a scene written straight onto an act sits among
 * the sequences beside it, not after all of them.
 */
/*
 * A sequence holds only scenes, but the list still travels as entries: since #101
 * an anchor names its own kind, and a shape that varies by level would put that
 * decision in every call site.
 */
const sceneEntriesIn = (sequence) => scenesIn(sequence).map((node) => ({ kind: 'scene', node }))

/*
 * What the campaign's description says, without what it is written in — the
 * same reduction `OutlineRow` makes for an act's, one level down (#132).
 *
 * Guarded on the result rather than on the field. A description that is only
 * markup reduces to nothing, and `v-if` on the raw text would leave an empty
 * italic line under the name with no way to tell what put it there.
 */
const summary = computed(() => toPlainText(campaign.value?.description))

const isEmpty = computed(() => tree.value && !children.value.length)

const everything = computed(() =>
  tree.value ? [...tree.value.acts, ...tree.value.sequences].map((node) => node.id) : [],
)

const allShut = computed(
  () => everything.value.length > 0 && everything.value.every((id) => collapsed.value.has(id)),
)

function toggleAll() {
  const next = allShut.value ? new Set() : new Set(everything.value)
  collapsed.value = next
  rememberCollapsed(campaignId.value, next)
}

/*
 * Dropping a row: the same call the ⋮ menu makes, and deliberately the only
 * path to the API either of them has (#109). Two ways of moving something that
 * built their own request bodies would eventually disagree about what a move
 * means — an omitted parent is "put this on the campaign", which is not what a
 * reorder ever intends.
 *
 * The failure is the one from #111. A refused drop has nowhere of its own to
 * report to: the row is already back where it started, because the directive
 * hands the DOM back before asking, so without this it would spring home and
 * say nothing.
 */
const { failed } = useWriteFailure()

async function dropped({ item, parent, after }) {
  try {
    await structure.place(campaignId.value, item.kind, item.id, { parent, after })
  } catch {
    failed()
  }
}

/*
 * A shut row held under a dragged one opens, rather than being dropped into
 * blind. Not `toggle`: springing open must never *close* something, and a
 * pointer resting over an act that is already open should do nothing at all.
 */
function springOpen(id) {
  if (!collapsed.value.has(id)) return

  toggle(id)
}

/* What each list is, and what it may hold — the tree's shape, written once per
 * level and read back off the DOM when something is dropped. */
const CAMPAIGN_LIST = { parent: null, accepts: ['act', 'sequence', 'scene'] }

const listFor = (kind, node) => ({
  parent: { id: node.id, kind },
  accepts: kind === 'act' ? ['sequence', 'scene'] : ['scene'],
})

const dragging = (list) => ({ ...list, onDrop: dropped, onSpringOpen: springOpen })
</script>

<template>
  <article class="structure">
    <header class="structure__head">
      <!--
        The name and the controls are one row, and the description is under it
        rather than beside it. All three were siblings in a single flex row, so
        the description inherited the whole of that row's layout — `align-items:
        flex-end`, `space-between`, and `gap` counted as a *row* gap, which set a
        lede a full step below the name it introduces and moved it again
        whenever the controls wrapped at a narrow width.
      -->
      <div class="structure__head-row">
        <h1>{{ campaign?.name ?? t('structure.heading') }}</h1>

        <!-- The campaign's own controls, laid out like a row's: whatever else is
             here, then the plus, then the column a row keeps its status and move
             menu in. So the campaign's plus sits above every act's plus. -->
        <div class="structure__actions">
          <Button
            v-if="everything.length"
            class="structure__collapse"
            size="small"
            severity="secondary"
            outlined
            :label="allShut ? t('structure.expandAll') : t('structure.collapseAll')"
            @click="toggleAll"
          />

          <AddChild
            v-if="tree"
            :campaign-id="campaignId"
            :allowed="['act', 'scene']"
            :parent-name="campaign?.name ?? t('structure.theCampaign')"
            @created="added"
          />

          <!-- A campaign has no status of its own and cannot be moved, so its
               copy of the row's trailing column is empty — but it is still
               there, which is what puts the plus above the plus on every act. -->
          <span class="structure__meta" aria-hidden="true" />
        </div>
      </div>

      <!--
        The campaign's description, under its name — the same thing an act's page
        does with its own, on the page that is the campaign's own.

        Inside the header rather than after it, so the rule that closes the
        header stays under the whole heading block instead of running between a
        name and the line that introduces it.

        Reduced to its words, exactly as `OutlineRow` reduces an act's one level
        down — same projection, same treatment, so the campaign's description
        and its acts' read as the same kind of thing rather than as two. It also
        keeps a heading or a read-aloud box from opening inside a page header,
        which is what rendering the dialect here would allow.
      -->
      <p v-if="summary" class="structure__description">{{ summary }}</p>
    </header>

    <ProgressSpinner
      v-if="!tree && structure.loading"
      class="structure__loading"
      :aria-label="t('structure.loading')"
    />

    <Message v-else-if="!tree && structure.error" severity="error" :closable="false">
      {{ t('structure.error') }}
      <Button link :label="t('structure.retry')" @click="structure.reload(campaignId)" />
    </Message>

    <!--
      A campaign nobody has written in yet. It says what an act *is* rather than
      only offering one, because this is the first place the word appears.
    -->
    <!-- Three keys around one `<strong>`: the kind is emphasised inside the
         sentence, and nothing in this app renders an HTML string. -->
    <p v-else-if="isEmpty" class="structure__empty">
      {{ t('structure.empty.before') }} <strong>{{ t('structure.empty.word') }}</strong>
      {{ t('structure.empty.after') }}
    </p>

    <!--
      Three lists, one per level, each sortable and all in one group so a row can
      be dragged out of its parent into another. What may land where is the
      list's own business — see `dragToPlace`, which reads it back off these
      elements when something is dropped.

      The rows carry `data-shut` and `data-accepts` as well, because a collapsed
      act has no children list to ask: those two are what let it spring open
      under a row held over it.
    -->
    <ol v-else-if="tree" v-drag-to-place="dragging(CAMPAIGN_LIST)" class="outline">
      <li
        v-for="child in children"
        :key="child.node.id"
        class="outline__group"
        :data-id="child.node.id"
        :data-kind="child.kind"
        :data-shut="isShut(child.node.id) || undefined"
        :data-accepts="
          child.kind === 'scene' ? undefined : listFor(child.kind, child.node).accepts.join(' ')
        "
      >
        <!-- ── An act ─────────────────────────────────────────────── -->
        <template v-if="child.kind === 'act'">
          <OutlineRow
            :campaign-id="campaignId"
            kind="act"
            :node="child.node"
            :siblings="children"
            :progress="progressOf(child.node)"
            collapsible
            :shut="isShut(child.node.id)"
            :allowed="['sequence', 'scene']"
            :renaming="renaming === child.node.id"
            @toggle="toggle"
            @created="added"
            @renamed="renaming = null"
            @cancel-rename="renaming = null"
          />

          <template v-if="!isShut(child.node.id)">
            <ol v-drag-to-place="dragging(listFor('act', child.node))" class="outline__children">
              <li
                v-for="under in childrenOfAct(child.node)"
                :key="under.node.id"
                :data-id="under.node.id"
                :data-kind="under.kind"
                :data-shut="isShut(under.node.id) || undefined"
                :data-accepts="under.kind === 'sequence' ? 'scene' : undefined"
              >
                <!-- A sequence inside the act -->
                <template v-if="under.kind === 'sequence'">
                  <OutlineRow
                    :campaign-id="campaignId"
                    kind="sequence"
                    :node="under.node"
                    :siblings="childrenOfAct(child.node)"
                    collapsible
                    :shut="isShut(under.node.id)"
                    :allowed="['scene']"
                    :renaming="renaming === under.node.id"
                    @toggle="toggle"
                    @created="added"
                    @renamed="renaming = null"
                    @cancel-rename="renaming = null"
                  />

                  <ol
                    v-if="!isShut(under.node.id)"
                    v-drag-to-place="dragging(listFor('sequence', under.node))"
                    class="outline__children"
                  >
                    <li
                      v-for="scene in scenesIn(under.node)"
                      :key="scene.id"
                      :data-id="scene.id"
                      data-kind="scene"
                    >
                      <OutlineRow
                        :campaign-id="campaignId"
                        kind="scene"
                        :node="scene"
                        :siblings="sceneEntriesIn(under.node)"
                        :renaming="renaming === scene.id"
                        @renamed="renaming = null"
                        @cancel-rename="renaming = null"
                      />
                    </li>
                  </ol>
                </template>

                <!-- A scene hanging off the act, skipping the sequence level -->
                <OutlineRow
                  v-else
                  :campaign-id="campaignId"
                  kind="scene"
                  :node="under.node"
                  :siblings="childrenOfAct(child.node)"
                  skips-level
                  :renaming="renaming === under.node.id"
                  @renamed="renaming = null"
                  @cancel-rename="renaming = null"
                />
              </li>
            </ol>

            <!--
              The one place the app teaches the word. #88 asks for it explicitly:
              "sequence" is screenwriting jargon and a game master will not arrive
              already using it, so the empty act is where it gets a sentence.
            -->
            <p v-if="!childrenOfAct(child.node).length" class="empty-slot">
              {{ t('structure.emptyAct.before') }}
              <strong>{{ t('structure.emptyAct.word') }}</strong>
              {{ t('structure.emptyAct.after') }}
            </p>
          </template>
        </template>

        <!-- ── A sequence written straight onto the campaign ───────── -->
        <template v-else-if="child.kind === 'sequence'">
          <OutlineRow
            :campaign-id="campaignId"
            kind="sequence"
            :node="child.node"
            :siblings="children"
            collapsible
            :shut="isShut(child.node.id)"
            :allowed="['scene']"
            :renaming="renaming === child.node.id"
            @toggle="toggle"
            @created="added"
            @renamed="renaming = null"
            @cancel-rename="renaming = null"
          />

          <ol
            v-if="!isShut(child.node.id)"
            v-drag-to-place="dragging(listFor('sequence', child.node))"
            class="outline__children"
          >
            <li
              v-for="scene in scenesIn(child.node)"
              :key="scene.id"
              :data-id="scene.id"
              data-kind="scene"
            >
              <OutlineRow
                :campaign-id="campaignId"
                kind="scene"
                :node="scene"
                :siblings="sceneEntriesIn(child.node)"
                :renaming="renaming === scene.id"
                @renamed="renaming = null"
                @cancel-rename="renaming = null"
              />
            </li>
          </ol>
        </template>

        <!-- ── A scene on the campaign itself ─────────────────────── -->
        <OutlineRow
          v-else
          :campaign-id="campaignId"
          kind="scene"
          :node="child.node"
          :siblings="children"
          :renaming="renaming === child.node.id"
          @renamed="renaming = null"
          @cancel-rename="renaming = null"
        />
      </li>
    </ol>
  </article>
</template>

<style scoped>
.structure {
  padding: var(--space-5) 0 var(--space-7);
}

/* The block, and the rule that closes it. The row inside does the aligning. */
.structure__head {
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--p-grimoire-rule-color);
}

.structure__head-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.structure__head-row h1 {
  margin: var(--space-1) 0 0;
  font-size: var(--step-3);
}

/*
 * The same treatment a description gets under an act's or a sequence's name in
 * the outline below — see `.row__description` in `OutlineRow.vue`. It is the
 * same thing said in the same place, one level up, so it reads the same way:
 * italic, muted, a step down from the text it introduces.
 *
 * **`display: block` is load-bearing.** `mode="inline"` renders a `<span>` root
 * (see `renderTree`), and on an inline box a vertical margin and a `max-width`
 * are silently ignored — so without this the lede has neither the space under
 * the name nor a measure, and flows as text rather than sitting under it.
 *
 * Its own margin rather than the row's gap: the distance between a title and
 * the controls beside it is not the distance between a title and the line
 * introducing it, and they do not have to be the same number.
 */
.structure__description {
  display: block;
  margin: var(--space-1) 0 0;
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
  font-style: italic;
}

.structure__loading {
  display: block;
  margin: var(--space-7) auto;
  width: 3rem;
  height: 3rem;
}

.structure__empty,
.empty-slot {
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
}

.structure__empty {
  margin: var(--space-6) 0;
  max-width: 46ch;
}

.empty-slot {
  margin: var(--space-2) 0 var(--space-3) 2.25rem;
  padding: var(--space-3);
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
  max-width: 52ch;
}

.outline,
.outline__children {
  list-style: none;
  margin: 0;
  padding: 0;
}

/*
 * Indentation is the tree. One step per level, applied to the nested list rather
 * than to the row, so a row cannot be indented independently of where it sits.
 */
.outline__children {
  margin-left: 1.5rem;
}

.outline__group + .outline__group {
  border-top: 1px solid var(--p-grimoire-rule-color);
}

/*
 * The three states SortableJS marks while a row is being dragged (#109).
 *
 * `.sortable-ghost` is the gap the row will drop into — the one thing that has
 * to be unmistakable, because it is the answer to "where is this going". A tinted
 * slot rather than an outline, so it reads as a space rather than as a row.
 *
 * `.sortable-drag` is the copy following the pointer, and it is the one place in
 * this app where something genuinely floats: the overlay shadow is exactly what
 * the README reserves for that, rather than an elevation scale the design system
 * does not have.
 */
.outline .sortable-ghost > * {
  opacity: 0.25;
}

.outline .sortable-ghost {
  background: var(--p-content-hover-background);
  border-radius: var(--p-border-radius-sm);
}

.outline .sortable-drag {
  background: var(--p-content-background);
  border-radius: var(--p-border-radius-sm);
  box-shadow: var(--p-overlay-popover-shadow);
  cursor: grabbing;
}

/*
 * The row does not advertise a grab handle it does not have: the whole row is
 * the surface, and the cursor is what says so. Only while a pointer is over a
 * row that can move — the chevron, the plus and the menu keep their own.
 */
.outline__group,
.outline__children > li {
  cursor: grab;
}

.outline__group :is(button, input, a),
.outline__children :is(button, input, a) {
  cursor: revert;
}

/*
 * Right-aligned and inset by the padding a row carries, so the plus inside lands
 * on the same vertical line as the plus on every act below rather than ten
 * pixels shy of it — which reads as a mistake in a way a frank difference would
 * not.
 */
.structure__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-right: var(--space-2);
}

.structure__meta {
  width: var(--outline-meta);
}
</style>
