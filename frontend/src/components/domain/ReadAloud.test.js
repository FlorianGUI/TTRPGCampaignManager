import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReadAloud from './ReadAloud.vue'

/*
 * The label is what tells a GM this block is meant to be spoken at the table,
 * so it must always be present — and overridable, since not every system calls
 * it "Read aloud".
 */

describe('ReadAloud', () => {
  it('labels the block by default', () => {
    const wrapper = mount(ReadAloud, { slots: { default: '<p>Boxed text.</p>' } })

    expect(wrapper.get('.read-aloud__label').text()).toBe('Read aloud')
  })

  it('accepts a system-specific label', () => {
    const wrapper = mount(ReadAloud, {
      props: { label: 'Boxed text' },
      slots: { default: '<p>Boxed text.</p>' },
    })

    expect(wrapper.get('.read-aloud__label').text()).toBe('Boxed text')
  })

  it('renders the passage it was given', () => {
    const wrapper = mount(ReadAloud, { slots: { default: '<p>The causeway ends at an arch.</p>' } })

    expect(wrapper.get('.read-aloud__body').text()).toBe('The causeway ends at an arch.')
  })

  it('renders as an <aside>, since it sits beside the narrative rather than in it', () => {
    const wrapper = mount(ReadAloud, { slots: { default: '<p>x</p>' } })

    expect(wrapper.element.tagName).toBe('ASIDE')
  })
})
