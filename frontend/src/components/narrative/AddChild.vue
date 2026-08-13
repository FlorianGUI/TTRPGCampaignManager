<script setup>
/*
 * The plus beside a parent's own name: write something new inside this.
 *
 * **Beside the name, not at the end of the list.** A button under a list has to
 * be read as belonging to the thing above it; a plus on the row itself says
 * where the new record goes before you press it — which matters most in the case
 * that is otherwise ambiguous, an act whose last child is a sequence with
 * children of its own.
 *
 * **No title is asked for.** Sketching an act is six additions in a row, and six
 * dialogs is five too many: the row appears at the end and its title is already
 * focused, so adding and naming are one gesture rather than two screens. Escape
 * leaves it unnamed, which is a real state — see `titleOf`.
 *
 * A dialog only where there is a choice to make. A sequence can hold nothing but
 * scenes, so its plus writes one and says nothing; the campaign and an act can
 * hold two kinds, and those ask which.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useStructureStore } from '../../stores/structure.js'

const props = defineProps({
  campaignId: { type: String, required: true },
  // What may go in here, which is the tree's shape rather than a preference: the
  // campaign takes acts and scenes, an act takes sequences and scenes, a sequence
  // takes scenes.
  allowed: { type: Array, required: true },
  parentName: { type: String, required: true },
  actId: { type: String, default: null },
  sequenceId: { type: String, default: null },
})

const emit = defineEmits(['created'])

const structure = useStructureStore()

const choosing = ref(false)
const saving = ref(false)

const LABELS = { act: 'Act', sequence: 'Sequence', scene: 'Scene' }

const EXPLAINS = {
  act: 'A major division of the campaign.',
  sequence: 'A run of scenes that tells a small story of its own.',
  scene: 'A unit of play: one place, one cast.',
}

function start() {
  if (props.allowed.length === 1) return add(props.allowed[0])
  choosing.value = true
}

async function add(kind) {
  saving.value = true

  try {
    // Untitled, and appended. The API takes a bare string, so an empty one is a
    // legitimate record rather than a rejected request — which is what lets the
    // row exist before it has a name.
    const node = await structure.createNode(props.campaignId, kind, {
      title: '',
      ...(kind !== 'act' && { act_id: props.actId }),
      ...(kind === 'scene' && { sequence_id: props.sequenceId }),
    })

    choosing.value = false
    emit('created', { kind, node })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <span class="add">
    <Button
      class="add__button"
      text
      rounded
      size="small"
      icon="pi pi-plus"
      :loading="saving"
      :aria-label="`Add to ${parentName}`"
      @click.stop="start"
    />

    <Dialog
      v-model:visible="choosing"
      modal
      :header="`Add to ${parentName}`"
      :style="{ width: 'min(26rem, 92vw)' }"
    >
      <ul class="add__choices">
        <li v-for="kind in allowed" :key="kind">
          <button type="button" class="add__choice" :disabled="saving" @click="add(kind)">
            <span class="add__choice-name">{{ LABELS[kind] }}</span>
            <span class="add__choice-what">{{ EXPLAINS[kind] }}</span>
          </button>
        </li>
      </ul>
    </Dialog>
  </span>
</template>

<style scoped>
.add {
  flex: none;
}

/*
 * Quiet until wanted. One of these sits on every container in the outline, so at
 * full strength they would out-shout the campaign they are meant to be adding to.
 */
.add__button {
  color: var(--p-text-muted-color);
}

.add__button:hover {
  color: var(--p-primary-color);
}

.add__choices {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/*
 * The choice is the whole row, not a radio beside a word: two options on one
 * screen, each with a sentence saying what it is, and pressing one is the answer
 * — a confirm button after that would be a second click for no second decision.
 */
.add__choice {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.add__choice:hover {
  border-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}

.add__choice:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.add__choice-name {
  display: block;
  font-family: var(--grimoire-font-display);
}

.add__choice-what {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
}
</style>
