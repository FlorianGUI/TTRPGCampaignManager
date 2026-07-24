import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EntityTag from './EntityTag.vue'
import { ENTITY_KINDS } from './entityKinds.js'

/*
 * The contract worth protecting here is the accessibility one: a kind is never
 * communicated by colour alone. Every kind must carry an icon *and* a
 * spoken-out label, and the accent must resolve to a real theme token.
 */

describe('entityKinds', () => {
  it('gives every kind both an icon and a spoken label', () => {
    for (const [kind, meta] of Object.entries(ENTITY_KINDS)) {
      expect(meta.icon, `${kind} icon`).toMatch(/^pi-/)
      expect(meta.label, `${kind} label`).toBeTruthy()
    }
  })
})

describe('EntityTag', () => {
  it('renders the label the caller passed, not the kind', () => {
    const wrapper = mount(EntityTag, { props: { kind: 'npc', label: 'Maerin Holt' } })

    expect(wrapper.get('.entity__label').text()).toBe('Maerin Holt')
  })

  it('exposes the kind to screen readers, since colour alone must not carry it', () => {
    const wrapper = mount(EntityTag, { props: { kind: 'monster', label: 'Owlbear' } })

    expect(wrapper.get('.visually-hidden').text()).toBe('(Monster)')
  })

  it('hides the decorative icon from the accessibility tree', () => {
    const wrapper = mount(EntityTag, { props: { kind: 'npc', label: 'Maerin Holt' } })
    const icon = wrapper.get('.entity__icon')

    expect(icon.attributes('aria-hidden')).toBe('true')
    expect(icon.classes()).toContain(ENTITY_KINDS.npc.icon)
  })

  it('resolves its accent to the theme token for that kind', () => {
    const wrapper = mount(EntityTag, { props: { kind: 'faction', label: 'The Fen Wardens' } })

    expect(wrapper.get('.entity').attributes('style')).toContain(
      '--entity-accent: var(--p-grimoire-entity-faction)',
    )
  })

  it('rejects a kind that has no token, rather than rendering an unstyled chip', () => {
    const { validator } = EntityTag.props.kind

    expect(validator('npc')).toBe(true)
    expect(validator('spaceship')).toBe(false)
  })
})
