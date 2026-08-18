<script setup>
/*
 * The plus beside a parent's own name: write something new inside this.
 *
 * **On the parent's own row, not at the end of the list.** A button under a list
 * has to be read as belonging to the thing above it; a plus on the row itself
 * says where the new record goes before you press it — which matters most in the
 * case that is otherwise ambiguous, an act whose last child is a sequence with
 * children of its own.
 *
 * It rides at the right of that row, with the other controls, everywhere it
 * appears — page headings included. Trailing it after the title put it at a
 * different place on every line, since titles are different lengths, and a
 * control you have to find again on each row is one you stop reaching for.
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
import { useWriteFailure } from '../../composables/useWriteFailure.js'

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
const { failed } = useWriteFailure()

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
  } catch {
    // Without this the plus spun and stopped and no row appeared, which reads as
    // a button that does nothing rather than as a request that was refused.
    failed()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <span class="add">
    <!-- Not `rounded`: the radius comes from the button token, and the ramp it
         reads is tight on purpose — "a book has crisp edges, not rounded app
         chrome". A pill here is a shape the design system does not have. -->
    <Button
      class="add__button"
      text
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
 * Quiet until wanted, relative to whatever it is sitting on.
 *
 * One of these is on every container in the outline, so at full strength they
 * would out-shout the campaign they are meant to be adding to. But it was a flat
 * `--p-text-muted-color`, and muted is an absolute: a token picked against the
 * page background, which is not the only background this lands on. Under a
 * display title, or in the dark theme, it faded to something you had to already
 * know was there.
 *
 * Mixed off `currentColor` instead, so it is derived from the text around it and
 * dims by the same proportion wherever it goes — one step quieter than its
 * neighbours in both themes rather than one fixed grey that happens to work in
 * one place.
 */
.add__button {
  color: color-mix(in oklab, currentColor 72%, transparent);
}

.add__button:hover {
  color: var(--p-primary-color);
}

/*
 * The focus ring hugs the button rather than floating off it.
 *
 * The global ring is 2px at 2px offset — right on a text field, and heavy on a
 * 28px circle, where the halo ends up wider than the icon inside it and reads as
 * a selection rather than a cursor position. Same thickness and same colour, so
 * it is no less visible and still clears the 3:1 that WCAG 1.4.11 asks of a focus
 * indicator; only the offset goes.
 *
 * Scoped rather than changed in `semantic.js`, because the token is right for
 * everything it was written for. `MoveControl` carries the same rule — the two
 * sit beside each other in every row and must not disagree about this.
 */
.add__button:focus-visible {
  outline-offset: 0;
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
