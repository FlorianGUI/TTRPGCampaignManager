<script setup>
/*
 * A field that takes Campaign Manager markdown, with the vocabulary attached.
 *
 * #103's complaint, answered: the reading side of this app teaches the dialect
 * and the writing side hid it, so a game master who had watched
 * `:npc[Maerin Holt]` become a chip had nowhere to find out how to make another
 * one. Every directive the renderer implements is a button here.
 *
 * One component rather than a toolbar each view wires up itself, because the
 * dialect is not the scene page's — session notes take the same one (#52), and
 * the caret arithmetic below is not worth writing twice.
 *
 * **The buttons are not a component of their own.** They were, briefly, and the
 * seam paid for nothing: the row had exactly one consumer, no state of its own
 * worth naming, and an `insert` event whose only listener was six lines below
 * where it was raised. The part that genuinely wanted separating is `toolbar.js`
 * — the rules about what a button writes and where the caret lands, which are
 * testable without mounting anything and are tested that way.
 *
 * **It is a `<textarea>` and nothing more.** No rich-text model, no
 * transformation on the way in or out: the buttons put characters into a string
 * and the string is what the API stores, byte for byte (#80). That is also why
 * the source is written and read at the same measure — what a game master types
 * here wraps the way it will wrap when they read it back at the table.
 */
import { nextTick, ref } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { TOOLBAR_ITEMS, applyInsertion } from './toolbar.js'
import { t } from '../i18n/index.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: [Number, String], default: 12 },
  ariaLabel: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])

const field = ref(null)
const row = ref(null)
/* Which button the single tab stop lands on — see the note above `move`. */
const active = ref(0)

/* PrimeVue's `Textarea` renders the element as its own root, so `$el` is the
   textarea itself rather than a wrapper to search — unlike the bare `<input>`
   in `OutlineRow`, where the ref is already the element. */
const textarea = () => field.value?.$el ?? null

/*
 * A directive with no catalogue key shows its own name. That is the fallback for
 * one added to `DIRECTIVES` before anyone writes copy for it, and it is
 * deliberately not `t(name)`: `t` throws for a key it does not hold, so asking
 * for copy that was never written would take the whole page down rather than
 * show a plain word.
 */
const nameOf = (item) => (item.label ? t(item.label) : item.name)

/*
 * Insert, then hand the field back.
 *
 * The focus and the caret are the whole point. A button that inserted text and
 * left the caret where the mouse had put it would make a game master click back
 * into the field and hunt for the brackets — which is the work the button was
 * pressed to avoid. `nextTick` because the caret is set on the text the model
 * has not rendered yet.
 */
async function insert(index, item) {
  active.value = index

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

/*
 * One tab stop, not nine.
 *
 * The row sits between the game master and the field, so leaving every button in
 * the tab order would mean nine presses to reach the textarea — the control
 * added to make writing easier would be the thing in the way of it. This is the
 * ARIA toolbar pattern: the group is one stop, and the arrows move within it.
 *
 * The remembered index is what makes it a stop rather than a trap — tabbing away
 * and back returns to the button last used, instead of walking from the start
 * again. Pressing one sets it too, so a game master who clicked `:dice` and tabs
 * back lands on `:dice`.
 */
const KEYS = {
  ArrowRight: (index, count) => (index + 1) % count,
  ArrowLeft: (index, count) => (index - 1 + count) % count,
  Home: () => 0,
  End: (index, count) => count - 1,
}

function move(event) {
  const next = KEYS[event.key]
  if (!next) return

  // Read from the DOM rather than a list of component refs: the buttons are the
  // only children, and this stays right if the markup around them changes.
  const buttons = row.value?.querySelectorAll('button') ?? []
  if (buttons.length === 0) return

  event.preventDefault()

  active.value = next(active.value, buttons.length)
  buttons[active.value].focus()
}
</script>

<template>
  <div class="md-field">
    <!-- Nothing here has an opinion about how many buttons there are.
         `TOOLBAR_ITEMS` is derived from `DIRECTIVES`, so adding `scene` to
         `ENTITY_KINDS` puts a tenth one on screen without this template
         changing. -->
    <div
      ref="row"
      class="md-field__tools"
      role="toolbar"
      :aria-label="t('markdown.toolbar')"
      @keydown="move"
    >
      <Button
        v-for="(item, index) in TOOLBAR_ITEMS"
        :key="item.name"
        type="button"
        size="small"
        severity="secondary"
        text
        class="md-field__tool"
        :icon="`pi ${item.icon}`"
        :label="nameOf(item)"
        :aria-label="t('markdown.insert', { name: nameOf(item) })"
        :tabindex="index === active ? 0 : -1"
        @click="insert(index, item)"
        @focus="active = index"
      />
    </div>

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
 * Wraps rather than scrolls. The row sits above a field whose width is the
 * measure the prose is read at, which is not wide enough for nine buttons on
 * one line at every window — and a control a game master has to scroll sideways
 * to find is barely better than one that was never there.
 */
.md-field__tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-5);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
}

/*
 * Tightened from the default: nine of these at button spacing reads as a row of
 * nine decisions. Closed up, it reads as one palette.
 */
.md-field__tool {
  padding: var(--space-1) var(--space-2);
  font-size: var(--step--1);
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
