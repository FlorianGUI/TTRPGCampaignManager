<script setup>
/*
 * One scene: the body a game master reads at the table, and the way through to
 * the next one.
 *
 * The body is the payload of this whole feature — hundreds of characters of
 * markdown per scene, which is why it is not in the structure tree and why this
 * page fetches its own. Everything else here exists to keep it readable: a
 * measure it does not exceed, a trail out, and a stepper that goes where the
 * story goes rather than where the siblings are.
 *
 * The dialect is #53's and this page does not know it. `CampaignMarkdown` takes
 * the source and decides what it becomes — read-aloud blocks, entity chips, dice
 * — so a directive added there appears here without this file changing.
 */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import CampaignMarkdown from '../markdown/CampaignMarkdown.vue'
import NarrativeTrail from '../components/narrative/NarrativeTrail.vue'
import SceneStatus from '../components/narrative/SceneStatus.vue'
import SceneStepper from '../components/narrative/SceneStepper.vue'
import { scenesInOrder, titleOf, trailTo, useStructureStore } from '../stores/structure.js'

const route = useRoute()
const structure = useStructureStore()

const campaignId = computed(() => route.params.campaignId)
const sceneId = computed(() => route.params.sceneId)

const scene = computed(() => structure.nodeFor('scene', sceneId.value))
const tree = computed(() => structure.treeFor(campaignId.value))

watch(
  [campaignId, sceneId],
  ([campaign, id]) => {
    structure.ensureLoaded(campaign)
    structure.ensureNode(campaign, 'scene', id)
  },
  { immediate: true },
)

const trail = computed(() => trailTo(tree.value, 'scene', scene.value))

/*
 * Narrative order, not sibling order — the last scene of an act steps into the
 * first of the next. Read from the tree, which every campaign route has already
 * loaded, so the stepper costs no request of its own.
 */
const order = computed(() => (tree.value ? scenesInOrder(tree.value) : []))

/* ── editing ─────────────────────────────────────────────────────────────── */

const STATUSES = [
  { label: 'Planned', value: 'planned' },
  { label: 'Done', value: 'done' },
  { label: 'Skipped', value: 'skipped' },
]

/*
 * What the scene says. Where it sits is the three-dots menu's — see
 * `GroupingPage` for why the two are kept apart.
 */
const editing = ref(false)
const draft = ref({ title: '', body: '', status: 'planned' })
const saving = ref(false)
const failure = ref(null)

function edit() {
  // Every field, because the write is a full replacement: a body left out of the
  // request is cleared rather than kept, and this is the field a game master
  // spent an hour on.
  draft.value = { title: scene.value.title, body: scene.value.body, status: scene.value.status }
  failure.value = null
  editing.value = true
}

async function save() {
  if (!draft.value.title.trim()) {
    failure.value = 'Give it a title.'
    return
  }

  saving.value = true

  try {
    await structure.saveNode(campaignId.value, 'scene', sceneId.value, { ...draft.value })

    editing.value = false
  } catch {
    failure.value = 'That could not be saved.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <article v-if="scene" class="scene">
    <NarrativeTrail :campaign-id="campaignId" :trail="trail" />

    <header class="scene__head">
      <p class="label-smallcaps">Scene</p>

      <template v-if="!editing">
        <h1>{{ titleOf(scene, 'scene') }}</h1>
        <SceneStatus :status="scene.status" with-label />
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Edit"
          icon="pi pi-pencil"
          @click="edit"
        />
      </template>

      <template v-else>
        <InputText v-model="draft.title" class="scene__title-field" aria-label="Title" />
        <Select
          v-model="draft.status"
          :options="STATUSES"
          option-label="label"
          option-value="value"
        />
      </template>
    </header>

    <!--
      Written and read in the same column. The source is plain text and stays
      plain text — nothing here parses it before sending it back, which is what
      "stored byte for byte" means from this end.
    -->
    <Textarea
      v-if="editing"
      v-model="draft.body"
      class="scene__field"
      rows="18"
      aria-label="Body"
    />

    <CampaignMarkdown v-else-if="scene.body" class="prose scene__body" :source="scene.body" />

    <p v-else class="scene__unwritten">
      Nothing written yet. This is the normal state of most of a campaign.
    </p>

    <Message v-if="failure" severity="error" :closable="false">{{ failure }}</Message>

    <div v-if="editing" class="scene__actions">
      <Button label="Save" :loading="saving" @click="save" />
      <Button label="Cancel" text severity="secondary" @click="editing = false" />
    </div>

    <SceneStepper v-if="!editing" :campaign-id="campaignId" :scenes="order" :current-id="sceneId" />
  </article>

  <Message v-else-if="structure.error" severity="error" :closable="false"
    >That is not here.</Message
  >
</template>

<style scoped>
/*
 * Two thirds of the pane, like the act and sequence pages, so moving between the
 * three does not move the column under the reader.
 *
 * The prose inside still holds its own measure — `.scene__body` is capped at a
 * reading width, because prose set to 120 characters is not read, it is skimmed.
 * The page is two thirds; the paragraph is not.
 */
.scene {
  padding: var(--space-5) 0 var(--space-7);
  width: 66.6667%;
}

@media (max-width: 900px) {
  .scene {
    width: 100%;
  }
}

.scene__body {
  max-width: 62ch;
}

.scene__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.scene__head p {
  flex-basis: 100%;
  margin: 0;
}

.scene__head h1 {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: var(--step-3);
}

.scene__title-field {
  flex: 1;
  min-width: 12rem;
}

.scene__body,
.scene__unwritten,
.scene__field {
  margin-top: var(--space-5);
}

.scene__field {
  width: 100%;
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--1);
  line-height: 1.6;
}

.scene__unwritten {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.scene__actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}
</style>
