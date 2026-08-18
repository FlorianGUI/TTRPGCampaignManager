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
import { DISCORD_SIGN_IN_URL, GOOGLE_SIGN_IN_URL, rememberDestination } from '../api/sso.js'
import { t } from '../i18n/index.js'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const formError = ref(null)
const submitting = ref(false)

/*
 * Why they are here, when they did not choose to be.
 *
 * Read once, on arrival, and cleared by the store as it is read: this explains
 * one sign-out, and a message that lingered would greet someone opening the
 * login page a week later. Nothing to show when the visitor simply navigated
 * here, which is the ordinary case.
 *
 * The sentence is the server's. The one thing added is the wait, because a
 * person told to try again with no idea when retries immediately — which is the
 * traffic the limit was objecting to in the first place (#68).
 */
const signedOut = auth.takeSignedOutReason()

function waitFor(seconds) {
  if (seconds < 60) return t('login.wait.seconds', { count: seconds })

  const minutes = Math.ceil(seconds / 60)

  return minutes === 1 ? t('login.wait.minute') : t('login.wait.minutes', { count: minutes })
}

function messageFor(error) {
  // 429 carries a sentence the backend wrote to be safe to show — fixed per
  // endpoint, with nothing about the account in it (#63). Showing it beats
  // inventing one, and it is the only case where the user can act on the wait.
  if (error?.status === 429) return error.detail
  if (error?.status === 401) return t('login.error.credentials')

  return t('login.error.generic')
}

/*
 * Stash the destination before leaving this origin.
 *
 * The Discord round trip is a full navigation away and back, so `?redirect=`
 * does not survive it. Without this, following a deep link while signed out
 * would send you to Discord and set you down at the home page, having forgotten
 * what you clicked.
 *
 * On the anchor's click rather than on mount, so a visitor who signs in with a
 * password instead leaves nothing behind in storage.
 */
function leaveForProvider() {
  rememberDestination(route.query.redirect)
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
    <h1>{{ t('login.title') }}</h1>

    <p v-if="signedOut?.message" class="auth-form__notice" role="status">
      {{ signedOut.message }}
      <!-- Falsy covers both the header the server did not send and a wait of
           zero seconds, which is not a wait worth a sentence. -->
      <template v-if="signedOut.retryAfter">
        {{ t('login.signedOut.retry', { wait: waitFor(signedOut.retryAfter) }) }}
      </template>
    </p>

    <p v-if="formError" class="auth-form__error" role="alert">{{ formError }}</p>

    <FormField
      id="login-username"
      v-model="username"
      :label="t('login.username')"
      autocomplete="username"
    />

    <FormField
      id="login-password"
      v-model="password"
      :label="t('login.password')"
      type="password"
      autocomplete="current-password"
    />

    <Button type="submit" :label="t('login.submit')" :loading="submitting" fluid />

    <p class="auth-form__or">
      <span>{{ t('login.or') }}</span>
    </p>

    <!--
      Anchors, and they have to stay anchors. A consent screen is a page at the
      provider's own address that the person has to be able to read and trust,
      so this is a top-level navigation rather than a fetch — neither Google nor
      Discord will be framed, and a consent prompt nobody can see is not consent.

      `rel` because this leaves the app: `noopener` denies the destination a
      handle on this window, and `noreferrer` keeps the URL we came from — which
      carries `?redirect=` — out of the provider's logs.

      Discord first, deliberately. This is a campaign manager and its players
      already organise there, so it is the account most of them will reach for.
    -->
    <Button
      as="a"
      :href="DISCORD_SIGN_IN_URL"
      rel="noopener noreferrer"
      icon="pi pi-discord"
      :label="t('login.discord')"
      severity="secondary"
      fluid
      @click="leaveForProvider"
    />

    <Button
      as="a"
      :href="GOOGLE_SIGN_IN_URL"
      rel="noopener noreferrer"
      icon="pi pi-google"
      :label="t('login.google')"
      severity="secondary"
      fluid
      @click="leaveForProvider"
    />

    <p class="auth-form__aside">
      {{ t('login.noAccount') }}
      <RouterLink :to="{ name: 'signup' }">{{ t('login.createOne') }}</RouterLink
      >.
    </p>

    <p class="auth-form__aside">
      <RouterLink :to="{ name: 'forgot-password' }">{{ t('login.forgotPassword') }}</RouterLink>
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

/*
 * Not an error colour: nothing the reader did is wrong, and the form below has
 * not been submitted yet. A rule down the side is how this design system marks
 * an aside — depth comes from borders here, never from a shadow.
 */
.auth-form__notice {
  margin: 0;
  padding-left: var(--space-3);
  border-left: 2px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
}

.auth-form__aside {
  margin: 0;
  text-align: center;
  font-size: 0.95rem;
}

/*
 * A rule with the word sitting in it, which is the separator this design system
 * already uses everywhere — depth comes from rules and borders here, not from a
 * z-axis. Built from a border rather than a component so it inherits the content
 * border colour in both schemes.
 */
.auth-form__or {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.auth-form__or::before,
.auth-form__or::after {
  content: '';
  flex: 1;
  border-top: 1px solid var(--p-content-border-color);
}

.auth-form :deep(button) {
  min-height: 44px;
}
</style>
