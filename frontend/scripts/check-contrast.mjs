/*
 * Checks the theme's foreground/background pairs against WCAG AA, in both
 * themes. Reads the ramps straight out of the preset so it can't drift from it.
 *
 *   node scripts/check-contrast.mjs
 *
 * Exits non-zero if any pair fails, so it can be wired into CI later.
 */
// The primitives layer is deliberately import-free, so this plain Node script
// can read the real ramps rather than regex-parsing the source for them. The
// two modules below are framework-free for the same reason, and are read here
// so the prose pairs are generated from the real palette — see PROSE below.
import {
  ink,
  vellum,
  gold,
  blood,
  moss,
  torch,
  scrying,
} from '../src/design-system/tokens/primitives.js'
import { PROSE_HUES, PROSE_TIERS } from '../src/design-system/proseColors.js'
import {
  LIGHT_PROSE_TIERS,
  DARK_PROSE_TIERS,
  READ_ALOUD_WASH,
} from '../src/design-system/tokens/semantic.js'

const srgb = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)

const channels = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))

function luminance(hex) {
  const [r, g, b] = channels(hex).map((c) => c / 255)
  return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)
}

function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
}

/*
 * A translucent wash flattened onto what is behind it.
 *
 * A ratio needs two opaque colours, and `readAloudBackground` is not one: text
 * in a read-aloud box sits on the card or the page *seen through* the wash.
 * Checking against the card alone is checking a surface nobody reads on, which
 * is how `torch` `subtle` sat below AA inside a read-aloud block while passing
 * everywhere else.
 */
function composite([r, g, b], alpha, backdrop) {
  const under = channels(backdrop)

  return `#${[r, g, b]
    .map((c, i) => Math.round(c * alpha + under[i] * (1 - alpha)))
    .map((c) => c.toString(16).padStart(2, '0'))
    .join('')}`
}

// [label, foreground, background, minimum]
// 4.5 = AA body text, 3.0 = AA large text (>=24px, or >=18.66px bold) and UI
// component boundaries per WCAG 1.4.11.
const parchment = [
  ['body text on card', vellum[800], vellum[0], 4.5],
  ['body text on page', vellum[800], vellum[100], 4.5],
  ['muted text on card', vellum[600], vellum[0], 4.5],
  ['muted text on page', vellum[600], vellum[100], 4.5],
  ['heading on card', vellum[900], vellum[0], 3],
  ['primary accent on card', gold[700], vellum[0], 4.5],
  ['primary accent on page', gold[700], vellum[100], 4.5],
  ['primary button label', vellum[0], gold[700], 4.5],
  ['focus ring on card', gold[600], vellum[0], 3],
  // Decorative separation only, so no AA floor; listed to keep it visible.
  ['card border on page', vellum[200], vellum[100], 1.0],
  // WCAG 1.4.11: a control's boundary needs 3:1 against the adjacent surface.
  ['input border on card', vellum[500], vellum[0], 3],
  ['danger text on card', blood[600], vellum[0], 4.5],
  ['success text on card', moss[600], vellum[0], 4.5],
  ['warning text on card', torch[700], vellum[0], 4.5],
  ['info text on card', scrying[600], vellum[0], 4.5],
  ['statblock heading', blood[700], vellum[50], 4.5],
  ['statblock body', vellum[800], vellum[50], 4.5],
  ['dice chip text', vellum[800], vellum[100], 4.5],
  ['entity/npc chip', scrying[700], vellum[0], 4.5],
  ['entity/location chip', moss[700], vellum[0], 4.5],
  ['entity/item chip', gold[700], vellum[0], 4.5],
  ['entity/monster chip', blood[700], vellum[0], 4.5],
  ['entity/faction chip', torch[700], vellum[0], 4.5],
  ['nav item rest', vellum[700], vellum[100], 4.5],
  ['nav item active', gold[700], vellum[100], 4.5],
  ['nav icon rest', vellum[500], vellum[100], 3],
]

const candlelight = [
  ['body text on card', ink[50], ink[900], 4.5],
  ['body text on page', ink[50], ink[950], 4.5],
  ['muted text on card', ink[200], ink[900], 4.5],
  ['muted text on page', ink[200], ink[950], 4.5],
  ['heading on card', ink[0], ink[900], 3],
  ['primary accent on card', gold[300], ink[900], 4.5],
  ['primary accent on page', gold[300], ink[950], 4.5],
  ['primary button label', ink[950], gold[400], 4.5],
  ['focus ring on card', gold[400], ink[900], 3],
  ['card border on page', ink[700], ink[950], 1.0],
  ['input border on card', ink[500], ink[900], 3],
  ['danger text on card', blood[400], ink[900], 4.5],
  ['success text on card', moss[400], ink[900], 4.5],
  ['warning text on card', torch[400], ink[900], 4.5],
  ['info text on card', scrying[400], ink[900], 4.5],
  ['statblock heading', blood[300], ink[800], 4.5],
  ['statblock body', ink[50], ink[800], 4.5],
  ['dice chip text', ink[50], ink[800], 4.5],
  ['entity/npc chip', scrying[300], ink[900], 4.5],
  ['entity/location chip', moss[300], ink[900], 4.5],
  ['entity/item chip', gold[300], ink[900], 4.5],
  ['entity/monster chip', blood[300], ink[900], 4.5],
  ['entity/faction chip', torch[300], ink[900], 4.5],
  ['nav item rest', ink[100], ink[950], 4.5],
  ['nav item active', gold[300], ink[950], 4.5],
  ['nav icon rest', ink[300], ink[950], 3],
]

/*
 * The prose palette (#147): seven hues × three tiers × four surfaces, per
 * theme. Eighty-four pairs.
 *
 * **Generated, not transcribed.** The `[label, fg, bg, min]` tuples above are
 * readable at their count and would drown at this one — and a hand-written row
 * per swatch is a row somebody forgets when an eighth hue is added, which is
 * precisely the pair that would then ship below AA. This reads the same tables
 * the app renders from, so a hue that exists is a hue that is checked.
 *
 * Four surfaces rather than two: a colour can sit on a card, on the page, or on
 * either of those seen through a read-aloud box's wash.
 */
function proseSurfaces(card, page, alpha) {
  return [
    ['card', card],
    ['page', page],
    ['read-aloud/card', composite(READ_ALOUD_WASH.tint, alpha, card)],
    ['read-aloud/page', composite(READ_ALOUD_WASH.tint, alpha, page)],
  ]
}

function prosePairs(tiers, surfaces) {
  return Object.entries(PROSE_HUES).flatMap(([hue, { ramp }]) =>
    Object.keys(PROSE_TIERS).flatMap((tier) =>
      surfaces.map(([where, background]) => [
        `prose ${hue} ${tier} on ${where}`,
        ramp[tiers[tier]],
        background,
        4.5,
      ]),
    ),
  )
}

const parchmentProse = prosePairs(
  LIGHT_PROSE_TIERS,
  proseSurfaces(vellum[0], vellum[100], READ_ALOUD_WASH.light),
)
const candlelightProse = prosePairs(
  DARK_PROSE_TIERS,
  proseSurfaces(ink[900], ink[950], READ_ALOUD_WASH.dark),
)

let failures = 0

for (const [theme, pairs] of [
  ['parchment (light)', [...parchment, ...parchmentProse]],
  ['candlelight (dark)', [...candlelight, ...candlelightProse]],
]) {
  console.log(`\n  ${theme}`)
  console.log(`  ${'─'.repeat(72)}`)
  for (const [label, fg, bg, min] of pairs) {
    const ratio = contrast(fg, bg)
    const ok = ratio >= min
    if (!ok) failures++
    const mark = ok ? '✓' : '✗'
    console.log(
      `  ${mark} ${label.padEnd(34)} ${fg} on ${bg}  ` +
        `${ratio.toFixed(2).padStart(5)}:1  (min ${min})`,
    )
  }
}

console.log(
  failures === 0
    ? '\n  All pairs pass WCAG AA.\n'
    : `\n  ${failures} pair(s) below AA — fix the ramp before building on it.\n`,
)
process.exit(failures === 0 ? 0 : 1)
