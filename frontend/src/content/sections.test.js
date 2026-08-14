import { describe, it, expect } from 'vitest'
import { sections } from './sample.js'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import { light, dark } from '../design-system/tokens/semantic.js'

/*
 * The two sections beneath the campaign's own outline.
 *
 * Most of what is here is a label and will be replaced the moment either
 * section has real data behind it. What is worth holding is the part that would
 * rot quietly: the icons are `ENTITY_KINDS`, so the way into every location and
 * the chip a `:location[…]` renders as in a scene cannot start disagreeing.
 */

describe('the sidebar sections', () => {
  it('are Resources and Organization', () => {
    expect(sections.map((section) => section.label)).toEqual(['Resources', 'Organization'])
  })

  it('hold what a campaign is made of, and what running it takes', () => {
    expect(sections.map((section) => section.items.map((item) => item.label))).toEqual([
      ['PCs', 'NPCs', 'Locations', 'Factions'],
      ['Sessions', 'Agenda'],
    ])
  })

  const iconFor = (label) =>
    sections.flatMap((section) => section.items).find((item) => item.label === label).icon

  it('mark a kind the way the rest of the app marks it', () => {
    expect(iconFor('NPCs')).toBe(ENTITY_KINDS.npc.icon)
    expect(iconFor('Locations')).toBe(ENTITY_KINDS.location.icon)
    expect(iconFor('Factions')).toBe(ENTITY_KINDS.faction.icon)
  })

  it('give the calendar to the agenda rather than to the sessions', () => {
    /*
     * The exception, and deliberate: the agenda is the thing with dates in it,
     * and sessions are what has already been played. `:session[…]` keeps the
     * calendar in prose, where it names one evening rather than the record of
     * all of them — so this asserts they now differ, which is the part a later
     * tidy-up would otherwise "fix" back.
     */
    expect(iconFor('Agenda')).toBe('pi-calendar')
    expect(iconFor('Sessions')).toBe('pi-list')
    expect(iconFor('Sessions')).not.toBe(ENTITY_KINDS.session.icon)
  })

  it('count nothing, because nothing here has been counted', () => {
    // The old numbers were invented, and a number nobody counted reads as data.
    for (const item of sections.flatMap((section) => section.items)) {
      expect(item.count).toBeUndefined()
    }
  })

  it('name an accent the design system actually defines, in both schemes', () => {
    /*
     * `AppNav` builds `--p-grimoire-context-<context>` from this. A name that no
     * token answers to is an error nowhere: it is a CSS variable resolving to
     * nothing and a section quietly losing its accent, in one scheme or in both.
     * So this asks the tokens rather than restating the strings.
     */
    for (const scheme of [light, dark]) {
      for (const section of sections) {
        expect(scheme.extend.grimoire.context).toHaveProperty(section.context)
      }
    }
  })
})
