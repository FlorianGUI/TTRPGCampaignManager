<script setup>
/*
 * How far through an act the table has got, as a dot filled in proportion.
 *
 * The number beside it carries the precision and the dot carries the glance,
 * which is the split a 15rem column needs — "4/6" is unreadable at a distance
 * and a dot alone never says how much is left.
 *
 * Four states rather than three. `empty` is not `not started`: an act with no
 * scenes has not been *written*, which is a different problem from written and
 * unplayed, and it is the one a game master can act on. It shows as an unfilled
 * ring with an em dash rather than a zero, because zero-of-zero reads as
 * progress that has not begun rather than as nothing to progress through.
 *
 * The state is never communicated by colour alone: the count is always there,
 * and the accessible name spells the state out.
 */
defineProps({
  progress: { type: Object, required: true },
})
</script>

<template>
  <span class="progress" :title="progress.label">
    <span
      class="progress__dot"
      :class="`progress__dot--${progress.label.replace(' ', '-')}`"
      :style="{ '--fill': `${progress.fill}%` }"
      aria-hidden="true"
    />
    <span class="progress__count">{{
      progress.total ? `${progress.played}/${progress.total}` : '—'
    }}</span>
    <span class="sr-only">{{ progress.label }}</span>
  </span>
</template>

<style scoped>
.progress {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.progress__dot {
  width: 10px;
  height: 10px;
  flex: none;
  border-radius: 50%;
  border: 1px solid var(--p-text-muted-color);
  position: relative;
  overflow: hidden;
}

/*
 * Filled by clipping rather than by a gradient stop, so the boundary stays hard
 * at any percentage — a gradient blurs it and reads as an unfinished render.
 */
.progress__dot::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--p-grimoire-context-characters);
  clip-path: inset(0 calc(100% - var(--fill, 0%)) 0 0);
}

.progress__dot--ongoing,
.progress__dot--finished {
  border-color: var(--p-grimoire-context-characters);
}

.progress__count {
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
