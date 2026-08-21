/*
 * Layer 1 — primitives. Raw ramps and scales, no meaning attached.
 *
 * Nothing here knows what a "border" or a "heading" is; that is the semantic
 * layer's job. Deliberately free of imports so plain Node tooling can read it
 * without pulling in Vue or PrimeVue — scripts/check-contrast.mjs imports this
 * module directly.
 */

// Warm near-blacks: leather, ink, banked embers. Never pure #000.
export const ink = {
  0: '#f7f3ea',
  50: '#ece5d6',
  100: '#dad1bd',
  200: '#c0b49b',
  300: '#a1927a',
  400: '#8a7c66',
  // Lightened from #6b5f4c so form-control borders clear 3:1 on ink.900.
  500: '#726653',
  600: '#524839',
  700: '#3a3229',
  800: '#241f19',
  900: '#17130f',
  950: '#0e0b09',
}

// Aged vellum: the reading surface. Never pure #fff.
export const vellum = {
  0: '#fffdf7',
  50: '#faf4e6',
  100: '#f3ead6',
  200: '#e6d9bd',
  300: '#d3c19f',
  400: '#b8a07b',
  500: '#96805f',
  600: '#6f5e45',
  700: '#544736',
  800: '#3b3125',
  900: '#251e16',
  950: '#150f0a',
}

// Candle-gold — the one arcane accent. Used sparingly, for affordances only.
export const gold = {
  50: '#fdf8ec',
  100: '#f9edcf',
  200: '#f2dca4',
  300: '#e8c877',
  400: '#dcb356',
  500: '#c9973a',
  600: '#a87a2b',
  700: '#7d5720',
  800: '#5c401a',
  900: '#402c14',
  950: '#26190b',
}

/*
 * Semantics in table language — and, since #147, the prose palette too.
 *
 * **Every hue carries 200 through 800.** The four that existed stopped at
 * 300–700, which is enough for one tone per scheme and not enough for three:
 * measured against `vellum[100]`, `torch` cleared 4.5:1 at exactly one step. So
 * the ends were built rather than the tiers picked, and the light theme walks
 * 800/700/600 down while the dark walks 200/300/400 up.
 *
 * **Not 900/800/700 in light**, which also passes AA and is still wrong: at 900
 * the hues converge on near-black and a red, a blue and a violet become three
 * blacks in running prose. 800 is as dark as this palette goes while the hue
 * still survives being read.
 *
 * `500` is the border step (`dangerBorder`, `successBorder`) and no tier uses
 * it. It is here so a new hue is shaped like the old ones and can be borrowed
 * for a border later; a ramp missing its middle is a ramp that cannot be.
 */
export const blood = {
  200: '#f5bcb8',
  300: '#e88f8a',
  400: '#d96b65',
  500: '#c04a44',
  600: '#9e332e',
  700: '#7d2622',
  800: '#5c1a17',
}
export const moss = {
  200: '#b8dcc0',
  300: '#8fc39c',
  400: '#6aa87c',
  500: '#4a8a5e',
  600: '#376b48',
  700: '#2a5437',
  800: '#1e3d28',
}
export const torch = {
  200: '#f7d9a8',
  300: '#f0c078',
  400: '#e0a458',
  500: '#c9873a',
  /*
   * Darkened twice, from #a36a28 and then again from #8f5c22.
   *
   * The first nudge was AA on the page: the original is 3.77:1 on `vellum[100]`
   * and cannot be a text tier at all. The second is AA *inside a read-aloud
   * box*, whose wash composites to `#e7e1d3` over the page — #8f5c22 lands at
   * 4.33:1 there, and a colour that fails only inside one block is the kind of
   * gap nobody finds by looking. This is the tightest pair in the palette at
   * 4.54:1, and the first to re-measure if any surface token moves.
   */
  600: '#8b591f',
  700: '#7d511e',
  800: '#5c3a15',
}
export const scrying = {
  200: '#c3d4e9',
  300: '#9db8dd',
  400: '#7f9dc9',
  500: '#5c7fb0',
  600: '#456490',
  700: '#354e71',
  800: '#26374f',
}

/*
 * The three #147 added, and why each earns a place rather than filling a wheel.
 *
 * `verdigris` is the teal between `moss` and `scrying`: without it those two are
 * the confusable pair at a glance. `wyrd` is violet, which the palette had none
 * of. `slate` is the neutral, and the most-reached-for swatch in any picker is
 * the one that says *less important* — every other hue here says *more*.
 *
 * `gold` is deliberately not among them. It is reserved for affordances, and
 * prose that can borrow the accent makes every link and button on the page
 * ambiguous.
 */
export const verdigris = {
  200: '#a8d8d0',
  300: '#7fc4b9',
  400: '#55a89c',
  500: '#3a8a7e',
  600: '#2b6b61',
  700: '#205349',
  800: '#163c35',
}
export const wyrd = {
  200: '#cbbde0',
  300: '#b09fd0',
  400: '#937fbc',
  500: '#7761a3',
  600: '#5c4a82',
  700: '#463965',
  800: '#322948',
}
export const slate = {
  200: '#c5cbd1',
  300: '#a8b1ba',
  400: '#8b96a1',
  500: '#6f7a86',
  600: '#56606a',
  700: '#414951',
  800: '#2e343a',
}

// Tight radii — a book has crisp edges, not rounded app chrome.
export const borderRadius = {
  none: '0',
  xs: '2px',
  sm: '3px',
  md: '4px',
  lg: '6px',
  xl: '10px',
}

/* The block handed to definePreset's `primitive` key. */
export const primitive = {
  ink,
  vellum,
  gold,
  blood,
  moss,
  torch,
  scrying,
  verdigris,
  wyrd,
  slate,
  borderRadius,
}
