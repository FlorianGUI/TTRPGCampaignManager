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
 * ellipsises and a tooltip carries the rest of it. The rest of it and nothing
 * else: the description is not in here, and is not shown anywhere in the chrome.
 * It is being kept for #31, where a campaign is something you can be invited to
 * and the description is what an invitation shows you about a table you have not
 * sat at yet — a different reader and a different moment from a game master
 * hovering the name of a campaign they are already inside.
 *
 * The ellipsis is visual only: CSS truncation does not shorten the accessible
 * name, so a screen reader reads the whole thing whether or not the tooltip is
 * reachable. That is what keeps a hover-only affordance from hiding anything.
 *
 * Rendered wherever `AppNav` is — the sticky sidebar, and the drawer below
 * 900px — so the campaign is named at every width rather than only where there
 * is room for it in the bar.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  campaign: { type: Object, required: true },
})

const title = ref(null)

/*
 * Whether the ellipsis is actually there.
 *
 * `scrollWidth` is what the name would need; `clientWidth` is what the column
 * gives it. They are equal until the text is too long, which is the same moment
 * CSS starts drawing the ellipsis — so this is the ellipsis itself answering,
 * not a guess at a character count. A guess would be wrong twice over: the face
 * is proportional, so "WWWWWW" and "iiiiii" are nothing like the same width, and
 * the column is not the same width in the sidebar as it is in the drawer.
 */
const clipped = ref(false)

function measure() {
  clipped.value = Boolean(title.value) && title.value.scrollWidth > title.value.clientWidth
}

let observer = null

onMounted(() => {
  measure()

  /*
   * The column resizes — the drawer opens at one width, the sidebar sits at
   * another — and a name that fits one may not fit the other. Guarded because
   * jsdom has no ResizeObserver: measuring once is a fine answer in a test, and
   * a missing global is not a reason for the sidebar to fail to render.
   */
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(measure)
    observer.observe(title.value)
  }

  /*
   * The display face is a self-hosted webfont with `font-display: swap`, so the
   * first paint measures the fallback and the real face arrives after it. Widths
   * change when it does, and without this the answer would be the fallback's
   * forever.
   */
  document.fonts?.ready.then(measure)
})

onBeforeUnmount(() => observer?.disconnect())

/*
 * A rename does not resize anything — the element is a block filling a fixed
 * column, so its own box is the same width whatever is written in it and the
 * observer never fires. `post` so the DOM already carries the new name by the
 * time this reads it back off the element.
 */
watch(() => props.campaign.name, measure, { flush: 'post' })

/*
 * The name, and only when the column is not showing all of it.
 *
 * A tooltip that repeats a line you are already reading teaches you that this
 * one is not worth waiting for, and then the time it *does* carry the rest of a
 * long name is the time you have stopped hovering. So a name that fits has no
 * popup at all: an empty value is how PrimeVue's directive is told to unbind
 * one, rather than show an empty box.
 */
const tooltip = computed(() => (clipped.value ? props.campaign.name : ''))
</script>

<template>
  <!--
    Just the name. No "Campaign" label above it: the nav's own Campaign section
    heading sits directly beneath this, and the same word twice in two lines
    reads as a mistake rather than as structure.
  -->
  <p ref="title" v-tooltip.right="tooltip" class="campaign-title">{{ campaign.name }}</p>
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
