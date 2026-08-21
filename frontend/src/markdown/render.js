import { h, Fragment } from 'vue'
import { specFor } from './dialect.js'
import { DIRECTIVE_COMPONENTS } from './directives.js'
import {
  DIRECTIVE_MARKER,
  ELISION,
  isBlock,
  isDirective,
  isDirectiveLabel,
  labelOf,
} from './nodes.js'

/*
 * mdast → vnodes. No HTML string is built anywhere in here, so there is nothing
 * to sanitise: a raw-HTML node in the source is a string handed to Vue as text,
 * which is the only thing text can be.
 *
 * Two modes, one walker:
 *
 *   block   the full document — headings, paragraphs, read-aloud boxes. Session
 *           notes and scenes.
 *   inline  inline directives still become components; block-level constructs
 *           flatten to their words. Descriptions, which are shown in places
 *           that have no room for a boxed paragraph.
 *
 * For the third projection — no components at all, for list cells and page
 * titles — see toPlainText.js. The three fallbacks all three of them share are
 * written down in nodes.js; both modes here take the Ignored case as *the
 * source*, which is why the walker carries the source text alongside the tree.
 */

export const MODES = ['block', 'inline']

const INLINE_ELEMENTS = {
  emphasis: 'em',
  strong: 'strong',
  delete: 'del',
}

const BLOCK_ELEMENTS = {
  paragraph: () => 'p',
  heading: (node) => `h${Math.min(node.depth ?? 1, 6)}`,
  blockquote: () => 'blockquote',
  list: (node) => (node.ordered ? 'ol' : 'ul'),
  listItem: () => 'li',
}

/*
 * Dropping v-html closes the injection hole that involves markup. It does not
 * close this one: `[click me](javascript:alert(document.cookie))` is an
 * ordinary markdown link, and `h('a', { href })` will happily fire it.
 *
 * So the scheme is whitelisted, and a link that fails renders as its own text.
 * Control characters and spaces are stripped before the test because browsers
 * strip them before following the URL — `java\tscript:` is a working scheme to
 * everyone except a naive regex.
 */
const HAS_SCHEME = /^[a-z][a-z0-9+.-]*:/i
const SAFE_SCHEME = /^(?:https?|mailto):/i

function safeUrl(url) {
  // eslint-disable-next-line no-control-regex
  const cleaned = String(url ?? '').replace(/[\u0000-\u0020]/g, '')
  if (!HAS_SCHEME.test(cleaned)) return cleaned // relative, fragment, protocol-relative
  return SAFE_SCHEME.test(cleaned) ? cleaned : null
}

function renderChildren(node, mode, source) {
  const children = node.children ?? []

  return children.flatMap((child, index) =>
    // Flattened blocks would otherwise run their last word into the next one's
    // first.
    index > 0 && mode === 'inline' && isBlock(child)
      ? [' ', renderNode(child, mode, source)]
      : [renderNode(child, mode, source)],
  )
}

/*
 * The author's own bytes, taken from the source by the offsets the parser
 * recorded.
 *
 * The fallback used to rebuild the directive from the tree, and the tree has
 * already thrown away how the attributes were written: `{label="the old man"}`
 * came back as `{label=the old man}`, which is not merely different but invalid
 * — an unquoted value ends at the first space, so a writer who copied the
 * fallback back into the field got a directive broken in a new way. `{flag}`
 * and `{empty=""}` parse to the same tree, so no reconstruction could have told
 * them apart either.
 *
 * Slicing is faithful by construction: no escaping rules to get right, and
 * nothing to keep in step as the dialect grows.
 */
function sliceOf(node, source) {
  const start = node.position?.start?.offset
  const end = node.position?.end?.offset

  if (typeof start !== 'number' || typeof end !== 'number') return null

  return source.slice(start, end)
}

/*
 * A container spans its own children, so quoting it whole would print the body
 * twice — once as source and once as the rendered children below it. Only the
 * opening line is the directive; the rest is the author's prose and renders as
 * prose.
 */
function openingOf(node, source) {
  const slice = sliceOf(node, source)
  if (slice === null) return `${DIRECTIVE_MARKER[node.type]}${node.name}`

  const newline = slice.indexOf('\n')

  return newline === -1 ? slice : slice.slice(0, newline)
}

// Quoted rather than assumed: a container left unclosed at the end of the body
// still parses, and printing a `:::` the author never typed would be the same
// bug in a smaller place.
function closingOf(node, source) {
  const slice = sliceOf(node, source)

  return slice !== null && slice.length > 3 && slice.endsWith(':::') ? ':::' : ''
}

/*
 * Ignored: a directive nobody recognises — a typo, or a note written against a
 * newer dialect — is shown as what the author typed. Swallowing it would lose
 * their writing with no signal that anything had happened.
 *
 * The class is a hook and carries no styling on purpose: the fallback is
 * already legible, and marking it more loudly is a design decision rather than
 * a correctness one.
 */
function renderLiteral(node, mode, source) {
  if (node.type === 'containerDirective') {
    // The `[label]` sits on the opening line, which has just been quoted whole.
    // Rendering it again below would print those words twice.
    const body = { children: (node.children ?? []).filter((child) => !isDirectiveLabel(child)) }
    const opening = openingOf(node, source)
    const closing = closingOf(node, source)

    return mode === 'inline'
      ? h('span', { class: 'markdown__unknown' }, [
          `${opening} `,
          ...renderChildren(body, mode, source),
        ])
      : h('div', { class: 'markdown__unknown' }, [
          h('p', opening),
          ...renderChildren(body, mode, source),
          ...(closing ? [h('p', closing)] : []),
        ])
  }

  const slice = sliceOf(node, source)

  return h(
    'span',
    { class: 'markdown__unknown' },
    slice === null ? `${DIRECTIVE_MARKER[node.type]}${node.name}` : slice,
  )
}

function renderDirective(node, mode, source) {
  const spec = specFor(node)
  const component = DIRECTIVE_COMPONENTS[node.name]
  if (!spec || !component) return renderLiteral(node, mode, source)

  const props = spec.props(node, labelOf(node))
  if (!props) return renderLiteral(node, mode, source)

  if (!spec.content) return h(component, props)

  /*
   * A *block* component in inline mode has no room to draw itself. Its words
   * are still the author's, so they stay and the box around them does not.
   *
   * An inline one has room by definition — `:color[…]` is a span in the middle
   * of a sentence, and a description is exactly where a game master would want
   * the mark they put there to survive. Asked of the node rather than of the
   * mode, so this stays right for whatever the dialect grows next: the question
   * was always "does this take a line of its own", and `isBlock` is where the
   * app already answers it.
   */
  return mode === 'inline' && isBlock(node)
    ? h(Fragment, renderChildren(node, mode, source))
    : h(component, props, () => renderChildren(node, mode, source))
}

function renderLink(node, mode, source) {
  const href = safeUrl(node.url)
  if (href === null) return h(Fragment, renderChildren(node, mode, source))

  return h('a', { href, title: node.title ?? undefined }, renderChildren(node, mode, source))
}

function renderNode(node, mode, source) {
  switch (node.type) {
    case 'text':
      return node.value
    // Ignored, and the whole of the HTML story. A raw <script> in the source is
    // markup this dialect does not implement, so it is left alone — and a
    // string left alone by Vue is text on the page.
    case 'html':
      return node.value
    case 'inlineCode':
      return h('code', node.value)
    case 'code':
      return mode === 'inline' ? node.value : h('pre', [h('code', node.value)])
    case 'break':
      return mode === 'inline' ? ' ' : h('br')
    case 'thematicBreak':
      return mode === 'inline' ? null : h('hr', { class: 'rule-double' })
    case 'link':
      return renderLink(node, mode, source)
    // Images wait for the asset context (#29): until there is somewhere for a
    // map to live, the alt text is the honest thing to show and an arbitrary
    // remote <img> in a shared note is a tracking pixel. With no alt there is
    // nothing to narrow to, so it is Skipped rather than shown as its URL — a
    // file path is not a caption and reads as one.
    case 'image':
      return node.alt || ELISION
    default:
      break
  }

  if (isDirective(node)) return renderDirective(node, mode, source)

  const inlineTag = INLINE_ELEMENTS[node.type]
  if (inlineTag) return h(inlineTag, renderChildren(node, mode, source))

  const blockTag = BLOCK_ELEMENTS[node.type]
  if (blockTag && mode === 'block') return h(blockTag(node), renderChildren(node, mode, source))

  // The root, every block node in inline mode, and any node type this walker
  // has never heard of: keep the content, drop the wrapper.
  return h(Fragment, renderChildren(node, mode, source))
}

export function renderTree(tree, mode, source = '') {
  // One root element, so a caller's class and attributes fall through — that is
  // how `.prose` gets applied from outside.
  return h(mode === 'inline' ? 'span' : 'div', renderChildren(tree, mode, source))
}
