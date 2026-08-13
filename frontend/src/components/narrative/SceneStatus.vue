<script setup>
/*
 * Whether a scene is still to come, has been played, or was cut.
 *
 * Three values and not a boolean, because `skipped` is the interesting one: a
 * scene cut in play is not the same as one still waiting, and a campaign that
 * deleted its cut scenes would lose the reason the next act reads the way it
 * does.
 *
 * Never colour alone — the word is written out beside the dot, and the dot's
 * shape differs too (hollow for planned, solid for played, faded for skipped).
 */
defineProps({
  status: { type: String, required: true },
})
</script>

<template>
  <span class="status" :class="`status--${status}`">
    <span class="status__dot" aria-hidden="true" />
    <span class="status__word">{{ status }}</span>
  </span>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status__dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
}

.status--played {
  color: var(--p-grimoire-context-characters);
}
.status--played .status__dot {
  background: var(--p-grimoire-context-characters);
}

.status--planned {
  color: var(--p-text-muted-color);
}
.status--planned .status__dot {
  border: 1px solid var(--p-text-muted-color);
}

.status--skipped {
  color: var(--p-grimoire-form-error-color);
}
.status--skipped .status__dot {
  background: var(--p-grimoire-form-error-color);
  opacity: 0.55;
}
</style>
