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

// Semantics in table language.
export const blood = {
  300: '#e88f8a',
  400: '#d96b65',
  500: '#c04a44',
  600: '#9e332e',
  700: '#7d2622',
}
export const moss = {
  300: '#8fc39c',
  400: '#6aa87c',
  500: '#4a8a5e',
  600: '#376b48',
  700: '#2a5437',
}
export const torch = {
  300: '#f0c078',
  400: '#e0a458',
  500: '#c9873a',
  600: '#a36a28',
  700: '#7d511e',
}
export const scrying = {
  300: '#9db8dd',
  400: '#7f9dc9',
  500: '#5c7fb0',
  600: '#456490',
  700: '#354e71',
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
  borderRadius,
}
