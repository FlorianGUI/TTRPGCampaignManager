import EntityTag from '../components/domain/EntityTag.vue'
import DiceChip from '../components/domain/DiceChip.vue'
import SourceRef from '../components/domain/SourceRef.vue'
import ReadAloud from '../components/domain/ReadAloud.vue'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'

/*
 * The other half of the table in `dialect.js`: directive name → the component
 * it becomes.
 *
 * Split from the rules it pairs with so that asking *whether* a directive is
 * recognised does not drag four Vue components along. `toPlainText` reduces a
 * body to the words for a table cell and a page title, and a projection that
 * renders nothing has no reason to import things that render.
 *
 * A name in `DIRECTIVES` with no component here is not a crash: `render.js`
 * treats it as a directive it cannot draw and shows the source, which is the
 * same fallback an unknown name gets. Adding a directive in two files is a
 * thing to get wrong, so getting it wrong degrades instead of throwing.
 */

const entityComponents = Object.keys(ENTITY_KINDS).map((kind) => [kind, EntityTag])

export const DIRECTIVE_COMPONENTS = Object.fromEntries([
  ...entityComponents,
  ['dice', DiceChip],
  ['ref', SourceRef],
  ['read-aloud', ReadAloud],
])
