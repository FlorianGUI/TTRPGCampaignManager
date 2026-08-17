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
 * Read-only, deliberately. This is #88's first PR and it proves the tree renders
 * before anything can rearrange it; editing, reordering and the node pages are
 * the two that follow.
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
</script>

<template>
  <article class="structure">
    <header class="structure__head">
      <h1>{{ campaign?.name ?? 'Structure' }}</h1>

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
          :label="allShut ? 'Expand all' : 'Collapse all'"
          @click="toggleAll"
        />

        <AddChild
          v-if="tree"
          :campaign-id="campaignId"
          :allowed="['act', 'scene']"
          :parent-name="campaign?.name ?? 'the campaign'"
          @created="added"
        />

        <!-- A campaign has no status of its own and cannot be moved, so its
             copy of the row's trailing column is empty — but it is still there,
             which is what puts the plus above the plus on every act. -->
        <span class="structure__meta" aria-hidden="true" />
      </div>
    </header>

    <ProgressSpinner
      v-if="!tree && structure.loading"
      class="structure__loading"
      aria-label="Loading"
    />

    <Message v-else-if="!tree && structure.error" severity="error" :closable="false">
      The structure could not be loaded.
      <Button link label="Try again" @click="structure.reload(campaignId)" />
    </Message>

    <!--
      A campaign nobody has written in yet. It says what an act *is* rather than
      only offering one, because this is the first place the word appears.
    -->
    <p v-else-if="isEmpty" class="structure__empty">
      Nothing here yet. An <strong>act</strong> is a major division of the campaign — or write a
      scene straight onto the campaign and add the shape later.
    </p>

    <ol v-else-if="tree" class="outline">
      <li v-for="child in children" :key="child.node.id" class="outline__group">
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
            <ol class="outline__children">
              <li v-for="under in childrenOfAct(child.node)" :key="under.node.id">
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

                  <ol v-if="!isShut(under.node.id)" class="outline__children">
                    <li v-for="scene in scenesIn(under.node)" :key="scene.id">
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
              Nothing in this act yet. A <strong>sequence</strong> is a run of scenes that tells a
              small story of its own inside it — or write a scene straight onto the act.
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

          <ol v-if="!isShut(child.node.id)" class="outline__children">
            <li v-for="scene in scenesIn(child.node)" :key="scene.id">
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

.structure__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--p-grimoire-rule-color);
}

.structure__head h1 {
  margin: var(--space-1) 0 0;
  font-size: var(--step-3);
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
