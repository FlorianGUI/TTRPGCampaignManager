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
const fieldErrors = ref({})
const formError = ref(null)
const submitting = ref(false)

/*
 * Our words for a field the API refused, keyed by the name it used.
 *
 * The message in a 422 is pydantic's — "value is not a valid email address: The
 * part after the @-sign is a special-use or reserved name" — written for whoever
 * wrote the request rather than for whoever is filling in the form. That does
 * not get shown. `loc` is the half worth keeping: it is a field name, not prose,
 * and *which field* is most of what the person needs to know (#102).
 *
 * Only `email` can realistically appear from this form — `username` and
 * `password` are bare `str` in `UserCreate`, so the API objects to them only if
 * one goes missing entirely. They are here because a field with no message is
 * the failure this issue is about, and because password rules are the kind of
 * thing that arrives later.
 */
const FIELD_SAYS = {
  username: 'That username was not accepted. Try a different one.',
  email: 'That does not look like an email address we can use. Try another.',
  password: 'That password was not accepted. Try a different one.',
}

/*
 * FastAPI's 422 body is an array of `{loc, msg}`, with `loc` ending in the field
 * it objected to. `CampaignForm.vue` reads it the same way; the two are not
 * shared yet on purpose — two copies is not a pattern, and extracting on the
 * second is how the wrong shape gets frozen. The third one is when to move it.
 */
function fieldsRefusedIn(error) {
  if (!Array.isArray(error.detail)) return {}

  return Object.fromEntries(
    error.detail
      .map((problem) => String(problem?.loc?.at(-1) ?? ''))
      .filter((field) => field in FIELD_SAYS)
      .map((field) => [field, FIELD_SAYS[field]]),
  )
}

function place(error) {
  if (error?.status === 409) {
    fieldErrors.value = { username: 'That username is taken. Try another.' }
    return
  }

  // 429 is the registration limit (#63), whose message is written to be shown.
  if (error?.status === 429) {
    formError.value = error.detail
    return
  }

  if (error?.status === 422) {
    fieldErrors.value = fieldsRefusedIn(error)

    // Anything the fields cannot hold: a 422 naming something this form does not
    // render, or a body in a shape we did not expect. It has to land somewhere —
    // an error placed nowhere leaves the form looking like it did nothing at all.
    if (!Object.keys(fieldErrors.value).length) {
      formError.value = 'Something in there was not accepted.'
    }
    return
  }

  formError.value = 'Something went wrong creating the account. Try again.'
}

async function submit() {
  submitting.value = true
  fieldErrors.value = {}
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
      :error="fieldErrors.username"
    />

    <FormField
      id="signup-email"
      v-model="email"
      label="Email"
      type="email"
      autocomplete="email"
      :error="fieldErrors.email"
    />

    <FormField
      id="signup-password"
      v-model="password"
      label="Password"
      type="password"
      autocomplete="new-password"
      :error="fieldErrors.password"
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
