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

  it('leaks no syntax when it elides either — a marker, never the markup', () => {
    const plain = toPlainText(':npx[Fen]{label="the old man"} and :dice[1d20]{result=high}')

    expect(plain).toBe('[…] and […]')
    expect(plain).not.toMatch(/[:{]/)
  })

  it('keeps the words of a read-aloud block without its label', () => {
    expect(toPlainText(':::read-aloud\nThe water is cold.\n:::')).toBe('The water is cold.')
  })

  /* The three fallbacks, from this projection's side. `block` and `inline` quote
     an unrecognised directive back verbatim; a table cell cannot, so it elides.
     What it must not do is reduce to the label, which is what made a broken
     directive read exactly like a working one everywhere off the page. */
  it('elides a directive it does not know rather than passing off the label', () => {
    expect(toPlainText('The party meets :npx[Fen Warden] outside.')).toBe(
      'The party meets […] outside.',
    )
  })

  it('elides a known name used in the wrong form, as the page does', () => {
    // `:::npc` names a directive that exists and uses it as a block. The label
    // rides on the opening line, so it goes with the wrapper rather than
    // surviving as if it were a paragraph.
    expect(toPlainText(':::npc[Fen]\nA warden.\n:::')).toBe('A warden.')
  })

  it('elides a directive whose attributes are refused', () => {
    expect(toPlainText('Rolls :dice[1d20]{outcome=nat20} now.')).toBe('Rolls […] now.')
  })

  it('elides a directive with no label rather than naming it', () => {
    // `:spellbook` used to come out as the word "spellbook" — an English key
    // reaching a French list, and a half-typed directive reading as prose.
    expect(toPlainText(':spellbook')).toBe('[…]')
    expect(toPlainText('A :npc with no name.')).toBe('A […] with no name.')
  })

  /* A container is the exception, and it is the same rule one level down: its
     children are ordinary blocks that happened to be wrapped, so the wrapper is
     what nobody recognised and the prose inside it is still the author's. */
  it('keeps the body of a block directive it does not know', () => {
    expect(toPlainText(':::spellbook\nMagic missile.\n:::')).toBe('Magic missile.')
  })

  it('elides an image with no alt rather than showing its URL', () => {
    expect(toPlainText('Look ![](https://example.com/map.png) here')).toBe('Look […] here')
    expect(toPlainText('Look ![a map](https://example.com/map.png) here')).toBe('Look a map here')
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
