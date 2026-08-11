<script setup>
/*
 * A labelled input and the error that belongs to it, wired together.
 *
 * This exists for the wiring rather than the markup. `for`/`id`, `aria-invalid`
 * and — the one that is easy to get wrong and impossible to see — the
 * `aria-describedby` pointing at the error text all have to agree, and doing
 * that by hand in every form is how a message ends up on screen for sighted
 * users and nowhere else. Here it is one relationship, defined once.
 *
 * `aria-describedby` is absent rather than empty when there is no error: an
 * attribute pointing at a missing id is worse than no attribute, because a
 * screen reader has nothing to announce and no way to say so.
 */
import { computed } from 'vue'
import InputText from 'primevue/inputtext'

const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  type: { type: String, default: 'text' },
  autocomplete: { type: String, default: null },
  // A ceiling the API also holds. Declared rather than left to fall through the
  // attrs, which would land it on this wrapper's `div` and enforce nothing.
  maxlength: { type: Number, default: null },
  error: { type: String, default: null },
})

defineEmits(['update:modelValue'])

const errorId = computed(() => `${props.id}-error`)
</script>

<template>
  <div class="field">
    <label :for="id">{{ label }}</label>

    <InputText
      :id="id"
      :model-value="modelValue"
      :type="type"
      :autocomplete="autocomplete"
      :maxlength="maxlength"
      :invalid="Boolean(error)"
      :aria-describedby="error ? errorId : undefined"
      fluid
      @update:model-value="$emit('update:modelValue', $event)"
    />

    <!--
      role="alert" so it is announced when it appears. The message arrives after
      a submit, so it is a change to the page rather than something present at
      load, and without this it would pass silently.
    -->
    <p v-if="error" :id="errorId" class="field__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field label {
  font-family: var(--grimoire-font-display);
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

.field :deep(input) {
  /* The 44px floor AppNav sets for touch targets applies here too — a field is
     something you tap before you can type in it. */
  min-height: 44px;
}

.field__error {
  margin: 0;
  color: var(--p-grimoire-form-error-color);
  font-size: 0.9rem;
}
</style>
