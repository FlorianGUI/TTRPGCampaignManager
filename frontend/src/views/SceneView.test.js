import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import SceneView from './SceneView.vue'

const request = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))

const BODY = ':::read-aloud\nThe gate does not swing. It sinks —\n:::'

/* PrimeVue's Select reads matchMedia on mount; jsdom has none. Not a fact about
   this page, only about the environment. */
window.matchMedia ??= () => ({
  matches: false,
  addEventListener() {},
  removeEventListener() {},
})

const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

const TREE = {
  acts: [{ id: 'a-1', title: 'Act I', description: '', position: 1024 }],
  sequences: [{ id: 'q-1', title: 'The Causeway', description: '', act_id: 'a-1', position: 1024 }],
  scenes: [
    scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1' }),
    scene('s-2', 'The sunken arch', 2048, { sequence_id: 'q-1' }),
    // On the act, after the sequence — so the story leaves the sequence and
    // carries on without leaving the act.
    scene('s-3', 'Interlude', 2048, { act_id: 'a-1' }),
  ],
}

const FULL = { ...scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1' }), body: BODY }

function routerFor() {
  const router = createRouter({
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
        component: SceneView,
      },
    ],
  })
  return router
}

/* The tree and the scene are two requests; answer each by its path. */
function answering({ tree = TREE, node = FULL } = {}) {
  request.mockImplementation((path) =>
    path.endsWith('/structure/') ? Promise.resolve(tree) : Promise.resolve(node),
  )
}

async function click(wrapper, label) {
  const button = wrapper.findAll('button').find((b) => b.text().includes(label))
  await button.trigger('click')
  await flushPromises()
}

async function render({ sceneId = 's-1', ...rest } = {}) {
  answering(rest)
  const router = routerFor()
  await router.push({ name: 'campaign-scene', params: { campaignId: 'c-1', sceneId } })
  await router.isReady()

  const wrapper = mount(SceneView, { global: { plugins: [PrimeVue, createPinia(), router] } })
  await flushPromises()
  return wrapper
}

describe('a scene’s page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('asks for the scene itself, because the tree carries no bodies', async () => {
    await render()

    expect(request).toHaveBeenCalledWith('/campaigns/c-1/scenes/s-1')
  })

  it('renders the body through the dialect rather than as text', async () => {
    // The read-aloud block becomes a component; if this ever shows the fence
    // itself, the page has started treating prose as a string.
    const wrapper = await render()

    expect(wrapper.text()).toContain('The gate does not swing')
    expect(wrapper.text()).not.toContain(':::read-aloud')
  })

  it('says so when nothing has been written, which is most of a campaign', async () => {
    const wrapper = await render({ node: { ...FULL, body: '' } })

    expect(wrapper.text()).toContain('Nothing written yet')
  })

  it('shows the way back, starting at the structure', async () => {
    /*
     * The page carries no tree beside it, so the trail is the one way back that
     * does not depend on the sidebar being on screen.
     */
    const wrapper = await render()
    const trail = wrapper.findAll('.trail a').map((a) => a.text())

    expect(trail).toEqual(['Structure', 'Act I', 'The Causeway'])
  })

  it('walks the story rather than the siblings', async () => {
    /*
     * "The sunken arch" is the last scene of its sequence, and next is the scene
     * on the act *after* it — out of the sequence, still inside the act. Sibling
     * order would have said there was no next at all.
     */
    const wrapper = await render({ sceneId: 's-2' })
    const steps = wrapper.findAll('.stepper__title').map((el) => el.text())

    expect(steps).toEqual(['Arrival at dusk', 'Interlude'])
  })

  it('offers no dead end at the ends of the campaign', async () => {
    // A disabled control on the first scene of every campaign is a permanent
    // reminder of an edge nobody needs telling about.
    const wrapper = await render({ sceneId: 's-1' })

    expect(wrapper.findAll('.stepper__step')).toHaveLength(1)
  })

  describe('editing', () => {
    it('loads the form with what is there, because the write replaces everything', async () => {
      const wrapper = await render()

      await click(wrapper, 'Edit')

      expect(wrapper.get('textarea').element.value).toBe(BODY)
    })

    it('sends every field, so a save cannot clear what it did not touch', async () => {
      const wrapper = await render()
      await click(wrapper, 'Edit')

      request.mockClear()
      answering()
      await click(wrapper, 'Save')

      expect(request).toHaveBeenCalledWith('/campaigns/c-1/scenes/s-1', {
        method: 'PUT',
        json: { title: 'Arrival at dusk', body: BODY, status: 'planned' },
      })
    })

    it('sends no placement at all, because this form does not move things', async () => {
      /*
       * The form owns what the scene says; the three-dots menu owns where it
       * sits. A Save that could also reorganise would put a rename and a move
       * behind one button, and only one of those is undone by doing it again.
       */
      const wrapper = await render()
      await click(wrapper, 'Edit')

      request.mockClear()
      answering()
      await click(wrapper, 'Save')

      const paths = request.mock.calls.map(([path]) => path)
      expect(paths.some((path) => path.endsWith('/placement'))).toBe(false)
    })

    it('refuses to save a scene with no title', async () => {
      /*
       * The API takes a bare string, so it accepts a blank title and answers 422
       * only for a missing one — this is the only thing between a game master
       * and a nameless scene.
       */
      const wrapper = await render()
      await click(wrapper, 'Edit')

      await wrapper.get('input').setValue('   ')
      await click(wrapper, 'Save')

      expect(wrapper.text()).toContain('Give it a title')
    })
  })

  it('answers the same for a scene that is not there as for one that is not yours', async () => {
    request.mockRejectedValue(new Error('404'))
    const router = routerFor()
    await router.push({ name: 'campaign-scene', params: { campaignId: 'c-1', sceneId: 's-9' } })
    await router.isReady()

    const wrapper = mount(SceneView, { global: { plugins: [PrimeVue, createPinia(), router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('not here')
  })
})
