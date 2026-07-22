import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HelloWorld from './HelloWorld.vue'

describe('HelloWorld', () => {
  it('renders the msg prop in a heading', () => {
    const wrapper = mount(HelloWorld, { props: { msg: 'Hello World' } })
    expect(wrapper.find('h1').text()).toBe('Hello World')
  })

  it('renders the running message', () => {
    const wrapper = mount(HelloWorld, { props: { msg: 'Hi' } })
    expect(wrapper.text()).toContain('up and running')
  })
})
