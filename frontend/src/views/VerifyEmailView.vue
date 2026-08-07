<script setup>
/*
 * Where a verification link lands.
 *
 * The link in the message points here rather than at the API, and this page is
 * the reason: a mail scanner that prefetches the URL loads a page and changes
 * nothing. Only a real load calls the endpoint, which is what stops a
 * single-use token being spent by something that is not a person (#38).
 *
 * Public, and deliberately usable signed out — someone registers on a laptop
 * and opens the mail on a phone, where they have no session at all.
 */
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { apiFetch } from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()

const state = ref('working')

onMounted(async () => {
  // Read from location rather than useRoute().query, so the token never becomes
  // part of a route the router might later restore or log.
  const token = new URLSearchParams(window.location.search).get('token')

  if (!token) {
    state.value = 'unusable'
    return
  }

  try {
    const user = await apiFetch('/users/verify-email', { method: 'POST', json: { token } })
    state.value = 'done'
    // Someone verifying in the tab they registered in is signed in already, and
    // their copy of themselves now says something untrue. Refreshing it costs
    // nothing and stops the rest of the app disagreeing with this page.
    if (auth.isSignedIn) auth.user = user
  } catch (error) {
    state.value = error?.status === 400 ? 'unusable' : 'failed'
  }

  // The token is a credential and it is sitting in the address bar, where it
  // will be read by anyone looking over a shoulder and kept in history. It has
  // been spent by now, so removing it costs nothing and leaves one less copy.
  window.history.replaceState({}, '', window.location.pathname)
})
</script>

<template>
  <div class="verify">
    <p v-if="state === 'working'" class="verify__working">Confirming your address…</p>

    <template v-else-if="state === 'done'">
      <h1>Address confirmed</h1>
      <p>Thank you — this address is now verified.</p>
      <Button as="router-link" :to="{ name: 'home' }" label="Continue" fluid />
    </template>

    <template v-else-if="state === 'unusable'">
      <h1>This link is no longer valid</h1>
      <!--
        One message for expired, already-used and never-issued, because the API
        answers all three the same way on purpose and there is nothing different
        to do about any of them. Saying which would also confirm to whoever is
        guessing that a token existed.
      -->
      <p>
        It may have expired, or already been used. Sign in and ask for a new one from your account.
      </p>
      <Button as="router-link" :to="{ name: 'login' }" label="Sign in" fluid />
    </template>

    <template v-else>
      <h1>Something went wrong</h1>
      <p>We could not confirm the address just now. The link is still good — try again shortly.</p>
    </template>
  </div>
</template>

<style scoped>
.verify {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-top: var(--space-5);
  text-align: center;
}

.verify h1 {
  margin: 0;
  font-size: 1.4rem;
}

.verify p {
  margin: 0;
}

.verify__working {
  color: var(--p-text-muted-color);
}

.verify :deep(a) {
  min-height: 44px;
}
</style>
