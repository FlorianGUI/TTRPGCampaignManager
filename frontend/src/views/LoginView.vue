<script setup>
/*
 * Sign in. The store does the work (#34); this places the fields, the errors
 * and where you land afterwards.
 *
 * The errors are the interesting part. The API is careful not to say whether a
 * username exists — a 401 is the same for an unknown account as for a wrong
 * password — so the message here has to be equally uninformative, or the
 * frontend hands out what the backend withheld. It sits above the form rather
 * than on a field for the same reason: pinning it to "password" would be a
 * claim that the username was fine.
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import FormField from '../components/FormField.vue'
import { useAuthStore } from '../stores/auth.js'
import { safeRedirect } from '../router/redirect.js'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const formError = ref(null)
const submitting = ref(false)

function messageFor(error) {
  // 429 carries a sentence the backend wrote to be safe to show — fixed per
  // endpoint, with nothing about the account in it (#63). Showing it beats
  // inventing one, and it is the only case where the user can act on the wait.
  if (error?.status === 429) return error.detail
  if (error?.status === 401) return 'That username and password do not match an account.'

  return 'Something went wrong signing in. Try again.'
}

async function submit() {
  submitting.value = true
  formError.value = null

  try {
    await auth.logIn(username.value, password.value)
    router.replace(safeRedirect(route.query.redirect))
  } catch (error) {
    formError.value = messageFor(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="auth-form" novalidate @submit.prevent="submit">
    <h1>Sign in</h1>

    <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

    <FormField id="login-username" v-model="username" label="Username" autocomplete="username" />

    <FormField
      id="login-password"
      v-model="password"
      label="Password"
      type="password"
      autocomplete="current-password"
    />

    <Button type="submit" label="Sign in" :loading="submitting" fluid />

    <p class="auth-form__aside">
      No account yet?
      <RouterLink :to="{ name: 'signup' }">Create one</RouterLink>.
    </p>

    <p class="auth-form__aside">
      <RouterLink :to="{ name: 'forgot-password' }">Forgot your password?</RouterLink>
    </p>
  </form>
</template>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-5);
}

.auth-form h1 {
  margin: 0;
  font-size: 1.4rem;
  text-align: center;
}

.auth-form__error {
  margin: 0;
  color: var(--p-grimoire-form-error-color);
}

.auth-form__aside {
  margin: 0;
  text-align: center;
  font-size: 0.95rem;
}

.auth-form :deep(button) {
  min-height: 44px;
}
</style>
