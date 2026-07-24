/*
 * Layer 3 — component overrides.
 *
 * Only where a PrimeVue component's default shape fights the direction. These
 * reference semantic tokens (`{border.radius.sm}`) rather than primitives, so a
 * ramp change never has to be chased down into this file.
 *
 * `shadow: 'none'` appears deliberately: Aura ships shadows on card and the
 * focus rings, and a book-like surface has no z-axis. See the elevation note in
 * frontend/README.md.
 */
export const components = {
  button: {
    root: {
      borderRadius: '{border.radius.sm}',
      paddingX: '0.85rem',
      paddingY: '0.45rem',
      gap: '0.45rem',
      label: { fontWeight: '600' },
    },
  },
  card: {
    root: { borderRadius: '{border.radius.md}', shadow: 'none' },
    body: { padding: '1.1rem', gap: '0.6rem' },
    caption: { gap: '0.35rem' },
    title: { fontSize: '1.125rem', fontWeight: '600' },
  },
  panel: {
    root: { borderRadius: '{border.radius.md}' },
    header: { padding: '0.7rem 1rem' },
    title: { fontWeight: '600' },
    content: { padding: '0 1rem 1rem 1rem' },
  },
  tag: {
    root: {
      fontSize: '0.75rem',
      fontWeight: '600',
      padding: '0.15rem 0.45rem',
      borderRadius: '{border.radius.xs}',
      gap: '0.3rem',
    },
  },
  inputtext: {
    root: { borderRadius: '{border.radius.sm}' },
  },
  tooltip: {
    root: { maxWidth: '20rem', borderRadius: '{border.radius.sm}', padding: '0.4rem 0.6rem' },
  },
}
