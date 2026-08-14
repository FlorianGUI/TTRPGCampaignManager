<script setup>
/*
 * How far through an act the table has got, as a dot filled in proportion.
 *
 * **A dot and nothing else, with the count in a tooltip.** An outline is read by
 * scanning down it, and a column of "3/3", "0/2", "—" is three numbers to parse
 * per row when the question being asked is only "which of these has anything
 * left in it". The dot answers that at a glance; the tooltip answers the follow-up
 * for the one row that prompted it.
 *
 * The count is not lost, only unasked-for: it is the accessible name, so a screen
 * reader hears "4 of 6 scenes played" where a sighted reader sees a half-filled
 * ring. Hover is never the only way to a fact.
 *
 * Four states rather than three. `empty` is not `not started`: an act with no
 * scenes has not been *written*, which is a different problem from written and
 * unplayed, and it is the one a game master can act on.
 */
defineProps({
  progress: { type: Object, required: true },
  // The pages have room for the words; the outline and the sidebar do not.
  withLabel: { type: Boolean, default: false },
})

const spellOut = ({ total, played, label }) =>
  total ? `${label} — ${played} of ${total} scenes played` : 'empty — nothing written in it yet'
</script>

<template>
  <span class="progress">
    <span
      v-tooltip.left="spellOut(progress)"
      class="progress__dot"
      :class="`progress__dot--${progress.label.replace(' ', '-')}`"
      :style="{ '--fill': `${progress.fill}%` }"
      role="img"
      :aria-label="spellOut(progress)"
    />
    <span v-if="withLabel" class="progress__count" aria-hidden="true">
      {{ progress.total ? `${progress.played}/${progress.total}` : '—' }}
    </span>
  </span>
</template>

<style scoped>
.progress {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.progress__dot {
  /* Match the status control's marker box, so act progress and scene status
     land on the same centre line in the outline and sidebar. */
  width: 24px;
  height: 24px;
  flex: none;
  position: relative;
}

.progress__dot::before {
  content: '';
  position: absolute;
  inset: 50% auto auto 50%;
  width: 10px;
  height: 10px;
  transform: translate(-50%, -50%);
  border: 1px solid var(--p-text-muted-color);
  border-radius: 50%;
}

/*
 * Filled by clipping rather than by a gradient stop, so the boundary stays hard
 * at any percentage — a gradient blurs it and reads as an unfinished render.
 */
.progress__dot::after {
  content: '';
  position: absolute;
  inset: 50% auto auto 50%;
  width: 10px;
  height: 10px;
  transform: translate(-50%, -50%);
  background: var(--p-grimoire-scene-done-color);
  border-radius: 50%;
  clip-path: inset(0 calc(100% - var(--fill, 0%)) 0 0 round 50%);
}

.progress__dot--ongoing::before,
.progress__dot--finished::before {
  border-color: var(--p-grimoire-scene-done-color);
}

.progress__count {
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
</style>
