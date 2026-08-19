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
  /*
   * Drawn rather than named: PrimeIcons has no die, and the nearest thing in it
   * is a lightning bolt, which says "sudden" and not "roll".
   */
  dice: { drawn: 'die', label: 'markdown.directive.dice', attributes: '{result=}' },
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
 * A face, however it is drawn. An entry that draws its own keeps `icon` empty so
 * nothing tries to render a font glyph on top of it; everything else falls back
 * to a plain one rather than arriving blank.
 */
function faceOf(presentation) {
  if (presentation.drawn) return { drawn: presentation.drawn, icon: null }

  return { icon: presentation.icon ?? FALLBACK_ICON }
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

  const attributes = presentation.attributes ?? ''

  // `fill` is how far back from the end the caret lands when the label is
  // already written — inside `{result=}` rather than after the closing brace.
  return { before: `${marker}${name}[`, after: `]${attributes}`, fill: attributes ? 1 : 0 }
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
    ...faceOf(presentation),
    label: presentation.label ?? null,
    ...shapeOf(name, spec, presentation),
  }
})

/*
 * The directives, split by whether they are one of a set.
 *
 * The six entity kinds are the same button six times — a chip with a different
 * accent — and they are what makes the row long. Behind one door they cost a
 * single slot; the three that are not a set stay out where they can be seen,
 * because `:::read-aloud`, `:dice` and `:ref` are each their own idea and none
 * of them is guessable.
 *
 * **Still derived, both halves.** The split asks `ENTITY_KINDS` whether a name
 * is a kind rather than listing which names are — so adding `scene` there puts
 * it in the menu with no edit here, and a new directive of any other sort
 * appears on the row.
 */
export const ENTITY_ITEMS = TOOLBAR_ITEMS.filter((item) => item.name in ENTITY_KINDS)

/*
 * Read-aloud first: it is the one that changes the page rather than a word in
 * it. Then the two inline marks, in the order a scene tends to want them.
 * A directive this list has never heard of falls in after them rather than
 * being dropped — `sort` is stable, so the table's own order survives.
 */
const MARKER_ORDER = ['read-aloud', 'dice', 'ref']

export const MARKER_ITEMS = TOOLBAR_ITEMS.filter((item) => !(item.name in ENTITY_KINDS)).sort(
  (a, b) => {
    const rank = (item) => {
      const at = MARKER_ORDER.indexOf(item.name)
      return at === -1 ? MARKER_ORDER.length : at
    }

    return rank(a) - rank(b)
  },
)

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

  return end - (item.fill ?? 0)
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
 * The other half of the toolbar: plain CommonMark.
 *
 * **Written out by hand, and that is the difference from the list above.** The
 * directives are generated because `DIRECTIVES` grows; CommonMark is a fixed
 * spec, so a hand-written list cannot go stale against it. What it *can* go
 * stale against is the renderer, which is why every entry here has a case in
 * `render.js` and a test that says so.
 *
 * **Only what renders.** No strikethrough and no table: `parse.js` is
 * `remarkParse` + `remarkDirective` with no `remark-gfm`, so neither parses and
 * both would put literal tildes and pipes on the page. `INLINE_ELEMENTS.delete`
 * exists in `render.js` and is unreachable, which makes strikethrough the
 * convincing one to add by mistake. No image either: `image` parses, but the
 * renderer shows its alt text and nothing else until #29 gives a map somewhere
 * to live. See #144, which may change the first two.
 *
 * **Icons, with the name in a tooltip**, and grouped the way an editor toolbar
 * usually is — character marks, then block marks, then the things that insert
 * something.
 *
 * PrimeIcons has no bold, italic, heading or quote glyph, so those four carry a
 * letterform instead: a bold `B`, a slanted `I`, an `H`, a quote mark. That is
 * not a fallback so much as the convention — the mark in an editor's bold button
 * is a `B` whatever the interface language, and it is read as a symbol rather
 * than as the first letter of an English word. The tooltip and the `aria-label`
 * carry the translated name.
 */
export const COMMONMARK_ITEMS = [
  {
    name: 'bold',
    group: 'mark',
    glyph: 'B',
    label: 'markdown.commonmark.bold',
    before: '**',
    after: '**',
  },
  {
    name: 'italic',
    group: 'mark',
    glyph: 'I',
    label: 'markdown.commonmark.italic',
    before: '*',
    after: '*',
  },
  {
    name: 'code',
    group: 'mark',
    icon: 'pi-code',
    label: 'markdown.commonmark.code',
    before: '`',
    after: '`',
  },
  /*
   * `##`, not `#`. Every page that shows a body already carries the title as its
   * `h1`, so a level-one heading in the prose would be a second one — and
   * `render.js` maps depth straight onto the tag. Deeper levels are a matter of
   * typing another `#`, which is visible the moment this button has been pressed
   * once; a level picker was the alternative and is more machinery than one row
   * of a toolbar should need.
   */
  {
    name: 'heading',
    group: 'block',
    glyph: 'H',
    label: 'markdown.commonmark.heading',
    prefix: '## ',
  },
  {
    name: 'bullet',
    group: 'block',
    icon: 'pi-list',
    label: 'markdown.commonmark.bullet',
    prefix: '- ',
  },
  /*
   * `1.` on every line rather than counting up. CommonMark numbers an ordered
   * list from its first item and ignores the rest, so this renders 1, 2, 3 — and
   * a list whose source does not have to be renumbered when a line moves is the
   * one that survives editing.
   */
  {
    name: 'ordered',
    group: 'block',
    icon: 'pi-sort-numeric-down',
    label: 'markdown.commonmark.ordered',
    prefix: '1. ',
  },
  { name: 'quote', group: 'block', glyph: '“', label: 'markdown.commonmark.quote', prefix: '> ' },
  {
    name: 'codeBlock',
    group: 'insert',
    icon: 'pi-align-justify',
    label: 'markdown.commonmark.codeBlock',
    before: '```\n',
    after: '\n```',
    block: true,
  },
  {
    name: 'rule',
    group: 'insert',
    icon: 'pi-minus',
    label: 'markdown.commonmark.rule',
    before: '---',
    after: '',
    block: true,
    standalone: true,
  },
  /*
   * Seeded with the scheme rather than an empty `()`. `safeUrl` in `render.js`
   * accepts `http`, `https` and `mailto` and renders anything else as its own
   * text, so a button offering a blank slot would be offering a way to write a
   * link that silently un-links itself.
   */
  {
    name: 'link',
    group: 'insert',
    icon: 'pi-link',
    label: 'markdown.commonmark.link',
    before: '[',
    after: '](https://)',
    fill: 1,
  },
]

/* The lines a selection touches, whole — a prefix applies to a line, and half a
   line is not one. */
function lineSpan(value, selectionStart, selectionEnd) {
  const start = value.lastIndexOf('\n', selectionStart - 1) + 1
  const ending = value.indexOf('\n', selectionEnd)
  const end = ending === -1 ? value.length : ending

  return { start, end }
}

/*
 * A prefix marks a line, so pressing the button acts on lines rather than on
 * whatever happened to be selected — a heading whose `##` landed mid-sentence
 * would render as text, the same failure the block directives avoid.
 *
 * It toggles. Applying `- ` to a list that is already a list should give the
 * game master their paragraph back, not `- - `, and a button whose only
 * direction is on is a button that has to be undone by hand.
 */
function applyLinePrefix(item, value, selectionStart, selectionEnd) {
  const { start, end } = lineSpan(value, selectionStart, selectionEnd)
  const lines = value.slice(start, end).split('\n')

  const marked = lines.every((line) => line.startsWith(item.prefix))
  const next = lines
    .map((line) => (marked ? line.slice(item.prefix.length) : `${item.prefix}${line}`))
    .join('\n')

  /*
   * Follow the caret rather than reselecting: the words did not move relative to
   * their own line, only every line's start did. So the shift is one prefix per
   * line at or above the caret — counting only the first would leave the caret
   * drifting further back the more lines were marked.
   */
  const above = value.slice(start, selectionEnd).split('\n').length
  const shift = (marked ? -1 : 1) * item.prefix.length * above

  return {
    value: value.slice(0, start) + next + value.slice(end),
    caret: Math.max(start, selectionEnd + shift),
  }
}

/*
 * A rule separates; it has nothing to say about the words that were selected.
 * Wrapping them in `---` would both destroy the selection and write something
 * that is not a thematic break.
 *
 * **It needs a blank line above it, not just a line of its own.** `---` on the
 * line directly under a paragraph is a setext heading in CommonMark: it turns
 * the paragraph above into an `<h2>` and draws no rule at all. That is the
 * nastiest thing this button could do, because the failure lands on the
 * *previous* sentence rather than where it was pressed.
 */
function blankLineBefore(value, at) {
  if (at === 0) return ''
  if (value[at - 1] !== '\n') return '\n\n'

  return at >= 2 && value[at - 2] === '\n' ? '' : '\n'
}

/*
 * The same count from the other side, so a rule dropped between two paragraphs
 * adds the two newlines it needs and not the four it would take to spell them
 * out twice.
 *
 * `skip` is how many of those newlines were already there. The caret has to step
 * over them to land at the start of the next paragraph rather than in the middle
 * of the blank line — where the writer's first keystroke would close the gap the
 * rule needs.
 */
function blankLineAfter(value, at) {
  if (at === value.length) return { trail: '\n', skip: 0 }
  if (value[at] !== '\n') return { trail: '\n\n', skip: 0 }

  return value[at + 1] === '\n' ? { trail: '', skip: 2 } : { trail: '\n', skip: 1 }
}

function applyStandalone(item, value, selectionEnd) {
  const lead = blankLineBefore(value, selectionEnd)
  const { trail, skip } = blankLineAfter(value, selectionEnd)
  const inserted = `${lead}${item.before}${trail}`

  return {
    value: value.slice(0, selectionEnd) + inserted + value.slice(selectionEnd),
    caret: selectionEnd + inserted.length + skip,
  }
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
  if (item.prefix) return applyLinePrefix(item, value, selectionStart, selectionEnd)
  if (item.standalone) return applyStandalone(item, value, selectionEnd)

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
