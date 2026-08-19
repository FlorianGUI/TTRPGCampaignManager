import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CampaignMarkdown from './CampaignMarkdown.vue'
import { toPlainText } from './toPlainText.js'
import { ELISION } from './nodes.js'

/*
 * The three fallbacks, asserted across all three projections at once.
 *
 * Each projection has its own suite already, and that is exactly how they came
 * to disagree: a directive used in the wrong form was a visible typo on the
 * page and invisible in every list, title and search result, and nothing
 * failed. A table read by all three is the only shape of test that catches the
 * next divergence.
 *
 * `Ignored` is deliberately not uniform — the source on screen, an elision in a
 * table cell — so it is written down here as two expectations rather than left
 * to be discovered and "fixed".
 */

const textIn = (source, mode) => mount(CampaignMarkdown, { props: { source, mode } }).text()

/* [what, source, block/inline text, plain text] */
const cases = [
  [
    'Interpreted — a directive the dialect knows keeps its label everywhere',
    'Meets :npc[Fen Warden] outside.',
    'Fen Warden',
    'Meets Fen Warden outside.',
  ],
  [
    'Ignored — a name nobody knows',
    'Meets :npx[Fen Warden] outside.',
    ':npx[Fen Warden]',
    `Meets ${ELISION} outside.`,
  ],
  [
    'Ignored — a known name in a form it does not take',
    ':::npc[Fen]\nA warden.\n:::',
    ':::npc[Fen]',
    'A warden.',
  ],
  [
    'Ignored — attributes the dialect refuses',
    'Rolls :dice[1d20]{result=high} now.',
    ':dice[1d20]{result=high}',
    `Rolls ${ELISION} now.`,
  ],
  [
    'Ignored — a directive with no label at all',
    'A :npc with no name.',
    ':npc',
    `A ${ELISION} with no name.`,
  ],
  [
    'Skipped — an image with nothing to narrow to',
    'Look ![](https://example.com/map.png) here',
    ELISION,
    `Look ${ELISION} here`,
  ],
]

describe('the three fallbacks agree across the three projections', () => {
  for (const [what, source, onPage, asPlainText] of cases) {
    it(what, () => {
      expect(textIn(source, 'block'), 'block').toContain(onPage)
      expect(textIn(source, 'inline'), 'inline').toContain(onPage)
      expect(toPlainText(source), 'plain').toBe(asPlainText)
    })
  }

  /* The divergence, stated as a rule rather than as a row: what a page shows to
     make a typo findable is the one thing a table cell must never show. */
  it('never leaks directive syntax into plain text, whatever the page shows', () => {
    for (const [, source] of cases) {
      expect(toPlainText(source), source).not.toMatch(/[:{]/)
    }
  })

  it('keeps the author’s words on the page for every case it cannot draw', () => {
    for (const [, source] of cases) {
      expect(textIn(source, 'block'), source).not.toBe('')
    }
  })
})
