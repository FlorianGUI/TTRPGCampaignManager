<script setup>
/*
 * Dice notation, optionally with a rolled result.
 * Monospace so stat lines align down a column.
 */
import { t } from '../../i18n/index.js'

defineProps({
  notation: { type: String, required: true },
  result: { type: Number, default: null },
  // 'crit' | 'fumble' | null — always paired with a label, never colour alone.
  outcome: { type: String, default: null },
})
</script>

<template>
  <span class="dice" :class="outcome && `dice--${outcome}`">
    <span class="dice__notation">{{ notation }}</span>
    <template v-if="result !== null">
      <span class="dice__arrow" aria-hidden="true">→</span>
      <span class="dice__result">{{ result }}</span>
    </template>
    <span v-if="outcome" class="dice__outcome">{{
      outcome === 'crit' ? t('dice.crit') : t('dice.fumble')
    }}</span>
  </span>
</template>

<style scoped>
.dice {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3em;
  padding: 0.05em 0.4em;
  font-family: var(--grimoire-font-mono);
  font-size: 0.85em;
  line-height: 1.5;
  white-space: nowrap;
  color: var(--p-grimoire-dice-color);
  background: var(--p-grimoire-dice-background);
  border: 1px solid var(--p-grimoire-dice-border-color);
  border-radius: var(--p-border-radius-xs);
}

.dice__arrow {
  opacity: 0.55;
}

.dice__result {
  font-weight: 600;
}

.dice__outcome {
  font-size: 0.8em;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.dice--crit {
  border-color: var(--p-grimoire-dice-crit-border-color);
}
.dice--crit .dice__result,
.dice--crit .dice__outcome {
  color: var(--p-grimoire-dice-crit-color);
}

.dice--fumble {
  border-color: var(--p-grimoire-dice-fumble-border-color);
}
.dice--fumble .dice__result,
.dice--fumble .dice__outcome {
  color: var(--p-grimoire-dice-fumble-color);
}
</style>
