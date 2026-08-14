<script setup>
/*
 * Whether a scene is still to come, finished with, or cut — and the way to say so.
 *
 * **Clicking cycles it**, to do → done → cut → to do, because marking prep off is
 * something a game master does forty times while working through an act and it
 * should not cost a page each time. A cycle rather than a menu for the same
 * reason: three states in a fixed order, so the next one is always one press
 * away and never a target to aim at.
 *
 * It is a button when it can be pressed and a plain mark when it cannot — the
 * scene's own page shows the status beside a `Select` that already sets it, and
 * two controls for one field is one too many.
 *
 * Three values and not a boolean, because `skipped` is the interesting one: a
 * scene cut in play is not the same as one still waiting, and a campaign that
 * deleted its cut scenes would lose the reason the next act reads the way it
 * does. The wording says *cut* rather than *skipped* on screen; the stored value
 * is unchanged.
 *
 * Never colour alone: the dot's shape differs too — hollow to do, solid done,
 * struck through when cut — and the word is its accessible name.
 */
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  withLabel: { type: Boolean, default: false },
  // Where there is somewhere better to set it, this is a mark and not a control.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['cycle'])

/* The order the dot walks. `planned` follows `skipped`, so it is a loop and a
   scene brought back from the cut pile takes one press rather than three. */
const ORDER = ['planned', 'done', 'skipped']

const WORDS = { planned: 'to do', done: 'done', skipped: 'cut' }

const word = computed(() => WORDS[props.status] ?? props.status)

const next = computed(() => ORDER[(ORDER.indexOf(props.status) + 1) % ORDER.length])

const hint = computed(() => `${word.value} — set to ${WORDS[next.value]}`)
</script>

<template>
  <span class="status" :class="`status--${status}`">
    <component
      :is="readonly ? 'span' : 'button'"
      v-tooltip.left="readonly ? word : hint"
      class="status__dot"
      :class="{ 'status__dot--pressable': !readonly }"
      :type="readonly ? undefined : 'button'"
      :role="readonly ? 'img' : undefined"
      :aria-label="readonly ? word : hint"
      @click.stop.prevent="!readonly && emit('cycle', next)"
    />
    <span v-if="withLabel" class="status__word" aria-hidden="true">{{ word }}</span>
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
  padding: 0;
  background: transparent;
  border: 1px solid var(--p-text-muted-color);
  position: relative;
}

.status__dot--pressable {
  cursor: pointer;
}

.status__dot--pressable:hover {
  /* The ring widens rather than the dot growing: a control that changes size
     moves the row under a pointer that is about to press it. */
  box-shadow: 0 0 0 3px var(--p-content-hover-background);
}

.status__dot:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.status--done {
  color: var(--p-grimoire-context-characters);
}
.status--done .status__dot {
  background: var(--p-grimoire-context-characters);
  border-color: var(--p-grimoire-context-characters);
}

.status--planned {
  color: var(--p-text-muted-color);
}

.status--skipped {
  color: var(--p-grimoire-form-error-color);
}
.status--skipped .status__dot {
  border-color: var(--p-grimoire-form-error-color);
  opacity: 0.75;
}

/* Struck through, so cut is told from to-do without reading the colour. */
.status--skipped .status__dot::after {
  content: '';
  position: absolute;
  inset: 50% -2px auto -2px;
  height: 1px;
  background: var(--p-grimoire-form-error-color);
}
</style>
