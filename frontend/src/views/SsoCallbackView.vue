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
import { t } from '../i18n/index.js'

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
 *
 * Not in the catalogue: these are the providers' own names, and a name is the
 * same word in every language.
 */
const PROVIDERS = { discord: 'Discord', google: 'Google' }

/*
 * The API's codes, plus `no-session` for the case it cannot report: the callback
 * said it signed us in and the cookie did not survive the trip. Each one has its
 * own pair of sentences in the catalogue, because each has a different next step
 * — which is the only reason the backend sends a code instead of prose.
 *
 * The list is here rather than inferred from the catalogue's keys, and that is
 * the guard: the code arrives in a URL, so it is whatever somebody typed, and
 * only a code we already know becomes half of a key. Anything else is `failed`.
 *
 * `{provider}` is filled by `t`. A placeholder rather than a template literal
 * because a translator needs the whole sentence, not a fragment either side of
 * a join — and in French the name lands in a different place in some of them.
 */
const CODES = [
  'cancelled',
  'provider-unavailable',
  'no-email',
  'unverified-email',
  'email-in-use',
  'no-session',
]

function say(code, provider) {
  const key = CODES.includes(code) ? code : 'failed'
  const values = { provider: PROVIDERS[provider] ?? t('sso.provider') }

  return { title: t(`sso.${key}.title`, values), detail: t(`sso.${key}.detail`, values) }
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
    failure.value = say(error, provider)
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
    failure.value = say('no-session', provider)
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
      <Button as="router-link" :to="{ name: 'login' }" :label="t('sso.backToSignIn')" fluid />
    </template>

    <p v-else class="sso__working">{{ t('sso.working') }}</p>
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
