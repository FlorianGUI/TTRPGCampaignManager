<script setup>
/*
 * Boxed text the GM reads to the table. Tinted, ruled top and bottom, italic.
 * The visible "Read aloud" label carries the meaning; the tint only reinforces it.
 */
defineProps({
  label: { type: String, default: 'Read aloud' },
})
</script>

<template>
  <aside class="read-aloud">
    <p class="read-aloud__label label-smallcaps">{{ label }}</p>
    <div class="read-aloud__body">
      <slot />
    </div>
  </aside>
</template>

<style scoped>
.read-aloud {
  margin: var(--space-5) 0;
  padding: var(--space-4) var(--space-5);
  background: var(--p-grimoire-read-aloud-background);
  border-top: 2px solid var(--p-grimoire-read-aloud-border-color);
  border-bottom: 2px solid var(--p-grimoire-read-aloud-border-color);
  border-left: 1px solid
    color-mix(in srgb, var(--p-grimoire-read-aloud-border-color) 35%, transparent);
  border-right: 1px solid
    color-mix(in srgb, var(--p-grimoire-read-aloud-border-color) 35%, transparent);
}

.read-aloud__label {
  margin: 0 0 var(--space-2);
  color: var(--p-grimoire-read-aloud-border-color);
}

.read-aloud__body {
  font-style: italic;
  font-size: var(--step-1);
  line-height: 1.65;
  color: var(--p-grimoire-read-aloud-color);
}

.read-aloud__body :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
