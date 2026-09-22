/*
 * What Enter writes when the caret is on a line that carries a marker.
 *
 * A game master writing an inventory should type `- ` once, not eleven times,
 * and a numbered sequence of events should count itself. #157.
 *
 * **A line, not a document.** Everywhere else in this directory the tree is the
 * authority, and here it cannot be: the `>` on a quote's second line is not a
 * node — it sits inside a text node with the words — so mdast has no answer to
 * "what marker is this line carrying". `livePreview.js` reads quote markers off
 * the line for exactly that reason. A prefix is a lexical fact about one line,
 * and reading it there is not a second opinion about the document.
 *
 * The tree would be the wrong instrument even if it could answer: the field
 * re-reads the document after a pause (#153), so the tree it holds is
 * deliberately up to 60ms out of date, and a keystroke cannot wait for it.
 *
 * Pure, and no CodeMirror: `editor.js` binds it. The rule is what is worth
 * testing and it is testable without mounting anything.
 */

/* Indentation, then any number of quote markers. Both are carried across
   verbatim, which is what makes `> - nested in a quote` continue as itself
   rather than as a case anyone had to write down. */
const LEAD = /^(\s*(?:>\s?)*)/

const BULLET = /^([-*+])(\s+)/
const ORDERED = /^(\d+)([.)])(\s+)/

/*
 * The marker on this line, and what the next one would be.
 *
 * `null` where there is nothing to continue — which is most lines, and is the
 * answer that hands Enter back to CodeMirror unchanged.
 */
function markerIn(line) {
  const lead = LEAD.exec(line)[1]
  const rest = line.slice(lead.length)

  const bullet = BULLET.exec(rest)
  if (bullet) return { length: lead.length + bullet[0].length, next: lead + bullet[1] + bullet[2] }

  const ordered = ORDERED.exec(rest)
  if (ordered) {
    return {
      length: lead.length + ordered[0].length,
      // The number a reader would expect next. `10.` after `9.` widens the
      // marker by a character, which is the writer's business and not this
      // function's: what it writes is what they would have typed.
      next: `${lead}${Number(ordered[1]) + 1}${ordered[2]}${ordered[3]}`,
    }
  }

  // A quote with no list inside it. The lead is the whole marker, and an
  // indent on its own is not one — carrying it would make Enter at the end of
  // any indented paragraph behave like a list.
  return lead.trimStart() ? { length: lead.length, next: lead } : null
}

/*
 * What Enter should do on this line, with the caret at this column.
 *
 * Three answers:
 *
 *   null                      not a line with a marker, or the caret is inside
 *                             the marker rather than past it. Ordinary Enter.
 *   { insert }                a newline and the next marker.
 *   { from, to, insert: '' }  the marker had nothing after it, so it is taken
 *                             away instead of repeated — which is how a writer
 *                             gets out of a list without deleting characters
 *                             one at a time. Columns, relative to the line.
 */
export function continuationFor(line, column) {
  const marker = markerIn(line)
  if (!marker || column < marker.length) return null

  /*
   * Empty is judged on the whole line rather than on what is before the caret:
   * the caret is past the marker and there is nothing after it either way, and
   * a writer pressing Enter on `- ` means to stop, wherever in those two
   * characters they happen to be.
   */
  if (!line.slice(marker.length).trim()) return { from: 0, to: line.length, insert: '' }

  return { insert: `\n${marker.next}` }
}

/*
 * The same rule, as the key binding.
 *
 * **No CodeMirror import, and that is not an accident.** A command is a
 * function handed a view and a keymap entry is a plain object, so this module
 * stays free of the editor it is bound into — which is what lets the rule above
 * be tested without one.
 *
 * A selection is left alone deliberately. Enter over a selection replaces it,
 * and continuing a marker while deleting what was under it is two ideas in one
 * keystroke; the ordinary behaviour is the one that will surprise nobody.
 */
export function continueMarker(view) {
  const range = view.state.selection.main

  if (view.state.selection.ranges.length > 1 || !range.empty) return false

  const line = view.state.doc.lineAt(range.head)
  const column = range.head - line.from
  const continuation = continuationFor(line.text, column)

  if (!continuation) return false

  const from = line.from + (continuation.from ?? column)
  const to = line.from + (continuation.to ?? column)

  view.dispatch({
    changes: { from, to, insert: continuation.insert },
    selection: { anchor: from + continuation.insert.length },
    scrollIntoView: true,
    // Grouped with typing rather than standing alone, so undo takes back a
    // continuation and the words around it the way it takes back a sentence.
    userEvent: 'input',
  })

  return true
}

/*
 * Bound ahead of `defaultKeymap` so Enter is offered here first. Every line
 * with no marker on it answers `false`, which hands the key straight back to
 * `insertNewlineAndIndent`, unchanged.
 */
export const continuationKeymap = [{ key: 'Enter', run: continueMarker }]
