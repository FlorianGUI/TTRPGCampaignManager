import { describe, expect, it, vi } from 'vitest'
import {
  COLOR_ITEMS,
  COMMONMARK_ITEMS,
  MARKER_ITEMS,
  TOOLBAR_ITEMS,
  applyInsertion,
  narrowedTo,
} from './toolbar.js'
import { DIRECTIVES, propsFor } from './dialect.js'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import { DEFAULT_TIER, PROSE_HUES, PROSE_TIERS } from '../design-system/proseColors.js'
import { labelOf } from './nodes.js'
import { parse } from './parse.js'

const itemFor = (name) => TOOLBAR_ITEMS.find((item) => item.name === name)

/* Where the caret ended up, written into the string so a failure reads as text
   rather than as two numbers that have to be counted out by hand. */
function withCaret({ value, caret }) {
  return `${value.slice(0, caret)}‸${value.slice(caret)}`
}

const insert = (name, value, start, end = start) =>
  withCaret(applyInsertion(itemFor(name), value, start, end))

describe('the toolbar is derived, not transcribed', () => {
  it('offers every directive the renderer implements', () => {
    expect(TOOLBAR_ITEMS.map((item) => item.name).sort()).toEqual(Object.keys(DIRECTIVES).sort())
  })

  it('offers every entity kind', () => {
    for (const kind of Object.keys(ENTITY_KINDS)) {
      expect(itemFor(kind)).toBeDefined()
    }
  })

  /* The acceptance test for #103's third box, and the reason this module reads
     `DIRECTIVES` instead of listing what it knows. A kind added to the table
     must arrive here without this file — or that one — being edited.

     Mocked rather than mutated: `DIRECTIVES` is built when `dialect.js` is
     imported, so pushing a kind into the live object proves nothing. The whole
     chain is rebuilt on top of a table that has `scene` in it, which is what
     adding one would actually do. */
  it('picks up a kind added to ENTITY_KINDS with no second edit', async () => {
    vi.resetModules()
    vi.doMock('../components/domain/entityKinds.js', () => ({
      ENTITY_KINDS: { ...ENTITY_KINDS, scene: { icon: 'pi-play', label: 'kind.scene' } },
    }))

    try {
      const fresh = await import('./toolbar.js')

      expect(fresh.TOOLBAR_ITEMS.map((item) => item.name)).toContain('scene')
      expect(fresh.TOOLBAR_ITEMS.find((item) => item.name === 'scene').icon).toBe('pi-play')
    } finally {
      vi.doUnmock('../components/domain/entityKinds.js')
      vi.resetModules()
    }
  })

  it('takes an entity kind face from ENTITY_KINDS rather than repeating it', () => {
    expect(itemFor('npc').icon).toBe(ENTITY_KINDS.npc.icon)
    expect(itemFor('npc').label).toBe(ENTITY_KINDS.npc.label)
  })

  /* A face of some sort, so none arrives blank — a named font icon for most, a
     drawn one where PrimeIcons has nothing to name. */
  it('gives every button a face, so none arrives blank', () => {
    for (const item of TOOLBAR_ITEMS) {
      expect(item.icon || item.drawn, item.name).toBeTruthy()
    }
  })

  /* The two are exclusive: an item that draws its own must not also carry a
     font icon, or the button would render both. */
  it('never gives a button two faces', () => {
    for (const item of TOOLBAR_ITEMS) {
      expect(Boolean(item.icon) && Boolean(item.drawn), item.name).toBe(false)
    }
  })

  /* PrimeIcons has no die, and the nearest thing in it is a lightning bolt. */
  it('draws the dice button rather than naming it', () => {
    expect(itemFor('dice').drawn).toBe('die')
    expect(itemFor('dice').icon).toBeNull()
  })

  it('opens a container directive on its own lines and an inline one in place', () => {
    expect(itemFor('read-aloud').block).toBe(true)
    expect(itemFor('npc').block).toBeUndefined()
  })
})

describe('inserting a directive', () => {
  it('wraps a selection as the label', () => {
    expect(insert('npc', 'The party meets Maerin Holt outside.', 16, 27)).toBe(
      'The party meets :npc[Maerin Holt]‸ outside.',
    )
  })

  it('leaves the caret where the label goes when there is no selection', () => {
    expect(insert('npc', 'The party meets  outside.', 16)).toBe('The party meets :npc[‸] outside.')
  })

  it('leaves the caret in the attribute when the label is already written', () => {
    expect(insert('dice', 'Rolls 2d8 + 5 to hit.', 6, 13)).toBe(
      'Rolls :dice[2d8 + 5]{result=‸} to hit.',
    )
  })

  it('offers the page attribute on a source reference', () => {
    expect(insert('ref', 'See Cities of the Vale.', 4, 22)).toBe(
      'See :ref[Cities of the Vale]{page=‸}.',
    )
  })

  it('wraps a selected block rather than replacing it', () => {
    expect(insert('read-aloud', 'A cold wind.', 0, 12)).toBe(':::read-aloud\nA cold wind.\n:::‸')
  })

  /* A block directive opened mid-paragraph is part of that paragraph's text, so
     it renders as itself — the exact failure the button exists to prevent. */
  it('breaks the line before a block directive that would land mid-sentence', () => {
    expect(insert('read-aloud', 'Before. After.', 8)).toBe(
      'Before. \n:::read-aloud\n‸\n:::\nAfter.',
    )
  })

  it('adds no line of its own when the caret already has one', () => {
    expect(insert('read-aloud', 'Before.\n\nAfter.', 8, 8)).toBe(
      'Before.\n:::read-aloud\n‸\n:::\nAfter.',
    )
  })

  it('leaves the rest of the field untouched', () => {
    const { value } = applyInsertion(itemFor('npc'), 'one two three', 4, 7)

    expect(value.startsWith('one ')).toBe(true)
    expect(value.endsWith(' three')).toBe(true)
  })
})

/*
 * The insertion is only worth anything if the parser agrees it is a directive.
 * These read what a button writes back through the real parser, so a change to
 * the dialect that breaks the syntax the toolbar types fails here rather than on
 * a game master's page.
 */
describe('what a button writes is what the parser reads', () => {
  const directiveIn = (source) => {
    const found = []
    const walk = (node) => {
      if (node.type in { textDirective: 1, leafDirective: 1, containerDirective: 1 })
        found.push(node)
      for (const child of node.children ?? []) walk(child)
    }
    walk(parse(source))
    return found
  }

  it('writes a real directive for every button', () => {
    for (const item of TOOLBAR_ITEMS) {
      const { value } = applyInsertion(item, 'Label', 0, 5)
      const [directive] = directiveIn(value)

      expect(directive, `${item.name} did not parse`).toBeDefined()
      expect(directive.name).toBe(item.name)
    }
  })

  it('writes a form the renderer accepts', () => {
    for (const item of TOOLBAR_ITEMS) {
      const { value } = applyInsertion(item, 'Label', 0, 5)
      const [directive] = directiveIn(value)

      expect(DIRECTIVES[item.name].types, `${item.name} wrote the wrong form`).toContain(
        directive.type,
      )
    }
  })

  it('carries the selected words through as the label', () => {
    const { value } = applyInsertion(itemFor('npc'), 'Maerin Holt', 0, 11)
    const [directive] = directiveIn(value)

    expect(directive.children[0].value).toBe('Maerin Holt')
  })
})

/*
 * The palette (#147). Twenty-one buttons for one directive, and the only set in
 * the toolbar whose members differ by attribute rather than by name.
 */
describe('the colour picker', () => {
  const firstDirective = (source) => {
    let found = null
    const walk = (node) => {
      if (!found && node.type === 'textDirective') found = node
      for (const child of node.children ?? []) walk(child)
    }
    walk(parse(source))
    return found
  }

  it('offers every hue at every tier', () => {
    expect(COLOR_ITEMS).toHaveLength(
      Object.keys(PROSE_HUES).length * Object.keys(PROSE_TIERS).length,
    )

    for (const hue of Object.keys(PROSE_HUES)) {
      for (const tier of Object.keys(PROSE_TIERS)) {
        expect(
          COLOR_ITEMS.some((item) => item.hue === hue && item.tier === tier),
          `${hue} ${tier}`,
        ).toBe(true)
      }
    }
  })

  /* The whole point of a picker: nobody has to know the attribute names. */
  it('writes the hue and the tier a game master clicked', () => {
    const bold = COLOR_ITEMS.find((item) => item.hue === 'torch' && item.tier === 'bold')

    expect(withCaret(applyInsertion(bold, 'a searing light here', 2, 15))).toBe(
      'a :color[searing light]{hue=torch tier=bold}‸ here',
    )
  })

  /*
   * `{hue=slate}`, not `{hue=slate tier=medium}`. A default exists so the common
   * case is short, and a picker that spelled it out anyway would teach a syntax
   * longer than the one it documents.
   */
  it('leaves the default tier out of the syntax', () => {
    const medium = COLOR_ITEMS.find((item) => item.hue === 'slate' && item.tier === DEFAULT_TIER)

    expect(withCaret(applyInsertion(medium, 'already open', 0, 12))).toBe(
      ':color[already open]{hue=slate}‸',
    )
  })

  /* Written and read back through the real parser and the real dialect: a
     swatch that produced a directive the renderer refuses would put text on the
     page where a colour was asked for. */
  it('writes something the dialect accepts, for every swatch', () => {
    for (const item of COLOR_ITEMS) {
      const { value } = applyInsertion(item, 'Words', 0, 5)
      const node = firstDirective(value)

      expect(node, `${item.name} did not parse`).not.toBeNull()
      expect(propsFor(node, labelOf(node)), item.name).toEqual({
        hue: item.hue,
        tier: item.tier,
      })
    }
  })

  /* Behind the door, not on the row — twenty-one more controls would have
     undone the shortening #146 was for. */
  it('keeps the swatches off the toolbar row', () => {
    expect(MARKER_ITEMS.map((item) => item.name)).not.toContain('color')
  })
})

/*
 * The CommonMark half. Hand-written rather than derived, because CommonMark is a
 * fixed spec and cannot grow under the toolbar the way `DIRECTIVES` can — but it
 * can drift from the *renderer*, which is what these check.
 */
describe('the CommonMark half', () => {
  const plain = (name) => COMMONMARK_ITEMS.find((item) => item.name === name)
  const write = (name, value, start, end = start) =>
    withCaret(applyInsertion(plain(name), value, start, end))

  it('offers nothing the parser cannot read', () => {
    const names = COMMONMARK_ITEMS.map((item) => item.name)

    expect(names).not.toContain('strikethrough')
    expect(names).not.toContain('table')
    expect(names).not.toContain('image')
  })

  it('names every button through the catalogue', () => {
    for (const item of COMMONMARK_ITEMS) expect(item.label).toMatch(/^markdown\./)
  })

  it('wraps a selection in an inline mark', () => {
    expect(write('bold', 'quite important', 6, 15)).toBe('quite **important**‸')
  })

  it('leaves the caret between the marks when there is no selection', () => {
    expect(write('italic', 'a  b', 2)).toBe('a *‸* b')
  })

  it('seeds a link with the scheme safeUrl will accept', () => {
    expect(write('link', 'the tide table', 0, 14)).toBe('[the tide table](https://‸)')
  })

  /* The caret keeps its place in the words rather than jumping to the end: the
     line moved, the sentence did not. */
  it('marks the line the caret is on, not the selection', () => {
    expect(write('heading', 'The causeway', 4)).toBe('## The ‸causeway')
  })

  it('marks every line a selection touches', () => {
    expect(write('bullet', 'salt\nrope\nlantern', 2, 12)).toBe('- salt\n- rope\n- la‸ntern')
  })

  /* `1.` on each line: CommonMark numbers from the first item and ignores the
     rest, so the source never has to be renumbered when a line moves. */
  it('numbers an ordered list without counting', () => {
    expect(write('ordered', 'one\ntwo', 0, 7)).toBe('1. one\n1. two‸')
  })

  /* A button whose only direction is on has to be undone by hand. */
  it('takes a prefix off again when every line already has it', () => {
    expect(write('quote', '> salt\n> rope', 0, 13)).toBe('salt\nrope‸')
  })

  it('adds the prefix when only some lines have it', () => {
    expect(write('bullet', '- salt\nrope', 0, 11)).toBe('- - salt\n- rope‸')
  })

  it('opens a fence around a selected block', () => {
    expect(write('codeBlock', '  +---+', 0, 7)).toBe('```\n  +---+\n```‸')
  })

  /* A rule separates; it has nothing to say about the words that were selected,
     and wrapping them in `---` would destroy them and write something that is
     not a thematic break. */
  it('drops a rule on its own line and keeps the selection', () => {
    expect(write('rule', 'before\nafter', 6, 6)).toBe('before\n\n---\n\n‸after')
  })

  /*
   * `---` on the line directly under a paragraph is a setext heading: it turns
   * that paragraph into an h2 and draws no rule. The failure lands on the
   * sentence above, nowhere near where the button was pressed.
   */
  it('leaves a blank line so the paragraph above stays a paragraph', () => {
    const { value } = applyInsertion(plain('rule'), 'A cold wind.', 12, 12)

    expect(value).toBe('A cold wind.\n\n---\n')
  })

  it('leaves a selection alone when dropping a rule', () => {
    const { value } = applyInsertion(plain('rule'), 'keep me', 0, 7)

    expect(value).toContain('keep me')
    expect(value).toContain('---')
  })
})

/*
 * The half that can rot: every CommonMark button must produce something
 * `render.js` has a case for. A mark that stopped rendering would otherwise show
 * up as literal asterisks on a game master's page.
 */
describe('what the CommonMark buttons write is what the renderer draws', () => {
  const typesIn = (source) => {
    const found = new Set()
    const walk = (node) => {
      found.add(node.type)
      for (const child of node.children ?? []) walk(child)
    }
    walk(parse(source))
    return found
  }

  const EXPECTED = {
    bold: 'strong',
    italic: 'emphasis',
    heading: 'heading',
    bullet: 'list',
    ordered: 'list',
    quote: 'blockquote',
    code: 'inlineCode',
    codeBlock: 'code',
    rule: 'thematicBreak',
    link: 'link',
  }

  it('covers every button', () => {
    expect(Object.keys(EXPECTED).sort()).toEqual(COMMONMARK_ITEMS.map((i) => i.name).sort())
  })

  it('parses into the node the renderer maps', () => {
    for (const item of COMMONMARK_ITEMS) {
      const { value } = applyInsertion(item, 'Words', 0, 5)

      expect(typesIn(value), `${item.name} wrote something else`).toContain(EXPECTED[item.name])
    }
  })

  /* The three that look obvious and would each write text the parser walks
     straight past. Guarded here so nobody adds them back believing they were
     merely forgotten. */
  it('confirms the excluded three still do not parse', () => {
    expect(typesIn('~~gone~~')).not.toContain('delete')
    expect(typesIn('| a | b |\n|---|---|\n| 1 | 2 |')).not.toContain('table')
    expect(typesIn('![map](/m.png)').has('image')).toBe(true)
  })
})

/*
 * The bridge between a function that returns a whole string and an editor that
 * records what changed. Its whole job is that undoing a button press restores a
 * caret rather than a selection across the scene, so what is checked is the
 * span — not that applying it produces the right text, which is arithmetic the
 * cases above already cover.
 */
describe('the change a press really makes', () => {
  const applied = ({ from, to, insert }, before) =>
    before.slice(0, from) + insert + before.slice(to)

  it('reaches only the characters that differ', () => {
    expect(narrowedTo('Before. After.', 'Before. :npc[]After.')).toEqual({
      from: 8,
      to: 8,
      insert: ':npc[]',
    })
  })

  it('keeps a wrap to the word it wrapped', () => {
    const change = narrowedTo('The tide is turning.', 'The tide is **turning**.')

    expect(change.from).toBe(12)
    expect(change.to).toBe(19)
  })

  /* Deleting is not something a button does, but the same helper carries the
     model's writes from outside — a cancelled edit puts back a shorter body. */
  it('narrows a removal as well as an addition', () => {
    expect(narrowedTo('a **bold** word', 'a bold word')).toEqual({
      from: 2,
      to: 10,
      insert: 'bold',
    })
  })

  it('says nothing changed when nothing did', () => {
    const { from, to, insert } = narrowedTo('Unchanged.', 'Unchanged.')

    expect(from).toBe(to)
    expect(insert).toBe('')
  })

  /*
   * The property that matters, over every button and both shapes of press. A
   * narrower change that does not reproduce the string would be a field that
   * quietly wrote something other than what was tested above.
   */
  it('reproduces exactly what the insertion returned', () => {
    const before = 'A cold wind off the water.'

    for (const item of TOOLBAR_ITEMS) {
      for (const [start, end] of [
        [7, 7],
        [2, 6],
      ]) {
        const { value } = applyInsertion(item, before, start, end)

        expect(applied(narrowedTo(before, value), before), item.name).toBe(value)
      }
    }
  })
})
