<script setup>
/*
 * The living reference: every token and every component in one place.
 *
 * Both themes, two different ways, deliberately:
 *
 *  - Tokens are rendered for *both* schemes side by side, read straight off the
 *    exported `light` / `dark` objects. That is exact, and it doesn't depend on
 *    which theme the app happens to be in.
 *  - Components are rendered live, in whichever theme is active, with a toggle
 *    in the header. PrimeVue 4 emits light values at `:root` and dark ones under
 *    `.theme-candlelight`, so a subtree can be forced dark but never forced
 *    light — a side-by-side gallery would show dark twice for anyone already in
 *    candlelight. One honest gallery plus a toggle beats two that lie.
 */
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import Tag from 'primevue/tag'

import StatBlock from '../components/domain/StatBlock.vue'
import ReadAloud from '../components/domain/ReadAloud.vue'
import DiceChip from '../components/domain/DiceChip.vue'
import EntityTag from '../components/domain/EntityTag.vue'
import SourceRef from '../components/domain/SourceRef.vue'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'

import {
  ink,
  vellum,
  gold,
  blood,
  moss,
  torch,
  scrying,
} from '../design-system/tokens/primitives.js'
import { light, dark } from '../design-system/tokens/semantic.js'
import { useTheme } from '../design-system/useTheme.js'
import { owlbear } from '../content/sample.js'

const { theme, density, toggleTheme, toggleDensity } = useTheme()

const RAMPS = { ink, vellum, gold, blood, moss, torch, scrying }

const TYPE_STEPS = [
  '--step-5',
  '--step-4',
  '--step-3',
  '--step-2',
  '--step-1',
  '--step-0',
  '--step--1',
  '--step--2',
]
const SPACE_STEPS = [
  '--space-1',
  '--space-2',
  '--space-3',
  '--space-4',
  '--space-5',
  '--space-6',
  '--space-7',
]
const RADII = ['none', 'xs', 'sm', 'md', 'lg', 'xl']

const isColour = (v) => typeof v === 'string' && (v.startsWith('#') || v.startsWith('rgb'))

/* Flattens a scheme into dot-paths so every leaf shows up, not a curated few. */
function flatten(node, prefix = '') {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return value && typeof value === 'object' ? flatten(value, path) : [[path, value]]
  })
}

/* Paired light/dark rows, keyed by the token path they share. */
const semanticRows = (() => {
  const l = Object.fromEntries(flatten(light))
  const d = Object.fromEntries(flatten(dark))
  return [...new Set([...Object.keys(l), ...Object.keys(d)])]
    .sort()
    .map((path) => ({ path, light: l[path], dark: d[path] }))
})()

const surfaceRows = semanticRows.filter((r) => r.path.startsWith('surface.'))
const tokenRows = semanticRows.filter((r) => !r.path.startsWith('surface.'))
</script>

<template>
  <article class="sg">
    <header class="sg__header">
      <p class="label-smallcaps">Design system</p>
      <h1>Styleguide</h1>
      <div class="prose">
        <p>
          Every token and component in the Grimoire preset. Tokens are listed for both schemes at
          once; components render in the active theme — use the toggles to compare.
        </p>
      </div>
      <p class="sg__controls">
        <Button
          :label="`Theme: ${theme}`"
          :icon="theme === 'candlelight' ? 'pi pi-sun' : 'pi pi-moon'"
          severity="secondary"
          outlined
          @click="toggleTheme"
        />
        <Button
          :label="`Density: ${density}`"
          :icon="density === 'compact' ? 'pi pi-bars' : 'pi pi-align-justify'"
          severity="secondary"
          outlined
          @click="toggleDensity"
        />
      </p>
    </header>

    <hr class="rule-double" />

    <!-- ---- Layer 1 ---------------------------------------------------- -->
    <section class="sg__section">
      <h2>Primitives</h2>
      <div class="prose">
        <p>Raw ramps. No meaning attached and identical in both themes.</p>
      </div>

      <div v-for="(ramp, name) in RAMPS" :key="name" class="sg__ramp">
        <p class="label-smallcaps">{{ name }}</p>
        <div class="sg__swatches">
          <div v-for="(hex, step) in ramp" :key="step" class="sg__swatch">
            <span class="sg__chip" :style="{ background: hex }" />
            <span class="sg__step">{{ step }}</span>
            <code class="sg__hex">{{ hex }}</code>
          </div>
        </div>
      </div>
    </section>

    <!-- ---- Layer 2 ---------------------------------------------------- -->
    <section class="sg__section">
      <h2>Semantic tokens</h2>
      <div class="prose">
        <p>
          Both schemes, side by side. The two do not walk the ramp in the same direction — parchment
          reads it top-down, candlelight bottom-up — so the pairs below are the single place that
          inversion is visible.
        </p>
      </div>

      <h3 class="sg__subhead">Surface</h3>
      <table class="sg__table">
        <thead>
          <tr>
            <th>Token</th>
            <th colspan="2">Parchment</th>
            <th colspan="2">Candlelight</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in surfaceRows" :key="row.path">
            <td>
              <code>{{ row.path }}</code>
            </td>
            <td>
              <span
                v-if="isColour(row.light)"
                class="sg__chip"
                :style="{ background: row.light }"
              />
            </td>
            <td>
              <code class="sg__hex">{{ row.light }}</code>
            </td>
            <td>
              <span v-if="isColour(row.dark)" class="sg__chip" :style="{ background: row.dark }" />
            </td>
            <td>
              <code class="sg__hex">{{ row.dark }}</code>
            </td>
          </tr>
        </tbody>
      </table>

      <h3 class="sg__subhead">Roles and app tokens</h3>
      <table class="sg__table">
        <thead>
          <tr>
            <th>Token</th>
            <th colspan="2">Parchment</th>
            <th colspan="2">Candlelight</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in tokenRows" :key="row.path">
            <td>
              <code>{{ row.path }}</code>
            </td>
            <td>
              <span
                v-if="isColour(row.light)"
                class="sg__chip"
                :style="{ background: row.light }"
              />
            </td>
            <td>
              <code class="sg__hex">{{ row.light }}</code>
            </td>
            <td>
              <span v-if="isColour(row.dark)" class="sg__chip" :style="{ background: row.dark }" />
            </td>
            <td>
              <code class="sg__hex">{{ row.dark }}</code>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- ---- Scales ------------------------------------------------------ -->
    <section class="sg__section">
      <h2>Type scale</h2>
      <div v-for="step in TYPE_STEPS" :key="step" class="sg__type-row">
        <code class="sg__hex">{{ step }}</code>
        <span :style="{ fontSize: `var(${step})` }">The Hollow Beneath Greyfen</span>
      </div>

      <h3 class="sg__subhead">Families</h3>
      <p style="font-family: var(--grimoire-font-display)">Display — Cinzel</p>
      <p style="font-family: var(--grimoire-font-body)">Body — Alegreya</p>
      <p style="font-family: var(--grimoire-font-mono)">Mono — IBM Plex Mono</p>

      <h3 class="sg__subhead">Roles</h3>
      <p class="label-smallcaps">label-smallcaps</p>
      <div class="prose prose--opener">
        <p>
          Prose with a drop cap, clamped to the reading measure. Chapter openers only, never
          mid-document.
        </p>
      </div>
    </section>

    <section class="sg__section">
      <h2>Spacing</h2>
      <div v-for="step in SPACE_STEPS" :key="step" class="sg__space-row">
        <code class="sg__hex">{{ step }}</code>
        <span class="sg__bar" :style="{ width: `var(${step})` }" />
      </div>
      <div class="prose">
        <p>Compact density shifts these values only — never the type scale.</p>
      </div>
    </section>

    <section class="sg__section">
      <h2>Radius</h2>
      <div class="sg__radii">
        <div v-for="r in RADII" :key="r" class="sg__radius">
          <span class="sg__radius-box" :style="{ borderRadius: `var(--p-border-radius-${r})` }" />
          <code class="sg__hex">{{ r }}</code>
        </div>
      </div>
    </section>

    <section class="sg__section">
      <h2>Elevation</h2>
      <div class="prose">
        <p>
          There is no elevation scale, deliberately. A printed page has no z-axis: depth here comes
          from rules, borders and the chrome/content split, and every <code>shadow</code> in the
          preset is explicitly <code>none</code>. Shadows survive only on genuinely floating
          surfaces — drawer, popover, menu — where they come from PrimeVue's overlay tokens.
        </p>
      </div>
    </section>

    <!-- ---- Ornament ---------------------------------------------------- -->
    <section class="sg__section">
      <h2>Ornament</h2>
      <p class="label-smallcaps">rule-double</p>
      <hr class="rule-double" />
      <p class="label-smallcaps">rule-fleuron</p>
      <div class="rule-fleuron" role="presentation"><span aria-hidden="true">❖</span></div>
      <p class="label-smallcaps">texture-grain</p>
      <div class="sg__grain texture-grain" />
      <div class="prose">
        <p>
          All of it is gated on <code>--grimoire-texture-opacity</code>, so the
          <code>.no-ornament</code> class turns every flourish off at once.
        </p>
      </div>
    </section>

    <!-- ---- Domain components -------------------------------------------- -->
    <section class="sg__section">
      <h2>Domain components</h2>

      <h3 class="sg__subhead">EntityTag — every kind</h3>
      <p class="sg__row">
        <EntityTag
          v-for="(meta, kind) in ENTITY_KINDS"
          :key="kind"
          :kind="kind"
          :label="meta.label"
        />
      </p>

      <h3 class="sg__subhead">DiceChip — every state</h3>
      <p class="sg__row">
        <DiceChip notation="1d20" />
        <DiceChip notation="2d6 + 3" :result="11" />
        <DiceChip notation="2d8 + 5" :result="19" outcome="crit" />
        <DiceChip notation="1d20" :result="1" outcome="fumble" />
      </p>

      <h3 class="sg__subhead">SourceRef</h3>
      <p class="sg__row">
        <SourceRef work="Cities of the Vale" :page="88" />
        <SourceRef work="SRD 5.1" />
      </p>

      <h3 class="sg__subhead">ReadAloud</h3>
      <ReadAloud>
        <p>
          The causeway ends at a sunken arch, half-swallowed by the peat, its keystone carved with a
          face you cannot quite meet the eyes of.
        </p>
      </ReadAloud>

      <h3 class="sg__subhead">StatBlock</h3>
      <div class="sg__statblock"><StatBlock :creature="owlbear" /></div>
    </section>

    <!-- ---- Overridden PrimeVue components -------------------------------- -->
    <section class="sg__section">
      <h2>PrimeVue components</h2>
      <div class="prose">
        <p>Only those the preset overrides — anything not listed uses Aura's defaults.</p>
      </div>

      <h3 class="sg__subhead">Button</h3>
      <p class="sg__row">
        <Button label="Primary" />
        <Button label="Secondary" severity="secondary" />
        <Button label="Outlined" outlined />
        <Button label="Text" text />
        <Button label="With icon" icon="pi pi-play" />
        <Button icon="pi pi-cog" rounded text aria-label="Settings" />
        <Button label="Disabled" disabled />
      </p>

      <h3 class="sg__subhead">InputText</h3>
      <p class="sg__row">
        <InputText placeholder="Search sources, NPCs, locations…" />
        <InputText placeholder="Invalid" invalid />
        <InputText placeholder="Disabled" disabled />
      </p>

      <h3 class="sg__subhead">Tag</h3>
      <p class="sg__row">
        <Tag value="Primary" />
        <Tag value="Success" severity="success" />
        <Tag value="Warn" severity="warn" />
        <Tag value="Danger" severity="danger" />
        <Tag value="Info" severity="info" />
      </p>

      <h3 class="sg__subhead">Card and Panel</h3>
      <div class="sg__pair">
        <Card>
          <template #title>Card title</template>
          <template #content><p>Flat by design — the preset sets its shadow to none.</p></template>
        </Card>
        <Panel header="Panel header">
          <p>Tight radii, book-like rather than app-like.</p>
        </Panel>
      </div>
    </section>
  </article>
</template>

<style scoped>
.sg {
  max-width: 68rem;
}

.sg__section {
  margin-top: var(--space-7);
}

.sg__section > h2 {
  margin-bottom: var(--space-3);
}

.sg__subhead {
  margin: var(--space-5) 0 var(--space-3);
}

.sg__controls,
.sg__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  margin-top: var(--space-3);
}

/* ---- Colour ---------------------------------------------------------- */

.sg__ramp {
  margin-top: var(--space-4);
}

.sg__swatches {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.sg__swatch {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  align-items: center;
}

.sg__chip {
  display: inline-block;
  width: 2.75rem;
  height: 1.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-xs);
}

.sg__step {
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
}

.sg__hex {
  font-family: var(--grimoire-font-mono);
  font-size: var(--step--2);
  color: var(--p-text-muted-color);
}

/* ---- Tables ---------------------------------------------------------- */

/* Long token tables scroll in their own container rather than the page. */
.sg__table {
  display: block;
  overflow-x: auto;
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-3);
  font-size: var(--step--1);
}

.sg__table th {
  text-align: left;
  font-family: var(--grimoire-font-display);
  font-size: var(--step--2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  padding: 0.3rem var(--space-2);
  border-bottom: 1px solid var(--p-grimoire-rule-color);
  white-space: nowrap;
}

.sg__table td {
  padding: 0.25rem var(--space-2);
  border-bottom: 1px solid var(--p-content-border-color);
  vertical-align: middle;
  white-space: nowrap;
}

.sg__table .sg__chip {
  width: 1.75rem;
  height: 1.1rem;
}

/* ---- Scales ---------------------------------------------------------- */

.sg__type-row,
.sg__space-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-4);
  margin-bottom: var(--space-2);
}

.sg__type-row > code,
.sg__space-row > code {
  flex: 0 0 5rem;
}

.sg__bar {
  display: inline-block;
  height: 0.75rem;
  background: var(--p-primary-color);
  border-radius: var(--p-border-radius-xs);
}

.sg__radii {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.sg__radius {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
}

.sg__radius-box {
  width: 3rem;
  height: 3rem;
  background: var(--p-content-hover-background);
  border: 1px solid var(--p-content-border-color);
}

.sg__grain {
  height: 4rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  background: var(--p-grimoire-chrome-background);
}

/* ---- Component gallery ------------------------------------------------ */

.sg__statblock {
  max-width: 26rem;
}

.sg__pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: var(--space-4);
  margin-top: var(--space-3);
}
</style>
