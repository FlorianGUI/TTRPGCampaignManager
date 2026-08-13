<script setup>
/*
 * The campaign's name, at the head of the navigation that belongs to it — and
 * the way into its structure.
 *
 * #79 made this deliberately unpressable, and the note it left is worth quoting
 * before overruling it: *"The tag it replaces looked pressable and mostly was
 * not, which is the worst of both: a thing that invites a click and answers with
 * nothing."* The complaint was **an unkept promise, not a pressable name**. It
 * was resolved by removing the affordance because there was nothing to point at;
 * #88 gives it somewhere to go, so it is resolved the other way instead. The
 * conditions that came with that are met here: it looks pressable, it carries
 * `aria-current` on the page it leads to, and this comment was rewritten rather
 * than deleted.
 *
 * It also stops being duplicated. The nav's Campaign section used to sit
 * directly beneath this with the word "Campaign" in it, so the sidebar named the
 * campaign and then announced the category on the next line. The name *is* the
 * section head now, and `Library` and `Characters` keep their small-caps labels
 * — those are categories and this is a proper noun, which is a difference worth
 * showing rather than flattening.
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
import { RouterLink } from 'vue-router'

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
 *
 * It survives this becoming a control. Hovering now means two things where the
 * name is clipped, which is untidy — but the alternative is a name you can
 * neither read in full nor identify, and the popup is conditional so it does not
 * appear on the names that do fit.
 */
const tooltip = computed(() => (clipped.value ? props.campaign.name : ''))

const structure = computed(() => ({
  name: 'campaign-structure',
  params: { campaignId: props.campaign.id },
}))
</script>

<template>
  <!--
    `custom`, so the ref lands on a real element rather than on the component —
    the measurement above reads `scrollWidth` off the node, and a component
    instance has none.
  -->
  <RouterLink v-slot="{ href, navigate, isActive }" :to="structure" custom>
    <a
      ref="title"
      v-tooltip.right="tooltip"
      class="campaign-title"
      :href="href"
      :aria-current="isActive ? 'page' : undefined"
      @click="navigate"
      >{{ campaign.name }}</a
    >
  </RouterLink>
</template>

<style scoped>
/*
 * The largest thing in the column, and the only one in the display face, so the
 * eye lands on where it is before it starts reading where it can go.
 *
 * It reads as pressable now, which #79's note demanded of anything that is: a
 * pointer, a hover that responds, and a focus ring. What it does not get is a
 * chevron or a border — the destination is the campaign's own structure, which
 * is where the name already implied it would take you.
 */
.campaign-title {
  display: block;
  overflow: hidden;
  /* Aligns with the nav items below rather than with the column edge, so the
     title and the list it heads share a left edge. */
  margin: 0 0 var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-left: 2px solid transparent;
  border-radius: var(--p-border-radius-sm);
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  font-size: var(--step-0);
  line-height: 1.15;
  color: var(--p-primary-color);
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.campaign-title:hover {
  background: var(--p-navigation-item-hover-background);
}

.campaign-title:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

/*
 * The active state matches a nav item's — border, weight and background — so the
 * head of the list and the list itself say "you are here" the same way, and it
 * survives without colour.
 */
.campaign-title[aria-current='page'] {
  border-left-color: var(--p-grimoire-context-campaign);
  background: var(--p-navigation-item-active-background);
}

@media (pointer: coarse) {
  .campaign-title {
    min-height: 44px;
    padding-block: var(--space-2);
  }
}
</style>
