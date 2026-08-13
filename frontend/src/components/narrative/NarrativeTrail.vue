<script setup>
/*
 * Where a node sits, and the way back out of it.
 *
 * **It always starts at Structure.** A node page carries no tree beside it —
 * that was cut deliberately, so there is no rail to click — which makes this the
 * one route back that does not depend on the sidebar being visible. Below the
 * sidebar breakpoint it is the *only* one that is.
 *
 * Only the direct parent is stored on a row, so the chain above a scene is
 * walked from the tree rather than read off it. See `trailTo`.
 *
 * The node's own name is not repeated here — it is the heading immediately
 * below, and a trail that ends by naming the page you are looking at makes the
 * reader check whether it is a link.
 */
import { RouterLink } from 'vue-router'

defineProps({
  campaignId: { type: String, required: true },
  trail: { type: Array, default: () => [] },
})

const ROUTES = { act: 'campaign-act', sequence: 'campaign-sequence', scene: 'campaign-scene' }
const PARAMS = { act: 'actId', sequence: 'sequenceId', scene: 'sceneId' }

const to = (campaignId, { kind, node }) => ({
  name: ROUTES[kind],
  params: { campaignId, [PARAMS[kind]]: node.id },
})
</script>

<template>
  <nav class="trail" aria-label="Breadcrumb">
    <ol>
      <li>
        <RouterLink :to="{ name: 'campaign-structure', params: { campaignId } }"
          >Structure</RouterLink
        >
      </li>
      <li v-for="step in trail" :key="step.node.id">
        <span class="trail__separator" aria-hidden="true">/</span>
        <RouterLink :to="to(campaignId, step)">{{ step.node.title }}</RouterLink>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.trail ol {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  list-style: none;
  margin: 0;
  padding: 0;
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
}

.trail li {
  display: flex;
  align-items: baseline;
  min-width: 0;
}

.trail__separator {
  color: var(--p-grimoire-rule-color);
  padding: 0 0.4em;
}

.trail a {
  color: var(--p-text-muted-color);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trail a:hover {
  color: var(--p-primary-color);
  text-decoration: underline;
}

.trail a:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}
</style>
