import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SourceRef from './SourceRef.vue'

/*
 * Citations are load-bearing for a source-book aggregator, so the page is
 * optional but must never render as an empty "p." when absent.
 */

describe('SourceRef', () => {
  it('renders the work on its own when there is no page', () => {
    const wrapper = mount(SourceRef, { props: { work: 'SRD 5.1' } })

    expect(wrapper.text()).toContain('SRD 5.1')
    expect(wrapper.find('.source-ref__page').exists()).toBe(false)
  })

  it('renders a page reference when given one', () => {
    const wrapper = mount(SourceRef, { props: { work: 'Cities of the Vale', page: 88 } })

    expect(wrapper.get('.source-ref__page').text()).toContain('88')
  })

  it('accepts a non-numeric page, since sources use roman numerals and inserts', () => {
    const wrapper = mount(SourceRef, { props: { work: 'Cities of the Vale', page: 'xiv' } })

    expect(wrapper.get('.source-ref__page').text()).toContain('xiv')
  })

  it('renders as a <cite>, so the citation is marked up as one', () => {
    const wrapper = mount(SourceRef, { props: { work: 'SRD 5.1' } })

    expect(wrapper.element.tagName).toBe('CITE')
  })
})
