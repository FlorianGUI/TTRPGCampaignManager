import { parse } from './parse.js'
import { textOf } from './nodes.js'

/*
 * The third projection: no components, no elements, no syntax. What a body says
 * when it has to fit in a table cell, a `title` attribute, a search result or
 * the page title.
 *
 * This is the mode most easily forgotten and the most visible when missing —
 * the moment descriptions are markdown, every list in the app renders raw
 * `:npc[…]` unless something reduces it. A directive the dialect knows comes
 * out as its label: `:npc[Fen Warden]` is "Fen Warden", never
 * ":npc[Fen Warden]".
 *
 * One that it does not know comes out as `[…]`, and this is the one place the
 * three fallbacks in nodes.js deliberately diverge. On screen a directive
 * nobody recognises is quoted back verbatim, because that is how a writer finds
 * their typo. A list cell cannot do that — leaking `:npx[` into a table is
 * worse than losing the signal — and it must not reduce to the label either,
 * which is what made a broken directive look exactly like a working one
 * everywhere outside the page it was written on. `[…]` refuses that trade
 * rather than picking a side.
 */
export function toPlainText(source) {
  return textOf(parse(source)).replace(/\s+/g, ' ').trim()
}
