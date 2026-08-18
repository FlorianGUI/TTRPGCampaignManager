<script setup>
import { computed } from 'vue'
import { ENTITY_KINDS } from './entityKinds.js'
import { t } from '../../i18n/index.js'

/*
 * Chip for a linked entity. Each kind gets its own accent *and* its own icon —
 * meaning is never carried by colour alone.
 */

const props = defineProps({
  kind: {
    type: String,
    required: true,
    validator: (value) => value in ENTITY_KINDS,
  },
  label: { type: String, required: true },
})

const meta = computed(() => ENTITY_KINDS[props.kind])
</script>

<template>
  <span class="entity" :style="{ '--entity-accent': `var(--p-grimoire-entity-${kind})` }">
    <i class="pi entity__icon" :class="meta.icon" aria-hidden="true" />
    <span class="entity__label">{{ label }}</span>
    <span class="visually-hidden">({{ t(meta.label) }})</span>
  </span>
</template>

<style scoped>
.entity {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  padding: 0.1em 0.45em 0.1em 0.4em;
  font-size: 0.8em;
  font-weight: 600;
  line-height: 1.6;
  white-space: nowrap;
  color: var(--entity-accent);
  border: 1px solid color-mix(in srgb, var(--entity-accent) 40%, transparent);
  background: color-mix(in srgb, var(--entity-accent) 9%, transparent);
  border-radius: var(--p-border-radius-xs);
}

.entity__icon {
  font-size: 0.85em;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
