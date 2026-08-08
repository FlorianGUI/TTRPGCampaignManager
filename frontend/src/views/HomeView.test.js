import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { RouterLinkStub } from '@vue/test-utils'
import HomeView from './HomeView.vue'
import { useAuthStore } from '../stores/auth.js'
import { readCurrentCampaign, forgetCurrentCampaign } from '../stores/currentCampaign.js'
import { ApiError } from '../api/http.js'

const request = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const HOLLOW = { id: 'c-1', name: 'The Hollow Crown', description: 'A kingdom with no heir.' }
const SALT = { id: 'c-2', name: 'Salt & Ashes', description: null }
const PHB = { id: 's-1', title: "Player's Handbook" }

/*
 * Answers whichever collection is being asked for, so a test can set up
 * campaigns and sources independently — including one failing while the other
 * does not, which is the case home has to survive.
 */
function api({ campaigns = [], sources = [] } = {}) {
  request.mockImplementation((path) => {
    const answer = path.startsWith('/campaigns') ? campaigns : sources

    return answer instanceof Error ? Promise.reject(answer) : Promise.resolve(answer)
  })
}

/*
 * Two jsdom gaps, stubbed the way AppShell.test.js stubs matchMedia — neither
 * is a fact about this view, only about the environment it is mounted in.
 *
 * `Textarea` observes its own size to grow with the description, and `Dialog`
 * teleports to the body, which puts the form outside the wrapper.
 */
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

async function mountHome() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { id: 'u-1', username: 'florian' }

  const wrapper = mount(HomeView, {
    global: {
      plugins: [PrimeVue, pinia],
      stubs: { RouterLink: RouterLinkStub, teleport: true },
    },
  })

  await flushPromises()

  return wrapper
}

describe('HomeView', () => {
  beforeEach(() => {
    request.mockReset()
    push.mockReset()
    forgetCurrentCampaign()
  })

  describe('with campaigns to choose from', () => {
    it('lists them in the order the API sent, without reordering them', async () => {
      api({ campaigns: [HOLLOW, SALT] })

      const names = (await mountHome()).findAll('.card__name').map((n) => n.text())

      // The order is decided by `campaign_repository.py`'s `order_by`. Sorting
      // again here would be a second opinion that the day this list is paged
      // would silently start disagreeing with the first.
      expect(names).toEqual(['The Hollow Crown', 'Salt & Ashes'])
    })

    it('links each card at the campaign, with the id in the path', async () => {
      api({ campaigns: [HOLLOW] })

      const link = (await mountHome()).findComponent(RouterLinkStub)

      // A real link rather than a click handler, so middle-click and
      // open-in-new-tab work and the new tab carries the campaign without
      // needing anything in storage.
      expect(link.props('to')).toEqual({
        name: 'campaign-sessions',
        params: { campaignId: 'c-1' },
      })
    })

    it('remembers the campaign on the way through', async () => {
      api({ campaigns: [HOLLOW] })
      const wrapper = await mountHome()

      await wrapper.findComponent(RouterLinkStub).trigger('click')

      expect(readCurrentCampaign()).toBe('c-1')
    })

    it('does not mark any of them as current', async () => {
      api({ campaigns: [HOLLOW, SALT] })

      /*
       * You only reach this screen when there is nothing remembered — you just
       * signed in, or you just left a campaign. The only card that could carry
       * a "current" mark is the one you are pointedly not in.
       */
      expect((await mountHome()).text()).not.toMatch(/current/i)
    })

    it('shows initials, not a broken avatar, for a campaign with no art', async () => {
      api({ campaigns: [HOLLOW] })

      expect((await mountHome()).get('.card__sigil').text()).toBe('TH')
    })

    it('offers no campaign metadata, because the API has none to give', async () => {
      api({ campaigns: [HOLLOW] })

      /*
       * `CampaignResponse` is `{ id, name, description, owner_id }` and neither
       * table has timestamps. Session counts and last-played dates are what
       * `content/sample.js` invents, and inventing them here would be the same
       * bug in a new place (#59).
       */
      const text = (await mountHome()).text()

      expect(text).not.toMatch(/session|last played|\d+ party/i)
    })
  })

  describe('a fresh account', () => {
    it('asks for a first campaign rather than showing an empty list', async () => {
      api({ campaigns: [] })

      const wrapper = await mountHome()

      expect(wrapper.text()).toContain('Start your first campaign')
      expect(wrapper.findAll('.card__name')).toHaveLength(0)
    })

    it('greets the person by name', async () => {
      api({ campaigns: [] })

      expect((await mountHome()).text()).toContain('florian')
    })

    it('offers no sources shelf, since nothing here could add one yet', async () => {
      api({ campaigns: [], sources: [] })

      // Until #51 there is no way to add a source from this screen, and an
      // empty shelf with no action under it is a dead end wearing a heading.
      expect((await mountHome()).text()).not.toContain('Your sources')
    })
  })

  describe('the sources shelf', () => {
    it('lists the library read-only when there is one', async () => {
      api({ campaigns: [HOLLOW], sources: [PHB] })

      const wrapper = await mountHome()

      expect(wrapper.text()).toContain("Player's Handbook")
      // Read-only until #51 owns adding and #50 owns the view.
      expect(wrapper.text()).not.toMatch(/add a source/i)
    })

    it('survives a library that is unreachable, because campaigns are the point', async () => {
      api({ campaigns: [HOLLOW], sources: new ApiError(500, null) })

      const wrapper = await mountHome()

      expect(wrapper.get('.card__name').text()).toBe('The Hollow Crown')
      expect(wrapper.text()).not.toContain('Your sources')
    })
  })

  describe('when campaigns cannot be fetched', () => {
    it('says so, and does not pass it off as an empty account', async () => {
      api({ campaigns: new ApiError(503, null) })

      const wrapper = await mountHome()

      expect(wrapper.text()).toContain('could not reach your campaigns')
      expect(wrapper.text()).not.toContain('Start your first campaign')
    })

    it('offers a retry', async () => {
      api({ campaigns: new ApiError(503, null) })
      const wrapper = await mountHome()

      api({ campaigns: [HOLLOW] })
      await wrapper.get('.home__retry').trigger('click')
      await flushPromises()

      expect(wrapper.get('.card__name').text()).toBe('The Hollow Crown')
    })
  })

  describe('creating a campaign', () => {
    /* From the empty state, which is where it is the primary action. The card
     * in the grid opens the same dialog. */
    async function openDialog() {
      api({ campaigns: [] })
      const wrapper = await mountHome()

      await wrapper.get('.home__empty button').trigger('click')
      await flushPromises()

      return wrapper
    }

    it('refuses a nameless campaign before asking the API', async () => {
      const wrapper = await openDialog()
      request.mockClear()

      await wrapper.get('form').trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Give the campaign a name')
      expect(request).not.toHaveBeenCalled()
    })

    it('trims the name, so a stray space is not part of it', async () => {
      const wrapper = await openDialog()
      request.mockResolvedValue(HOLLOW)

      await wrapper.get('#campaign-name').setValue('  The Hollow Crown  ')
      await wrapper.get('form').trigger('submit')
      await flushPromises()

      expect(request).toHaveBeenCalledWith(
        '/campaigns/',
        expect.objectContaining({ json: { name: 'The Hollow Crown', description: null } }),
      )
    })

    it('goes straight into the campaign it just made', async () => {
      const wrapper = await openDialog()
      request.mockResolvedValue(HOLLOW)

      await wrapper.get('#campaign-name').setValue('The Hollow Crown')
      await wrapper.get('form').trigger('submit')
      await flushPromises()

      // You just made it; being returned to a list to find it again would be a
      // step for its own sake.
      expect(readCurrentCampaign()).toBe('c-1')
      expect(push).toHaveBeenCalledWith({
        name: 'campaign-sessions',
        params: { campaignId: 'c-1' },
      })
    })

    it('keeps you in the form when the API refuses', async () => {
      const wrapper = await openDialog()
      request.mockRejectedValue(new ApiError(500, null))

      await wrapper.get('#campaign-name').setValue('The Hollow Crown')
      await wrapper.get('form').trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Something went wrong creating the campaign')
      expect(push).not.toHaveBeenCalled()
      expect(readCurrentCampaign()).toBeNull()
    })
  })
})
