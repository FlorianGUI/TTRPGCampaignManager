<script setup>
/*
 * An act or a sequence: a title, a description, and what it holds.
 *
 * One component for both levels because they differ in exactly two things — an
 * act shows progress, a sequence explains what it is — and two views would have
 * been the same file twice with a word changed. `ActView` and `SequenceView` are
 * the routes; this is what they both are.
 *
 * The page carries no tree beside it. Getting back is the breadcrumb, which
 * always starts at Structure; getting *down* is the contents list.
 */
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import CampaignMarkdown from '../markdown/CampaignMarkdown.vue'
import ActProgress from '../components/narrative/ActProgress.vue'
import AddChild from '../components/narrative/AddChild.vue'
import NarrativeTrail from '../components/narrative/NarrativeTrail.vue'
import NodeContents from '../components/narrative/NodeContents.vue'
import { actProgress, titleOf, trailTo, useStructureStore } from '../stores/structure.js'
// The sentence only — see the note in `SceneView`. The controls this page hosts
// (`AddChild`, and the move menu inside `NodeContents`) speak through the toast
// instead, because a menu command has no form to report to.
import { COULD_NOT_SAVE } from '../composables/useWriteFailure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  kind: { type: String, required: true },
  id: { type: String, required: true },
})

const structure = useStructureStore()

const node = computed(() => structure.nodeFor(props.kind, props.id))
const tree = computed(() => structure.treeFor(props.campaignId))

watch(
  () => [props.campaignId, props.id],
  ([campaignId, id]) => {
    structure.ensureLoaded(campaignId)
    structure.ensureNode(campaignId, props.kind, id)
  },
  { immediate: true },
)

const trail = computed(() => trailTo(tree.value, props.kind, node.value))

const progress = computed(() =>
  props.kind === 'act' && tree.value && node.value ? actProgress(tree.value, node.value) : null,
)

/*
 * What this holds, in `position` order and mixing the two kinds — separating
 * them would put every scene written straight onto an act after all of its
 * sequences, whatever order the story goes in.
 */
const children = computed(() => {
  if (!tree.value || !node.value) return []

  const mine =
    props.kind === 'act'
      ? [
          ...tree.value.sequences
            .filter((s) => s.act_id === props.id)
            .map((n) => ({ kind: 'sequence', node: n })),
          ...tree.value.scenes
            .filter((s) => s.act_id === props.id)
            .map((n) => ({ kind: 'scene', node: n })),
        ]
      : tree.value.scenes
          .filter((s) => s.sequence_id === props.id)
          .map((n) => ({ kind: 'scene', node: n }))

  return mine.sort(
    (a, b) => a.node.position - b.node.position || a.node.id.localeCompare(b.node.id),
  )
})

/* ── editing ─────────────────────────────────────────────────────────────── */

/*
 * **This form owns what the record says, and nothing about where it sits.**
 *
 * A parent picker lived here for a while. The split that settled is cleaner: the
 * form is content, the three-dots menu is movement — because an edit form that
 * could also reparent meant a rename and a reorganisation shared one Save button,
 * and only one of those is undone by doing it again.
 */
const editing = ref(false)
const draft = ref({ title: '', description: '' })
const saving = ref(false)
const failure = ref(null)

function edit() {
  // Loaded with the current values, because the write is a full replacement: a
  // form that started empty would clear the description of whatever it saved.
  draft.value = { title: node.value.title, description: node.value.description }
  failure.value = null
  editing.value = true
}

async function save() {
  if (!draft.value.title.trim()) {
    // The API takes a bare string, so it accepts a blank title and answers 422
    // only for a missing one. This is the only thing between a game master and
    // a nameless act.
    failure.value = 'Give it a title.'
    return
  }

  saving.value = true

  try {
    await structure.saveNode(props.campaignId, props.kind, props.id, {
      title: draft.value.title,
      description: draft.value.description,
    })

    editing.value = false
  } catch {
    failure.value = COULD_NOT_SAVE
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <article v-if="node" class="node">
    <NarrativeTrail :campaign-id="campaignId" :trail="trail" />

    <header class="node__head">
      <p class="label-smallcaps">{{ kind }}</p>

      <template v-if="!editing">
        <h1>{{ titleOf(node, kind) }}</h1>
        <Button
          class="node__edit"
          size="small"
          severity="secondary"
          outlined
          label="Edit"
          icon="pi pi-pencil"
          @click="edit"
        />
      </template>

      <InputText v-else v-model="draft.title" class="node__title-field" aria-label="Title" />
    </header>

    <ActProgress
      v-if="progress && !editing"
      :progress="progress"
      with-label
      class="node__progress"
    />

    <!-- Editing and reading in the same place, so the measure and the wrapping
         a game master writes against are the ones they will read back. -->
    <template v-if="editing">
      <Textarea v-model="draft.description" class="node__field" rows="6" aria-label="Description" />

      <Message v-if="failure" severity="error" :closable="false">{{ failure }}</Message>

      <div class="node__actions">
        <Button label="Save" :loading="saving" @click="save" />
        <Button label="Cancel" text severity="secondary" @click="editing = false" />
      </div>
    </template>

    <CampaignMarkdown
      v-else-if="node.description"
      class="prose node__prose"
      :source="node.description"
    />

    <!--
      The one place the app explains the word, and #88 asks for it by name: a
      game master who has not studied screenwriting will not arrive already using
      it. Shown on the sequence's own page, where there is room for a sentence.
    -->
    <p v-if="kind === 'sequence'" class="node__teach">
      A <strong>sequence</strong> is a run of scenes that tells a small story of its own inside an
      act — a beginning and an end, at a smaller scale than the act around it.
    </p>

    <section class="node__section">
      <div class="node__section-head">
        <h2 class="label-smallcaps">Contains</h2>
        <AddChild
          :campaign-id="campaignId"
          :allowed="kind === 'act' ? ['sequence', 'scene'] : ['scene']"
          :parent-name="titleOf(node, kind)"
          :act-id="kind === 'act' ? id : null"
          :sequence-id="kind === 'sequence' ? id : null"
        />
      </div>

      <NodeContents v-if="children.length" :campaign-id="campaignId" :children="children" />
      <p v-else class="node__empty">
        Nothing in it yet.
        <template v-if="kind === 'act'">
          Add a <strong>sequence</strong> — a run of scenes that tells a small story of its own — or
          write a scene straight onto this act.
        </template>
        <template v-else>Write a scene in it.</template>
      </p>
    </section>
  </article>

  <Message v-else-if="structure.error" severity="error" :closable="false">
    <!-- A node that is not yours answers exactly as one that never existed, so
         there is one message for both and it does not guess between them. -->
    That is not here.
  </Message>
</template>

<style scoped>
/*
 * Two thirds of the pane, at every width above the breakpoint.
 *
 * A proportion rather than a fixed measure, so the page keeps the same shape on
 * a laptop and on a wide monitor instead of becoming a narrow ribbon adrift in
 * whitespace. Below the sidebar's breakpoint it takes the width it is given —
 * two thirds of a phone is not a column, it is a margin.
 */
.node {
  padding: var(--space-5) 0 var(--space-7);
  width: 66.6667%;
}

@media (max-width: 900px) {
  .node {
    width: 100%;
  }
}

.node__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.node__head p {
  flex-basis: 100%;
  margin: 0;
}

.node__head h1 {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: var(--step-3);
}

.node__title-field {
  flex: 1;
  min-width: 0;
}

.node__progress,
.node__prose,
.node__field,
.node__teach {
  margin-top: var(--space-4);
}

.node__field {
  width: 100%;
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--1);
}

.node__actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.node__teach {
  padding: var(--space-3);
  border-left: 2px solid var(--p-primary-color);
  background: var(--p-content-hover-background);
  border-radius: 0 var(--p-border-radius-sm) var(--p-border-radius-sm) 0;
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
  max-width: 56ch;
}

.node__section {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--p-grimoire-rule-color);
}

/*
 * The heading left, the plus right — above the column the rows put their own
 * controls in, so it is the same target at the same edge one line further up.
 */
.node__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.node__empty {
  margin: var(--space-3) 0 0;
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
  max-width: 56ch;
}
</style>
