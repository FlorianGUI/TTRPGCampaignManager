/*
 * Checks the theme's foreground/background pairs against WCAG AA, in both
 * themes. Reads the ramps straight out of the preset so it can't drift from it.
 *
 *   node scripts/check-contrast.mjs
 *
 * Exits non-zero if any pair fails, so it can be wired into CI later.
 */
// The primitives layer is deliberately import-free, so this plain Node script
// can read the real ramps rather than regex-parsing the source for them.
import {
  ink,
  vellum,
  gold,
  blood,
  moss,
  torch,
  scrying,
} from '../src/design-system/tokens/primitives.js'

const srgb = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)

function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)
}

function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
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

let failures = 0

for (const [theme, pairs] of [
  ['parchment (light)', parchment],
  ['candlelight (dark)', candlelight],
]) {
  console.log(`\n  ${theme}`)
  console.log(`  ${'─'.repeat(62)}`)
  for (const [label, fg, bg, min] of pairs) {
    const ratio = contrast(fg, bg)
    const ok = ratio >= min
    if (!ok) failures++
    const mark = ok ? '✓' : '✗'
    console.log(
      `  ${mark} ${label.padEnd(24)} ${fg} on ${bg}  ` +
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
