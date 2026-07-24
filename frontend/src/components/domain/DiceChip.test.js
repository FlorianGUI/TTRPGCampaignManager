import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DiceChip from './DiceChip.vue'

/*
 * Two behaviours worth pinning: a rolled chip must be distinguishable from an
 * unrolled one (a result of 0 is a real result, not an absent one), and an
 * outcome must always carry a word, never just a colour.
 */

describe('DiceChip', () => {
  it('shows notation only until a result exists', () => {
    const wrapper = mount(DiceChip, { props: { notation: '1d20' } })

    expect(wrapper.get('.dice__notation').text()).toBe('1d20')
    expect(wrapper.find('.dice__result').exists()).toBe(false)
  })

  it('treats a result of 0 as rolled, not as missing', () => {
    const wrapper = mount(DiceChip, { props: { notation: '1d4 - 4', result: 0 } })

    expect(wrapper.get('.dice__result').text()).toBe('0')
  })

  it('labels a crit in words as well as colour', () => {
    const wrapper = mount(DiceChip, { props: { notation: '2d8 + 5', result: 19, outcome: 'crit' } })

    expect(wrapper.get('.dice').classes()).toContain('dice--crit')
    expect(wrapper.get('.dice__outcome').text()).toBe('crit')
  })

  it('labels a fumble in words as well as colour', () => {
    const wrapper = mount(DiceChip, { props: { notation: '1d20', result: 1, outcome: 'fumble' } })

    expect(wrapper.get('.dice').classes()).toContain('dice--fumble')
    expect(wrapper.get('.dice__outcome').text()).toBe('fumble')
  })

  it('carries no outcome text for an ordinary roll', () => {
    const wrapper = mount(DiceChip, { props: { notation: '1d10 + 5', result: 7 } })

    expect(wrapper.find('.dice__outcome').exists()).toBe(false)
    expect(wrapper.get('.dice').classes()).not.toContain('dice--crit')
  })

  it('hides the decorative arrow from the accessibility tree', () => {
    const wrapper = mount(DiceChip, { props: { notation: '1d6', result: 2 } })

    expect(wrapper.get('.dice__arrow').attributes('aria-hidden')).toBe('true')
  })
})
