import { propsFor } from './dialect.js'

/*
 * The facts about an mdast node that every projection needs: whether it takes a
 * line of its own, what it says with the markup stripped off, and — when it
 * cannot be shown as it was written — which of three things to do instead.
 *
 * # The three fallbacks
 *
 * Every projection (`block`, `inline`, `toPlainText`) meets nodes it cannot
 * draw. What it does then is one of exactly three things, and naming them here
 * is what stops each projection inventing its own answer:
 *
 *   Interpreted  a faithful narrowing exists, so take it and add nothing. A
 *                directive's label, a link's text, an image's alt, a code
 *                block's value. `:npc[Fen Warden]` is "Fen Warden" in a list
 *                cell. Information is narrowed, not lost, and a marker would
 *                be noise.
 *
 *   Skipped      the node is recognised and there is nothing left once the
 *                projection drops what it cannot draw — an image with no alt.
 *                It reduces to ELISION, which says *there was something here*
 *                so a cell reads as a summary rather than as the whole truth.
 *
 *   Ignored      the node matched no known pattern: a typo, a wrong form, a
 *                note written against a newer dialect, a raw <script>. The
 *                walker does not act on it and the author's own text stands,
 *                byte for byte. This is the only case that needs the source.
 *
 * The line between the first two is "is there anything left after the
 * narrowing?" — not "did we lose something", because narrowing always loses
 * something. The line before the third is whether the dialect recognised it at
 * all.
 *
 * # Where the projections deliberately differ
 *
 * Ignored shows the source in `block` and `inline`, and ELISION in
 * `toPlainText`. A list cell is the one place where leaking `:npc[` is worse
 * than losing the signal, and ELISION is what lets that trade be refused
 * rather than picked: no syntax on screen, and no pretending the cell is
 * complete. This is a decision, not a divergence to tidy up later.
 */

export const DIRECTIVE_MARKER = {
  textDirective: ':',
  leafDirective: '::',
  containerDirective: ':::',
}

/*
 * The mark left where something was dropped. One definition, because a cell
 * reading `[…]` and a cell reading `(...)` would look like two different bugs.
 */
export const ELISION = '[…]'

const BLOCK_TYPES = new Set([
  'paragraph',
  'heading',
  'blockquote',
  'list',
  'listItem',
  'code',
  'thematicBreak',
  'leafDirective',
  'containerDirective',
])

export function isDirective(node) {
  return node.type in DIRECTIVE_MARKER
}

export function isBlock(node) {
  return BLOCK_TYPES.has(node.type)
}

/*
 * A container carries its `[label]` as a first child flagged by the parser,
 * sitting on the opening line rather than in the body. Anything that quotes
 * that line back has already shown those words and must not show them twice.
 */
export function isDirectiveLabel(node) {
  return node.data?.directiveLabel === true
}

/*
 * Whether the dialect accepts this directive as written — name, form and
 * attributes together. The one question that separates Interpreted from
 * Ignored, asked from `render.js` and from `textOf` so that the page and the
 * list cell can never disagree about which fallback applies.
 */
export function isRecognised(node) {
  return propsFor(node, labelOf(node)) !== null
}

function joinChildren(node) {
  return (node.children ?? [])
    .map((child, index) => (index > 0 && isBlock(child) ? ` ${textOf(child)}` : textOf(child)))
    .join('')
}

/*
 * The words in a node, with everything else discarded — a link's text, an
 * image's alt, a directive's label. What the plain-text projection is built on.
 */
export function textOf(node) {
  if (node.type === 'text' || node.type === 'html' || node.type === 'inlineCode') return node.value
  if (node.type === 'code') return node.value
  if (node.type === 'break' || node.type === 'thematicBreak') return ' '

  // Skipped: an image is its alt here and until #29 gives assets somewhere to
  // live. With no alt there is nothing to narrow to — and never the URL, which
  // is a file path wearing the clothes of a sentence.
  if (node.type === 'image') return node.alt || ELISION

  /*
   * Ignored, projected — and projected the same way whatever form the directive
   * took. What a directive nobody recognises contains is an argument to
   * something we cannot read: printing it as prose is what made
   * `:npx[Fen Warden]` indistinguishable from a chip that worked in every list,
   * title and search result in the app, and the body of an unreadable block is
   * no more trustworthy than the label of an unreadable span.
   *
   * A container tempts an exception here, since its children look like ordinary
   * blocks that merely got wrapped. Taking it would mean the same source
   * degrading two ways depending on the marker that failed, which is exactly
   * the per-node inventiveness these three cases exist to end. The page still
   * shows all of it, byte for byte, which is where an author finds their typo.
   */
  if (isDirective(node) && !isRecognised(node)) return ELISION

  return joinChildren(node)
}

/*
 * The label a directive hands to its component — the same words, minus the
 * fallbacks above. `:npc` with nothing in brackets comes back empty rather than
 * as an elision or as the directive name, because a refusal is what should
 * follow and both of those would become a chip.
 */
export function labelOf(node) {
  return joinChildren(node)
}
