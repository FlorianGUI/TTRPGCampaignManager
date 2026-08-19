<script setup>
/*
 * A field that takes Campaign Manager markdown, with the vocabulary attached.
 *
 * One component rather than a toolbar each view wires up itself, because the
 * dialect is not the scene page's — session notes take the same one (#52), and
 * the caret arithmetic below is not worth writing twice.
 *
 * **It is a `<textarea>` and nothing more.** No rich-text model, no
 * transformation on the way in or out: the buttons put characters into a string
 * and the string is what the API stores, byte for byte (#80). That is also why
 * the source is written and read at the same measure — what a game master types
 * here wraps the way it will wrap when they read it back at the table.
 */
import { nextTick, ref } from 'vue'
import Textarea from 'primevue/textarea'
import MarkdownToolbar from './MarkdownToolbar.vue'
import { applyInsertion } from './toolbar.js'
import { t } from '../i18n/index.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: [Number, String], default: 12 },
  ariaLabel: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])

const field = ref(null)

/* PrimeVue's `Textarea` renders the element as its own root, so `$el` is the
   textarea itself rather than a wrapper to search — unlike the bare `<input>`
   in `OutlineRow`, where the ref is already the element. */
const textarea = () => field.value?.$el ?? null

/*
 * Insert, then hand the field back.
 *
 * The focus and the caret are the whole point. A button that inserted text and
 * left the caret where the mouse had put it would make a game master click back
 * into the field and hunt for the brackets — which is the work the button was
 * pressed to avoid. `nextTick` because the caret is set on the text the model
 * has not rendered yet.
 */
async function insert(item) {
  const element = textarea()
  if (!element) return

  const { value, caret } = applyInsertion(
    item,
    props.modelValue,
    element.selectionStart,
    element.selectionEnd,
  )

  emit('update:modelValue', value)

  await nextTick()

  element.focus()
  element.setSelectionRange(caret, caret)
}
</script>

<template>
  <div class="md-field">
    <MarkdownToolbar @insert="insert" />

    <Textarea
      ref="field"
      class="md-field__area"
      :model-value="modelValue"
      :rows="rows"
      :aria-label="ariaLabel"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <!-- Said outright rather than left to be inferred from the buttons. A game
         master who has not pressed one still needs to know the field is not
         plain text, and #103's first acceptance is that the form says so
         without having to be hovered to find out. -->
    <p class="md-field__hint">{{ t('markdown.hint') }}</p>
  </div>
</template>

<style scoped>
.md-field {
  display: flex;
  flex-direction: column;
}

/*
 * The mono face and the measure come from here now rather than from each view,
 * which is what makes this a component and not a toolbar bolted onto two
 * textareas that had drifted apart.
 */
.md-field__area {
  width: 100%;
  margin-top: var(--space-2);
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--1);
  line-height: 1.6;
}

.md-field__hint {
  margin: var(--space-2) 0 0;
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
}
</style>
