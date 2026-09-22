import { describe, expect, it } from 'vitest'
import { decorationsFor, SYNTAX } from './livePreview.js'
import { parse } from './parse.js'

/*
 * What the field draws, checked as data.
 *
 * Every case here is a sentence about what a game master sees, and none of them
 * needs a DOM to ask it — which is the point of the split. `editor.js` turns
 * these descriptors into CodeMirror decorations and has no decisions of its own
 * left to make.
 */

const at = (offset) => [{ from: offset, to: offset }]

const decorations = (source, ranges = []) => decorationsFor(parse(source), source, ranges)

/*
 * The source with the concealed runs cut out of it.
 *
 * That is the claim being made — *this is the text on screen* — and a list of
 * offsets is not: a failure here reads as the sentence a writer would have been
 * looking at, rather than as two numbers to be counted out by hand.
 */
function shown(source, ranges = []) {
  const hidden = decorations(source, ranges).filter((descriptor) => descriptor.kind === 'hide')

  return [...source]
    .map((char, index) =>
      hidden.some((descriptor) => index >= descriptor.from && index < descriptor.to) ? '' : char,
    )
    .join('')
}

const marks = (source, ranges = []) =>
  decorations(source, ranges)
    .filter((descriptor) => descriptor.kind === 'mark' && descriptor.class !== SYNTAX)
    .map((descriptor) => [descriptor.class, source.slice(descriptor.from, descriptor.to)])

const lines = (source, ranges = []) =>
  decorations(source, ranges)
    .filter((descriptor) => descriptor.kind === 'line')
    .map((descriptor) => descriptor.class)

const widgets = (source, ranges = []) =>
  decorations(source, ranges)
    .filter((descriptor) => descriptor.kind === 'widget')
    .map((descriptor) => [descriptor.name, source.slice(descriptor.from, descriptor.to)])

describe('the marks a writer already knows', () => {
  it('draws bold and italic and takes their markers away', () => {
    expect(shown('A **cold** and *quiet* wind.')).toBe('A cold and quiet wind.')
    expect(marks('A **cold** and *quiet* wind.')).toEqual([
      ['md-strong', 'cold'],
      ['md-em', 'quiet'],
    ])
  })

  /*
   * The case that decides whether the markers are counted from the tree or from
   * the text. `***both***` is an emphasis wrapping a strong — one asterisk each
   * side and then two — and counting the run at the edge of the outer node
   * would have said three and eaten the inner one.
   */
  it('splits the markers of a nested pair correctly', () => {
    expect(shown('It is ***both***.')).toBe('It is both.')
    expect(marks('It is ***both***.')).toEqual([
      ['md-em', '**both**'],
      ['md-strong', 'both'],
    ])
  })

  it('reads the backtick fence rather than assuming one', () => {
    expect(shown('Type ``a ` b`` in.')).toBe('Type a ` b in.')
    expect(marks('Type `x` in.')).toEqual([['md-code', 'x']])
  })

  it('shows a link as its words', () => {
    expect(shown('See [the map](http://example.com/m).')).toBe('See the map.')
    expect(marks('See [the map](http://example.com/m).')).toEqual([['md-link', 'the map']])
  })

  it('takes the hashes off a heading and sizes the line', () => {
    expect(shown('### The Causeway')).toBe('The Causeway')
    expect(lines('### The Causeway')).toEqual(['md-h3'])
  })

  /* Seven hashes is not a heading in CommonMark, and the page stops at six. A
     field that sized a paragraph as an `h7` would be showing something the
     reader will never get. */
  it('stops where the parser and the page stop', () => {
    expect(lines('####### Deep')).toEqual([])
    expect(lines('###### Six')).toEqual(['md-h6'])
  })

  /* No prefix to take off, so nothing is taken off — and the line is still a
     heading. A construct the walker cannot help with must not be one it
     damages. */
  it('leaves the underline of a setext heading alone', () => {
    expect(shown('Title\n=====')).toBe('Title\n=====')
    expect(lines('Title\n=====')).toEqual(['md-h1'])
  })

  it('rules a quote down the side instead of writing its markers', () => {
    expect(shown('> First line.\n> Second line.')).toBe('First line.\nSecond line.')
    expect(lines('> First line.\n> Second line.')).toEqual(['md-quote', 'md-quote'])
  })

  it('draws a bullet and leaves a number', () => {
    expect(widgets('- one\n- two')).toEqual([
      ['bullet', '-'],
      ['bullet', '-'],
    ])
    expect(widgets('1. first\n2. second')).toEqual([])
  })

  /* The space after the marker is the author's text, and it is what keeps
     `• one` from becoming `•one`. */
  it('replaces the marker character and not the space after it', () => {
    expect(shown('- one')).toBe('- one')
    expect(lines('- one')).toEqual(['md-list'])
  })

  it('draws a thematic break rather than its dashes', () => {
    expect(widgets('a\n\n---\n\nb')).toEqual([['rule', '---']])
  })

  it('washes a fenced block and empties its fences', () => {
    const source = '```js\ncode here\n```'

    expect(shown(source)).toBe('\ncode here\n')
    expect(lines(source)).toEqual(['md-codeblock', 'md-codeblock', 'md-codeblock'])
  })

  /*
   * The block with something after it, which is the only shape it is ever
   * really in. The first version of this looked for the closing fence in a
   * slice that ran to the end of the *document* rather than the end of the
   * line, so every paragraph below the block landed inside the match and the
   * closing ``` stayed on screen — a bug no case ending at the fence could see.
   */
  it('empties the closing fence of a block that is not the last thing written', () => {
    expect(shown('```\nmap\n```\n\nAnd on.')).toBe('\nmap\n\n\nAnd on.')
  })

  /* An indented block has no fence to empty, and its indentation is the syntax
     — taking it away would leave a block that stops being one. */
  it('leaves an indented block its indentation', () => {
    const source = 'text\n\n    indented code'

    expect(shown(source)).toBe(source)
    expect(lines(source)).toEqual(['md-codeblock'])
  })
})

describe('the caret gives the characters back', () => {
  it('opens a construct the caret is inside', () => {
    expect(shown('A **cold** wind.', at(5))).toBe('A **cold** wind.')
  })

  /*
   * At the edge, not one past it. The source appears a keystroke before it is
   * needed rather than a keystroke after, which is the difference between an
   * editor that gets out of the way and one that has to be fought.
   */
  it('opens one the caret has only just reached', () => {
    expect(shown('A **cold** wind.', at(2))).toBe('A **cold** wind.')
    expect(shown('A **cold** wind.', at(10))).toBe('A **cold** wind.')
  })

  it('leaves the one next door closed', () => {
    expect(shown('A **cold** and *quiet* wind.', at(5))).toBe('A **cold** and quiet wind.')
  })

  it('opens every construct a selection covers', () => {
    expect(shown('A **cold** and *quiet* wind.', [{ from: 0, to: 27 }])).toBe(
      'A **cold** and *quiet* wind.',
    )
  })

  /*
   * A quote opens one line at a time. Opening all of a four-paragraph quote
   * because the caret is in the last of them would put markers back on screen
   * nowhere near where anyone is looking.
   */
  it('opens a quote by the line rather than by the block', () => {
    expect(shown('> First line.\n> Second line.', at(4))).toBe('> First line.\nSecond line.')
  })

  it('shows the dashes of a rule the caret is on', () => {
    expect(widgets('a\n\n---\n\nb', at(4))).toEqual([])
  })

  it('shows the marker of the list item the caret is in', () => {
    expect(widgets('- one\n- two', at(3))).toEqual([['bullet', '-']])
  })

  it('shows a fence the caret is on and keeps the other one closed', () => {
    expect(shown('```js\ncode here\n```', at(2))).toBe('```js\ncode here\n')
  })

  /* Marks are not markers. Bold stays bold while it is being edited, or the
     line would jump on every keystroke inside a word. */
  it('keeps drawing the words while their markers are showing', () => {
    expect(marks('A **cold** wind.', at(5))).toEqual([['md-strong', 'cold']])
  })

  /* A revealed marker is dimmed rather than left to read as two more characters
     of the sentence — which is why it carries a mark of its own and not only a
     concealment. */
  it('dims a marker it has given back', () => {
    const syntax = decorations('A **cold** wind.', at(5))
      .filter((descriptor) => descriptor.class === SYNTAX)
      .map((descriptor) => 'A **cold** wind.'.slice(descriptor.from, descriptor.to))

    expect(syntax).toEqual(['**', '**'])
  })
})

describe('what this issue does not touch', () => {
  /* #154's, all of it. The markers stay, and the body is still prose — a bold
     word inside a read-aloud box is bold for the same reason it is anywhere. */
  it('leaves a directive as it was typed and still draws inside it', () => {
    const source = ':::read-aloud\nThe **gate** sinks.\n:::'

    expect(shown(source)).toBe(':::read-aloud\nThe gate sinks.\n:::')
    expect(marks(source)).toEqual([['md-strong', 'gate']])
  })

  it('leaves an inline directive whole', () => {
    expect(shown('Meet :npc[Maerin Holt] there.')).toBe('Meet :npc[Maerin Holt] there.')
  })

  it('has nothing to say about an empty field', () => {
    expect(decorations('')).toEqual([])
  })
})
