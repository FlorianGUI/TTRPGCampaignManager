<script setup>
/*
 * The dialect, as buttons.
 *
 * #103's complaint in one component: the reading side of this app teaches the
 * dialect and the writing side hid it, so a game master who had watched
 * `:npc[Maerin Holt]` become a chip had nowhere to find out how to make another
 * one. Every directive the renderer implements is on screen here.
 *
 * **It knows nothing about the list it renders.** `TOOLBAR_ITEMS` is derived
 * from `DIRECTIVES`, so this file has no opinion about how many buttons there
 * are or what they are called, and adding `scene` to `ENTITY_KINDS` puts a tenth
 * one here without this template changing.
 *
 * It does not touch the field either. It says which directive was asked for and
 * `MarkdownField` decides what that means for the text — the two are split so
 * the insertion rules can be tested without mounting anything.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import { TOOLBAR_ITEMS } from './toolbar.js'
import { t } from '../i18n/index.js'

const emit = defineEmits(['insert'])

/*
 * One tab stop, not nine.
 *
 * A toolbar sits between the game master and the field, so leaving every button
 * in the tab order would mean nine presses to reach the textarea — the control
 * added to make writing easier would be the thing in the way of it. This is the
 * ARIA toolbar pattern: the group is one stop, and the arrows move within it.
 *
 * The remembered index is what makes it a stop rather than a trap — tabbing away
 * and back returns to the button last used, instead of walking from the start
 * again.
 */
const row = ref(null)
const active = ref(0)

const KEYS = {
  ArrowRight: (index, count) => (index + 1) % count,
  ArrowLeft: (index, count) => (index - 1 + count) % count,
  Home: () => 0,
  End: (index, count) => count - 1,
}

/* Pressing one also makes it the remembered stop, so a game master who clicked
   `:dice` and tabs back lands on `:dice`. */
function press(index, item) {
  active.value = index
  emit('insert', item)
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

/*
 * A directive with no catalogue key shows its own name. That is the fallback for
 * one added to `DIRECTIVES` before anyone writes copy for it, and it is
 * deliberately not `t(name)`: `t` throws for a key it does not hold, so asking
 * for copy that was never written would take the whole page down rather than
 * show a plain word.
 */
const nameOf = (item) => (item.label ? t(item.label) : item.name)
</script>

<template>
  <div
    ref="row"
    class="md-toolbar"
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
      class="md-toolbar__button"
      :icon="`pi ${item.icon}`"
      :label="nameOf(item)"
      :aria-label="t('markdown.insert', { name: nameOf(item) })"
      :tabindex="index === active ? 0 : -1"
      @click="press(index, item)"
      @focus="active = index"
    />
  </div>
</template>

<style scoped>
/*
 * Wraps rather than scrolls. The row sits above a field whose width is the
 * measure the prose is read at, which is not wide enough for nine buttons on
 * one line at every window — and a control a game master has to scroll sideways
 * to find is barely better than one that was never there.
 */
.md-toolbar {
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
.md-toolbar__button {
  padding: var(--space-1) var(--space-2);
  font-size: var(--step--1);
}
</style>
