<script setup>
/*
 * The chrome for the pages that sit *above* any campaign — today just the
 * chooser at `/`.
 *
 * Not `AppShell`, and that is the decision issue #59 exists to make. The shell's
 * sidebar navigates a campaign, and on this screen you have not chosen one: its
 * Campaign section would be four items that lead nowhere. Suppressing them was
 * the alternative, and a nav of dimmed links reads as broken rather than as
 * not-yet-available.
 *
 * Not `AuthLayout` either, though that was the cheaper guess. This page needs a
 * way to sign out — an account you cannot leave is worse than an extra
 * component — and the auth layout has no bar to put one in, only a brand and a
 * 24rem column. What is shared with it is the idea rather than the markup: no
 * card, no shadow, depth from the rule and the surface (see the elevation note
 * in frontend/README.md).
 */
import ChromeActions from './ChromeActions.vue'
import { t } from '../i18n/index.js'
</script>

<template>
  <div class="bare">
    <header class="bare__topbar texture-grain">
      <div class="bare__brand">
        <i class="pi pi-book" aria-hidden="true" />
        <span>{{ t('app.name') }}</span>
      </div>

      <ChromeActions class="bare__actions" />
    </header>

    <main class="bare__content">
      <div class="bare__column">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.bare__topbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--shell-topbar);
  padding: 0 var(--space-4);
  background: var(--p-grimoire-chrome-background);
  border-bottom: 1px solid var(--p-grimoire-chrome-border-color);
}

.bare__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
  color: var(--p-primary-color);
}

.bare__actions {
  margin-left: auto;
}

/*
 * The chooser sits on the chrome surface rather than the content one. It is a
 * doorway, not a page of the book — the parchment starts on the other side of
 * it, which is what makes entering a campaign feel like entering something.
 */
.bare__content {
  min-height: calc(100dvh - var(--shell-topbar));
  padding: var(--space-7) var(--space-5) var(--space-6);
  background: var(--p-grimoire-chrome-background);
}

.bare__column {
  width: 100%;
  max-width: 46rem;
  margin-inline: auto;
}

@media (max-width: 640px) {
  .bare__content {
    padding: var(--space-5) var(--space-4);
  }

  /* The mark carries the brand; the wordmark is what has to give first (#25). */
  .bare__brand span {
    display: none;
  }
}
</style>
