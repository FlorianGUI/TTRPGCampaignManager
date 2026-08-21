import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Grimoire from './preset.js'
import {
  DEFAULT_TIER,
  PROSE_HUES,
  PROSE_SWATCHES,
  PROSE_TIERS,
  isProseColor,
  proseColorClass,
} from './proseColors.js'
import { gold } from './tokens/primitives.js'
import { LIGHT_PROSE_TIERS, DARK_PROSE_TIERS, light, dark } from './tokens/semantic.js'

/*
 * The palette is asked the same question by four modules that must never
 * disagree: the dialect (is this a colour?), the picker (what can be chosen?),
 * the tokens (what does it resolve to?) and the stylesheet (what paints it?).
 *
 * Every check below is one of those four agreeing with the table, and the last
 * one is the only one a person has to maintain by hand.
 */

/*
 * Read as text, not imported: what is being checked is the stylesheet's own
 * source, and `import '…css'` hands back a module Vite has already processed.
 * A path rather than a `URL` because these run in jsdom, whose `URL` is not the
 * one `node:fs` accepts.
 */
const css = readFileSync(join(import.meta.dirname, '../assets/base.css'), 'utf8')

describe('the prose palette', () => {
  it('names a real ramp for every hue', () => {
    for (const [hue, { ramp }] of Object.entries(PROSE_HUES)) {
      expect(ramp, hue).toBeTypeOf('object')
    }
  })

  /*
   * Three tiers is why the ramps were extended at all: measured on the page,
   * `torch` cleared AA at exactly one step before #147. A ramp missing an end is
   * a hue that silently resolves to `undefined` in one theme.
   */
  it('carries every step both schemes ask of every ramp', () => {
    for (const [hue, { ramp }] of Object.entries(PROSE_HUES)) {
      for (const steps of [LIGHT_PROSE_TIERS, DARK_PROSE_TIERS]) {
        for (const [tier, step] of Object.entries(steps)) {
          expect(ramp[step], `${hue} ${tier} (${step})`).toMatch(/^#[0-9a-f]{6}$/)
        }
      }
    }
  })

  /* `primitives.js` reserves gold for affordances. Prose that can borrow the
     accent makes every link and button on the page ambiguous. */
  it('does not offer the accent as a prose colour', () => {
    for (const { ramp } of Object.values(PROSE_HUES)) {
      expect(ramp).not.toBe(gold)
    }
  })

  it('gives both schemes the same tiers, and the picker the same again', () => {
    const tiers = Object.keys(PROSE_TIERS)

    expect(Object.keys(LIGHT_PROSE_TIERS)).toEqual(tiers)
    expect(Object.keys(DARK_PROSE_TIERS)).toEqual(tiers)
    expect(tiers).toContain(DEFAULT_TIER)
  })

  /*
   * The two schemes walk the ramp in opposite directions — light down from 800,
   * dark up from 200 — which is the same inversion `LIGHT_ROLES` and
   * `DARK_ROLES` are kept apart to preserve. Collapsed into shared indices, this
   * is twenty-one dark-on-dark spans.
   */
  it('states its own values in each scheme rather than deriving one from the other', () => {
    for (const [hue, tiers] of Object.entries(light.extend.grimoire.prose)) {
      for (const [tier, hex] of Object.entries(tiers)) {
        expect(dark.extend.grimoire.prose[hue][tier], `${hue} ${tier}`).not.toBe(hex)
      }
    }
  })

  it('emits a token for every swatch in both schemes', () => {
    for (const { hue, tier } of PROSE_SWATCHES) {
      expect(light.extend.grimoire.prose[hue]?.[tier], `light ${hue} ${tier}`).toMatch(/^#/)
      expect(dark.extend.grimoire.prose[hue]?.[tier], `dark ${hue} ${tier}`).toMatch(/^#/)
    }
  })

  it('lays the picker out as a row per tier and a column per hue', () => {
    expect(PROSE_SWATCHES).toHaveLength(
      Object.keys(PROSE_HUES).length * Object.keys(PROSE_TIERS).length,
    )
    expect(PROSE_SWATCHES.slice(0, Object.keys(PROSE_HUES).length).map((s) => s.tier)).toEqual(
      Array(Object.keys(PROSE_HUES).length).fill(Object.keys(PROSE_TIERS)[0]),
    )
  })

  /*
   * `Object.hasOwn`, not `in`: `{hue=constructor}` inherits a truthy answer from
   * `Object.prototype` and would resolve to a class nothing has ever styled.
   */
  it('refuses a name inherited from the prototype', () => {
    expect(isProseColor('constructor', DEFAULT_TIER)).toBe(false)
    expect(isProseColor('moss', 'toString')).toBe(false)
    expect(isProseColor('moss', DEFAULT_TIER)).toBe(true)
  })

  /*
   * **The one table in the app that is written out rather than generated.** CSS
   * cannot build a custom-property name from a class, so `base.css` spells all
   * twenty-one out — and this is what keeps that copy honest. An eighth hue
   * added to `PROSE_HUES` fails here rather than shipping three swatches that
   * render unstyled.
   */
  it('has a rule in base.css for every swatch, and none for anything else', () => {
    for (const { hue, tier } of PROSE_SWATCHES) {
      const rule = new RegExp(
        `\\.${proseColorClass(hue, tier)}\\s*\\{[^}]*--prose-color:\\s*` +
          `var\\(--p-grimoire-prose-${hue}-${tier}\\)`,
      )

      expect(css, `${hue} ${tier}`).toMatch(rule)
    }

    expect(css.match(/\.prose-color--/g)).toHaveLength(PROSE_SWATCHES.length)
  })

  /*
   * The seam nothing else covers: a class in `base.css` names a CSS variable,
   * and whether PrimeVue emits a variable by that name is a fact about how
   * `definePreset` flattens `extend.grimoire.prose.<hue>.<tier>`. Get the
   * nesting wrong and every rule above resolves to nothing — twenty-one spans
   * rendering in the inherited text colour, which is exactly the failure that
   * looks like no failure at all.
   *
   * Both schemes, because the dark values live under the theme's selector and a
   * scheme that emitted none would leave the light values in place — a palette
   * that does not flip, which is the whole reason this is tokens.
   */
  it('emits a variable for every rule, in both schemes', () => {
    mount(
      { template: '<div />' },
      {
        global: {
          plugins: [
            [PrimeVue, { theme: { preset: Grimoire, options: { darkModeSelector: '.dark' } } }],
          ],
        },
      },
    )

    const emitted = [...document.querySelectorAll('style')].map((tag) => tag.textContent).join('\n')
    const [parchment, candlelight] = emitted.split('.dark')

    for (const { hue, tier } of PROSE_SWATCHES) {
      const variable = `--p-grimoire-prose-${hue}-${tier}`

      expect(parchment, `light ${hue} ${tier}`).toContain(
        `${variable}:${light.extend.grimoire.prose[hue][tier]}`,
      )
      expect(candlelight, `dark ${hue} ${tier}`).toContain(
        `${variable}:${dark.extend.grimoire.prose[hue][tier]}`,
      )
    }
  })
})
