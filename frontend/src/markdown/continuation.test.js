import { describe, expect, it } from 'vitest'
import { continuationFor } from './continuation.js'

/*
 * What Enter writes, checked as text.
 *
 * `‸` is the caret, put in the string rather than passed as a column, because
 * every case here is a sentence about a line a game master is looking at and a
 * number would have to be counted out by hand to read it.
 */
const enter = (line) => {
  const column = line.indexOf('‸')
  const answer = continuationFor(line.replace('‸', ''), column)

  if (!answer) return null

  return answer.insert === '' ? '' : answer.insert
}

describe('Enter carries the marker on', () => {
  it('continues a bullet', () => {
    expect(enter('- a rope, forty feet‸')).toBe('\n- ')
    expect(enter('* a rope‸')).toBe('\n* ')
    expect(enter('+ a rope‸')).toBe('\n+ ')
  })

  /* The number a reader would expect next, which is the whole reason not to
     leave this to the writer: a list typed by hand goes 1. 2. 3. 3. 4. */
  it('counts a numbered list on', () => {
    expect(enter('3. the gate opens‸')).toBe('\n4. ')
    expect(enter('9. the ninth thing‸')).toBe('\n10. ')
    expect(enter('1) a paren list‸')).toBe('\n2) ')
  })

  it('continues a quote', () => {
    expect(enter('> The Wardens do not answer letters.‸')).toBe('\n> ')
  })

  /* Falls out of reading indentation, then quote markers, then a list marker,
     in that order — rather than being a case anybody had to write down. */
  it('continues a list inside a quote', () => {
    expect(enter('> - a rope‸')).toBe('\n> - ')
  })

  it('carries the indentation, so a nested item stays nested', () => {
    expect(enter('  - nested‸')).toBe('\n  - ')
    expect(enter('    1. deep‸')).toBe('\n    2. ')
  })

  /* The marker's own spacing, not a guess at it: someone who lines their list
     up with two spaces keeps them. */
  it('keeps the spacing the marker was written with', () => {
    expect(enter('-  wide‸')).toBe('\n-  ')
  })

  it('continues from the middle of the line as well as the end', () => {
    expect(enter('- a rope,‸ forty feet')).toBe('\n- ')
  })
})

describe('Enter takes the marker away when there is nothing on the line', () => {
  /* Otherwise a list is something a writer cannot leave except by deleting
     characters one at a time. */
  it('clears an empty bullet', () => {
    expect(enter('- ‸')).toBe('')
  })

  it('clears an empty number and an empty quote', () => {
    expect(enter('4. ‸')).toBe('')
    expect(enter('> ‸')).toBe('')
  })

  it('clears the indentation with it', () => {
    const answer = continuationFor('  - ', 4)

    expect(answer).toEqual({ from: 0, to: 4, insert: '' })
  })

  /* Whitespace after the marker is not content. A line of `- ` with a stray
     space is still an empty item to everyone looking at it. */
  it('treats a line of nothing but spaces as empty', () => {
    expect(enter('-   ‸')).toBe('')
  })
})

describe('Enter is left alone everywhere else', () => {
  it('has nothing to say about a paragraph', () => {
    expect(enter('A cold wind off the water.‸')).toBe(null)
    expect(enter('‸')).toBe(null)
  })

  /* An indent on its own is not a marker. Carrying it would make Enter at the
     end of any indented line behave like a list — including inside a code
     block, where it would be actively wrong. */
  it('does not treat indentation as a marker', () => {
    expect(enter('    indented code‸')).toBe(null)
  })

  /* The caret is in the marker rather than past it, so the writer is editing
     the marker and not the item. */
  it('stands aside when the caret is inside the marker', () => {
    expect(enter('-‸ a rope')).toBe(null)
    expect(enter('‸- a rope')).toBe(null)
    expect(enter('3.‸ the gate')).toBe(null)
  })

  /* `2026.` at the start of a sentence is a year, and `-5` is a number. Both
     need the space the syntax requires before they are a list. */
  it('needs the space a marker is written with', () => {
    expect(enter('-5 degrees‸')).toBe(null)
    expect(enter('1.5 miles out‸')).toBe(null)
  })
})
