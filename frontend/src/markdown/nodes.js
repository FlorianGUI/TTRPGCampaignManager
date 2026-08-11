/*
 * The two facts about an mdast node that both renderers need: whether it takes
 * a line of its own, and what it says with the markup stripped off.
 */

export const DIRECTIVE_MARKER = {
  textDirective: ':',
  leafDirective: '::',
  containerDirective: ':::',
}

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
  if (node.type === 'image') return node.alt ?? ''
  if (node.type === 'break' || node.type === 'thematicBreak') return ' '

  // An unlabelled directive still has a name, and a name is more than nothing:
  // reducing to plain text must not be able to reduce something to silence.
  if (isDirective(node) && (node.children ?? []).length === 0) return node.name

  return joinChildren(node)
}

/*
 * The label a directive hands to its component — the same words, minus that
 * fallback. `:npc` with nothing in brackets is a half-typed directive, and it
 * must not become a chip reading "npc".
 */
export function labelOf(node) {
  return joinChildren(node)
}
