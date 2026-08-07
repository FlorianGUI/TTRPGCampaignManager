<script setup>
import { nextTick, onScopeDispose, ref, watch } from 'vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import { useRouter } from 'vue-router'
import AppNav from './AppNav.vue'
import VerificationNotice from './VerificationNotice.vue'
import { storeToRefs } from 'pinia'
import { useThemeStore } from '../stores/theme.js'
import { useAuthStore } from '../stores/auth.js'

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
})

// storeToRefs keeps the two values reactive; actions are taken off the store
// directly, which is the Pinia idiom and what plain destructuring would break.
const themeStore = useThemeStore()
const { theme, density } = storeToRefs(themeStore)
const { toggleTheme, toggleDensity } = themeStore

/*
 * Signing out revokes server-side before it clears anything locally — clearing
 * only the client would leave a working refresh cookie behind, which is the one
 * way to log out that does not log you out (#35).
 *
 * `POST /users/logout` answers 204 whether or not there was a session, so there
 * is no failure state to design here: no confirmation dialog, no error
 * affordance, no disabled-while-pending. It ends the session on this device
 * only — if the copy ever says "everywhere", that is a different endpoint.
 */
const auth = useAuthStore()
const router = useRouter()

async function signOut() {
  await auth.logOut()
  router.push({ name: 'login' })
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
            Density is a pointer-precision affordance: compact shrinks targets
            that are already at the 44px floor on touch, so it is not offered
            there (issue #25).
          -->
          <Button
            class="shell__density-toggle"
            text
            rounded
            :icon="density === 'compact' ? 'pi pi-bars' : 'pi pi-align-justify'"
            :aria-label="`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} density`"
            :title="`Density: ${density}`"
            @click="toggleDensity"
          />
          <Button
            text
            rounded
            :icon="theme === 'candlelight' ? 'pi pi-sun' : 'pi pi-moon'"
            :aria-label="`Switch to ${theme === 'candlelight' ? 'parchment' : 'candlelight'} theme`"
            :title="`Theme: ${theme}`"
            @click="toggleTheme"
          />
          <!--
            Last in the row, and it never folds. The priority ladder (#25) drops
            the wordmark and then the search field as the bar narrows, because
            both have somewhere else to go — the mark still carries the brand,
            and search reopens as a row underneath. Sign out has no such
            fallback: an account you cannot leave on a phone is worse than a
            cramped bar, so it holds its place at every width.

            Last rather than first because it is the most consequential and the
            least frequent control here, and it should not sit where a thumb
            reaching for the theme toggle lands.
          -->
          <Button
            class="shell__sign-out"
            text
            rounded
            icon="pi pi-sign-out"
            aria-label="Sign out"
            title="Sign out"
            @click="signOut"
          />
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
 * The same 44px floor AppNav sets. These are icon-only targets with no label to
 * widen them, so they are the smallest things in the chrome — and sign out is
 * now among them, which is not a control to make people aim at twice.
 *
 * Coarse pointers only: on a mouse the default size is comfortable, and forcing
 * 44px there would space the bar out for no one's benefit.
 */
@media (pointer: coarse) {
  .shell__actions :deep(button) {
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
}

@media (pointer: coarse) {
  .shell__density-toggle {
    display: none;
  }
}
</style>
