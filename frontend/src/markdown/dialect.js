import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import { DEFAULT_TIER, isProseColor } from '../design-system/proseColors.js'

/*
 * The dialect, as a table: directive name → the rules it is accepted under.
 *
 * Everything the app knows about the *shape* of Campaign Manager markdown is
 * here. A new directive is an entry, not a branch in a walker.
 *
 * **This module imports no components, and must not start.** Three consumers
 * need to ask whether a directive is recognised — `render.js`, which draws it;
 * `toolbar.js`, which writes it; and `nodes.js`, which reduces it to plain text
 * for a table cell. Only the first has any business pulling in Vue components,
 * and `toPlainText` exists precisely because there are places that render
 * nothing at all. The components live next door in `directives.js`.
 *
 * Each entry declares:
 *   types      which directive forms are accepted — `:x[…]` inline, `::x` leaf,
 *              `:::x` container. Using the wrong form is a typo, and typos
 *              degrade to visible text rather than rendering something odd.
 *   content    true when the children are the block's *content*, handed to the
 *              default slot. Otherwise they are the label, and the component
 *              takes it as a prop.
 *   props      the props to pass, or null to refuse — a refusal degrades the
 *              directive to visible text. That is how an attribute the dialect
 *              does not understand gets the same treatment as a directive it
 *              does not understand, rather than being silently dropped into a
 *              component that will mislabel it.
 */

// Directive attributes are text: `{result=9}` arrives as the string "9". Coerce
// here, once, rather than loosening a component's prop types to accommodate the
// parser.
function toNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined // undefined ⟹ refuse
}

const OUTCOMES = ['crit', 'fumble']

/*
 * `ENTITY_KINDS` is the authority on kinds and this is the only place the
 * dialect asks it. Adding `scene` there (see #80) is the whole change needed to
 * make `:scene[The parley at Stonegate]` render.
 */
const entityDirectives = Object.keys(ENTITY_KINDS).map((kind) => [
  kind,
  {
    types: ['textDirective'],
    props: (node, label) => (label ? { kind, label } : null),
  },
])

export const DIRECTIVES = Object.fromEntries([
  ...entityDirectives,

  [
    'dice',
    {
      types: ['textDirective'],
      props: (node, notation) => {
        if (!notation) return null

        const result = toNumber(node.attributes.result)
        if (result === undefined) return null

        const outcome = node.attributes.outcome ?? null
        if (outcome !== null && !OUTCOMES.includes(outcome)) return null

        return { notation, result, outcome }
      },
    },
  ],

  [
    'ref',
    {
      types: ['textDirective'],
      props: (node, work) => (work ? { work, page: node.attributes.page ?? null } : null),
    },
  ],

  /*
   * The one directive whose attributes are its whole point: `:color[…]` with no
   * hue is a phrase with no colour, which is a phrase.
   *
   * **Both attributes refuse rather than fall back.** An unknown hue could
   * quietly become `slate` and an unknown tier could quietly become `medium`,
   * and both would leave a game master looking at prose that renders but is not
   * what they wrote. `:dice[1d20]{outcome=nat20}` set the precedent: an
   * attribute the dialect cannot honour degrades the directive to its own text,
   * where the typo is visible and fixable.
   *
   * `content: true` because the words are the phrase, not a label for it — so
   * `:color[the **ward** answers]{hue=wyrd}` keeps its bold. `read-aloud` is the
   * only other content directive and is a block; this one is inline, which is
   * the distinction `render.js` draws when it decides what survives `inline`
   * mode.
   */
  [
    'color',
    {
      types: ['textDirective'],
      content: true,
      props: (node) => {
        const hue = node.attributes.hue
        const tier = node.attributes.tier ?? DEFAULT_TIER

        return isProseColor(hue, tier) ? { hue, tier } : null
      },
    },
  ],

  [
    'read-aloud',
    {
      types: ['containerDirective'],
      content: true,
      // Undefined rather than null: ReadAloud defaults the label to "Read
      // aloud", and a default only applies to an absent prop.
      props: (node) => ({ label: node.attributes.label || undefined }),
    },
  ],
])

/*
 * The entry for a node, or null if the dialect does not accept it in that form.
 *
 * Name and form are checked together on purpose: `:::npc[Fen]` names a
 * directive that exists and uses it as a block, which is a typo rather than a
 * new feature, and it degrades exactly like a name nobody has heard of.
 */
export function specFor(node) {
  /*
   * `Object.hasOwn`, not a bare lookup. `DIRECTIVES` is an ordinary object, so
   * `:constructor[x]` finds `Object.prototype.constructor` — a function with no
   * `types` — and asking it took the whole page down with a TypeError. Every
   * other unknown name degrades to visible text, and this one crashed, which is
   * the opposite of what a dialect nobody can typo-proof is supposed to do.
   */
  const spec = Object.hasOwn(DIRECTIVES, node.name) ? DIRECTIVES[node.name] : null

  return spec && spec.types.includes(node.type) ? spec : null
}

/*
 * The props a directive resolves to, or null if it is refused.
 *
 * The single question behind "is this directive recognised?", asked the same
 * way by everything that has to answer it. A refusal here and a name nobody
 * knows are the same outcome to a reader — the page shows what was typed — so
 * they must not be two different tests in two different files.
 */
export function propsFor(node, label) {
  const spec = specFor(node)

  return spec ? spec.props(node, label) : null
}
