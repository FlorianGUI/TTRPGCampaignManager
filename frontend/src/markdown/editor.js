import { StateEffect, StateField } from '@codemirror/state'
import { Decoration, EditorView, ViewPlugin, WidgetType } from '@codemirror/view'
import { parse } from './parse.js'
import { decorationsFor } from './livePreview.js'

/*
 * The CodeMirror half of the live preview: descriptors in, decorations out.
 *
 * Everything with a rule in it is next door in `livePreview.js` and is tested
 * without a DOM. What is left here is the part that can only be said in
 * CodeMirror's vocabulary — which is deliberately not much, and is the reason
 * the seam is where it is.
 *
 * **No HTML string is built here either.** A widget is a DOM node made with
 * `createElement`, the same posture `render.js` holds on the reading side, so
 * the guarantee the README states about the dependency list is not weakened by
 * the writing side having gained a renderer.
 */

/*
 * The two things the source says rather than shows.
 *
 * A bullet is drawn as the `•` the reader would see, as **text** and not as a
 * decorative flourish: a screen reader announcing the list marker is the
 * behaviour a `-` already had, and a widget that hid it would be a regression
 * wearing a feature's clothes. A rule has nothing to announce — it is the
 * double rule `render.js` draws on the page, from the same token — so it is
 * hidden from the accessibility tree rather than read out as an empty box.
 *
 * Nothing is lost to a reader who cannot see either: what a marker conceals
 * comes back the moment the caret reaches it, which is how it comes back for
 * everybody.
 */
class Drawn extends WidgetType {
  constructor(name) {
    super()
    this.name = name
  }

  eq(other) {
    return other.name === this.name
  }

  toDOM() {
    const node = document.createElement('span')
    node.className = `md-${this.name}`

    if (this.name === 'bullet') node.textContent = '•'
    else node.setAttribute('aria-hidden', 'true')

    return node
  }

  /* The caret has to be able to land past a bullet by clicking near it, which
     it cannot do if the widget swallows the event first. */
  ignoreEvent() {
    return false
  }
}

const BULLET = new Drawn('bullet')
const RULE = new Drawn('rule')

const WIDGETS = { bullet: BULLET, rule: RULE }

const HIDDEN = Decoration.replace({})

function decorate(descriptor, doc) {
  switch (descriptor.kind) {
    case 'hide':
      return HIDDEN.range(descriptor.from, descriptor.to)
    case 'mark':
      return Decoration.mark({ class: descriptor.class }).range(descriptor.from, descriptor.to)
    case 'widget':
      return Decoration.replace({ widget: WIDGETS[descriptor.name] }).range(
        descriptor.from,
        descriptor.to,
      )
    default:
      // A line decoration is a point at the line's start, and the descriptor
      // carries an offset somewhere on that line — the parser has no idea where
      // lines begin and the document does.
      return Decoration.line({ class: descriptor.class }).range(doc.lineAt(descriptor.from).from)
  }
}

function setFor(state, tree, source) {
  const ranges = state.selection.ranges.map((range) => ({ from: range.from, to: range.to }))

  return Decoration.set(
    decorationsFor(tree, source, ranges).map((descriptor) => decorate(descriptor, state.doc)),
    // Sorted here rather than in the walker: the order decorations have to
    // arrive in is CodeMirror's rule, and the walker's order is the tree's.
    true,
  )
}

/* A tree that matches the document, and the text it was read from. */
const rebuilt = StateEffect.define()

/*
 * How long the field waits after the last keystroke before reading the document
 * again.
 *
 * **Measured, as #142 asked.** The walk over the tree costs 0.6ms on a
 * two-thousand-word body and the parse costs twenty to thirty — the whole
 * document, every keystroke, because that is the only unit `remark-parse`
 * takes. Under about four kilobytes that is a few milliseconds and nobody would
 * notice; at eight it is past a frame, and typing a long scene stutters.
 *
 * The delay is uniform rather than reserved for long bodies, because the second
 * reason to have it holds at every size: `**bold` is a half-written construct,
 * and re-reading the document between the two asterisks makes marks appear and
 * vanish under the fingers. Waiting for a pause is what makes the field settle
 * once instead of flickering per character.
 */
const QUIET = 60

/*
 * The tree, kept until the text it describes has actually changed.
 *
 * Moving the caret changes which markers are showing and none of what they are,
 * so a selection re-derives from the tree already held — the cheap half of the
 * work, and the half that has to be instant. Typing is the only thing that
 * invalidates a tree, and while one is stale the decorations are carried along
 * by the edits rather than thrown away: what is on screen goes on being right
 * about everything except the words being typed, which is where the writer is
 * looking anyway.
 */
const decorations = StateField.define({
  create(state) {
    const source = state.doc.toString()
    const tree = parse(source)

    return { tree, fresh: true, set: setFor(state, tree, source) }
  },

  update(value, transaction) {
    for (const effect of transaction.effects) {
      if (!effect.is(rebuilt)) continue

      return {
        tree: effect.value.tree,
        fresh: true,
        set: setFor(transaction.state, effect.value.tree, effect.value.source),
      }
    }

    // The offsets in the tree are now behind the document. The decorations are
    // not — `map` moves them with the change — but nothing new may be derived
    // from the tree until the parse below catches up.
    if (transaction.docChanged) {
      return { ...value, fresh: false, set: value.set.map(transaction.changes) }
    }

    if (!transaction.selection || !value.fresh) return value

    return {
      ...value,
      set: setFor(transaction.state, value.tree, transaction.state.doc.toString()),
    }
  },

  provide: (field) => EditorView.decorations.from(field, (value) => value.set),
})

/*
 * The one thing here that cannot be said as a transaction: waiting.
 *
 * A state field is a pure function of what it is handed, so the timer lives in
 * a view plugin and its result arrives the way every other change does — as an
 * effect on a transaction.
 */
const reparser = ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.view = view
      this.timer = 0
    }

    update(update) {
      if (!update.docChanged) return

      clearTimeout(this.timer)
      this.timer = setTimeout(() => this.reread(), QUIET)
    }

    reread() {
      const source = this.view.state.doc.toString()

      this.view.dispatch({ effects: rebuilt.of({ source, tree: parse(source) }) })
    }

    destroy() {
      clearTimeout(this.timer)
    }
  },
)

export const livePreview = [decorations, reparser]
