import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MarkdownField from './MarkdownField.vue'
import MarkdownToolbar from './MarkdownToolbar.vue'
import { TOOLBAR_ITEMS } from './toolbar.js'
import { DIRECTIVES } from './directives.js'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import { t } from '../i18n/index.js'

/*
 * What this file protects is the promise the field makes: that the vocabulary is
 * on screen, that pressing a button leaves the game master typing where the
 * words go, and that nothing between the keyboard and the model rewrites what
 * was written.
 *
 * The insertion arithmetic itself is `toolbar.test.js`'s — it has rules in it
 * and needs no DOM to check them.
 *
 * **Mounted inside a holder that owns the model, and attached to the document.**
 * Both are needed to test the thing worth testing. A field mounted bare never
 * sees its own text come back, because `v-model` is the parent's half of the
 * contract and there is no parent — and the caret would then be set against a
 * textarea still holding the old string. Detached, `focus()` is a no-op and
 * `document.activeElement` stays on the body. Neither is true on the page.
 */
const Holder = {
  components: { MarkdownField },
  props: { start: { type: String, default: '' }, rows: { type: Number, default: 12 } },
  data() {
    return { body: this.start }
  },
  template: `<MarkdownField v-model="body" :rows="rows" aria-label="Body" />`,
}

const mountField = (start = '') =>
  mount(Holder, { props: { start }, attachTo: document.body, global: { plugins: [PrimeVue] } })

const nameOf = (item) => (item.label ? t(item.label) : item.name)

const buttonFor = (wrapper, name) => {
  const item = TOOLBAR_ITEMS.find((candidate) => candidate.name === name)
  const label = t('markdown.insert', { name: nameOf(item) })

  return wrapper
    .findAllComponents({ name: 'Button' })
    .find((button) => button.attributes('aria-label') === label)
}

describe('MarkdownField says what it takes', () => {
  /* #103's first acceptance: the form says the field takes the dialect, without
     having to be hovered to find out. */
  it('names the dialect on screen', () => {
    expect(mountField().text()).toContain(t('markdown.hint'))
  })

  it('carries the aria-label the view gave it through to the textarea', () => {
    expect(mountField().get('textarea').attributes('aria-label')).toBe('Body')
  })

  it('shows a button for every directive the renderer implements', () => {
    const toolbar = mountField().getComponent(MarkdownToolbar)

    expect(toolbar.findAllComponents({ name: 'Button' })).toHaveLength(
      Object.keys(DIRECTIVES).length,
    )
  })

  it('gives every button a name a screen reader can read', () => {
    for (const button of mountField().findAllComponents({ name: 'Button' })) {
      expect(button.attributes('aria-label')).toBeTruthy()
    }
  })

  it('groups the buttons, so they are announced as one control and not nine', () => {
    const toolbar = mountField().get('[role="toolbar"]')

    expect(toolbar.attributes('aria-label')).toBe(t('markdown.toolbar'))
  })

  /*
   * The toolbar stands between the game master and the field. Nine tab stops to
   * get past it would make the control that exists to help with writing the
   * obstacle to it, so the group is one stop and the arrows move inside it.
   */
  it('takes one tab stop rather than one per button', () => {
    const buttons = mountField().findAll('button')
    const reachable = buttons.filter((button) => button.attributes('tabindex') === '0')

    expect(buttons.length).toBe(Object.keys(DIRECTIVES).length)
    expect(reachable).toHaveLength(1)
  })

  it('walks the buttons with the arrow keys', async () => {
    const wrapper = mountField()
    const toolbar = wrapper.get('[role="toolbar"]')
    const buttons = wrapper.findAll('button')

    await toolbar.trigger('keydown', { key: 'ArrowRight' })

    expect(document.activeElement).toBe(buttons[1].element)
    expect(buttons[1].attributes('tabindex')).toBe('0')
    expect(buttons[0].attributes('tabindex')).toBe('-1')
  })

  it('wraps around rather than stopping at the ends', async () => {
    const wrapper = mountField()
    const toolbar = wrapper.get('[role="toolbar"]')
    const buttons = wrapper.findAll('button')

    await toolbar.trigger('keydown', { key: 'ArrowLeft' })

    expect(document.activeElement).toBe(buttons.at(-1).element)
  })

  it('jumps to either end with Home and End', async () => {
    const wrapper = mountField()
    const toolbar = wrapper.get('[role="toolbar"]')
    const buttons = wrapper.findAll('button')

    await toolbar.trigger('keydown', { key: 'End' })
    expect(document.activeElement).toBe(buttons.at(-1).element)

    await toolbar.trigger('keydown', { key: 'Home' })
    expect(document.activeElement).toBe(buttons[0].element)
  })

  /* Typing in the field must not be intercepted — the handler sits on the
     toolbar, but a key it does not claim has to keep travelling. */
  it('leaves keys it does not use alone', async () => {
    const wrapper = mountField()

    await wrapper.get('[role="toolbar"]').trigger('keydown', { key: 'a' })

    expect(wrapper.findAll('button')[0].attributes('tabindex')).toBe('0')
  })

  /* Not `type="submit"`, which is what a bare button inside a form defaults to.
     A toolbar that saved the scene would be a memorable bug. */
  it('does not submit anything', () => {
    for (const button of mountField().findAll('button')) {
      expect(button.attributes('type')).toBe('button')
    }
  })
})

describe('pressing a button', () => {
  it('writes the directive into the model', async () => {
    const wrapper = mountField()

    await buttonFor(wrapper, 'npc').trigger('click')

    expect(wrapper.vm.body).toBe(':npc[]')
  })

  it('wraps what the game master had selected', async () => {
    const wrapper = mountField('Maerin Holt')

    wrapper.get('textarea').element.setSelectionRange(0, 11)
    await buttonFor(wrapper, 'npc').trigger('click')

    expect(wrapper.vm.body).toBe(':npc[Maerin Holt]')
  })

  /*
   * The caret is the reason the button is worth pressing. Leaving it where the
   * mouse was would mean clicking back into the field and hunting for the
   * brackets, which is the work the button was pressed to avoid.
   */
  it('hands the field back with the caret where the label goes', async () => {
    const wrapper = mountField()
    const textarea = wrapper.get('textarea').element

    await buttonFor(wrapper, 'npc').trigger('click')

    expect(document.activeElement).toBe(textarea)
    expect(textarea.selectionStart).toBe(':npc['.length)
    expect(textarea.selectionEnd).toBe(':npc['.length)
  })

  it('leaves the caret in the attribute when the label is already written', async () => {
    const wrapper = mountField('2d8 + 5')
    const textarea = wrapper.get('textarea').element

    textarea.setSelectionRange(0, 7)
    await buttonFor(wrapper, 'dice').trigger('click')

    expect(wrapper.vm.body).toBe(':dice[2d8 + 5]{result=}')
    expect(textarea.selectionStart).toBe(':dice[2d8 + 5]{result='.length)
  })

  it('opens a read-aloud box around the selection', async () => {
    const wrapper = mountField('A cold wind off the water.')

    wrapper.get('textarea').element.setSelectionRange(0, 26)
    await buttonFor(wrapper, 'read-aloud').trigger('click')

    expect(wrapper.vm.body).toBe(':::read-aloud\nA cold wind off the water.\n:::')
  })

  it('inserts at the caret rather than at the end of the field', async () => {
    const wrapper = mountField('Before. After.')

    wrapper.get('textarea').element.setSelectionRange(8, 8)
    await buttonFor(wrapper, 'npc').trigger('click')

    expect(wrapper.vm.body).toBe('Before. :npc[]After.')
  })

  it('leaves every kind able to write itself', async () => {
    for (const kind of Object.keys(ENTITY_KINDS)) {
      const wrapper = mountField()

      await buttonFor(wrapper, kind).trigger('click')

      expect(wrapper.vm.body).toBe(`:${kind}[]`)
    }
  })
})

describe('MarkdownField stores what was typed', () => {
  /* #80 is emphatic that the body stays a string. Typing must reach the model
     unchanged — no trimming, no normalising, no reformatting of the markdown. */
  it('passes typing through untouched', async () => {
    const wrapper = mountField()
    const source = '  :::read-aloud\n\n  ragged   spacing  \n:::  \n\n'

    await wrapper.get('textarea').setValue(source)

    expect(wrapper.vm.body).toBe(source)
  })

  it('shows the source it was given', () => {
    expect(mountField('Already written.').get('textarea').element.value).toBe('Already written.')
  })
})
