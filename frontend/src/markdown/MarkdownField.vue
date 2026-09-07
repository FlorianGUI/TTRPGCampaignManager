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
 * **It is a string and nothing more.** No rich-text model, no transformation on
 * the way in or out: the buttons put characters into a string and the string is
 * what the API stores, byte for byte (#80). That is also why the source is
 * written and read at the same measure — what a game master types here wraps the
 * way it will wrap when they read it back at the table.
 *
 * **The surface is a CodeMirror view rather than a `<textarea>`** since #152,
 * and the reason is narrow: a textarea renders one text style for its whole
 * value, so the bold word and the chip #142 asks for are not awkward on one but
 * impossible. Nothing is drawn on it yet — #153 and #154 add the decorations.
 * What CodeMirror is here for is that it styles ranges and still hands back
 * plain offsets into the same string, which is why `applyInsertion` below did
 * not have to change; and that it builds DOM nodes rather than markup, so the
 * guarantee the README states as a fact about the dependency list survives the
 * writing side gaining a renderer of its own.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Popover from 'primevue/popover'
import { Compartment, EditorState } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
import {
  COLOR_ITEM,
  COLOR_ITEMS,
  COMMONMARK_ITEMS,
  ENTITY_ITEMS,
  MARKER_ITEMS,
  applyInsertion,
  narrowedTo,
} from './toolbar.js'
import { t } from '../i18n/index.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: [Number, String], default: 12 },
  ariaLabel: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])

const host = ref(null)
const row = ref(null)
/* Which button the single tab stop lands on — see the note above `move`. */
const active = ref(0)

/*
 * Not a `ref`. The view is not state the template reads, and making it reactive
 * would have Vue walk a document, a selection and a DOM tree on every keystroke
 * to find out that nothing rendered here depends on any of it.
 */
let view = null

/*
 * The label is the one extension that can change after the view is built, so it
 * is the one that needs a compartment. `t()` is not reactive (#87 decides the
 * locale before mount and there is no switcher), but the prop is a prop and a
 * parent is free to change it.
 */
const label = new Compartment()

const contentAttributes = () => EditorView.contentAttributes.of({ 'aria-label': props.ariaLabel })

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        /*
         * A textarea's undo is the browser's and comes free. CodeMirror's does
         * not, and a field that silently stopped answering ⌘Z would be a poor
         * trade for a bold word.
         */
        history(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        /*
         * Tab is deliberately unbound — `defaultKeymap` leaves it alone, so it
         * moves focus the way it did out of the textarea. The toolbar spent #146
         * getting the tab order down to one stop; a field that swallowed Tab
         * would be a trap at the end of it.
         */
        EditorView.lineWrapping,
        label.of(contentAttributes()),
        /*
         * The single place the model is told anything. Every write — typing, a
         * paste, a toolbar press — is a transaction, so raising the event from
         * here rather than from each of them is what makes "byte for byte" one
         * claim instead of three.
         */
        EditorView.updateListener.of((update) => {
          if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
        }),
      ],
    }),
  })
})

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})

watch(
  () => props.ariaLabel,
  () => view?.dispatch({ effects: label.reconfigure(contentAttributes()) }),
)

/*
 * The parent's half of `v-model`, and it has to be able to tell its own echo
 * from a genuine change. Every keystroke emits, the parent writes the value
 * back, and dispatching that identical string again would reset the selection
 * to the start of the document on every character typed.
 */
watch(
  () => props.modelValue,
  (next) => {
    const current = view?.state.doc.toString()
    if (current === undefined || next === current) return

    view.dispatch({ changes: narrowedTo(current, next) })
  },
)

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
 * The second door, and the toolbar's first `Popover`.
 *
 * A palette is a grid — seven hues across, three tiers down — and `Menu` is a
 * vertical list. Twenty-one swatches in a column would be a scroll, and the
 * thing a picker has to do is let the eye compare two hues side by side.
 *
 * The row could not hold them any other way: #146 cut this toolbar down to one
 * tier of icons precisely so it would stop being a wall, and twenty-one more
 * controls would have undone that in a single feature.
 */
const palette = ref(null)

/*
 * One roving index across everything, so the arrows walk the whole toolbar and
 * the tab order still sees a single stop. The two doors are the last of them and
 * each hands its own keyboard over once open.
 */
const PLAIN_AT = 0
const MARKER_AT = COMMONMARK_ITEMS.length
const PALETTE_INDEX = MARKER_AT + MARKER_ITEMS.length
const MENU_INDEX = PALETTE_INDEX + 1

/*
 * Hue *and* tier, both from the catalogue.
 *
 * A grid of twenty-one unlabelled colour squares is unusable without sight, and
 * a tooltip reading only "wyrd" is unusable with it — three of the swatches are
 * wyrd. `nameOf` cannot do this: every swatch inherits the same `label` from the
 * `color` directive, and the pair is what names the button. #87 is why both
 * halves are keys rather than words.
 */
const swatchName = (item) => `${t(item.hueLabel)} ${t(item.tierLabel)}`

/* Counted, not written: the grid is as wide as the palette has hues. */
const HUE_COUNT = new Set(COLOR_ITEMS.map((item) => item.hue)).size

/*
 * Close first, then insert.
 *
 * `Popover.hide()` only lowers a flag — it does not restore focus to the
 * trigger, and the focus trap unbinds without reaching for anything — so the
 * field `insert` focuses keeps it. Closing after would race that.
 */
function pick(item) {
  palette.value.hide()

  return insert(PALETTE_INDEX, item)
}

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
 * pressed to avoid.
 *
 * **One transaction, carrying both the text and the caret.** That is what makes
 * a press one step to undo rather than two, and it is why nothing here has to
 * wait a tick: the document and the selection land together, and the model hears
 * about it from the update listener like every other write.
 *
 * `narrowedTo` is what stands between the string `applyInsertion` returns and
 * the change the editor records. Handing over the whole document works and
 * misbehaves afterwards — undo and redo would restore a selection spanning the
 * scene — so the press is dispatched as the span that actually differs.
 */
function insert(index, item) {
  active.value = index

  if (!view) return

  const source = view.state.doc.toString()
  const { from, to } = view.state.selection.main
  const { value, caret } = applyInsertion(item, source, from, to)

  view.dispatch({ changes: narrowedTo(source, value), selection: { anchor: caret } })

  view.focus()
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

        <!-- A glyph rather than an icon, and the convention every editor uses:
             a letterform over a bar carrying the colour. PrimeIcons has a
             palette glyph, and it would say "choose a colour" where this says
             "colour these words". -->
        <Button
          v-tooltip.bottom="{ value: nameOf(COLOR_ITEM), showOnFocus: true }"
          type="button"
          size="small"
          severity="secondary"
          text
          class="md-field__tool"
          :aria-label="nameOf(COLOR_ITEM)"
          aria-haspopup="true"
          :tabindex="PALETTE_INDEX === active ? 0 : -1"
          @click="palette.toggle($event)"
          @focus="active = PALETTE_INDEX"
        >
          <span class="md-field__ink" aria-hidden="true">
            <span class="md-field__ink-letter">A</span>
            <span class="md-field__ink-bar" />
          </span>
        </Button>

        <!-- Seven across and three down, both counted off the palette rather
             than written here: an eighth hue widens the grid on its own. -->
        <Popover ref="palette">
          <div
            class="md-palette"
            role="group"
            :aria-label="nameOf(COLOR_ITEM)"
            :style="{ '--palette-columns': HUE_COUNT }"
          >
            <button
              v-for="item in COLOR_ITEMS"
              :key="item.name"
              v-tooltip.bottom="{ value: swatchName(item), showOnFocus: true }"
              type="button"
              class="md-palette__swatch"
              :class="item.class"
              :aria-label="t('markdown.insert', { name: swatchName(item) })"
              @click="pick(item)"
            />
          </div>
        </Popover>

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

    <!-- The view is built into this element on mount, so there is nothing to
         render here. `rows` survives the move as a custom property: the
         textarea took a line count, and the height that used to come from the
         attribute is now the same count times the line height, which keeps both
         callers looking as they did. -->
    <div ref="host" class="md-field__area" :style="{ '--md-rows': rows }" />

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
 * The colour door: an `A` with a bar under it.
 *
 * Stacked rather than side by side, because the bar is standing in for the ink
 * the letter would be written in — that is what makes it read as *colour these
 * words* rather than as a swatch that happens to sit next to a letter.
 *
 * The bar shows no hue of its own. A picker button that previewed one would be
 * claiming a current colour, and there is none: every press opens the grid.
 */
.md-field__ink {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.12em;
  line-height: 1;
}

.md-field__ink-letter {
  font-family: var(--grimoire-font-display);
  font-size: 1.05em;
  font-weight: 700;
  line-height: 1;
}

.md-field__ink-bar {
  width: 1em;
  height: 0.2em;
  border-radius: var(--p-border-radius-xs);
  background: currentcolor;
}

/*
 * The palette: a hue per column, a tier per row.
 *
 * Reading down a column is comparing one hue's three weights; reading across a
 * row is comparing seven hues at the same weight. Both are things a game master
 * actually does, and neither is possible in a list — which is why this is the
 * toolbar's one `Popover` and not a second `Menu`.
 */
.md-palette {
  display: grid;
  grid-template-columns: repeat(var(--palette-columns), 1fr);
  gap: var(--space-1);
}

/*
 * Square, and big enough to hit. 1.75rem clears nothing like the 44px touch
 * floor the app holds elsewhere — but that floor is for controls a thumb has to
 * find on a page, and this is a grid opened deliberately, where the density is
 * what makes the comparison possible at all.
 *
 * The colour comes from `--prose-color`, set by the same twenty-one rules in
 * `base.css` that paint the rendered span. So a swatch cannot show one thing and
 * write another.
 */
.md-palette__swatch {
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-xs);
  background: var(--prose-color);
  cursor: pointer;
}

.md-palette__swatch:hover {
  border-color: var(--p-text-color);
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
}

/*
 * The field's own chrome, written out because the element that carried it is
 * gone.
 *
 * These are `.p-inputtext`'s rules, reading the tokens `.p-inputtext` reads
 * them *from* — `--p-form-field-*`, the semantic layer, rather than the
 * `--p-inputtext-*` a component emits. That is not a preference: PrimeVue
 * registers a component's tokens the first time one of its components is
 * mounted, so a field on a page with no other input would have resolved every
 * one of them to nothing and drawn no border at all. Reading the layer above is
 * what makes the field's appearance a fact about the theme rather than about
 * what else happens to be on screen.
 *
 * `:deep` throughout: CodeMirror builds its own DOM imperatively, so none of it
 * carries this component's scope attribute. The host element does, which is
 * what keeps these rules from reaching any other editor on the page.
 */
.md-field__area :deep(.cm-editor) {
  background: var(--p-form-field-background);
  color: var(--p-form-field-color);
  border: 1px solid var(--p-form-field-border-color);
  border-radius: var(--p-form-field-border-radius);
  box-shadow: var(--p-form-field-shadow);
  transition:
    background var(--p-form-field-transition-duration),
    color var(--p-form-field-transition-duration),
    border-color var(--p-form-field-transition-duration),
    outline-color var(--p-form-field-transition-duration),
    box-shadow var(--p-form-field-transition-duration);
}

.md-field__area :deep(.cm-editor:hover) {
  border-color: var(--p-form-field-hover-border-color);
}

/*
 * Focus is the border going gold, which is how every other field on the page
 * shows it — the ring under it is transparent by design, and kept because it is
 * the one thing a forced-colours mode has to draw.
 *
 * CodeMirror's own focused state is a dotted outline in a hardcoded near-black:
 * a foreign object on parchment and invisible on candlelight. Replaced here
 * rather than added to.
 */
.md-field__area :deep(.cm-editor.cm-focused) {
  border-color: var(--p-form-field-focus-border-color);
  box-shadow: var(--p-form-field-focus-ring-shadow);
  outline: var(--p-form-field-focus-ring-width) var(--p-form-field-focus-ring-style)
    var(--p-form-field-focus-ring-color);
  outline-offset: var(--p-form-field-focus-ring-offset);
}

/*
 * The writing surface itself. `--md-rows` is the `rows` the view asked for, and
 * a minimum rather than a height: the field grew with its content as a textarea
 * only when dragged, and growing on its own is the better half of the trade —
 * what a game master is writing stays on screen.
 */
.md-field__area :deep(.cm-content) {
  min-height: calc(var(--md-rows) * 1.6em);
  padding: var(--p-form-field-padding-y) var(--p-form-field-padding-x);
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--1);
  line-height: 1.6;
  /* The caret is drawn by the browser rather than by CodeMirror — no
     `drawSelection`, so the native selection and cursor are what appear, and
     both follow the text colour into the dark scheme on their own. */
  caret-color: var(--p-form-field-color);
}

/* CodeMirror indents every line by a few pixels of its own; the padding above
   is the field's, and two of them read as a wobble at the start of the measure. */
.md-field__area :deep(.cm-line) {
  padding: 0;
}

/* Wrapping, not scrolling: a horizontal scrollbar under a column of prose set
   at the measure it is read at would be a regression on its own. */
.md-field__area :deep(.cm-scroller) {
  font-family: inherit;
  line-height: inherit;
  overflow-x: hidden;
}

.md-field__hint {
  margin: var(--space-2) 0 0;
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
}
</style>
