import { isDirective } from './nodes.js'

/*
 * What the field draws over the characters a game master typed, as plain data.
 *
 * #142's complaint, in the words it arrived in: *"pendant qu'on édite le texte,
 * ce serait vraiment plus pratique de voir directement les changements qu'on
 * fait … et non avec des balises."* So `**bold**` reads as bold while it is
 * being written, and the asterisks come back when the caret goes looking for
 * them.
 *
 * **The tree is the one `CampaignMarkdown` renders**, from the same `parse()`.
 * Every node it carries has `position.start.offset`, so "which characters are
 * this `strong`" is a lookup rather than a second parser — and a second parser
 * is the thing that would eventually disagree with the page under exactly the
 * input that matters. It is also why this module is not a CodeMirror language:
 * a Lezer grammar would be that second parser wearing a different hat.
 *
 * **No CodeMirror in here, and no DOM.** The output is four kinds of
 * descriptor, and `editor.js` is what turns them into decorations. That split
 * is `toolbar.js`'s, for the same reason: the rules — which characters vanish,
 * which line is a heading, when the source comes back — are the part worth
 * testing, and they are testable without mounting anything.
 *
 *   hide    these characters are not shown
 *   mark    these characters are drawn with a class
 *   line    the line at this offset is drawn with a class
 *   widget  these characters are replaced by something drawn
 *
 * `line` carries an offset rather than a line number because a line is the
 * editor's idea and not the parser's; whoever holds the document resolves it.
 */

export const SYNTAX = 'md-syntax'

const STRONG = 'md-strong'
const EMPHASIS = 'md-em'
const CODE = 'md-code'
const LINK = 'md-link'
const QUOTE = 'md-quote'
const LIST = 'md-list'
const CODE_BLOCK = 'md-codeblock'

const HEADING = (depth) => `md-h${Math.min(depth ?? 1, 6)}`

const MARKS = { strong: STRONG, emphasis: EMPHASIS }

/*
 * A construct opens when the selection touches it.
 *
 * Touching rather than containing, and the whole construct rather than the
 * marker: the caret arriving at the first `*` of `**bold**` should show the
 * asterisks, and so should the caret sitting in the middle of the word, which
 * is nowhere near them. Both are the same question asked of the same range.
 *
 * Inclusive at both ends on purpose. A caret one character to the left of a
 * construct is outside it and a caret exactly at its edge is about to be inside
 * it, so the source appears a keystroke before it is needed rather than a
 * keystroke after — which is the difference between an editor that gets out of
 * the way and one that has to be fought.
 */
function touched(from, to, ranges) {
  return ranges.some((range) => range.from <= to && range.to >= from)
}

const span = (node) => [node.position?.start?.offset, node.position?.end?.offset]

/*
 * Where the children start and end — which is where the markers stop.
 *
 * Counted from the tree rather than from the text, and that is what makes
 * `***both***` come out right: the emphasis owns one asterisk each side and the
 * strong inside it owns two, and no amount of counting characters at the edge
 * of the outer node would have told them apart. It is the same argument
 * `render.js` makes for slicing the source instead of rebuilding it.
 */
function inner(node) {
  const children = (node.children ?? []).filter((child) => child.position)
  if (children.length === 0) return null

  return [children[0].position.start.offset, children.at(-1).position.end.offset]
}

/*
 * A marker: dimmed when it shows, gone when it does not.
 *
 * Both, always, and not one or the other. The `mark` is what makes a revealed
 * `**` read as punctuation rather than as two more characters of the sentence;
 * under a `hide` it costs nothing, because there is nothing to draw.
 */
function conceal(out, from, to, open) {
  if (!(to > from)) return

  out.push({ kind: 'mark', from, to, class: SYNTAX })
  if (!open) out.push({ kind: 'hide', from, to })
}

/*
 * The lines a node covers, as offsets.
 *
 * A blockquote's `>` is not in the tree — the second line of a two-line quote
 * sits inside a single text node, marker and all — so anything that works line
 * by line has to find its own lines. The parser knows where the block is; the
 * source knows where the lines are.
 */
function* linesIn(source, from, to) {
  let at = from

  while (at <= to) {
    const newline = source.indexOf('\n', at)
    const end = newline === -1 || newline > to ? to : newline

    yield { from: at, to: end }

    at = end + 1
  }
}

const VISITORS = {
  strong: markPair,
  emphasis: markPair,
  inlineCode: inlineCodeSpan,
  link: linkSpan,
  heading: headingLine,
  blockquote: quoteLines,
  listItem: listMarker,
  thematicBreak: rule,
  code: codeBlock,
}

/* `strong` and `emphasis`: the same shape twice, and the class is the only
   difference between them. */
function markPair(node, { out, ranges }) {
  const [from, to] = span(node)
  const body = inner(node)
  if (!body) return

  out.push({ kind: 'mark', from: body[0], to: body[1], class: MARKS[node.type] })

  const open = touched(from, to, ranges)
  conceal(out, from, body[0], open)
  conceal(out, body[1], to, open)
}

/*
 * The one construct whose markers cannot be found through its children, because
 * it has none — the value is a string on the node. The fence is however many
 * backticks were typed, so it is read off the text rather than assumed to be
 * one: ``a ` b`` is a perfectly ordinary way to write a backtick.
 */
function inlineCodeSpan(node, { out, source, ranges }) {
  const [from, to] = span(node)
  const slice = source.slice(from, to)

  const open = /^`+/.exec(slice)?.[0].length ?? 0
  const close = /`+$/.exec(slice)?.[0].length ?? 0
  if (from + open >= to - close) return

  const revealed = touched(from, to, ranges)

  out.push({ kind: 'mark', from: from + open, to: to - close, class: CODE })
  conceal(out, from, from + open, revealed)
  conceal(out, to - close, to, revealed)
}

/* `[text](url)`: the text is the children, so everything on either side of them
   is the machinery — one bracket before, and the whole target after. */
function linkSpan(node, { out, ranges }) {
  const [from, to] = span(node)
  const body = inner(node)
  if (!body) return

  const open = touched(from, to, ranges)

  out.push({ kind: 'mark', from: body[0], to: body[1], class: LINK })
  conceal(out, from, body[0], open)
  conceal(out, body[1], to, open)
}

/*
 * `## Title`. The hashes and the space after them are whatever sits between the
 * line's start and the first word, which is also why a setext heading —
 * underlined with `===` rather than prefixed — conceals nothing and is left to
 * read as what it is.
 */
function headingLine(node, { out, ranges }) {
  const [from, to] = span(node)
  const body = inner(node)

  out.push({ kind: 'line', from, class: HEADING(node.depth) })
  if (body) conceal(out, from, body[0], touched(from, to, ranges))
}

/*
 * Line by line, and revealed line by line.
 *
 * A quote can be several paragraphs long, and opening the whole of it because
 * the caret is somewhere in the third one would put markers back on screen
 * nowhere near where anyone is looking. The line is the unit a writer is
 * working in.
 */
function quoteLines(node, { out, source, ranges }) {
  const [from, to] = span(node)

  for (const line of linesIn(source, from, to)) {
    const marker = /^\s*>\s?/.exec(source.slice(line.from, line.to))
    if (!marker) continue

    out.push({ kind: 'line', from: line.from, class: QUOTE })
    conceal(out, line.from, line.from + marker[0].length, touched(line.from, line.to, ranges))
  }
}

/*
 * A bullet becomes a bullet; a number stays a number.
 *
 * `-` is notation for something the reader sees as `•`, so it is drawn as one.
 * `1.` already *is* what the reader sees, and replacing it with itself would be
 * a widget that earns nothing and takes the caret's ability to sit inside the
 * number with it. Only the marker character is replaced — the space after it is
 * the author's text and is what keeps `• one` looking like a list item.
 */
function listMarker(node, { out, source, ranges, ordered }) {
  const [from] = span(node)
  const body = inner(node)
  if (!body || ordered) return

  const line = {
    from,
    to: source.indexOf('\n', from) === -1 ? body[1] : source.indexOf('\n', from),
  }

  out.push({ kind: 'line', from, class: LIST })

  if (touched(line.from, line.to, ranges)) return

  out.push({ kind: 'widget', name: 'bullet', from, to: from + 1 })
}

/* `---` is a drawing instruction and nothing else: there is no text under it to
   preserve, so the whole of it is replaced by the rule it asks for. */
function rule(node, { out, ranges }) {
  const [from, to] = span(node)
  if (touched(from, to, ranges)) return

  out.push({ kind: 'widget', name: 'rule', from, to })
}

/*
 * The block is washed and the fences are emptied rather than removed.
 *
 * Taking the newline with them would join the code to the paragraph above it,
 * so what is concealed is each fence line's *content*. The line stays, empty,
 * and reads as the padding a code block wants at its top and bottom anyway.
 */
function codeBlock(node, { out, source, ranges }) {
  const [from, to] = span(node)
  const lines = [...linesIn(source, from, to)]

  for (const line of lines) out.push({ kind: 'line', from: line.from, class: CODE_BLOCK })

  const fenced = /^\s*(```|~~~)/.test(source.slice(lines[0].from, lines[0].to))
  if (!fenced) return

  /* To the end of the *line*, not of the document. Slicing to the end of the
     source put every paragraph after the block inside the match, so `\s*$`
     never held and the closing fence stayed on screen. */
  const last = lines.at(-1)
  const closing = lines.length > 1 && /^\s*(```|~~~)\s*$/.test(source.slice(last.from, last.to))

  conceal(out, lines[0].from, lines[0].to, touched(lines[0].from, lines[0].to, ranges))

  if (closing) conceal(out, last.from, last.to, touched(last.from, last.to, ranges))
}

function walk(node, context) {
  /*
   * A directive is #154's, and its markers are left standing here — but its
   * body is the author's prose and a `**bold**` inside a read-aloud box is
   * bold for the same reason it is anywhere else. So: nothing for the node,
   * everything for the children.
   */
  if (!isDirective(node)) {
    const visit = VISITORS[node.type]

    if (visit && node.position) visit(node, context)
  }

  for (const child of node.children ?? []) {
    walk(child, node.type === 'list' ? { ...context, ordered: Boolean(node.ordered) } : context)
  }
}

/*
 * The tree, the text it was parsed from, and where the caret is — because the
 * last of those decides which markers are showing, and a decoration set that
 * did not know it would be right only until someone clicked.
 */
export function decorationsFor(tree, source, ranges = []) {
  const out = []

  walk(tree, { out, source, ranges, ordered: false })

  return out
}
