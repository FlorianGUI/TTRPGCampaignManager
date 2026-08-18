<script setup>
/*
 * "Your address is not confirmed", and a way to fix it.
 *
 * A notice rather than a wall, because verification is advisory (#38): an
 * unverified account is a working account, and what verification gates is
 * linking a provider identity later — not the door.
 *
 * Dismissible for the session only, and it comes back on reload. Permanent
 * dismissal would mean someone can bury the one prompt that gets them a
 * verified address; nagging on every navigation would be worse than the problem.
 * In memory rather than localStorage, deliberately: the state is "I have
 * acknowledged this today", not a preference.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import { apiFetch } from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'
import { t } from '../i18n/index.js'

const auth = useAuthStore()

const dismissed = ref(false)
const sending = ref(false)
const outcome = ref(null)

async function resend() {
  sending.value = true
  outcome.value = null

  try {
    await apiFetch('/users/verify-email/resend', { method: 'POST', token: auth.token })
    outcome.value = { kind: 'sent', message: t('verification.sent') }
  } catch (error) {
    // The 429 carries a sentence the backend wrote to be shown, and it is the only
    // failure here the reader can act on. Everything else gets a plain retry.
    outcome.value = {
      kind: 'failed',
      message: error?.status === 429 ? error.detail : t('verification.failed'),
    }
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <aside
    v-if="auth.isSignedIn && !auth.user.email_verified && !dismissed"
    class="notice"
    role="status"
  >
    <p class="notice__text">
      <template v-if="outcome">{{ outcome.message }}</template>
      <template v-else>{{ t('verification.text') }}</template>
    </p>

    <div class="notice__actions">
      <Button
        v-if="outcome?.kind !== 'sent'"
        size="small"
        text
        :loading="sending"
        :label="t('verification.resend')"
        @click="resend"
      />
      <Button
        size="small"
        text
        icon="pi pi-times"
        :aria-label="t('verification.dismiss')"
        @click="dismissed = true"
      />
    </div>
  </aside>
</template>

<style scoped>
.notice {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--p-grimoire-chrome-raised-background);
  border-bottom: 1px solid var(--p-grimoire-chrome-border-color);
}

.notice__text {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: 0.95rem;
}

.notice__actions {
  display: flex;
  gap: var(--space-1);
  flex-shrink: 0;
}

@media (pointer: coarse) {
  .notice__actions :deep(button) {
    min-height: 44px;
    min-width: 44px;
  }
}

@media (max-width: 640px) {
  .notice {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-2);
  }
}
</style>
