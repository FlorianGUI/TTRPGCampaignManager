import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'

/*
 * SPIKE — first-draft token values, deliberately kept flat.
 *
 * This is the surface we iterate on to find the visual direction. Once it feels
 * right it gets restructured into the three layers described in issue #23
 * (primitive -> semantic -> component) in separate files. Don't build features
 * on top of it in this shape.
 *
 * Pinned to PrimeVue 4 (MIT). v5 relicensed to a commercial model that shows a
 * license banner without a key; v4's theming is what issue #23 describes anyway.
 * The practical consequence for this file is that themed values live under
 * `colorScheme: { light, dark }` rather than in CSS `light-dark()` pairs.
 */

// ---------------------------------------------------------------------------
// Primitives — raw ramps, no meaning attached.
// The contrast checker parses these by name; see scripts/check-contrast.mjs.
// ---------------------------------------------------------------------------

// Warm near-blacks: leather, ink, banked embers. Never pure #000.
const ink = {
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
const vellum = {
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
const gold = {
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
const blood = { 300: '#e88f8a', 400: '#d96b65', 500: '#c04a44', 600: '#9e332e', 700: '#7d2622' }
const moss = { 300: '#8fc39c', 400: '#6aa87c', 500: '#4a8a5e', 600: '#376b48', 700: '#2a5437' }
const torch = { 300: '#f0c078', 400: '#e0a458', 500: '#c9873a', 600: '#a36a28', 700: '#7d511e' }
const scrying = { 300: '#9db8dd', 400: '#7f9dc9', 500: '#5c7fb0', 600: '#456490', 700: '#354e71' }

/*
 * Surface roles.
 *
 * The two schemes do NOT walk the ramp in the same direction: parchment reads
 * it top-down (content on vellum.0) while candlelight reads it bottom-up
 * (content on ink.900). Naming each role and mapping it per scheme keeps that
 * inversion in one place — every role below is a contrast pair the checker in
 * scripts/check-contrast.mjs verifies by the same name.
 */
const LIGHT_ROLES = {
  page: 100,
  chromeRaised: 50,
  chromeBorder: 300,
  content: 0,
  contentRaised: 50,
  contentBorder: 200,
  rule: 300,
  text: 800,
  textHover: 900,
  textMuted: 600,
  textMutedHover: 700,
  navItem: 700,
  navIcon: 500,
  field: 0,
  fieldFilled: 50,
  fieldDisabled: 100,
  fieldBorder: 500,
  fieldBorderHover: 600,
  fieldPlaceholder: 500,
  listIcon: 400,
  overlay: 0,
  diceBg: 100,
  diceBorder: 300,
}

const DARK_ROLES = {
  page: 950,
  chromeRaised: 900,
  chromeBorder: 800,
  content: 900,
  contentRaised: 800,
  contentBorder: 700,
  rule: 700,
  text: 50,
  textHover: 0,
  textMuted: 200,
  textMutedHover: 100,
  navItem: 100,
  navIcon: 300,
  field: 950,
  fieldFilled: 800,
  fieldDisabled: 800,
  fieldBorder: 500,
  fieldBorderHover: 400,
  fieldPlaceholder: 300,
  listIcon: 400,
  overlay: 800,
  diceBg: 800,
  diceBorder: 600,
}

/*
 * One scheme's colour block. Both schemes share this shape; what differs is the
 * ramp, the role map above, and the direction travelled through the accent.
 */
function scheme({ ramp, roles, accent, onAccent, tone }) {
  // r('text') -> the hex for that role in this scheme's ramp.
  const r = (role) => ramp[roles[role]]

  return {
    surface: { ...ramp },

    primary: {
      color: accent[700],
      contrastColor: onAccent,
      hoverColor: accent[800],
      activeColor: accent[900],
    },

    text: {
      color: r('text'),
      hoverColor: r('textHover'),
      // One step further than Aura's default — the muted pair is where warm
      // palettes fall below 4.5:1.
      mutedColor: r('textMuted'),
      hoverMutedColor: r('textMutedHover'),
    },

    content: {
      background: r('content'),
      hoverBackground: r('contentRaised'),
      borderColor: r('contentBorder'),
      color: '{text.color}',
      hoverColor: '{text.hover.color}',
    },

    navigation: {
      item: {
        color: r('navItem'),
        hoverColor: r('textHover'),
        activeColor: accent[700],
        hoverBackground: r('contentRaised'),
        activeBackground: r('contentRaised'),
        icon: { color: r('navIcon'), hoverColor: r('navItem'), activeColor: accent[700] },
      },
      submenuLabel: { background: 'transparent', color: r('navIcon') },
      submenuIcon: { color: r('navIcon'), hoverColor: r('navItem'), activeColor: accent[700] },
    },

    formField: {
      background: r('field'),
      disabledBackground: r('fieldDisabled'),
      filledBackground: r('fieldFilled'),
      filledHoverBackground: r('fieldFilled'),
      filledFocusBackground: r('field'),
      // fieldBorder sits mid-ramp in both schemes: WCAG 1.4.11 wants 3:1 on a
      // control's boundary and the softer steps miss it.
      borderColor: r('fieldBorder'),
      hoverBorderColor: r('fieldBorderHover'),
      focusBorderColor: accent[600],
      invalidBorderColor: tone.danger,
      color: '{text.color}',
      disabledColor: '{text.muted.color}',
      placeholderColor: r('fieldPlaceholder'),
      invalidPlaceholderColor: tone.danger,
      floatLabelColor: '{text.muted.color}',
      floatLabelFocusColor: accent[700],
      floatLabelActiveColor: '{text.muted.color}',
      floatLabelInvalidColor: '{form.field.invalid.placeholder.color}',
      iconColor: '{text.muted.color}',
      shadow: 'none',
    },

    list: {
      option: {
        focusBackground: r('contentRaised'),
        selectedBackground: '{highlight.background}',
        selectedFocusBackground: '{highlight.focus.background}',
        color: '{text.color}',
        focusColor: '{text.hover.color}',
        selectedColor: '{highlight.color}',
        selectedFocusColor: '{highlight.focus.color}',
        icon: { color: r('listIcon'), focusColor: r('navItem') },
      },
      optionGroup: { background: 'transparent', color: '{text.muted.color}' },
    },

    overlay: {
      select: { background: r('overlay'), borderColor: r('contentBorder'), color: '{text.color}' },
      popover: { background: r('overlay'), borderColor: r('contentBorder'), color: '{text.color}' },
      modal: { background: r('overlay'), borderColor: r('contentBorder'), color: '{text.color}' },
    },

    mask: { background: tone.mask, color: '{text.muted.color}' },

    highlight: {
      background: tone.highlightBackground,
      focusBackground: tone.highlightFocusBackground,
      color: accent[800],
      focusColor: accent[900],
    },

    focusRing: { color: accent[600] },

    // App-owned tokens; PrimeVue emits these as --p-grimoire-*.
    extend: {
      grimoire: {
        // Chrome sits behind and around content — the screen, not the page.
        chrome: {
          background: r('page'),
          raisedBackground: r('chromeRaised'),
          borderColor: r('chromeBorder'),
        },
        rule: { color: r('rule'), strongColor: accent[700] },
        readAloud: {
          background: tone.readAloudBackground,
          borderColor: tone.info,
          color: '{text.color}',
        },
        statblock: {
          background: r('contentRaised'),
          ruleColor: tone.danger,
          headingColor: tone.dangerStrong,
        },
        dice: {
          background: r('diceBg'),
          borderColor: r('diceBorder'),
          color: r('text'),
          critColor: tone.success,
          critBorderColor: tone.successBorder,
          fumbleColor: tone.danger,
          fumbleBorderColor: tone.dangerBorder,
        },
        // Per-context accent, so each bounded context is recognisable at a glance.
        context: {
          campaign: accent[700],
          compendium: tone.info,
          characters: tone.success,
        },
        entity: {
          npc: tone.info,
          location: tone.success,
          item: accent[700],
          monster: tone.dangerStrong,
          faction: tone.warning,
          session: r('navItem'),
        },
      },
    },
  }
}

const light = scheme({
  ramp: vellum,
  roles: LIGHT_ROLES,
  // On parchment the accent must be dark to carry text contrast, so the scheme
  // walks *down* the gold ramp.
  accent: { 600: gold[600], 700: gold[700], 800: gold[800], 900: gold[900] },
  onAccent: vellum[0],
  tone: {
    danger: blood[600],
    dangerStrong: blood[700],
    dangerBorder: blood[500],
    success: moss[600],
    successBorder: moss[500],
    warning: torch[700],
    info: scrying[600],
    mask: 'rgb(37 30 22 / 0.45)',
    highlightBackground: gold[100],
    highlightFocusBackground: gold[200],
    readAloudBackground: 'rgb(92 127 176 / 0.08)',
  },
})

const dark = scheme({
  ramp: ink,
  roles: DARK_ROLES,
  // On candlelight it walks *up* — the same token names, mirrored.
  accent: { 600: gold[400], 700: gold[300], 800: gold[200], 900: gold[100] },
  onAccent: ink[950],
  tone: {
    danger: blood[400],
    dangerStrong: blood[300],
    dangerBorder: blood[500],
    success: moss[400],
    successBorder: moss[500],
    warning: torch[400],
    info: scrying[400],
    mask: 'rgb(6 5 4 / 0.7)',
    highlightBackground: 'rgb(220 179 86 / 0.16)',
    highlightFocusBackground: 'rgb(220 179 86 / 0.24)',
    readAloudBackground: 'rgb(92 127 176 / 0.1)',
  },
})

export const Grimoire = definePreset(Aura, {
  primitive: {
    ink,
    vellum,
    gold,
    blood,
    moss,
    torch,
    scrying,
    borderRadius: {
      none: '0',
      xs: '2px',
      sm: '3px',
      md: '4px',
      lg: '6px',
      xl: '10px',
    },
  },

  semantic: {
    // Book-like rather than app-like: tight radii, quick motion.
    transitionDuration: '0.16s',
    disabledOpacity: '0.45',
    anchorGutter: '2px',

    primary: {
      50: '{gold.50}',
      100: '{gold.100}',
      200: '{gold.200}',
      300: '{gold.300}',
      400: '{gold.400}',
      500: '{gold.500}',
      600: '{gold.600}',
      700: '{gold.700}',
      800: '{gold.800}',
      900: '{gold.900}',
      950: '{gold.950}',
    },

    focusRing: { width: '2px', style: 'solid', offset: '2px', shadow: 'none' },

    formField: {
      paddingX: '0.65rem',
      paddingY: '0.45rem',
      borderRadius: '{border.radius.sm}',
      focusRing: { width: '2px', style: 'solid', offset: '1px', shadow: 'none' },
    },

    list: {
      padding: '0.25rem 0.25rem',
      gap: '2px',
      header: { padding: '0.5rem 0.65rem 0.25rem' },
      option: { padding: '0.4rem 0.65rem', borderRadius: '{border.radius.sm}' },
      optionGroup: { padding: '0.4rem 0.65rem', fontWeight: '600' },
    },

    navigation: {
      list: { padding: '0.25rem 0.25rem', gap: '2px' },
      item: { padding: '0.45rem 0.65rem', borderRadius: '{border.radius.sm}', gap: '0.5rem' },
      submenuLabel: { padding: '0.6rem 0.65rem 0.3rem', fontWeight: '600' },
    },

    content: { borderRadius: '{border.radius.md}' },

    overlay: {
      select: { borderRadius: '{border.radius.md}' },
      popover: { borderRadius: '{border.radius.md}', padding: '0.75rem' },
      modal: { borderRadius: '{border.radius.lg}', padding: '1.25rem' },
    },

    colorScheme: { light, dark },
  },

  components: {
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
  },
})

export default Grimoire
