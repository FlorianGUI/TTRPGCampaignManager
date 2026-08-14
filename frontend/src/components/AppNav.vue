<script setup>
/*
 * The campaign navigation list, with no opinion about its container.
 *
 * Rendered twice by AppShell: once in the sticky sidebar on wide viewports and
 * once inside the drawer below 900px. Keeping it here means the two entry
 * points can never drift apart.
 */

import { RouterLink } from 'vue-router'

defineProps({
  // Each carries a `label`, its `items`, an optional `context` accent, and an
  // optional `to` — a route of the section's own, which makes its head a link.
  sections: { type: Array, required: true },
  active: { type: String, default: null },
})

defineEmits(['navigate'])
</script>

<template>
  <div v-for="section in sections" :key="section.label" class="nav__section">
    <!--
      A head is a link where the section has somewhere of its own to go, and a
      paragraph where it does not — `nav-section` turns the pressable states on
      for the anchor and leaves the paragraph inert, so nothing here promises a
      destination that is not there. `Library` and `Characters` are headings
      today; they become links the day they are given a `to`, with no change to
      how they look until they do.
    -->
    <RouterLink v-if="section.to" v-slot="{ href, navigate, isActive }" :to="section.to" custom>
      <a
        class="label-smallcaps nav-section"
        :href="href"
        :aria-current="isActive ? 'page' : undefined"
        @click="navigate"
        >{{ section.label }}</a
      >
    </RouterLink>

    <p v-else class="label-smallcaps nav-section">{{ section.label }}</p>
    <ul class="nav__list">
      <li v-for="item in section.items" :key="item.label">
        <a
          class="nav__item"
          :class="{ 'nav__item--active': item.label === active }"
          :style="
            section.context && {
              '--context-accent': `var(--p-grimoire-context-${section.context})`,
            }
          "
          :aria-current="item.label === active ? 'page' : undefined"
          href="#"
          @click.prevent="$emit('navigate', item)"
        >
          <i class="pi nav__item-icon" :class="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
          <span v-if="item.count" class="nav__item-count">{{ item.count }}</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.nav__section + .nav__section {
  margin-top: var(--space-4);
}

.nav__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav__item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.35rem var(--space-2);
  border-radius: var(--p-border-radius-sm);
  font-size: var(--step--1);
  color: var(--p-navigation-item-color);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition:
    background var(--p-transition-duration),
    color var(--p-transition-duration);
}

.nav__item:hover {
  background: var(--p-navigation-item-hover-background);
  color: var(--p-navigation-item-hover-color);
}

/* Active state is border + weight + colour, so it survives without colour. */
.nav__item--active {
  color: var(--context-accent, var(--p-primary-color));
  border-left-color: var(--context-accent, var(--p-primary-color));
  background: var(--p-navigation-item-active-background);
  font-weight: 600;
}

.nav__item-icon {
  /* Campaign markers occupy this same column, so labels line up across the
     campaign outline and the Library/Characters navigation beneath it. */
  width: 24px;
  flex: none;
  text-align: center;
  font-size: 0.85em;
  color: var(--p-navigation-item-icon-color);
}

.nav__item--active .nav__item-icon {
  color: inherit;
}

.nav__item-count {
  margin-left: auto;
  font-family: var(--grimoire-font-mono);
  font-size: 0.75em;
  color: var(--p-text-muted-color);
}

/*
 * Touch targets: 0.35rem of padding is fine for a mouse and far under the 44px
 * guideline for a finger. The floor is set in absolute pixels rather than in
 * --space-*, so no change to the spacing scale can quietly lower it — which is
 * why it needed no adjusting when #79 removed the compact density.
 */
@media (pointer: coarse) {
  .nav__item {
    min-height: 44px;
    padding-block: 0.5rem;
    font-size: var(--step-0);
  }
}
</style>
