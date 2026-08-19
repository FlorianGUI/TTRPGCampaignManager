import { describe, expect, it, vi } from 'vitest'
import { TOOLBAR_ITEMS, applyInsertion } from './toolbar.js'
import { DIRECTIVES } from './directives.js'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
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

     Mocked rather than mutated: `DIRECTIVES` is built when `directives.js` is
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

  it('gives every button an icon, so none arrives blank', () => {
    for (const item of TOOLBAR_ITEMS) expect(item.icon).toBeTruthy()
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
