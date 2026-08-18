import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import { PrimeVueToastSymbol } from 'primevue/usetoast'
import GroupingPage from './GroupingPage.vue'

const request = vi.hoisted(() => vi.fn())

/* A fake in place of the real service — see the note in `MoveControl.test.js`. */
const toast = { add: vi.fn() }

vi.mock('../api/client.js', () => ({ request }))

const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

const ACT = {
  id: 'a-1',
  title: 'Act I — Water Rising',
  description: 'The Wardens’ trust.',
  position: 1024,
}
const CAUSEWAY = {
  id: 'q-1',
  title: 'The Causeway',
  description: '',
  act_id: 'a-1',
  position: 2048,
}

const TREE = {
  acts: [ACT],
  sequences: [CAUSEWAY],
  scenes: [
    scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1', status: 'done' }),
    // On the act, and *before* the sequence — so ordering the two kinds together
    // is the only way it lands in the right place.
    scene('s-2', 'Interlude', 1024, { act_id: 'a-1' }),
  ],
}

function routerFor() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/campaigns/:campaignId/structure',
        name: 'campaign-structure',
        component: { template: '<div />' },
      },
      {
        path: '/campaigns/:campaignId/acts/:actId',
        name: 'campaign-act',
        component: { template: '<div />' },
      },
      {
        path: '/campaigns/:campaignId/sequences/:sequenceId',
        name: 'campaign-sequence',
        component: { template: '<div />' },
      },
      {
        path: '/campaigns/:campaignId/scenes/:sceneId',
        name: 'campaign-scene',
        component: { template: '<div />' },
      },
    ],
  })
}

function answering({ tree = TREE, node = ACT } = {}) {
  request.mockImplementation((path) =>
    path.endsWith('/structure/') ? Promise.resolve(tree) : Promise.resolve(node),
  )
}

async function click(wrapper, label) {
  await wrapper
    .findAll('button')
    .find((b) => b.text().includes(label))
    .trigger('click')
  await flushPromises()
}

async function render({ kind = 'act', id = 'a-1', ...rest } = {}) {
  answering(rest)
  const wrapper = mount(GroupingPage, {
    props: { campaignId: 'c-1', kind, id },
    global: {
      plugins: [PrimeVue, createPinia(), routerFor()],
      provide: { [PrimeVueToastSymbol]: toast },
    },
  })
  await flushPromises()
  return wrapper
}

describe('an act’s page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('names it and renders what it says through the dialect', async () => {
    const wrapper = await render()

    expect(wrapper.get('h1').text()).toBe('Act I — Water Rising')
    expect(wrapper.text()).toContain('The Wardens’ trust.')
  })

  it('shows how far through it the table has got', async () => {
    // One of two scenes played — and the sequence's scene counts towards the act
    // it sits inside.
    const wrapper = await render()

    expect(wrapper.get('.progress__count').text()).toBe('1/2')
  })

  it('lists what it holds, sequences and scenes together in story order', async () => {
    /*
     * Separating the two kinds would put every scene written straight onto an
     * act after all of its sequences, whatever order the story goes in.
     */
    const wrapper = await render()
    const contents = wrapper.findAll('.contents__title').map((el) => el.text())

    expect(contents).toEqual(['Interlude', 'The Causeway'])
  })

  it('leads down into what it holds', async () => {
    const wrapper = await render()

    expect(wrapper.get('.contents__item').attributes('href')).toBe('/campaigns/c-1/scenes/s-2')
  })

  it('shows the way back, which starts at the structure', async () => {
    const wrapper = await render()

    expect(wrapper.findAll('.trail a').map((a) => a.text())).toEqual(['Structure'])
  })

  it('offers a sequence when it is empty, and says what one is', async () => {
    const wrapper = await render({
      tree: { acts: [ACT], sequences: [], scenes: [] },
    })

    expect(wrapper.get('.node__empty').text()).toContain('sequence')
  })

  describe('editing', () => {
    it('loads the form with what is there, because the write replaces everything', async () => {
      const wrapper = await render()

      await click(wrapper, 'Edit')

      expect(wrapper.get('textarea').element.value).toBe('The Wardens’ trust.')
    })

    it('sends both fields, so saving a title cannot clear a description', async () => {
      const wrapper = await render()
      await click(wrapper, 'Edit')

      request.mockClear()
      answering()
      await click(wrapper, 'Save')

      expect(request).toHaveBeenCalledWith('/campaigns/c-1/acts/a-1', {
        method: 'PUT',
        json: { title: 'Act I — Water Rising', description: 'The Wardens’ trust.' },
      })
    })

    it('asks the tree again, so the outline cannot keep an old title', async () => {
      const wrapper = await render()
      await click(wrapper, 'Edit')

      request.mockClear()
      answering()
      await click(wrapper, 'Save')

      expect(request).toHaveBeenCalledWith('/campaigns/c-1/structure/')
    })

    it('refuses a nameless act', async () => {
      const wrapper = await render()
      await click(wrapper, 'Edit')

      await wrapper.get('input').setValue('  ')
      await click(wrapper, 'Save')

      expect(wrapper.text()).toContain('Give it a title')
    })
  })
})

describe('a sequence’s page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('explains the word, which is jargon a game master will not arrive using', async () => {
    // #88 asks for this by name. The sequence's own page is where there is room
    // for a sentence rather than a label.
    const wrapper = await render({ kind: 'sequence', id: 'q-1', node: CAUSEWAY })

    expect(wrapper.get('.node__teach').text()).toContain('run of scenes')
  })

  it('shows the act above it in the trail', async () => {
    /*
     * Only the direct parent is stored, so the chain is walked from the tree —
     * a scene under a sequence does not record that sequence's act, because a
     * copy kept there could disagree after a move.
     */
    const wrapper = await render({ kind: 'sequence', id: 'q-1', node: CAUSEWAY })

    expect(wrapper.findAll('.trail a').map((a) => a.text())).toEqual([
      'Structure',
      'Act I — Water Rising',
    ])
  })

  it('carries no progress of its own', async () => {
    // Progress is an act's, because that is the scale a game master judges it at.
    const wrapper = await render({ kind: 'sequence', id: 'q-1', node: CAUSEWAY })

    expect(wrapper.find('.progress__count').exists()).toBe(false)
  })
})
