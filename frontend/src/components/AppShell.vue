<script setup>
import { nextTick, onScopeDispose, ref, watch } from 'vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import { useRouter } from 'vue-router'
import AppNav from './AppNav.vue'
import ChromeActions from './ChromeActions.vue'
import VerificationNotice from './VerificationNotice.vue'
import { forgetCurrentCampaign } from '../stores/currentCampaign.js'

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

const router = useRouter()

/*
 * Leaving a campaign, which is the other half of #59's decision to put home
 * outside this shell: without a way back, the chooser is reachable only by
 * signing out, and that is not a way back.
 *
 * Forgetting is what makes `/` show the chooser rather than bouncing straight
 * back into the campaign just left. The rule lives in the id, not in a flag —
 * see `enterRememberedCampaign` in router/routes.js.
 */
function leaveCampaign() {
  forgetCurrentCampaign()
  router.push({ name: 'home' })
}

/* Kept in sync with the max-width: 900px breakpoint below. */
const WIDE_QUERY = '(min-width: 901px)'

const navOpen = ref(false)
const searchOpen = ref(false)
const searchField = ref(null)

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

watch(searchOpen, async (open) => {
  if (!open) return
  await nextTick()
  searchField.value?.$el?.focus()
})
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
          Where you are, and the way out of it. On the left, next to the brand,
          rather than in the actions cluster: that row ends in sign out, and two
          adjacent leave-shaped icons on a phone is a mis-tap that ends the
          session instead of the campaign.

          It is also where #48's switcher goes — the chip already names the
          current campaign, so that issue adds a dropdown to something that
          exists rather than reopening the placement question.
        -->
        <div v-if="campaign" class="shell__campaign">
          <span class="shell__campaign-name">{{ campaign.name }}</span>
          <!--
            Settings for the campaign you are in (#49). It sits on the chip
            rather than in the actions cluster because it belongs to *this*
            campaign, not to the app — and beside a name is where you look for
            the thing that changes it.

            A cog and a × read as different actions, so the mis-tap the note
            below is about does not apply between these two. If the bar does end
            up carrying more than it can, #79 owns that.
          -->
          <Button
            class="shell__campaign-settings"
            as="router-link"
            :to="{ name: 'campaign-settings', params: { campaignId: campaign.id } }"
            text
            rounded
            icon="pi pi-cog"
            :aria-label="`Settings for ${campaign.name}`"
            title="Campaign settings"
          />
          <Button
            class="shell__campaign-leave"
            text
            rounded
            icon="pi pi-times"
            :aria-label="`Leave ${campaign.name}`"
            title="Back to your campaigns"
            @click="leaveCampaign"
          />
        </div>

        <div class="shell__search">
          <InputText placeholder="Search sources, NPCs, locations…" fluid />
        </div>

        <div class="shell__actions">
          <Button
            class="shell__search-toggle"
            text
            rounded
            icon="pi pi-search"
            aria-label="Search"
            aria-controls="shell-search-row"
            :aria-expanded="searchOpen"
            @click="searchOpen = !searchOpen"
          />
          <!--
            Density, theme and sign out, shared with BareLayout's bar so the two
            cannot drift apart. Sign out is last in that row and never folds:
            the priority ladder (#25) drops the wordmark and then the search
            field as the bar narrows, because both have somewhere else to go —
            the mark still carries the brand, and search reopens as a row
            underneath. An account you cannot leave on a phone is worse than a
            cramped bar.
          -->
          <ChromeActions />
        </div>
      </div>

      <div v-if="searchOpen" id="shell-search-row" class="shell__search-row">
        <InputText
          ref="searchField"
          placeholder="Search sources, NPCs, locations…"
          fluid
          @keydown.esc="searchOpen = false"
        />
      </div>
    </header>

    <!-- Under the bar and above everything else, so it is seen once per page rather
         than competing with the content it sits over. -->
    <VerificationNotice />

    <div class="shell__body">
      <nav class="shell__sidebar texture-grain" aria-label="Campaign">
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

/*
 * A border rather than a fill: the chip names a place, it is not a control —
 * only the cog and the × inside it are pressable. Giving the whole thing a
 * button's surface would invite people to click the name and wonder why nothing
 * happened — until #48, when the name becomes the switcher and that expectation
 * is right.
 */
.shell__campaign {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  min-width: 0;
  padding-left: var(--space-3);
  border: 1px solid var(--p-grimoire-chrome-border-color);
  border-radius: var(--p-border-radius-sm);
  background: var(--p-grimoire-chrome-raised-background);
}

.shell__campaign-name {
  overflow: hidden;
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  font-size: var(--step--1);
  letter-spacing: 0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell__search {
  flex: 1;
  max-width: 26rem;
}

.shell__search-row {
  padding: 0 var(--space-4) var(--space-3);
}

.shell__actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-1);
}

/*
 * The same 44px floor AppNav sets, for the icon-only targets this component
 * owns. The shared cluster sets its own — see ChromeActions.
 *
 * Coarse pointers only: on a mouse the default size is comfortable, and forcing
 * 44px there would space the bar out for no one's benefit.
 */
@media (pointer: coarse) {
  .shell__nav-toggle,
  .shell__search-toggle,
  .shell__campaign-settings,
  .shell__campaign-leave {
    min-height: 44px;
    min-width: 44px;
  }
}

/* Both toggles are small-screen only; the wide layout shows the real controls. */
.shell__nav-toggle,
.shell__search-toggle,
.shell__search-row {
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
   * Priority on one row: brand + nav + theme survive, the search field folds
   * down to an icon that opens a full-width row underneath.
   */
  .shell__search {
    display: none;
  }

  .shell__search-toggle {
    display: inline-flex;
  }

  .shell__search-row {
    display: block;
  }

  .shell__brand span {
    /* The mark carries the brand; the wordmark is what has to give first. */
    display: none;
  }

  /*
   * The chip is the next rung down that ladder. It keeps its place — leaving a
   * campaign has to stay possible on a phone — but gives up most of its width,
   * because the drawer names the campaign in full a tap away.
   */
  .shell__campaign-name {
    max-width: 6rem;
  }
}
</style>
