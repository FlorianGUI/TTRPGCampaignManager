<script setup>
/*
 * The scene before this one, and the one after — in the order the story goes in.
 *
 * **Across sequence and act boundaries**, not among siblings. The last scene of
 * one act steps into the first of the next, because that is what "next" means to
 * a game master working through an evening. It is the payoff for `position`
 * being explicit in the data rather than implied by a timestamp.
 *
 * It matters more than it looks. A node page carries no tree beside it, so this
 * is the main way through a campaign once you are reading rather than
 * reorganising — going back to the outline between every scene is the thing it
 * exists to avoid.
 */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  campaignId: { type: String, required: true },
  scenes: { type: Array, required: true },
  currentId: { type: String, required: true },
})

const at = computed(() => props.scenes.findIndex((scene) => scene.id === props.currentId))

const previous = computed(() => (at.value > 0 ? props.scenes[at.value - 1] : null))

const next = computed(() =>
  at.value >= 0 && at.value < props.scenes.length - 1 ? props.scenes[at.value + 1] : null,
)

const to = (scene) => ({
  name: 'campaign-scene',
  params: { campaignId: props.campaignId, sceneId: scene.id },
})
</script>

<template>
  <nav v-if="previous || next" class="stepper" aria-label="Scenes either side of this one">
    <!--
      An end of the campaign renders nothing rather than a disabled control: a
      dead button on the first scene of every campaign is a permanent reminder of
      an edge nobody needs telling about.
    -->
    <RouterLink v-if="previous" class="stepper__step" :to="to(previous)">
      <span class="stepper__label">Previous scene</span>
      <span class="stepper__title">{{ previous.title }}</span>
    </RouterLink>
    <span v-else />

    <RouterLink v-if="next" class="stepper__step stepper__step--next" :to="to(next)">
      <span class="stepper__label">Next scene</span>
      <span class="stepper__title">{{ next.title }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.stepper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--p-grimoire-rule-color);
}

.stepper__step {
  display: block;
  min-width: 0;
  padding: var(--space-3);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
  color: var(--p-text-muted-color);
  text-decoration: none;
}

.stepper__step:hover {
  border-color: var(--p-primary-color);
  color: var(--p-text-color);
}

.stepper__step:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.stepper__step--next {
  text-align: right;
}

.stepper__label {
  display: block;
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  margin-bottom: var(--space-1);
}

.stepper__title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 520px) {
  .stepper {
    grid-template-columns: 1fr;
  }

  .stepper__step--next {
    text-align: left;
  }
}
</style>
