<script setup>
import { onScopeDispose, ref } from 'vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import AppNav from './AppNav.vue'
import CampaignTitle from './CampaignTitle.vue'
import CampaignNav from './narrative/CampaignNav.vue'
import ChromeActions from './ChromeActions.vue'
import VerificationNotice from './VerificationNotice.vue'

/*
 * Dark leather chrome (top bar + sidebar) framing a parchment reading surface.
 * The chrome stays dark-ish in both themes; only the content area really flips.
 *
 * Scroll model (issue #25): the document scrolls, not an inner pane. The top
 * bar is sticky at the top and the sidebar is sticky just under it, which keeps
 * the framing without a nested scroller. The sidebar only grows its own
 * scrollbar when the nav is genuinely taller than the viewport.
 *
 * Below WIDE_QUERY the sidebar is replaced by a drawer rather than hidden — a
 * hidden nav with no replacement makes every context unreachable.
 */

defineProps({
  sections: { type: Array, required: true },
  active: { type: String, default: null },
  // Null while the list is still in flight, and on any route that is not inside
  // a campaign. The chip is simply absent until there is a name to put in it.
  campaign: { type: Object, default: null },
})

/*
 * Leaving a campaign moved to `ChromeActions` with the rest of #79's menu. It is
 * still the other half of #59's decision to put home outside this shell —
 * without a way back the chooser is reachable only by signing out, and that is
 * not a way back — but the way back is now an item rather than an icon.
 */

/* Kept in sync with the max-width: 900px breakpoint below. */
const WIDE_QUERY = '(min-width: 901px)'

const navOpen = ref(false)

/*
 * The sidebar and the drawer are both in the DOM, each hidden by CSS at the
 * other's breakpoint. Resizing past the breakpoint with the drawer open would
 * otherwise leave two navs on screen.
 */
if (typeof window !== 'undefined' && window.matchMedia) {
  const wide = window.matchMedia(WIDE_QUERY)
  const closeNav = (event) => {
    if (event.matches) navOpen.value = false
  }

  wide.addEventListener('change', closeNav)
  onScopeDispose(() => wide.removeEventListener('change', closeNav))
}
</script>

<template>
  <div class="shell">
    <header class="shell__topbar texture-grain">
      <div class="shell__bar">
        <Button
          class="shell__nav-toggle"
          text
          rounded
          icon="pi pi-bars"
          aria-label="Open navigation"
          :aria-expanded="navOpen"
          @click="navOpen = true"
        />

        <div class="shell__brand">
          <i class="pi pi-book" aria-hidden="true" />
          <span>Campaign Manager</span>
        </div>

        <!--
          The campaign is named in the sidebar now, at the head of the navigation
          it belongs to, rather than as a tag up here beside the brand. This row
          is about the app; the campaign is not.
        -->

        <div class="shell__actions">
          <!--
            Who you are, and the menu behind it — shared with BareLayout's bar so
            the two cannot drift apart. The campaign is the one thing that
            differs between them, and it travels as a prop rather than forking
            the component: inside a campaign the menu grows "Campaign settings"
            and "Close campaign", and on the chooser it simply does not.
          -->
          <ChromeActions :campaign="campaign" />
        </div>
      </div>
    </header>

    <!-- Under the bar and above everything else, so it is seen once per page rather
         than competing with the content it sits over. -->
    <VerificationNotice />

    <div class="shell__body">
      <nav class="shell__sidebar texture-grain" aria-label="Campaign">
        <!--
          The campaign's name, then what it holds, then the rest of the app. The
          name heads its own list rather than sitting above a section labelled
          "Campaign" — the same word twice in two lines read as a mistake.
        -->
        <CampaignTitle v-if="campaign" :campaign="campaign" />
        <CampaignNav v-if="campaign" :campaign="campaign" />
        <AppNav :sections="sections" :active="active" />
      </nav>

      <main class="shell__content">
        <slot />
      </main>
    </div>

    <Drawer
      v-model:visible="navOpen"
      class="shell__drawer"
      header="Campaign"
      :pt="{ root: { 'aria-label': 'Campaign' } }"
    >
      <!--
        The name travels with the nav rather than staying behind in a bar that no
        longer carries it: below the sidebar breakpoint this drawer is the only
        place the campaign is named at all.
      -->
      <CampaignTitle v-if="campaign" :campaign="campaign" />
      <CampaignNav v-if="campaign" :campaign="campaign" @navigate="navOpen = false" />
      <AppNav :sections="sections" :active="active" @navigate="navOpen = false" />
    </Drawer>
  </div>
</template>

<style scoped>
.shell__topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--p-grimoire-chrome-background);
  border-bottom: 1px solid var(--p-grimoire-chrome-border-color);
}

.shell__bar {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  height: var(--shell-topbar);
  padding: 0 var(--space-4);
}

.shell__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
  color: var(--p-primary-color);
}

.shell__actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-1);
}

/*
 * The same 44px floor AppNav sets, for the one icon-only target this component
 * still owns. The shared cluster sets its own — see ChromeActions.
 *
 * A touch guideline, not a density workaround: this floor predates #79 removing
 * the compact scale and outlives it unchanged, because a finger is the same size
 * whatever the spacing tokens say.
 *
 * Coarse pointers only: on a mouse the default size is comfortable, and forcing
 * 44px there would space the bar out for no one's benefit.
 */
@media (pointer: coarse) {
  .shell__nav-toggle {
    min-height: 44px;
    min-width: 44px;
  }
}

/* Small-screen only; the wide layout shows the sidebar itself. */
.shell__nav-toggle {
  display: none;
}

.shell__body {
  display: flex;
}

.shell__sidebar {
  flex: 0 0 var(--shell-sidebar);
  padding: var(--space-3) var(--space-2);
  background: var(--p-grimoire-chrome-background);
  border-right: 1px solid var(--p-grimoire-chrome-border-color);
  /*
   * Sticky rather than a scroll pane: the column tracks the viewport under the
   * top bar, and overflow-y only produces a scrollbar for a nav that really is
   * taller than the screen.
   */
  position: sticky;
  top: var(--shell-topbar);
  height: calc(100dvh - var(--shell-topbar));
  overflow-y: auto;
}

.shell__content {
  flex: 1;
  min-width: 0;
  padding: var(--space-6) var(--space-7);
  background: var(--p-content-background);
  /* Short pages still fill the frame, so the reading surface never stops short. */
  min-height: calc(100dvh - var(--shell-topbar));
}

.shell__drawer :deep(.p-drawer-content) {
  padding-inline: var(--space-2);
}

/* ---- Tablet ---------------------------------------------------------- */

@media (max-width: 1100px) {
  .shell {
    --shell-sidebar: 13rem;
  }

  .shell__content {
    padding: var(--space-5) var(--space-5);
  }
}

/* ---- Below the sidebar breakpoint ------------------------------------ */

@media (max-width: 900px) {
  .shell__sidebar {
    display: none;
  }

  .shell__nav-toggle {
    display: inline-flex;
  }

  .shell__bar {
    gap: var(--space-3);
  }

  .shell__content {
    padding: var(--space-4);
  }
}

/* ---- Phone ----------------------------------------------------------- */

@media (max-width: 640px) {
  /*
   * #25's priority ladder had four rungs and search took two of them. What is
   * left on this row is the nav toggle, the brand and the account trigger — the
   * campaign moved into the sidebar and the drawer — so the ladder is one rung
   * long: the wordmark goes, because the mark still carries the brand. The
   * username gives up width in ChromeActions rather than here.
   *
   * Nothing folds away entirely any more. That is the point of the rework: every
   * control the bar still has is one there is no second way to reach.
   */
  .shell__brand span {
    display: none;
  }
}
</style>
