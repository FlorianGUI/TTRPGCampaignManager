<script setup>
import DiceChip from './DiceChip.vue'
import SourceRef from './SourceRef.vue'

/*
 * Monster / NPC stat block, with the classic ruled header and ability row.
 * Shape follows the SRD block so imported source material maps onto it directly.
 */
defineProps({
  creature: { type: Object, required: true },
})

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha']

function modifier(score) {
  const mod = Math.floor((score - 10) / 2)
  return mod >= 0 ? `+${mod}` : `${mod}`
}
</script>

<template>
  <article class="statblock">
    <header class="statblock__head">
      <h3 class="statblock__name">{{ creature.name }}</h3>
      <p class="statblock__meta">{{ creature.meta }}</p>
    </header>

    <hr class="statblock__rule" />

    <dl class="statblock__lines">
      <div v-for="line in creature.lines" :key="line.label" class="statblock__line">
        <dt>{{ line.label }}</dt>
        <dd>
          {{ line.value }}
          <DiceChip v-if="line.dice" :notation="line.dice" />
        </dd>
      </div>
    </dl>

    <hr class="statblock__rule" />

    <div class="statblock__abilities">
      <div v-for="key in ABILITIES" :key="key" class="statblock__ability">
        <span class="statblock__ability-name">{{ key }}</span>
        <span class="statblock__ability-score">
          {{ creature.abilities[key] }}
          <span class="statblock__ability-mod">({{ modifier(creature.abilities[key]) }})</span>
        </span>
      </div>
    </div>

    <hr class="statblock__rule" />

    <dl class="statblock__lines">
      <div v-for="line in creature.details" :key="line.label" class="statblock__line">
        <dt>{{ line.label }}</dt>
        <dd>{{ line.value }}</dd>
      </div>
    </dl>

    <hr class="statblock__rule statblock__rule--strong" />

    <section v-for="trait in creature.traits" :key="trait.name" class="statblock__trait">
      <p>
        <em class="statblock__trait-name">{{ trait.name }}.</em> {{ trait.text }}
      </p>
    </section>

    <h4 v-if="creature.actions?.length" class="statblock__section-heading">Actions</h4>
    <section v-for="action in creature.actions" :key="action.name" class="statblock__trait">
      <p>
        <em class="statblock__trait-name">{{ action.name }}.</em> {{ action.text }}
        <DiceChip v-if="action.dice" :notation="action.dice" />
        {{ action.after }}
      </p>
    </section>

    <footer v-if="creature.source" class="statblock__source">
      <SourceRef :work="creature.source.work" :page="creature.source.page" />
    </footer>
  </article>
</template>

<style scoped>
.statblock {
  /*
   * The block is laid out against its own width, not the viewport's: it sits in
   * a ~26rem aside on wide screens and runs full width once the aside stacks,
   * so a viewport breakpoint would describe the wrong box (issue #25).
   */
  container-type: inline-size;
  padding: var(--space-4) var(--space-5);
  background: var(--p-grimoire-statblock-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  /* The block is dense by design — a column of its own inside wider content. */
  font-size: var(--step--1);
  line-height: 1.5;
}

.statblock__name {
  font-size: var(--step-2);
  color: var(--p-grimoire-statblock-heading-color);
  margin: 0;
}

.statblock__meta {
  margin: 0.1em 0 0;
  font-style: italic;
  color: var(--p-text-muted-color);
}

.statblock__rule {
  border: 0;
  border-top: 1px solid var(--p-grimoire-statblock-rule-color);
  margin: var(--space-3) 0;
  opacity: 0.55;
}

.statblock__rule--strong {
  border-top-width: 2px;
  opacity: 1;
}

.statblock__lines {
  margin: 0;
}

.statblock__line {
  display: flex;
  gap: 0.4em;
  margin: 0;
}

.statblock__line dt {
  font-weight: 700;
  color: var(--p-grimoire-statblock-heading-color);
}

.statblock__line dd {
  margin: 0;
}

.statblock__abilities {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--space-2);
  text-align: center;
}

/* Six columns of "20 (+5)" stop fitting around a phone-width block: wrap to 3×2. */
@container (max-width: 22rem) {
  .statblock__abilities {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    row-gap: var(--space-3);
  }
}

.statblock__ability-name {
  display: block;
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  font-size: 0.85em;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-grimoire-statblock-heading-color);
}

.statblock__ability-score {
  font-family: var(--grimoire-font-mono);
  font-size: 0.9em;
}

.statblock__ability-mod {
  color: var(--p-text-muted-color);
}

.statblock__trait p {
  margin: 0 0 var(--space-3);
}

.statblock__trait-name {
  font-weight: 700;
}

.statblock__section-heading {
  font-size: var(--step-1);
  color: var(--p-grimoire-statblock-heading-color);
  border-bottom: 1px solid var(--p-grimoire-statblock-rule-color);
  padding-bottom: 0.1em;
  margin: var(--space-4) 0 var(--space-3);
}

.statblock__source {
  margin-top: var(--space-3);
  padding-top: var(--space-2);
  border-top: 1px solid var(--p-content-border-color);
}
</style>
