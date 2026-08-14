<script setup>
/*
 * Whether a scene is still to come, has been played, or was cut.
 *
 * **A dot, with the word in a tooltip.** Forty rows each carrying PLANNED in
 * small caps is forty words competing with the titles they sit beside — and the
 * question an outline is scanned for is "what is left", which a column of dots
 * answers and a column of words obscures.
 *
 * The word is the accessible name rather than absent, so nothing is reachable
 * only by hovering. Where there is room for it — a scene's own page — `withLabel`
 * puts it back.
 *
 * Three values and not a boolean, because `skipped` is the interesting one: a
 * scene cut in play is not the same as one still waiting, and a campaign that
 * deleted its cut scenes would lose the reason the next act reads the way it does.
 *
 * The three are never told apart by colour alone: the dot's *shape* differs too —
 * hollow for planned, solid for played, faded for skipped.
 */
defineProps({
  status: { type: String, required: true },
  withLabel: { type: Boolean, default: false },
})
</script>

<template>
  <span class="status" :class="`status--${status}`">
    <span v-tooltip.left="status" class="status__dot" role="img" :aria-label="status" />
    <span v-if="withLabel" class="status__word" aria-hidden="true">{{ status }}</span>
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
  width: 10px;
  height: 10px;
  flex: none;
  border-radius: 50%;
}

.status--done {
  color: var(--p-grimoire-context-characters);
}
.status--done .status__dot {
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
