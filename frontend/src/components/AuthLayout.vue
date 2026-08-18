<script setup>
/*
 * The chrome for pages a signed-out visitor can reach: brand, a single column,
 * and nothing else.
 *
 * Deliberately not AppShell. The shell's sidebar navigates a campaign, and a
 * campaign is exactly what someone who has not signed in does not have — a
 * login page framed by it would offer a nav where every item is a dead end.
 *
 * No card, no shadow. Depth here comes from the rule under the brand and the
 * parchment surface itself, the same way it does everywhere else (see the
 * elevation note in frontend/README.md).
 */
import { t } from '../i18n/index.js'
</script>

<template>
  <div class="auth">
    <main class="auth__panel">
      <div class="auth__brand">
        <i class="pi pi-book" aria-hidden="true" />
        <span>{{ t('app.name') }}</span>
      </div>

      <hr class="rule-double" />

      <slot />
    </main>
  </div>
</template>

<style scoped>
.auth {
  display: flex;
  justify-content: center;
  /* Off-centre vertically: a form sitting on the optical centre reads as
     floating, and the eye expects it slightly above the true middle. */
  align-items: flex-start;
  min-height: 100dvh;
  padding: var(--space-7) var(--space-4);
  background: var(--p-content-background);
}

.auth__panel {
  width: 100%;
  max-width: 24rem;
}

.auth__brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: var(--grimoire-font-display);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--p-primary-color);
}

@media (max-width: 640px) {
  .auth {
    padding: var(--space-5) var(--space-4);
  }
}
</style>
