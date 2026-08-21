<script setup>
import {
  PROSE_HUES,
  PROSE_TIERS,
  DEFAULT_TIER,
  proseColorClass,
} from '../../design-system/proseColors.js'

/*
 * A coloured phrase — `:color[searing light]{hue=torch tier=bold}`.
 *
 * **The first thing in the dialect that is presentation and nothing else.**
 * Every other directive says what a phrase *is*; this one says how it looks,
 * and that difference is the whole of its accessibility story.
 *
 * **So there is no ARIA on it, deliberately.** `EntityTag` announces "(NPC)" to
 * a screen reader because the chip's colour and icon carry a fact a listener
 * would otherwise miss. Here there is no fact: announcing "wyrd, bold" would
 * read out a decision about ink. Colour that carries meaning should have been a
 * semantic directive instead — the text stays the text.
 *
 * **A class, not a style.** The class resolves to a token and the token flips
 * with the scheme, so nothing here knows a hex and a theme switch needs no
 * re-render. The twenty-one rules live in `base.css`, which is also where the
 * picker's swatches read them from.
 */

const props = defineProps({
  hue: {
    type: String,
    required: true,
    validator: (value) => Object.hasOwn(PROSE_HUES, value),
  },
  // `dialect.js` refuses an unknown tier before it reaches here, so this default
  // is for the directive written without one — `{hue=slate}`, which the picker
  // itself produces for the middle tier.
  tier: {
    type: String,
    default: DEFAULT_TIER,
    validator: (value) => Object.hasOwn(PROSE_TIERS, value),
  },
})
</script>

<template>
  <span class="prose-color" :class="proseColorClass(props.hue, props.tier)"><slot /></span>
</template>

<style scoped>
/*
 * Colour only — no weight, no underline, no background.
 *
 * The tier already carries the emphasis, and a mark that also changed weight
 * would be two marks fighting over one phrase. Bold is `**` and stays `**`.
 */
.prose-color {
  color: var(--prose-color);
}
</style>
