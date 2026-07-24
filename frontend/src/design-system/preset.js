import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import { primitive } from './tokens/primitives.js'
import { semantic } from './tokens/semantic.js'
import { components } from './tokens/components.js'

/*
 * The Grimoire preset — composition only. All values live in the three token
 * layers under tokens/, and each layer may only reach downwards:
 *
 *   primitives  raw ramps and scales, no meaning, no imports
 *        ↑
 *   semantic    gives primitives jobs; owns the light/dark schemes
 *        ↑
 *   components  per-component overrides, referencing semantic tokens
 *
 * Pinned to PrimeVue 4 (MIT). v5 relicensed to a commercial model that shows a
 * license banner without a key, so don't bump the major.
 */
export const Grimoire = definePreset(Aura, {
  primitive,
  semantic,
  components,
})

export default Grimoire
