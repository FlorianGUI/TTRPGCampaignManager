<script setup>
/*
 * Whether a scene is planned, done, or skipped — and the way to say so.
 *
 * **Clicking cycles it**, planned → done → skipped → planned, because marking prep off is
 * something a game master does forty times while working through an act and it
 * should not cost a page each time. A cycle rather than a menu for the same
 * reason: three states in a fixed order, so the next one is always one press
 * away and never a target to aim at.
 *
 * It is a button when it can be pressed and a plain mark when it cannot. The
 * status is changed wherever a scene is read, so marking it off never requires
 * opening its edit form.
 *
 * Three values and not a boolean, because `skipped` is the interesting one: a
 * scene skipped in play is not the same as one still waiting, and a campaign
 * that deleted it would lose the reason the next act reads the way it does.
 *
 * Never colour alone: the dot's shape differs too — hollow planned, solid done,
 * struck through when skipped — and the word is its accessible name.
 */
import { computed } from 'vue'
import { t } from '../../i18n/index.js'

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

const WORDS = {
  planned: 'scene.status.planned',
  done: 'scene.status.done',
  skipped: 'scene.status.skipped',
}

/* A status the app does not know is shown as it arrived rather than looked up:
   `t` throws on a key it has no copy for, and an unexpected value from the API
   is not a reason for a scene to fail to render. */
const wordFor = (status) => (WORDS[status] ? t(WORDS[status]) : status)

const word = computed(() => wordFor(props.status))

const next = computed(() => ORDER[(ORDER.indexOf(props.status) + 1) % ORDER.length])

/*
 * What it is, then what pressing it does — both, because this string is the
 * button's accessible name as well as its tooltip. Naming only the action leaves
 * the current status readable in the dot's shape and nowhere else, so a scene's
 * state would be announced in the sidebar (where the mark is readonly and names
 * itself) and silent in the outline, which is the one place it can be changed.
 */
const hint = computed(() =>
  t('scene.status.hint', { status: word.value, next: wordFor(next.value) }),
)
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
  width: 24px;
  height: 24px;
  flex: none;
  border-radius: var(--p-border-radius-sm);
  padding: 0;
  background: transparent;
  border: 0;
  color: inherit;
  position: relative;
}

/* The button has the same crisp square hit area as the outline's plus, while
   the familiar dot remains the status mark inside it. */
.status__dot::before {
  content: '';
  position: absolute;
  inset: 50% auto auto 50%;
  width: 10px;
  height: 10px;
  transform: translate(-50%, -50%);
  border: 1px solid currentColor;
  border-radius: 50%;
}

.status__dot--pressable {
  cursor: pointer;
}

/* The box lights up rather than the dot growing: a control that changes size
   moves the row under a pointer that is about to press it. */
.status__dot--pressable:hover {
  background: var(--p-button-text-primary-hover-background);
}

/*
 * Hugging, like the plus and the move menu it shares a column with — see the
 * note in `AddChild`. Three square controls a thumb's width apart, and a ring
 * that floats on one of them reads as a different kind of thing.
 */
.status__dot:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: 0;
}

.status--done {
  color: var(--p-grimoire-scene-done-color);
}
.status--done .status__dot::before {
  background: currentColor;
}

.status--planned {
  color: var(--p-text-muted-color);
}

.status--skipped {
  color: var(--p-grimoire-form-error-color);
}
.status--skipped .status__dot {
  opacity: 0.75;
}

/* Struck through, so cut is told from to-do without reading the colour. */
.status--skipped .status__dot::after {
  content: '';
  position: absolute;
  inset: 50% 6px auto;
  height: 1px;
  background: var(--p-grimoire-form-error-color);
}
</style>
