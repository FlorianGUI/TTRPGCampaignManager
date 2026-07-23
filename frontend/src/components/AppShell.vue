<script setup>
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { useTheme } from '../design-system/useTheme.js'

/*
 * Dark leather chrome (top bar + sidebar) framing a parchment reading surface.
 * The chrome stays dark-ish in both themes; only the content area really flips.
 */

defineProps({
  sections: { type: Array, required: true },
  active: { type: String, default: null },
})

const { theme, density, toggleTheme, toggleDensity } = useTheme()
</script>

<template>
  <div class="shell">
    <header class="shell__topbar texture-grain">
      <div class="shell__brand">
        <i class="pi pi-book" aria-hidden="true" />
        <span>Campaign Manager</span>
      </div>

      <div class="shell__search">
        <InputText placeholder="Search sources, NPCs, locations…" fluid />
      </div>

      <div class="shell__actions">
        <Button
          text
          rounded
          :icon="density === 'compact' ? 'pi pi-bars' : 'pi pi-align-justify'"
          :aria-label="`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} density`"
          :title="`Density: ${density}`"
          @click="toggleDensity"
        />
        <Button
          text
          rounded
          :icon="theme === 'candlelight' ? 'pi pi-sun' : 'pi pi-moon'"
          :aria-label="`Switch to ${theme === 'candlelight' ? 'parchment' : 'candlelight'} theme`"
          :title="`Theme: ${theme}`"
          @click="toggleTheme"
        />
      </div>
    </header>

    <div class="shell__body">
      <nav class="shell__sidebar texture-grain" aria-label="Campaign">
        <div v-for="section in sections" :key="section.label" class="shell__section">
          <p class="label-smallcaps shell__section-label">{{ section.label }}</p>
          <ul class="shell__list">
            <li v-for="item in section.items" :key="item.label">
              <a
                class="shell__item"
                :class="{ 'shell__item--active': item.label === active }"
                :style="
                  section.context && {
                    '--context-accent': `var(--p-grimoire-context-${section.context})`,
                  }
                "
                :aria-current="item.label === active ? 'page' : undefined"
                href="#"
                @click.prevent
              >
                <i class="pi shell__item-icon" :class="item.icon" aria-hidden="true" />
                <span>{{ item.label }}</span>
                <span v-if="item.count" class="shell__item-count">{{ item.count }}</span>
              </a>
            </li>
          </ul>
        </div>
      </nav>

      <main class="shell__content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.shell__topbar {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  height: var(--shell-topbar);
  padding: 0 var(--space-4);
  flex: 0 0 auto;
  background: var(--p-grimoire-chrome-background);
  border-bottom: 1px solid var(--p-grimoire-chrome-border-color);
}

.shell__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
  color: var(--p-primary-color);
}

.shell__search {
  flex: 1;
  max-width: 26rem;
}

.shell__actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-1);
}

.shell__body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.shell__sidebar {
  flex: 0 0 var(--shell-sidebar);
  padding: var(--space-3) var(--space-2);
  overflow-y: auto;
  background: var(--p-grimoire-chrome-background);
  border-right: 1px solid var(--p-grimoire-chrome-border-color);
}

.shell__section + .shell__section {
  margin-top: var(--space-4);
}

.shell__section-label {
  margin: 0 0 var(--space-1);
  padding: 0 var(--space-2);
}

.shell__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.shell__item {
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

.shell__item:hover {
  background: var(--p-navigation-item-hover-background);
  color: var(--p-navigation-item-hover-color);
}

/* Active state is border + weight + colour, so it survives without colour. */
.shell__item--active {
  color: var(--context-accent, var(--p-primary-color));
  border-left-color: var(--context-accent, var(--p-primary-color));
  background: var(--p-navigation-item-active-background);
  font-weight: 600;
}

.shell__item-icon {
  font-size: 0.85em;
  color: var(--p-navigation-item-icon-color);
}

.shell__item--active .shell__item-icon {
  color: inherit;
}

.shell__item-count {
  margin-left: auto;
  font-family: var(--grimoire-font-mono);
  font-size: 0.75em;
  color: var(--p-text-muted-color);
}

.shell__content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-7);
  background: var(--p-content-background);
}

@media (max-width: 900px) {
  .shell__sidebar {
    display: none;
  }

  .shell__content {
    padding: var(--space-4);
  }
}
</style>
