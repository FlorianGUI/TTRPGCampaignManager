import { DIRECTIVES } from './directives.js'
import { DIRECTIVE_MARKER } from './nodes.js'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'

/*
 * The writing side of the dialect: one button per directive the renderer knows,
 * and the text each one puts into the field.
 *
 * **Derived from `DIRECTIVES`, never transcribed.** The reading side already
 * teaches the dialect — a game master watches `:npc[Maerin Holt]` become a chip
 * and has no way to find out how to make another one (#103). A hand-written list
 * here would close that gap once and reopen it the first time somebody adds a
 * kind, so the list is built from the same table the walker dispatches on.
 * Adding `scene` to `ENTITY_KINDS` is the whole change needed to get a tenth
 * button.
 *
 * Nothing here parses. A button appends characters to a string; the string is
 * what the API stores, byte for byte (#80).
 */

/*
 * What a directive cannot say about itself.
 *
 * `DIRECTIVES` carries what the *renderer* needs — the component, the accepted
 * forms, how props are refused — and none of that is a face or a name. The rest
 * is here, keyed by directive name, and it is presentation only: every entry is
 * optional and a directive with none still gets a working button.
 *
 * That fallback is the point. A directive added to the table tomorrow appears in
 * the toolbar tomorrow, plainly labelled and inserting valid syntax, rather than
 * being silently absent until somebody remembers this file.
 */
const PRESENTATION = {
  dice: { icon: 'pi-bolt', label: 'markdown.directive.dice', attributes: '{result=}' },
  ref: { icon: 'pi-book', label: 'markdown.directive.ref', attributes: '{page=}' },
  'read-aloud': { icon: 'pi-megaphone', label: 'markdown.directive.readAloud' },
}

const FALLBACK_ICON = 'pi-code'

/*
 * Entity kinds are not in `PRESENTATION` and must not be: `ENTITY_KINDS` already
 * pairs each one with an icon and a catalogue key, for the chip. The toolbar
 * reads the same row rather than keeping a second opinion about what an NPC
 * looks like.
 */
function presentationFor(name) {
  const kind = ENTITY_KINDS[name]
  if (kind) return { icon: kind.icon, label: kind.label }

  return PRESENTATION[name] ?? {}
}

/*
 * A container directive opens and closes on lines of its own; an inline one sits
 * in the middle of a sentence. `types` already records which forms the renderer
 * accepts, so the shape of the insertion follows from the table too — using the
 * wrong form is a typo, and a button that typed one would be a strange thing to
 * ship.
 */
function shapeOf(name, spec, presentation) {
  const type = spec.types[0]
  const marker = DIRECTIVE_MARKER[type]

  if (type === 'containerDirective') {
    return { before: `${marker}${name}\n`, after: '\n:::', block: true }
  }

  return { before: `${marker}${name}[`, after: `]${presentation.attributes ?? ''}` }
}

/*
 * The buttons, in the order `DIRECTIVES` declares them — entity kinds first,
 * because that is how the table is built, and they are the ones a game master
 * reaches for most.
 *
 * `label` is a catalogue key or absent; a caller with no key shows the directive
 * name, which is worse copy than a translation and better than a missing one.
 */
export const TOOLBAR_ITEMS = Object.entries(DIRECTIVES).map(([name, spec]) => {
  const presentation = presentationFor(name)

  return {
    name,
    icon: presentation.icon ?? FALLBACK_ICON,
    label: presentation.label ?? null,
    ...shapeOf(name, spec, presentation),
  }
})

/*
 * Where the caret goes once the text is in.
 *
 * With no selection it goes where the label belongs, so the next keystroke is
 * the name — the whole reason to press the button was not remembering the
 * syntax, and landing after the closing bracket would mean typing it out anyway.
 *
 * With a selection the label is already written, so the caret goes to whatever
 * is still blank: the attribute value for `:dice` and `:ref`, and the end for
 * everything else. `{result=}` inserted and abandoned is a refused directive,
 * which the renderer shows as text — honest, and worth steering away from.
 */
function caretAfterSelection(item, start, selection) {
  const end = start + item.before.length + selection.length + item.after.length

  // The attribute stub always ends `=}`, so the value slot is one back from the
  // brace. No stub means nothing left to fill.
  return item.attributes || item.after.endsWith('=}') ? end - 1 : end
}

/*
 * A block directive needs the line to itself. Opening `:::read-aloud` halfway
 * through a paragraph makes it part of that paragraph's text, so the button
 * would produce something that renders as itself — exactly the failure it exists
 * to prevent.
 */
function blockPadding(value, start, end) {
  const startsLine = start === 0 || value[start - 1] === '\n'
  const endsLine = end === value.length || value[end] === '\n'

  return { lead: startsLine ? '' : '\n', trail: endsLine ? '' : '\n' }
}

/*
 * The insertion itself: a string in, a string and a caret out.
 *
 * Kept apart from the component because this is the part with rules in it — what
 * a selection becomes, where the caret lands, whether a block needs a line — and
 * a rule that can be tested without mounting anything is a rule that gets
 * tested.
 */
export function applyInsertion(item, value, selectionStart, selectionEnd) {
  const selection = value.slice(selectionStart, selectionEnd)

  const { lead, trail } = item.block
    ? blockPadding(value, selectionStart, selectionEnd)
    : { lead: '', trail: '' }

  const inserted = `${lead}${item.before}${selection}${item.after}${trail}`
  const next = value.slice(0, selectionStart) + inserted + value.slice(selectionEnd)

  const start = selectionStart + lead.length
  const caret = selection ? caretAfterSelection(item, start, selection) : start + item.before.length

  return { value: next, caret }
}
