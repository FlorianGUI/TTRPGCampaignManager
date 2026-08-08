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
import { forgetCurrentCampaign } from '../stores/currentCampaign.js'
import { takeDestination } from '../api/sso.js'

const auth = useAuthStore()
const router = useRouter()

/*
 * Which provider it was, for the sentences below.
 *
 * The API names it on the way back because this page cannot know: the round trip
 * left this origin, so whichever button was pressed is two navigations ago. It
 * is a provider's name and nothing more — no id, no scope, nothing secret.
 *
 * Anything unrecognised falls back to "the provider", which reads acceptably in
 * every sentence here. That matters because the value arrives in a URL and a URL
 * is whatever someone typed: interpolating it raw would put attacker-chosen text
 * into our own error copy.
 */
const PROVIDERS = { discord: 'Discord', google: 'Google' }

/*
 * The API's codes, plus `no-session` for the case it cannot report: the callback
 * said it signed us in and the cookie did not survive the trip. Written out
 * here rather than assembled from the code, because these are sentences a person
 * reads at the moment something went wrong, and each one has a different next
 * step — which is the only reason the backend sends a code instead of prose.
 *
 * `{provider}` is filled in below. A placeholder rather than a template literal
 * because these are the strings a translation file would eventually hold, and a
 * translator needs the whole sentence, not a fragment either side of a join.
 */
const MESSAGES = {
  cancelled: {
    title: 'Sign-in cancelled',
    detail: 'You did not authorise the app at {provider}, so nothing has changed here.',
  },
  'provider-unavailable': {
    title: '{provider} did not answer',
    detail:
      'We could not reach {provider} just now. Nothing is wrong with your account — try again shortly.',
  },
  'no-email': {
    title: 'Your {provider} account has no email address',
    detail:
      'An account here needs one, for password resets and confirmations. Add an address to {provider} and try again, or sign in with a password instead.',
  },
  'unverified-email': {
    title: '{provider} has not confirmed your address',
    detail:
      'We only accept an address the provider has confirmed, so that nobody can reach an account by typing someone else’s address into a profile. Confirm it with {provider}, then come back.',
  },
  'email-in-use': {
    title: 'That address already belongs to an account here',
    detail:
      'The account has not confirmed the address yet, so we cannot safely link it to {provider}. Sign in with your password, confirm your address, and {provider} will link to it after that.',
  },
  'no-session': {
    title: 'The sign-in did not stick',
    detail:
      '{provider} signed you in, but the session did not reach this tab. Try signing in again.',
  },
}

const FALLBACK = {
  title: 'Something went wrong',
  detail: 'We could not finish signing you in with {provider}. Try again shortly.',
}

function fill(message, provider) {
  const name = PROVIDERS[provider] ?? 'the provider'

  return {
    title: message.title.replaceAll('{provider}', name),
    detail: message.detail.replaceAll('{provider}', name),
  }
}

const failure = ref(null)

onMounted(async () => {
  const query = new URLSearchParams(window.location.search)
  const error = query.get('error')
  const provider = query.get('provider')

  // Out of the address bar either way: it is noise on a URL somebody may bookmark
  // or share, and a stale code shown again after a reload would be a lie.
  window.history.replaceState({}, '', window.location.pathname)

  if (error) {
    failure.value = fill(MESSAGES[error] ?? FALLBACK, provider)
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
    failure.value = fill(MESSAGES['no-session'], provider)
    return
  }

  /*
   * A provider sign-in is a sign-in, and it has to forget the last campaign the
   * way `logIn` does — but it cannot rely on that, because it never calls it.
   * The session arrives through `boot()`, which is the same call a returning
   * visitor's cold open makes, and that one must *not* forget: resuming where
   * you left off is the whole point of it.
   *
   * So the difference is drawn here, at the one place that knows it: reaching
   * this line means somebody just came back from a provider, not that a cookie
   * was still good. Without it, signing in on a shared browser would drop you
   * into whichever campaign the last person was reading (#59).
   *
   * Provider-agnostic on purpose — this page is the single landing point for
   * every provider, so a new one is covered the day it is added.
   */
  forgetCurrentCampaign()

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
