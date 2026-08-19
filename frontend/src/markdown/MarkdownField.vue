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
import { computed, nextTick, ref } from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Textarea from 'primevue/textarea'
import { COMMONMARK_ITEMS, ENTITY_ITEMS, MARKER_ITEMS, applyInsertion } from './toolbar.js'
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
 * Nineteen controls above a field was a wall. What shortened it was noticing
 * which of them are the same button repeated.
 *
 * **Left: the plain marks**, laid out one per control the way a writing toolbar
 * always has. They are words rather than icons because PrimeIcons has no bold,
 * italic, heading or quote glyph, and the single-letter conventions are
 * language-bound — French marks bold `G` for *gras*.
 *
 * **Right: the dialect's own.** `:::read-aloud`, `:dice` and `:ref` keep their
 * places: each is its own idea, none is guessable, and #103 exists because a
 * game master has no way to find them. The six entity kinds are one idea with
 * six accents, so they go behind a single door at the end — the length of that
 * run was the problem, and a menu is where a set belongs.
 *
 * `Menu` popup is the control `MoveControl` and `ChromeActions` already use.
 */
const menu = ref(null)

/*
 * One roving index across everything, so the arrows walk the whole toolbar and
 * the tab order still sees a single stop. The menu button is the last of them
 * and hands its own keyboard over once open.
 */
const PLAIN_AT = 0
const MARKER_AT = COMMONMARK_ITEMS.length
const MENU_INDEX = MARKER_AT + MARKER_ITEMS.length

/*
 * The plain marks in runs, with a rule between them — character marks, block
 * marks, then the things that insert something. Ten identical icons in an
 * unbroken line is the shape that made the row unreadable; the grouping is what
 * lets the eye find bold without counting.
 *
 * Built from the items' own `group` rather than sliced by index, so reordering
 * the list or adding a mark cannot silently put a separator in the wrong place.
 */
const PLAIN_GROUPS = COMMONMARK_ITEMS.reduce((groups, item, index) => {
  const last = groups.at(-1)

  if (last && last.group === item.group) last.items.push({ item, index })
  else groups.push({ group: item.group, items: [{ item, index }] })

  return groups
}, [])

const entityItems = computed(() =>
  ENTITY_ITEMS.map((item) => ({
    label: nameOf(item),
    icon: `pi ${item.icon}`,
    command: () => insert(MENU_INDEX, item),
  })),
)

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
      <template v-for="(group, at) in PLAIN_GROUPS" :key="group.group">
        <span v-if="at > 0" class="md-field__rule" aria-hidden="true" />

        <Button
          v-for="entry in group.items"
          :key="entry.item.name"
          v-tooltip.bottom="{ value: nameOf(entry.item), showOnFocus: true }"
          type="button"
          size="small"
          severity="secondary"
          text
          class="md-field__tool md-field__tool--plain"
          :aria-label="t('markdown.insert', { name: nameOf(entry.item) })"
          :tabindex="PLAIN_AT + entry.index === active ? 0 : -1"
          @click="insert(PLAIN_AT + entry.index, entry.item)"
          @focus="active = PLAIN_AT + entry.index"
        >
          <i v-if="entry.item.icon" class="pi" :class="entry.item.icon" aria-hidden="true" />
          <span v-else class="md-field__glyph" :class="`md-field__glyph--${entry.item.name}`">{{
            entry.item.glyph
          }}</span>
        </Button>
      </template>

      <span class="md-field__custom">
        <Button
          v-for="(item, index) in MARKER_ITEMS"
          :key="item.name"
          v-tooltip.bottom="{ value: nameOf(item), showOnFocus: true }"
          type="button"
          size="small"
          severity="secondary"
          text
          class="md-field__tool"
          :aria-label="t('markdown.insert', { name: nameOf(item) })"
          :tabindex="MARKER_AT + index === active ? 0 : -1"
          @click="insert(MARKER_AT + index, item)"
          @focus="active = MARKER_AT + index"
        >
          <i v-if="item.icon" class="pi" :class="item.icon" aria-hidden="true" />

          <!-- A die, because PrimeIcons has none and the nearest thing in it is
               a lightning bolt — which says "sudden", not "roll". Stroked in
               `currentColor` so it takes the button's states along with the font
               icons beside it, and hidden from the accessibility tree because
               the button is already named. -->
          <svg
            v-else-if="item.drawn === 'die'"
            class="md-field__die"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            aria-hidden="true"
          >
            <!-- Drawn to the edge of the viewBox, inset only by half the
                 stroke so it is not clipped. Sitting at 3.5 with a 24 box left
                 the die a third smaller than the font icons beside it, which
                 carry their own bearing already. -->
            <rect x="0.9" y="0.9" width="22.2" height="22.2" rx="4.6" />
            <g fill="currentColor" stroke="none">
              <circle cx="7.4" cy="7.4" r="2.05" />
              <circle cx="16.6" cy="7.4" r="2.05" />
              <circle cx="12" cy="12" r="2.05" />
              <circle cx="7.4" cy="16.6" r="2.05" />
              <circle cx="16.6" cy="16.6" r="2.05" />
            </g>
          </svg>
        </Button>

        <Button
          type="button"
          size="small"
          severity="secondary"
          text
          class="md-field__tool"
          icon="pi pi-angle-down"
          icon-pos="right"
          :label="t('markdown.entity')"
          :aria-label="t('markdown.entity')"
          aria-haspopup="true"
          :tabindex="MENU_INDEX === active ? 0 : -1"
          @click="menu.toggle($event)"
          @focus="active = MENU_INDEX"
        />
        <Menu ref="menu" :model="entityItems" popup />
      </span>
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
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-5);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
}

.md-field__tool {
  padding: var(--space-1) var(--space-2);
  font-size: var(--step--1);
}

/*
 * The plain marks are the quieter half: muted, so the eye reaches the dialect's
 * own controls on the right first. They are the ones a game master would have
 * found without help.
 */
.md-field__tool--plain {
  color: var(--p-text-muted-color);
}

/*
 * A hairline between runs, the way an editor toolbar has always separated
 * character marks from block ones. Rules are how this design system makes a
 * division — there is no elevation scale to reach for — and ten identical icons
 * in an unbroken line was the shape that made the row unreadable.
 */
.md-field__rule {
  align-self: stretch;
  width: 1px;
  margin: var(--space-1) var(--space-1);
  background: var(--p-content-border-color);
}

/*
 * The four marks PrimeIcons has no glyph for. A letterform rather than a
 * picture, which is the convention rather than a compromise: the mark on an
 * editor's bold button is a `B` whatever language the interface speaks, read as
 * a symbol and not as the first letter of a word. The name is in the tooltip.
 *
 * Set in the display face so it reads as drawn rather than typed, and sized to
 * sit on the same optical line as the `pi` icons beside it.
 */
.md-field__glyph {
  display: inline-block;
  min-width: 1em;
  font-family: var(--grimoire-font-display);
  font-size: 1.05em;
  line-height: 1;
  text-align: center;
}

.md-field__glyph--bold {
  font-weight: 700;
}

.md-field__glyph--italic {
  font-style: italic;
}

/*
 * `rem`, not `em`, because that is the unit PrimeIcons sizes itself in: `.pi`
 * sets `font-size: 1rem` and so draws at 16px regardless of the button's own
 * 14px text. Matching in `em` made the die 14px and visibly the odd one out.
 */
.md-field__die {
  width: 1rem;
  height: 1rem;
}

/* The quote mark hangs high in the face; nudged down to sit level with the row
   rather than floating above it. */
.md-field__glyph--quote {
  font-size: 1.5em;
  /* The mark is drawn against the cap line, so it needs pushing down almost a
     third of its own height to sit level with the icons beside it. */
  transform: translateY(0.22em);
}

/*
 * Pushed to the far end and kept together, so the two groups read as two
 * vocabularies rather than one long run. `margin-left: auto` rather than a
 * separator: depth here comes from space and rules, and the row already sits on
 * one.
 */
.md-field__custom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  margin-left: auto;
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
