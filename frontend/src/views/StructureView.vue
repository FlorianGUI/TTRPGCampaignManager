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
import ActProgress from '../components/narrative/ActProgress.vue'
import SceneStatus from '../components/narrative/SceneStatus.vue'
import { actProgress, useStructureStore } from '../stores/structure.js'
import { readCollapsed, rememberCollapsed } from '../stores/collapsedNarrative.js'

const route = useRoute()
const structure = useStructureStore()

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
      <div>
        <p class="label-smallcaps">Campaign</p>
        <h1>Structure</h1>
      </div>

      <Button
        v-if="everything.length"
        class="structure__collapse"
        size="small"
        severity="secondary"
        outlined
        :label="allShut ? 'Expand all' : 'Collapse all'"
        @click="toggleAll"
      />
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
          <div class="row row--act">
            <button
              type="button"
              class="chevron"
              :aria-expanded="!isShut(child.node.id)"
              :aria-label="`${isShut(child.node.id) ? 'Expand' : 'Collapse'} ${child.node.title}`"
              @click="toggle(child.node.id)"
            >
              <i
                class="pi"
                :class="isShut(child.node.id) ? 'pi-chevron-right' : 'pi-chevron-down'"
              />
            </button>

            <div class="row__main">
              <h2 class="row__title">{{ child.node.title }}</h2>
              <p v-if="child.node.description" class="row__description">
                {{ child.node.description }}
              </p>
            </div>

            <ActProgress :progress="progressOf(child.node)" />
          </div>

          <ol v-if="!isShut(child.node.id)" class="outline__children">
            <li v-for="under in childrenOfAct(child.node)" :key="under.node.id">
              <!-- A sequence inside the act -->
              <template v-if="under.kind === 'sequence'">
                <div class="row row--sequence">
                  <button
                    type="button"
                    class="chevron"
                    :aria-expanded="!isShut(under.node.id)"
                    :aria-label="`${isShut(under.node.id) ? 'Expand' : 'Collapse'} ${under.node.title}`"
                    @click="toggle(under.node.id)"
                  >
                    <i
                      class="pi"
                      :class="isShut(under.node.id) ? 'pi-chevron-right' : 'pi-chevron-down'"
                    />
                  </button>

                  <div class="row__main">
                    <h3 class="row__title row__title--sequence">{{ under.node.title }}</h3>
                    <p v-if="under.node.description" class="row__description">
                      {{ under.node.description }}
                    </p>
                  </div>
                </div>

                <ol v-if="!isShut(under.node.id)" class="outline__children">
                  <li v-for="scene in scenesIn(under.node)" :key="scene.id">
                    <div class="row row--scene">
                      <span class="chevron chevron--none" aria-hidden="true" />
                      <span class="row__main row__title--scene">{{ scene.title }}</span>
                      <SceneStatus :status="scene.status" />
                    </div>
                  </li>
                </ol>
              </template>

              <!--
                A scene hanging off the act, skipping the sequence level. Marked,
                because at this indent it would otherwise look like a sequence
                with no children.
              -->
              <div v-else class="row row--scene">
                <span class="chevron chevron--none" aria-hidden="true" />
                <span class="row__skip" title="Attached to the act, skipping the sequence level"
                  >↳</span
                >
                <span class="row__main row__title--scene">{{ under.node.title }}</span>
                <SceneStatus :status="under.node.status" />
              </div>
            </li>
          </ol>

          <!--
            The one place the app teaches the word. #88 asks for it explicitly:
            "sequence" is screenwriting jargon and a game master will not arrive
            already using it, so the empty act is where it gets a sentence.
          -->
          <p v-if="!isShut(child.node.id) && !childrenOfAct(child.node).length" class="empty-slot">
            Nothing in this act yet. A <strong>sequence</strong> is a run of scenes that tells a
            small story of its own inside it — or write a scene straight onto the act.
          </p>
        </template>

        <!-- ── A sequence written straight onto the campaign ───────── -->
        <template v-else-if="child.kind === 'sequence'">
          <div class="row row--sequence row--at-campaign">
            <button
              type="button"
              class="chevron"
              :aria-expanded="!isShut(child.node.id)"
              :aria-label="`${isShut(child.node.id) ? 'Expand' : 'Collapse'} ${child.node.title}`"
              @click="toggle(child.node.id)"
            >
              <i
                class="pi"
                :class="isShut(child.node.id) ? 'pi-chevron-right' : 'pi-chevron-down'"
              />
            </button>

            <div class="row__main">
              <h2 class="row__title row__title--sequence">{{ child.node.title }}</h2>
              <p v-if="child.node.description" class="row__description">
                {{ child.node.description }}
              </p>
            </div>
          </div>

          <ol v-if="!isShut(child.node.id)" class="outline__children">
            <li v-for="scene in scenesIn(child.node)" :key="scene.id">
              <div class="row row--scene">
                <span class="chevron chevron--none" aria-hidden="true" />
                <span class="row__main row__title--scene">{{ scene.title }}</span>
                <SceneStatus :status="scene.status" />
              </div>
            </li>
          </ol>
        </template>

        <!-- ── A scene on the campaign itself ─────────────────────── -->
        <div v-else class="row row--scene row--at-campaign">
          <span class="chevron chevron--none" aria-hidden="true" />
          <span class="row__main row__title--scene">{{ child.node.title }}</span>
          <SceneStatus :status="child.node.status" />
        </div>
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
  font-size: var(--step-0);
  font-weight: 400;
}

.row__title--scene {
  font-size: var(--step--1);
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
