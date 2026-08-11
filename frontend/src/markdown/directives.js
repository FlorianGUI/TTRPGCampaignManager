import EntityTag from '../components/domain/EntityTag.vue'
import DiceChip from '../components/domain/DiceChip.vue'
import SourceRef from '../components/domain/SourceRef.vue'
import ReadAloud from '../components/domain/ReadAloud.vue'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'

/*
 * The dialect, as a table: directive name → the component it becomes.
 *
 * Everything the renderer knows about Campaign Manager markdown is here. A new
 * directive is an entry, not a branch in the walker.
 *
 * Each entry declares:
 *   component  what to render
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
    component: EntityTag,
    types: ['textDirective'],
    props: (node, label) => (label ? { kind, label } : null),
  },
])

export const DIRECTIVES = Object.fromEntries([
  ...entityDirectives,

  [
    'dice',
    {
      component: DiceChip,
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
      component: SourceRef,
      types: ['textDirective'],
      props: (node, work) => (work ? { work, page: node.attributes.page ?? null } : null),
    },
  ],

  [
    'read-aloud',
    {
      component: ReadAloud,
      types: ['containerDirective'],
      content: true,
      // Undefined rather than null: ReadAloud defaults the label to "Read
      // aloud", and a default only applies to an absent prop.
      props: (node) => ({ label: node.attributes.label || undefined }),
    },
  ],
])
