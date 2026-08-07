import { ink, vellum, gold, blood, moss, torch, scrying } from './primitives.js'

/*
 * Layer 2 — semantic. Gives the primitives jobs.
 *
 * Everything colour-bearing in the app reads a token from this layer, never a
 * ramp directly, so a theme switch is a token swap and no component needs to
 * know which scheme is active.
 *
 * Pinned to PrimeVue 4 (MIT); v4 puts themed values under
 * `colorScheme: { light, dark }` rather than in CSS `light-dark()` pairs.
 */

/*
 * Surface roles.
 *
 * The two schemes do NOT walk the ramp in the same direction: parchment reads
 * it top-down (content on vellum.0) while candlelight reads it bottom-up
 * (content on ink.900). Naming each role and mapping it per scheme keeps that
 * inversion in one place — every role below is a contrast pair the checker in
 * scripts/check-contrast.mjs verifies by the same name.
 *
 * Do not collapse these back into shared numeric indices. That is what caused
 * the light-on-light dark theme bug caught during the spike.
 */
export const LIGHT_ROLES = {
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

export const DARK_ROLES = {
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
        // Error text under a form field. `tone.danger` rather than the ramp
        // directly, and the same value the invalid border already uses, so a
        // field and its message cannot drift apart. The pair it makes with the
        // content background is the one check-contrast.mjs calls "danger text
        // on card", already gated at AA in both schemes.
        form: { errorColor: tone.danger },
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
        // Per-section accent, so each nav section is recognisable at a glance.
        // These are nav sections, not backend contexts: `library` is the frontend
        // name for a game master's sources, and has no context of its own.
        context: {
          campaign: accent[700],
          library: tone.info,
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

export const light = scheme({
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

export const dark = scheme({
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

/*
 * The block handed to definePreset's `semantic` key.
 *
 * No elevation scale, deliberately — see the design-system notes in
 * frontend/README.md. Depth here comes from rules, borders and the
 * chrome/content split, and every `shadow` below is explicitly `none`.
 */
export const semantic = {
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
}
