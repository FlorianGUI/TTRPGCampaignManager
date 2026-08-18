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
import { t } from '../i18n/index.js'

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
 *
 * Those two share one sentence, and it names no field. It does not need to: the
 * message renders under the label and `FormField` ties it there with
 * `aria-describedby`, so the placement says which field it is — which is the
 * whole point of this issue. Naming it in the words as well would be saying it
 * twice, and would be two sentences to keep in step for a case that says the
 * same thing either way. `email` keeps its own because it says something more
 * than "no": that the address itself is the problem.
 */
const NOT_ACCEPTED = 'signup.error.notAccepted'

const FIELD_SAYS = {
  username: NOT_ACCEPTED,
  email: 'signup.error.email',
  password: NOT_ACCEPTED,
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
      .map((field) => [field, t(FIELD_SAYS[field])]),
  )
}

function place(error) {
  if (error?.status === 409) {
    fieldErrors.value = { username: t('signup.error.usernameTaken') }
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
      formError.value = t('signup.error.something')
    }
    return
  }

  formError.value = t('signup.error.generic')
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
    <h1>{{ t('signup.title') }}</h1>

    <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

    <FormField
      id="signup-username"
      v-model="username"
      :label="t('signup.username')"
      autocomplete="username"
      :error="fieldErrors.username"
    />

    <FormField
      id="signup-email"
      v-model="email"
      :label="t('signup.email')"
      type="email"
      autocomplete="email"
      :error="fieldErrors.email"
    />

    <FormField
      id="signup-password"
      v-model="password"
      :label="t('signup.password')"
      type="password"
      autocomplete="new-password"
      :error="fieldErrors.password"
    />

    <Button type="submit" :label="t('signup.submit')" :loading="submitting" fluid />

    <p class="auth-form__aside">
      {{ t('signup.haveOne') }}
      <RouterLink :to="{ name: 'login' }">{{ t('signup.signIn') }}</RouterLink
      >.
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
