import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkDirective from 'remark-directive'

/*
 * Campaign Manager markdown, as far as text goes: CommonMark plus the generic
 * directive syntax (`:npc[…]`, `:::read-aloud`). Everything past this point is
 * a tree.
 *
 * `.parse()` and never `.process()` — the processor has no compiler attached,
 * deliberately. There is no step here that can produce an HTML string, so there
 * is no string for anything downstream to inject into, and nothing to sanitise.
 * That is why the dependency list stops at these three: adding remark-rehype,
 * remark-stringify or any rehype-* would put a compiler back and quietly undo
 * the whole arrangement.
 */
const processor = unified().use(remarkParse).use(remarkDirective)

export function parse(source) {
  return processor.parse(source ?? '')
}
