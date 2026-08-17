<script setup>
/*
 * "We could not ask", said out loud.
 *
 * What stands in for the app when the boot refresh never got an answer — no
 * network, or a 502 from nginx while the backend is being replaced. The session
 * is untouched and may well be fine; nobody has been signed out (#68).
 *
 * It exists because the alternative to a redirect had to be something. The guard
 * lets the navigation stand so the URL survives, which without this would draw
 * the shell around a page with no data and no explanation — the app looking
 * broken instead of the server being briefly away.
 *
 * The retry is here rather than a reload because a reload throws the URL through
 * a full navigation for no gain: `retryBoot` asks the same question again and
 * the page carries on where it was if the answer arrives.
 */
import { ref } from 'vue'
import Button from 'primevue/button'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()

const retrying = ref(false)

async function retry() {
  retrying.value = true

  try {
    await auth.retryBoot()
  } finally {
    retrying.value = false
  }
}
</script>

<template>
  <main class="unreachable" role="alert">
    <h1 class="unreachable__title">Can't reach the server</h1>

    <p class="unreachable__text">
      This is on our end, not yours — you have not been signed out. It usually means the app is
      being updated, and it passes in a moment.
    </p>

    <Button label="Try again" :loading="retrying" @click="retry" />
  </main>
</template>

<style scoped>
.unreachable {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  max-width: 34rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
  text-align: center;
}

.unreachable__title {
  margin: 0;
  font-size: 1.4rem;
}

.unreachable__text {
  margin: 0;
  color: var(--p-text-muted-color);
}

.unreachable :deep(button) {
  min-height: 44px;
}
</style>
