import { describe, it, expect } from 'vitest'
import { toPlainText } from './toPlainText.js'

/*
 * The projection that stops list cells and page titles from showing raw
 * dialect. The rule it exists to enforce is narrow and absolute: no syntax
 * comes out, and no content goes missing.
 */

describe('toPlainText', () => {
  it('reduces a directive to its label', () => {
    expect(toPlainText('The party meets :npc[Fen Warden] outside.')).toBe(
      'The party meets Fen Warden outside.',
    )
  })

  it('leaks no directive syntax, whichever directive it is', () => {
    const plain = toPlainText(
      ':npc[Fen] pays :dice[2d6]{result=9} for :item[the Key] :ref[SRD]{page=12}',
    )

    expect(plain).toBe('Fen pays 2d6 for the Key SRD')
    expect(plain).not.toMatch(/[:{[]/)
  })

  it('keeps the words of a read-aloud block without its label', () => {
    expect(toPlainText(':::read-aloud\nThe water is cold.\n:::')).toBe('The water is cold.')
  })

  it('keeps the words of a directive it does not know', () => {
    expect(toPlainText('The party meets :npx[Fen Warden] outside.')).toBe(
      'The party meets Fen Warden outside.',
    )
  })

  it('names a directive that has no label, so nothing comes out empty', () => {
    expect(toPlainText(':spellbook')).toBe('spellbook')
  })

  it('strips ordinary markdown too', () => {
    expect(toPlainText('# Greyfen\n\nA causeway of **black timber**.')).toBe(
      'Greyfen A causeway of black timber.',
    )
  })

  it('joins blocks with a space and collapses the rest, so it fits on one line', () => {
    expect(toPlainText('One.\n\n\nTwo.\n\n- three\n- four')).toBe('One. Two. three four')
  })

  it('drops a link’s target and keeps its text', () => {
    expect(toPlainText('Read [the SRD](https://example.com/srd).')).toBe('Read the SRD.')
  })

  it('renders a script tag as the text it is', () => {
    expect(toPlainText('<script>alert(1)</script>')).toBe('<script>alert(1)</script>')
  })

  it('is empty for an empty body', () => {
    expect(toPlainText('')).toBe('')
    expect(toPlainText(undefined)).toBe('')
  })
})
