import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatBlock from './StatBlock.vue'

/*
 * The ability modifier is the only real logic in this component, and it is the
 * kind that is wrong in a way nobody notices: D&D floors *away* from zero for
 * negative scores, so 3 -> -4, not -3. Everything else here is markup.
 */

const creature = {
  name: 'Owlbear',
  meta: 'Large monstrosity, unaligned',
  lines: [{ label: 'Armor Class', value: '13 (natural armor)' }],
  abilities: { str: 20, dex: 12, con: 17, int: 3, wis: 12, cha: 7 },
  details: [{ label: 'Challenge', value: '3 (700 XP)' }],
  traits: [{ name: 'Keen Sight and Smell', text: 'Advantage on Perception checks.' }],
  actions: [{ name: 'Beak', text: 'Melee Weapon Attack.', dice: '1d10 + 5' }],
  source: { work: 'SRD 5.1', page: 344 },
}

function modifiersFrom(abilities) {
  const wrapper = mount(StatBlock, { props: { creature: { ...creature, abilities } } })
  return wrapper.findAll('.statblock__ability-mod').map((el) => el.text())
}

describe('StatBlock', () => {
  it('renders one ability column per ability, in SRD order', () => {
    const wrapper = mount(StatBlock, { props: { creature } })

    expect(wrapper.findAll('.statblock__ability-name').map((el) => el.text())).toEqual([
      'str',
      'dex',
      'con',
      'int',
      'wis',
      'cha',
    ])
  })

  it('signs positive modifiers explicitly', () => {
    expect(modifiersFrom({ str: 20, dex: 12, con: 17, int: 3, wis: 12, cha: 7 })).toEqual([
      '(+5)',
      '(+1)',
      '(+3)',
      '(-4)',
      '(+1)',
      '(-2)',
    ])
  })

  it('floors negative modifiers away from zero', () => {
    // 9 and 8 both give -1; 7 is the first score that reaches -2.
    expect(modifiersFrom({ str: 9, dex: 8, con: 7, int: 3, wis: 1, cha: 11 })).toEqual([
      '(-1)',
      '(-1)',
      '(-2)',
      '(-4)',
      '(-5)',
      '(+0)',
    ])
  })

  it('treats a score of 10 as no modifier rather than a blank', () => {
    expect(modifiersFrom({ str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 })).toEqual([
      '(+0)',
      '(+0)',
      '(+0)',
      '(+0)',
      '(+0)',
      '(+0)',
    ])
  })

  it('omits the actions heading when a creature has none', () => {
    const wrapper = mount(StatBlock, { props: { creature: { ...creature, actions: [] } } })

    expect(wrapper.find('.statblock__section-heading').exists()).toBe(false)
  })

  it('omits the source footer when a creature is unsourced', () => {
    const wrapper = mount(StatBlock, { props: { creature: { ...creature, source: null } } })

    expect(wrapper.find('.statblock__source').exists()).toBe(false)
  })
})
