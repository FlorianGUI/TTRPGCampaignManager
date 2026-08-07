<script setup>
/*
 * Where a reset link lands: choose a new password, then go and sign in.
 *
 * Same arrangement as VerifyEmailView, and for the same reason — the link in the
 * message points here rather than at the API, so a mail scanner prefetching it
 * loads a page and changes nothing. It matters more here: a reset link spent by
 * a scanner is somebody locked out, not merely unverified.
 *
 * It deliberately does not sign anyone in afterwards. The reset revoked every
 * session the account had (#71), which is the point of it — signing one straight
 * back in would quietly undo the part that matters. So this ends at the login
 * page, with the password they just chose.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import FormField from '../components/FormField.vue'
import { apiFetch } from '../api/http.js'

/*
 * Read during setup rather than in onMounted, so the first paint already knows
 * whether there is a token. Deferring it renders the "this link is missing its
 * token" branch for a frame and then replaces it — a flicker that tells anyone
 * whose eye is quicker than the next tick that their link is broken.
 *
 * From `location` rather than the router, so the token never becomes part of a
 * route that could be restored or logged.
 */
const token = ref(new URLSearchParams(window.location.search).get('token'))
const password = ref('')
const submitting = ref(false)
const done = ref(false)
const formError = ref(null)

// Out of the address bar immediately. Unlike a verification link this one is still
// live while the form sits open, so it is a working credential on screen.
window.history.replaceState({}, '', window.location.pathname)

async function submit() {
  submitting.value = true
  formError.value = null

  try {
    await apiFetch('/users/reset-password', {
      method: 'POST',
      json: { token: token.value, password: password.value },
    })
    done.value = true
  } catch (error) {
    formError.value =
      error?.status === 400
        ? 'This link is no longer valid. It may have expired, or already been used — ask for a new one.'
        : 'Something went wrong. Try again shortly.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-form">
    <h1>Choose a new password</h1>

    <template v-if="done">
      <p>Your password has been changed, and every session has been signed out.</p>
      <Button as="router-link" :to="{ name: 'login' }" label="Sign in" fluid />
    </template>

    <template v-else-if="!token">
      <p>This link is missing its token. Ask for a new one and try again.</p>
      <RouterLink :to="{ name: 'forgot-password' }">Request a reset link</RouterLink>
    </template>

    <form v-else class="auth-form__fields" novalidate @submit.prevent="submit">
      <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

      <FormField
        id="reset-password"
        v-model="password"
        label="New password"
        type="password"
        autocomplete="new-password"
      />

      <Button type="submit" label="Change my password" :loading="submitting" fluid />

      <p class="auth-form__aside">
        <RouterLink :to="{ name: 'forgot-password' }">Ask for a new link</RouterLink>
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

.auth-form :deep(button),
.auth-form :deep(a.p-button) {
  min-height: 44px;
}
</style>
