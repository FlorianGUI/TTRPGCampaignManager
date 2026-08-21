import { blood, torch, moss, scrying, verdigris, wyrd, slate } from './tokens/primitives.js'

/*
 * The prose palette: seven hues, three tiers, and the names both of them go by.
 *
 * **Here rather than in `markdown/`, because this is a palette the dialect
 * happens to expose and not a thing the dialect owns.** Four modules ask it a
 * question and none of them should hold an opinion of its own: `dialect.js`
 * asks whether `{hue=…}` names something, `toolbar.js` asks what the picker's
 * grid is, `ProseColor.vue` asks nothing at all beyond the class, and
 * `check-contrast.mjs` asks for every pair it has to gate. An eighth hue is a
 * row here plus a ramp in `primitives.js` plus three lines of CSS — and nothing
 * else, anywhere.
 *
 * **Named, never free-form.** `{hue=#c04a44}` cannot ship: a hex fixed at write
 * time cannot flip with the scheme — anything readable on parchment is close to
 * invisible on candlelight — and the contrast checker cannot gate a value that
 * is not in a ramp. A name can flip, because the theme owns what it resolves
 * to. That is the whole reason this is tokens and not a colour input.
 *
 * **And it is presentation, which is new.** Every other directive says what
 * something *is* — an NPC, a die roll, a source. This one says what a word
 * *looks like*, and the cost is real: a note is colour-coded to a convention
 * only its author knows. Worth naming here rather than discovering later. A
 * rule the game owns — damage types, say — comes back as its own semantic
 * directive built on these tokens, never as a preset in this picker.
 *
 * `import`-light on purpose: `check-contrast.mjs` is a plain Node script and
 * reads this module directly, the same way it reads `primitives.js`.
 */

/*
 * Hue name → the ramp it draws from.
 *
 * The names follow the house convention — `ink`, `vellum`, `gold`, `blood`,
 * `moss`, `torch`, `scrying` name a thing on the table rather than a wavelength
 * — so `wyrd` and not `violet`. `slate` and `verdigris` sit closest to naming
 * their own colour, and are the two a reader guesses right first time.
 *
 * The key is the ramp's own name, which is what lets `--p-grimoire-prose-*` and
 * `--p-<hue>-*` be read side by side without a translation table.
 */
export const PROSE_HUES = {
  blood: { ramp: blood, label: 'prose.hue.blood' },
  torch: { ramp: torch, label: 'prose.hue.torch' },
  moss: { ramp: moss, label: 'prose.hue.moss' },
  scrying: { ramp: scrying, label: 'prose.hue.scrying' },
  verdigris: { ramp: verdigris, label: 'prose.hue.verdigris' },
  wyrd: { ramp: wyrd, label: 'prose.hue.wyrd' },
  slate: { ramp: slate, label: 'prose.hue.slate' },
}

/*
 * How much of it — three steps of emphasis, in the order the picker draws them.
 *
 * **`subtle`, not `light`.** Jira's third shade is called light because Jira's
 * third shade is genuinely pale. Ours cannot be: a pastel on parchment fails AA
 * outright, so `subtle` is `600` in the light theme — a mid-dark colour — and
 * `400` in the dark one, which is *lighter* than `bold`. The word "light" would
 * be wrong in one theme and misleading in the other. "Subtle" describes the
 * emphasis, which is the thing that actually holds in both.
 *
 * Worth accepting up front: three AA-passing tiers span roughly 4.5:1 to 13:1.
 * That is a visible difference and a compressed one, and it will not look like
 * Jira's palette. A true pastel tier is possible only as a highlight
 * *background*, which is a different feature.
 */
export const PROSE_TIERS = {
  bold: { label: 'prose.tier.bold' },
  medium: { label: 'prose.tier.medium' },
  subtle: { label: 'prose.tier.subtle' },
}

/*
 * What `{hue=moss}` means with no `tier` written.
 *
 * Middle rather than boldest: colour applied to a phrase is a mark, and a mark
 * whose default shouts has to be turned down every time it is used. It is also
 * what the picker leaves out of the syntax — `{hue=moss}` says the same thing
 * as `{hue=moss tier=medium}` in fewer characters a game master has to read.
 */
export const DEFAULT_TIER = 'medium'

/*
 * Whether the dialect accepts this pair. `Object.hasOwn` rather than `in`:
 * `{hue=constructor}` inherits a truthy answer from `Object.prototype` and
 * would resolve to a class nothing has ever styled.
 */
export function isProseColor(hue, tier) {
  return Object.hasOwn(PROSE_HUES, hue) && Object.hasOwn(PROSE_TIERS, tier)
}

/*
 * The class that carries a pair, defined once because two very different places
 * write it: the span in a game master's prose, and the swatch in the picker
 * that puts it there. Its rules live in `base.css` rather than in either
 * component, so both read the same twenty-one.
 */
export function proseColorClass(hue, tier) {
  return `prose-color--${hue}-${tier}`
}

/*
 * The picker's grid, in reading order: a row per tier, a column per hue. Seven
 * across and three down, which is why this is a `Popover` and not the `Menu`
 * the entity kinds sit behind — a palette is a grid, and a menu is a list.
 */
export const PROSE_SWATCHES = Object.entries(PROSE_TIERS).flatMap(([tier, tierMeta]) =>
  Object.entries(PROSE_HUES).map(([hue, hueMeta]) => ({
    hue,
    tier,
    hueLabel: hueMeta.label,
    tierLabel: tierMeta.label,
    class: proseColorClass(hue, tier),
  })),
)
