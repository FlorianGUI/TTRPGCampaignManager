import { parse } from './parse.js'
import { textOf } from './nodes.js'

/*
 * The third projection: no components, no elements, no syntax. What a body says
 * when it has to fit in a table cell, a `title` attribute, a search result or
 * the page title.
 *
 * This is the mode most easily forgotten and the most visible when missing —
 * the moment descriptions are markdown, every list in the app renders raw
 * `:npc[…]` unless something reduces it. A directive comes out as its label:
 * `:npc[Fen Warden]` is "Fen Warden", never ":npc[Fen Warden]".
 *
 * Unknown directives degrade the same way they do on screen — by keeping the
 * author's words. Here that means the label alone, without the marker: a list
 * cell is the one place where leaking syntax is worse than losing the signal
 * that a directive was misspelled.
 */
export function toPlainText(source) {
  return textOf(parse(source)).replace(/\s+/g, ' ').trim()
}
