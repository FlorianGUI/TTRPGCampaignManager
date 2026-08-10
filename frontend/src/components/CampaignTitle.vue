<script setup>
/*
 * The campaign's name, at the head of the navigation that belongs to it.
 *
 * It is a title and not a control — no border, no chevron, nothing to press.
 * The tag it replaces looked pressable and mostly was not, which is the worst of
 * both: a thing that invites a click and answers with nothing. What you can *do*
 * to a campaign lives in the account menu in the top bar, with the other
 * actions.
 *
 * A 15rem column is narrower than a lot of campaign names, so the name
 * ellipsises and a tooltip carries the rest — the description too, when there is
 * one, because that is the line the game master wrote to recognise the table by.
 *
 * The ellipsis is visual only: CSS truncation does not shorten the accessible
 * name, so a screen reader reads the whole thing whether or not the tooltip is
 * reachable. That is what keeps a hover-only affordance from hiding anything.
 *
 * Rendered wherever `AppNav` is — the sticky sidebar, and the drawer below
 * 900px — so the campaign is named at every width rather than only where there
 * is room for it in the bar.
 */
import { computed } from 'vue'

const props = defineProps({
  campaign: { type: Object, required: true },
})

/*
 * Name on the first line, description under it. `pre-line` in the `pt` below is
 * what turns the newline into one — the tooltip renders text, so without it the
 * two would run together into a sentence that says neither.
 */
const tooltip = computed(() => ({
  value: props.campaign.description
    ? `${props.campaign.name}\n${props.campaign.description}`
    : props.campaign.name,
  pt: { text: { style: 'white-space: pre-line' } },
}))
</script>

<template>
  <!--
    Just the name. No "Campaign" label above it: the nav's own Campaign section
    heading sits directly beneath this, and the same word twice in two lines
    reads as a mistake rather than as structure.
  -->
  <p v-tooltip.right="tooltip" class="campaign-title">{{ campaign.name }}</p>
</template>

<style scoped>
/*
 * The largest thing in the column, and the only one in the display face, so the
 * eye lands on where it is before it starts reading where it can go.
 *
 * The cursor stays an arrow: this is a label, and a pointer would promise a
 * click that does nothing.
 */
.campaign-title {
  overflow: hidden;
  /* Aligns with the nav items below rather than with the column edge, so the
     title and the list it heads share a left edge. */
  margin: 0 0 var(--space-4);
  padding: 0 var(--space-2);
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  font-size: var(--step-0);
  line-height: 1.15;
  color: var(--p-primary-color);
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
}
</style>
