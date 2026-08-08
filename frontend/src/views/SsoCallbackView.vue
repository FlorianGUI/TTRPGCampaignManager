<script setup>
/*
 * Where a provider sign-in lands, after the API has finished with it.
 *
 * There is nothing in the URL to read but an `error` code. On the happy path the
 * API has already set the refresh cookie and redirected here with a bare URL —
 * so this page's whole job is to do what a returning visitor does: refresh, load
 * the user, and go where they were headed. That indirection is why no access
 * token ever reaches browser history, a Referer header, or a proxy log.
 *
 * Public, and it has to be. A guard here would run before the boot refresh
 * resolves on the failure path and bounce an error code into a login redirect,
 * swallowing the one piece of information this page exists to show.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useAuthStore } from '../stores/auth.js'
import { takeDestination } from '../api/sso.js'

const auth = useAuthStore()
const router = useRouter()

/*
 * The API's codes, plus `no-session` for the case it cannot report: the callback
 * said it signed us in and the cookie did not survive the trip. Written out
 * here rather than assembled from the code, because these are sentences a person
 * reads at the moment something went wrong, and each one has a different next
 * step — which is the only reason the backend sends a code instead of prose.
 */
const MESSAGES = {
  cancelled: {
    title: 'Sign-in cancelled',
    detail: 'You did not authorise the app at Discord, so nothing has changed here.',
  },
  'provider-unavailable': {
    title: 'Discord did not answer',
    detail:
      'We could not reach Discord just now. Nothing is wrong with your account — try again shortly.',
  },
  'no-email': {
    title: 'Your Discord account has no email address',
    detail:
      'An account here needs one, for password resets and confirmations. Add an address to Discord and try again, or sign in with a password instead.',
  },
  'unverified-email': {
    title: 'Discord has not confirmed your address',
    detail:
      'We only accept an address the provider has confirmed, so that nobody can reach an account by typing someone else’s address into a profile. Confirm it with Discord, then come back.',
  },
  'email-in-use': {
    title: 'That address already belongs to an account here',
    detail:
      'The account has not confirmed the address yet, so we cannot safely link it to Discord. Sign in with your password, confirm your address, and Discord will link to it after that.',
  },
  'no-session': {
    title: 'The sign-in did not stick',
    detail: 'Discord signed you in, but the session did not reach this tab. Try signing in again.',
  },
}

const FALLBACK = {
  title: 'Something went wrong',
  detail: 'We could not finish signing you in with Discord. Try again shortly.',
}

const failure = ref(null)

onMounted(async () => {
  const error = new URLSearchParams(window.location.search).get('error')

  // Out of the address bar either way: it is noise on a URL somebody may bookmark
  // or share, and a stale code shown again after a reload would be a lie.
  window.history.replaceState({}, '', window.location.pathname)

  if (error) {
    failure.value = MESSAGES[error] ?? FALLBACK
    return
  }

  /*
   * `boot()` rather than a refresh of our own. main.js already started one on
   * this page load and it is idempotent, so this waits for that request instead
   * of making a second — and a second would be worse than wasteful: rotation
   * means the loser of that race presents a spent token, which the API reads as
   * a leak and answers by revoking the whole session.
   */
  await auth.boot()

  if (!auth.isSignedIn) {
    failure.value = MESSAGES['no-session']
    return
  }

  // `replace`, so Back from the app does not return to a callback URL whose
  // authorization code was spent the moment it was used.
  router.replace(takeDestination())
})
</script>

<template>
  <div class="sso">
    <template v-if="failure">
      <h1>{{ failure.title }}</h1>
      <p role="alert">{{ failure.detail }}</p>
      <Button as="router-link" :to="{ name: 'login' }" label="Back to sign in" fluid />
    </template>

    <p v-else class="sso__working">Finishing your sign-in…</p>
  </div>
</template>

<style scoped>
.sso {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-5);
  text-align: center;
}

.sso h1 {
  margin: 0;
  font-size: 1.4rem;
}

.sso p {
  margin: 0;
}

.sso__working {
  color: var(--p-text-muted-color);
}

.sso :deep(a) {
  min-height: 44px;
}
</style>
