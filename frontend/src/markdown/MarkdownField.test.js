import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import PrimeVue from 'primevue/config'
import { EditorView } from '@codemirror/view'
import { undo } from '@codemirror/commands'
import MarkdownField from './MarkdownField.vue'
import {
  COLOR_ITEMS,
  COMMONMARK_ITEMS,
  ENTITY_ITEMS,
  MARKER_ITEMS,
  TOOLBAR_ITEMS,
} from './toolbar.js'
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

/*
 * The editor behind the field, found the way CodeMirror offers rather than
 * through a prop the component exposes for tests. Nothing in the app needs the
 * view handed to it, and adding an API so a test can reach one would be the
 * test deciding the component's shape.
 */
const editor = (wrapper) => EditorView.findFromDOM(wrapper.get('.md-field__area').element)

const sourceOf = (wrapper) => editor(wrapper).state.doc.toString()

const caretIn = (wrapper) => editor(wrapper).state.selection.main

const select = (wrapper, from, to) =>
  editor(wrapper).dispatch({ selection: { anchor: from, head: to } })

/*
 * Typing, as the editor sees it. A keypress on a contenteditable reaches
 * CodeMirror as a DOM mutation its observer turns into exactly this transaction,
 * and jsdom has no contenteditable to mutate — so the transaction is where the
 * test starts. What is being checked is what the field does with a change, not
 * whether a browser can produce one.
 */
const typeInto = async (wrapper, source) => {
  editor(wrapper).dispatch({
    changes: { from: 0, to: editor(wrapper).state.doc.length, insert: source },
  })

  await nextTick()
}

const nameOf = (item) => (item.label ? t(item.label) : item.name)

const buttonFor = (wrapper, name) => {
  const item = TOOLBAR_ITEMS.find((candidate) => candidate.name === name) ?? { name, label: null }
  const label = t('markdown.insert', { name: nameOf(item) })

  return wrapper
    .findAllComponents({ name: 'Button' })
    .find((button) => button.attributes('aria-label') === label)
}

/*
 * Press a directive wherever it lives. The entity kinds moved into a menu and
 * the rest stayed on the row, and every test below cares about what gets written
 * rather than which surface it was written from — so the seam is hidden here
 * instead of splitting each case in two.
 */
const swatchName = (item) => `${t(item.hueLabel)} ${t(item.tierLabel)}`

/*
 * Open the palette and hand back its swatches.
 *
 * Queried off the document rather than off the wrapper: a `Popover` teleports to
 * the body, so the grid is on the page but not inside the component's own tree.
 * Every caller unmounts, which is what takes the teleported node back out again
 * — a stale grid left behind would be found by the next test that looks.
 */
const openPalette = async (wrapper) => {
  const door = wrapper
    .findAllComponents({ name: 'Button' })
    .find((button) => button.attributes('aria-label') === t('markdown.directive.color'))

  await door.trigger('click')
  await nextTick()

  return [...document.querySelectorAll('.md-palette__swatch')]
}

const press = async (wrapper, name) => {
  const button = buttonFor(wrapper, name)

  if (button) {
    await button.trigger('click')
    return
  }

  const item = TOOLBAR_ITEMS.find((candidate) => candidate.name === name)
  const entry = wrapper
    .findComponent({ name: 'Menu' })
    .props('model')
    .find((candidate) => candidate.label === nameOf(item))

  if (!entry) throw new Error(`no control for ${name}`)

  entry.command()
  await nextTick()
}

describe('MarkdownField says what it takes', () => {
  /* #103's first acceptance: the form says the field takes the dialect, without
     having to be hovered to find out. */
  it('names the dialect on screen', () => {
    expect(mountField().text()).toContain(t('markdown.hint'))
  })

  /* The writing surface is a contenteditable now, so the label the view passes
     has to arrive on it as an attribute rather than on an element that carries
     one natively. Without this the field is announced as nothing at all. */
  it('carries the aria-label the view gave it through to the writing surface', () => {
    const content = mountField().get('.cm-content')

    expect(content.attributes('aria-label')).toBe('Body')
    expect(content.attributes('role')).toBe('textbox')
    expect(content.attributes('aria-multiline')).toBe('true')
  })

  it('reaches every directive the renderer implements', async () => {
    const wrapper = mountField()
    const onRow = wrapper
      .findAllComponents({ name: 'Button' })
      .map((button) => button.attributes('aria-label'))
    const inMenu = wrapper
      .findComponent({ name: 'Menu' })
      .props('model')
      .map((entry) => entry.label)
    const inPalette = await openPalette(wrapper)

    for (const item of TOOLBAR_ITEMS) {
      /* `:color` is one directive with twenty-one faces, and is reached by
         picking a hue rather than by pressing the name — a `:color[…]` with no
         hue is refused, so a button that wrote one would be a button that
         writes text. */
      const reachable =
        item.name === 'color'
          ? inPalette.length === COLOR_ITEMS.length
          : onRow.includes(t('markdown.insert', { name: nameOf(item) })) ||
            inMenu.includes(nameOf(item))

      expect(reachable, item.name).toBe(true)
    }

    wrapper.unmount()
  })

  /*
   * The row has no space for twenty-one more controls — #146 had just cut it
   * down to one tier of icons — and a palette is a grid rather than a list,
   * which is why this is a `Popover` where the entity kinds are a `Menu`.
   */
  it('puts every hue and tier behind one door', async () => {
    const wrapper = mountField()
    const swatches = await openPalette(wrapper)

    expect(swatches).toHaveLength(COLOR_ITEMS.length)

    wrapper.unmount()
  })

  /*
   * Both halves of the name, both from the catalogue (#87).
   *
   * A grid of twenty-one unlabelled colour squares is unusable without sight.
   * Labelling them by hue alone is unusable *with* it as well — three of the
   * twenty-one are wyrd, and only the tier tells them apart.
   */
  it('names every swatch by its hue and its tier', async () => {
    const wrapper = mountField()
    const labels = (await openPalette(wrapper)).map((swatch) => swatch.getAttribute('aria-label'))

    for (const item of COLOR_ITEMS) {
      expect(labels, item.name).toContain(t('markdown.insert', { name: swatchName(item) }))
      expect(swatchName(item)).not.toMatch(/^prose\./)
    }

    wrapper.unmount()
  })

  /* The swatch and the span it writes read the same twenty-one rules, so a
     picker cannot show one colour and insert another. */
  it('paints each swatch with the class the rendered span carries', async () => {
    const wrapper = mountField()
    const swatches = await openPalette(wrapper)

    for (const [index, item] of COLOR_ITEMS.entries()) {
      expect([...swatches[index].classList], item.name).toContain(item.class)
    }

    wrapper.unmount()
  })

  /*
   * The six kinds are one idea with six accents, and the length of that run was
   * what made the row a wall. The three that are not a set stay out, because
   * each is its own idea and none is guessable — which is what #103 is about.
   */
  it('puts the entity kinds behind one door and leaves the rest out', () => {
    const wrapper = mountField()

    expect(wrapper.findComponent({ name: 'Menu' }).props('model')).toHaveLength(ENTITY_ITEMS.length)

    const onRow = wrapper
      .findAllComponents({ name: 'Button' })
      .map((button) => button.attributes('aria-label'))

    for (const item of MARKER_ITEMS) {
      expect(onRow, item.name).toContain(t('markdown.insert', { name: nameOf(item) }))
    }
  })

  /* Read-aloud first — it is the one that changes the page rather than a word
     in it — then the two inline marks. */
  it('orders the visible directives read-aloud, dice, source', () => {
    expect(MARKER_ITEMS.map((item) => item.name)).toEqual(['read-aloud', 'dice', 'ref'])
  })

  it('lays the plain marks out before the dialect own', () => {
    const names = mountField()
      .findAll('button')
      .map((button) => button.attributes('aria-label'))

    expect(names[0]).toBe(t('markdown.insert', { name: t('markdown.commonmark.bold') }))
    expect(names.at(-1)).toBe(t('markdown.entity'))
  })

  /*
   * Every button is an icon now, so the name has to be somewhere else entirely.
   * `aria-label` covers the screen reader; the tooltip covers the mouse; and it
   * is set to open on focus too, because a tooltip that only answers to hover is
   * one the keyboard never sees.
   */
  it('names every icon-only button without showing the word', () => {
    const buttons = mountField().findAllComponents({ name: 'Button' })

    for (const button of buttons.slice(0, -1)) {
      expect(button.attributes('aria-label')).toBeTruthy()
      expect(button.text()).not.toMatch(/\w{3,}/)
    }
  })

  /*
   * Ten identical icons in an unbroken line was the shape that made the row
   * unreadable, so the runs are ruled off from each other. Between only — the
   * gap that pushes the dialect's own controls to the far end already separates
   * them, and a rule there as well left a hairline stranded in open space.
   */
  it('rules the plain marks off into runs', () => {
    const wrapper = mountField()
    const runs = new Set(COMMONMARK_ITEMS.map((item) => item.group))

    expect(wrapper.findAll('.md-field__rule')).toHaveLength(runs.size - 1)
  })

  it('draws a letterform for the marks PrimeIcons has no glyph for', () => {
    const wrapper = mountField()

    for (const item of COMMONMARK_ITEMS.filter((candidate) => candidate.glyph)) {
      expect(wrapper.find(`.md-field__glyph--${item.name}`).text(), item.name).toBe(item.glyph)
    }
  })

  it('gives every plain mark either an icon or a glyph', () => {
    for (const item of COMMONMARK_ITEMS) {
      expect(Boolean(item.icon) !== Boolean(item.glyph), item.name).toBe(true)
    }
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

    // The plain marks, the dialect's own, and the two doors — colour and
    // entity — which each hand their own keyboard over once open.
    expect(buttons.length).toBe(COMMONMARK_ITEMS.length + MARKER_ITEMS.length + 2)
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

    await press(wrapper, 'npc')

    expect(wrapper.vm.body).toBe(':npc[]')
  })

  it('wraps what the game master had selected', async () => {
    const wrapper = mountField('Maerin Holt')

    select(wrapper, 0, 11)
    await press(wrapper, 'npc')

    expect(wrapper.vm.body).toBe(':npc[Maerin Holt]')
  })

  /*
   * The caret is the reason the button is worth pressing. Leaving it where the
   * mouse was would mean clicking back into the field and hunting for the
   * brackets, which is the work the button was pressed to avoid.
   */
  it('hands the field back with the caret where the label goes', async () => {
    const wrapper = mountField()

    await press(wrapper, 'npc')

    expect(document.activeElement).toBe(wrapper.get('.cm-content').element)
    expect(caretIn(wrapper).from).toBe(':npc['.length)
    expect(caretIn(wrapper).to).toBe(':npc['.length)
  })

  it('leaves the caret in the attribute when the label is already written', async () => {
    const wrapper = mountField('2d8 + 5')

    select(wrapper, 0, 7)
    await press(wrapper, 'dice')

    expect(wrapper.vm.body).toBe(':dice[2d8 + 5]{result=}')
    expect(caretIn(wrapper).from).toBe(':dice[2d8 + 5]{result='.length)
  })

  it('opens a read-aloud box around the selection', async () => {
    const wrapper = mountField('A cold wind off the water.')

    select(wrapper, 0, 26)
    await press(wrapper, 'read-aloud')

    expect(wrapper.vm.body).toBe(':::read-aloud\nA cold wind off the water.\n:::')
  })

  it('inserts at the caret rather than at the end of the field', async () => {
    const wrapper = mountField('Before. After.')

    select(wrapper, 8, 8)
    await press(wrapper, 'npc')

    expect(wrapper.vm.body).toBe('Before. :npc[]After.')
  })

  /* The menu is the only way to reach a kind now, so the command it runs has to
     do the same work a button did. */
  it('writes through the menu the same way it writes through a button', async () => {
    const wrapper = mountField('Maerin Holt')

    select(wrapper, 0, 11)

    const npc = wrapper
      .findComponent({ name: 'Menu' })
      .props('model')
      .find((entry) => entry.label === t('entity.npc'))

    npc.command()
    await nextTick()

    expect(wrapper.vm.body).toBe(':npc[Maerin Holt]')
  })

  it('offers every kind in the menu, with its own face', () => {
    const model = mountField().findComponent({ name: 'Menu' }).props('model')

    for (const item of ENTITY_ITEMS) {
      const entry = model.find((candidate) => candidate.label === nameOf(item))

      expect(entry, item.name).toBeDefined()
      expect(entry.icon).toContain(item.icon)
    }
  })

  it('leaves every kind able to write itself', async () => {
    for (const kind of Object.keys(ENTITY_KINDS)) {
      const wrapper = mountField()

      await press(wrapper, kind)

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

    await typeInto(wrapper, source)

    expect(wrapper.vm.body).toBe(source)
    expect(sourceOf(wrapper)).toBe(source)
  })

  it('shows the source it was given', () => {
    expect(sourceOf(mountField('Already written.'))).toBe('Already written.')
  })

  /* The parent's half of `v-model`. A body arriving from anywhere but the
     keyboard — a cancelled edit, a scene loaded after the form opened — has to
     reach the field, and the guard that stops the round trip fighting itself is
     the easiest thing here to write backwards. */
  it('takes a value written from outside', async () => {
    const wrapper = mountField('First.')

    wrapper.vm.body = 'Second.'
    await nextTick()

    expect(sourceOf(wrapper)).toBe('Second.')
  })

  /* Undo is the browser's on a textarea and nobody's on a contenteditable, so
     it is a thing this field can quietly stop having. A toolbar press is one
     step, not the two a separate insert and caret move would leave. */
  it('undoes a toolbar press in one step', async () => {
    const wrapper = mountField('Maerin Holt')

    select(wrapper, 0, 11)
    await press(wrapper, 'npc')
    expect(sourceOf(wrapper)).toBe(':npc[Maerin Holt]')

    undo(editor(wrapper))
    await nextTick()

    expect(sourceOf(wrapper)).toBe('Maerin Holt')
    expect(wrapper.vm.body).toBe('Maerin Holt')
  })
})
