<script setup>
/*
 * Create an account. Registering signs you in (#33), so there is no login call
 * chained on and one place for it to fail rather than two.
 *
 * Unlike sign-in, one error here does belong on a field: a 409 is a taken
 * username and nothing else. `/users/register` has exactly one way to conflict,
 * so the status is the discriminator — keying off the detail string would break
 * the day someone rewords it, and the API deliberately sends no error code.
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import FormField from '../components/FormField.vue'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const usernameError = ref(null)
const formError = ref(null)
const submitting = ref(false)

function place(error) {
  if (error?.status === 409) {
    usernameError.value = 'That username is taken. Try another.'
    return
  }

  // 429 is the registration limit (#63), whose message is written to be shown.
  if (error?.status === 429) {
    formError.value = error.detail
    return
  }

  // 422 is a shape the API validated and we did not — a malformed email, most
  // likely. `detail` is an array of field problems here rather than a sentence,
  // so it is not something to print at someone.
  if (error?.status === 422) {
    formError.value = 'Check the details above — something there was not accepted.'
    return
  }

  formError.value = 'Something went wrong creating the account. Try again.'
}

async function submit() {
  submitting.value = true
  usernameError.value = null
  formError.value = null

  try {
    await auth.register(username.value, email.value, password.value)
    router.replace('/')
  } catch (error) {
    place(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="auth-form" novalidate @submit.prevent="submit">
    <h1>Create an account</h1>

    <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

    <FormField
      id="signup-username"
      v-model="username"
      label="Username"
      autocomplete="username"
      :error="usernameError"
    />

    <FormField id="signup-email" v-model="email" label="Email" type="email" autocomplete="email" />

    <FormField
      id="signup-password"
      v-model="password"
      label="Password"
      type="password"
      autocomplete="new-password"
    />

    <Button type="submit" label="Create account" :loading="submitting" fluid />

    <p class="auth-form__aside">
      Already have one?
      <RouterLink :to="{ name: 'login' }">Sign in</RouterLink>.
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
