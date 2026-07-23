<script setup>
/*
 * Inline citation back to the source material. Deliberately quiet — it should
 * be findable when scanning but never compete with the text it annotates.
 */
defineProps({
  work: { type: String, required: true },
  page: { type: [Number, String], default: null },
})
</script>

<template>
  <cite class="source-ref">
    <i class="pi pi-book source-ref__icon" aria-hidden="true" />
    <span>{{ work }}</span>
    <span v-if="page !== null" class="source-ref__page">p.&thinsp;{{ page }}</span>
  </cite>
</template>

<style scoped>
.source-ref {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3em;
  font-style: normal;
  font-size: 0.8em;
  color: var(--p-text-muted-color);
}

.source-ref__icon {
  font-size: 0.9em;
}

.source-ref__page {
  font-family: var(--grimoire-font-mono);
  font-size: 0.9em;
}
</style>
