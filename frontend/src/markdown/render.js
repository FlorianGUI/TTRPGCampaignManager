import { h, Fragment } from 'vue'
import { DIRECTIVES } from './directives.js'
import { DIRECTIVE_MARKER, isBlock, isDirective, labelOf } from './nodes.js'

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
 * titles — see toPlainText.js.
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

function renderChildren(node, mode) {
  const children = node.children ?? []

  return children.flatMap((child, index) =>
    // Flattened blocks would otherwise run their last word into the next one's
    // first.
    index > 0 && mode === 'inline' && isBlock(child)
      ? [' ', renderNode(child, mode)]
      : [renderNode(child, mode)],
  )
}

function attributesText(node) {
  const entries = Object.entries(node.attributes ?? {})
  if (entries.length === 0) return ''

  return `{${entries.map(([key, value]) => `${key}=${value}`).join(' ')}}`
}

/*
 * A directive nobody recognises — a typo, or a note written against a newer
 * dialect — is shown as what the author typed. Swallowing it would lose their
 * writing with no signal that anything had happened.
 *
 * The class is a hook and carries no styling on purpose: the fallback is
 * already legible, and marking it more loudly is a design decision rather than
 * a correctness one.
 */
function renderLiteral(node, mode) {
  const opening = `${DIRECTIVE_MARKER[node.type]}${node.name}`
  const children = node.children ?? []

  if (node.type === 'containerDirective') {
    const marker = `${opening}${attributesText(node)}`

    return mode === 'inline'
      ? h('span', { class: 'markdown__unknown' }, [`${marker} `, ...renderChildren(node, mode)])
      : h('div', { class: 'markdown__unknown' }, [
          h('p', marker),
          ...renderChildren(node, mode),
          h('p', ':::'),
        ])
  }

  return h('span', { class: 'markdown__unknown' }, [
    opening,
    ...(children.length ? ['[', ...renderChildren(node, mode), ']'] : []),
    attributesText(node),
  ])
}

function renderDirective(node, mode) {
  const spec = DIRECTIVES[node.name]
  if (!spec || !spec.types.includes(node.type)) return renderLiteral(node, mode)

  const props = spec.props(node, labelOf(node))
  if (!props) return renderLiteral(node, mode)

  if (!spec.content) return h(spec.component, props)

  // A block component in inline mode has no room to draw itself. Its words are
  // still the author's, so they stay.
  return mode === 'inline'
    ? h(Fragment, renderChildren(node, mode))
    : h(spec.component, props, () => renderChildren(node, mode))
}

function renderLink(node, mode) {
  const href = safeUrl(node.url)
  if (href === null) return h(Fragment, renderChildren(node, mode))

  return h('a', { href, title: node.title ?? undefined }, renderChildren(node, mode))
}

function renderNode(node, mode) {
  switch (node.type) {
    case 'text':
      return node.value
    // The whole of the HTML story. A raw <script> in the source is a string,
    // and a string rendered by Vue is text on the page.
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
      return renderLink(node, mode)
    // Images wait for the asset context (#29): until there is somewhere for a
    // map to live, the alt text is the honest thing to show and an arbitrary
    // remote <img> in a shared note is a tracking pixel.
    case 'image':
      return node.alt || node.url
    default:
      break
  }

  if (isDirective(node)) return renderDirective(node, mode)

  const inlineTag = INLINE_ELEMENTS[node.type]
  if (inlineTag) return h(inlineTag, renderChildren(node, mode))

  const blockTag = BLOCK_ELEMENTS[node.type]
  if (blockTag && mode === 'block') return h(blockTag(node), renderChildren(node, mode))

  // The root, every block node in inline mode, and any node type this walker
  // has never heard of: keep the content, drop the wrapper.
  return h(Fragment, renderChildren(node, mode))
}

export function renderTree(tree, mode) {
  // One root element, so a caller's class and attributes fall through — that is
  // how `.prose` gets applied from outside.
  return h(mode === 'inline' ? 'span' : 'div', renderChildren(tree, mode))
}
