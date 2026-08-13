import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import CampaignNav from './CampaignNav.vue'

const request = vi.hoisted(() => vi.fn())

vi.mock('../../api/client.js', () => ({ request }))

const campaign = { id: 'c-1', name: 'The Hollow Crown', description: null }

const scene = (id, title, position, extra = {}) => ({
  id,
  title,
  status: 'planned',
  act_id: null,
  sequence_id: null,
  position,
  ...extra,
})

function routerFor() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
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
        path: '/campaigns/:campaignId/scenes/:sceneId',
        name: 'campaign-scene',
        component: { template: '<div />' },
      },
    ],
  })
}

async function render(tree) {
  request.mockResolvedValue(tree)
  const wrapper = mount(CampaignNav, {
    props: { campaign },
    global: { plugins: [createPinia(), routerFor()] },
  })
  await flushPromises()
  return wrapper
}

const labels = (wrapper) => wrapper.findAll('.nav__item-label').map((el) => el.text())

describe('the campaign’s own children in the sidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    request.mockReset()
  })

  it('lists what the campaign holds directly, in position order', async () => {
    /*
     * Depth one is acts *and* scenes hanging off the campaign, together — which
     * is what makes a one-shot work with no special case.
     */
    const wrapper = await render({
      acts: [{ id: 'a-1', title: 'Act I', description: '', position: 2048 }],
      sequences: [],
      scenes: [scene('s-1', 'Session zero', 1024)],
    })

    expect(labels(wrapper)).toEqual(['Session zero', 'Act I'])
  })

  it('stops at depth one, because three levels do not fit a 15rem column', async () => {
    const wrapper = await render({
      acts: [{ id: 'a-1', title: 'Act I', description: '', position: 1024 }],
      sequences: [
        { id: 'q-1', title: 'The Causeway', description: '', act_id: 'a-1', position: 1024 },
      ],
      scenes: [scene('s-1', 'Arrival at dusk', 1024, { sequence_id: 'q-1' })],
    })

    expect(labels(wrapper)).toEqual(['Act I'])
  })

  it('leaves a sequence written onto the campaign to the structure page', async () => {
    // Three kinds at one indent reads as a mess in this column; the page has
    // room for it and this does not.
    const wrapper = await render({
      acts: [],
      sequences: [
        { id: 'q-1', title: 'Loose thread', description: '', act_id: null, position: 1024 },
      ],
      scenes: [],
    })

    expect(wrapper.find('.campaign-nav').exists()).toBe(false)
  })

  it('shows how far through an act the table has got', async () => {
    const wrapper = await render({
      acts: [{ id: 'a-1', title: 'Act I', description: '', position: 1024 }],
      sequences: [],
      scenes: [
        scene('s-1', 'Played', 1024, { act_id: 'a-1', status: 'played' }),
        scene('s-2', 'Waiting', 2048, { act_id: 'a-1' }),
      ],
    })

    // The count is the dot's accessible name now, not a column of digits beside
    // every row — hover explains it, and nothing is reachable only by hovering.
    expect(wrapper.get('.progress__dot').attributes('aria-label')).toBe(
      'ongoing — 1 of 2 scenes played',
    )
  })

  it('says an empty act is empty rather than nought of nought', async () => {
    // Zero-of-zero reads as progress not yet begun rather than as nothing to
    // progress through, and only one of those is a problem to act on.
    const wrapper = await render({
      acts: [{ id: 'a-1', title: 'Act III', description: '', position: 1024 }],
      sequences: [],
      scenes: [],
    })

    expect(wrapper.get('.progress__dot').attributes('aria-label')).toBe(
      'empty — nothing written in it yet',
    )
  })

  it('marks a scene that belongs to no act', async () => {
    const wrapper = await render({
      acts: [],
      sequences: [],
      scenes: [scene('s-1', 'Session zero', 1024)],
    })

    expect(wrapper.get('.nav__item-loose').exists()).toBe(true)
  })

  it('renders nothing at all for a campaign with nothing in it', async () => {
    // Rather than an empty list with a heading over it, which reads as a
    // section that failed to load.
    const wrapper = await render({ acts: [], sequences: [], scenes: [] })

    expect(wrapper.find('.campaign-nav').exists()).toBe(false)
  })

  it('leads to the act itself, not to the outline', async () => {
    /*
     * Landing on the structure and then having to find the act you just clicked
     * is the journey this removes — the outline is one click away from the act's
     * own page for whoever wants it.
     */
    const wrapper = await render({
      acts: [{ id: 'a-1', title: 'Act I', description: '', position: 1024 }],
      sequences: [],
      scenes: [],
    })

    expect(wrapper.get('a').attributes('href')).toBe('/campaigns/c-1/acts/a-1')
  })

  it('leads a campaign-level scene to its own page too', async () => {
    const wrapper = await render({
      acts: [],
      sequences: [],
      scenes: [scene('s-1', 'Session zero', 1024)],
    })

    expect(wrapper.get('a').attributes('href')).toBe('/campaigns/c-1/scenes/s-1')
  })
})
