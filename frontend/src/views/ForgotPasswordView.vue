<script setup>
/*
 * Ask for a reset link.
 *
 * One field, and it takes either an email address or a username (#71), because
 * someone who has forgotten their password may equally not remember which
 * address they signed up with — and the login page asks for a username, so
 * demanding an address here would be a second thing to remember at the worst
 * possible moment.
 *
 * The API answers 204 whether or not anything matched, on purpose: it is the one
 * unauthenticated endpoint that takes an identifier, so it is the one that could
 * be asked whether an account exists. This page must not undo that. There is no
 * field-level error, no different wording on the two paths, and no hint in the
 * copy — the message below is the only thing it ever says.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import FormField from '../components/FormField.vue'
import { apiFetch } from '../api/http.js'
import { t } from '../i18n/index.js'

const identifier = ref('')
const submitting = ref(false)
const sent = ref(false)
const formError = ref(null)

async function submit() {
  submitting.value = true
  formError.value = null

  try {
    await apiFetch('/users/forgot-password', {
      method: 'POST',
      json: { identifier: identifier.value },
    })
    sent.value = true
  } catch (error) {
    // 429 has the limiter's own sentence, which is safe to show and says nothing
    // about whether anything matched. Anything else is a plain retry.
    formError.value = error?.status === 429 ? error.detail : t('forgot.error.generic')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-form">
    <h1>{{ t('forgot.title') }}</h1>

    <template v-if="sent">
      <!--
        Deliberately says "if", and says it whatever happened. Naming the address
        back, or confirming that an account was found, would hand out exactly what
        the endpoint refuses to.
      -->
      <p>{{ t('forgot.sent') }}</p>
      <RouterLink :to="{ name: 'login' }">{{ t('forgot.backToSignIn') }}</RouterLink>
    </template>

    <form v-else class="auth-form__fields" novalidate @submit.prevent="submit">
      <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

      <FormField
        id="forgot-identifier"
        v-model="identifier"
        :label="t('forgot.identifier')"
        autocomplete="username"
      />

      <Button type="submit" :label="t('forgot.submit')" :loading="submitting" fluid />

      <p class="auth-form__aside">
        {{ t('forgot.remembered') }}
        <RouterLink :to="{ name: 'login' }">{{ t('forgot.signIn') }}</RouterLink
        >.
      </p>
    </form>
  </div>
</template>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-5);
  text-align: center;
}

.auth-form__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  text-align: left;
}

.auth-form h1 {
  margin: 0;
  font-size: 1.4rem;
}

.auth-form p {
  margin: 0;
}

.auth-form__error {
  color: var(--p-grimoire-form-error-color);
}

.auth-form__aside {
  text-align: center;
  font-size: 0.95rem;
}

.auth-form :deep(button) {
  min-height: 44px;
}
</style>
