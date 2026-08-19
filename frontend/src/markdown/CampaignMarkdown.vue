<script>
import { computed } from 'vue'
import { parse } from './parse.js'
import { renderTree, MODES } from './render.js'

/*
 * Campaign Manager markdown, rendered. Every screen that shows authored prose —
 * a session note (#52), a scene, an act's description (#80) — imports this and
 * not the parser. One dialect, one renderer, one place a bug can live.
 *
 * A render function rather than a template, because the output is components
 * chosen at runtime from the source text. That is also the security posture:
 * `v-html` is not avoided here so much as unreachable, since no HTML string is
 * ever produced to put in it. See render.js.
 *
 * The root element is one node, so `class`, `id` and the rest fall through —
 * `<CampaignMarkdown class="prose" :source="note.body" />` is how the reading
 * measure gets applied from outside.
 */
export default {
  name: 'CampaignMarkdown',
  props: {
    source: { type: String, default: '' },
    mode: {
      type: String,
      default: 'block',
      validator: (value) => MODES.includes(value),
    },
  },
  setup(props) {
    const tree = computed(() => parse(props.source))

    /*
     * The source goes down with the tree. A directive the dialect cannot read
     * is shown as the author's own bytes, and the tree no longer has them —
     * mdast keeps offsets into this string rather than how anything was typed.
     */
    return () => renderTree(tree.value, props.mode, props.source ?? '')
  },
}
</script>
