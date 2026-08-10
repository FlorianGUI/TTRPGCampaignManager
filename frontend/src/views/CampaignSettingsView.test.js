import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import CampaignSettingsView from './CampaignSettingsView.vue'
import {
  forgetCurrentCampaign,
  readCurrentCampaign,
  rememberCurrentCampaign,
} from '../stores/currentCampaign.js'
import { ApiError } from '../api/http.js'

const request = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())

vi.mock('../api/client.js', () => ({ request }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace }),
  useRoute: () => ({ params: { campaignId: 'c-1' } }),
}))

const HOLLOW = { id: 'c-1', name: 'The Hollow Crown', description: 'A kingdom with no heir.' }
const SALT = { id: 'c-2', name: 'Salt & Ashes', description: null }

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

/*
 * The list is the only thing this page reads. `answer` sets up what the first
 * call — always `GET /campaigns/` — replies with; later calls are the writes,
 * which each test sets up for itself.
 */
async function mountView(list = [HOLLOW, SALT]) {
  setActivePinia(createPinia())
  request.mockImplementation(() =>
    list instanceof Error ? Promise.reject(list) : Promise.resolve(list),
  )

  const wrapper = mount(CampaignSettingsView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })

  await flushPromises()

  return wrapper
}

async function save(wrapper) {
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

/* Types into the confirmation box and hands back the delete button, which is
 * where the typed name shows up as a state rather than as text. */
async function type(wrapper, typed) {
  await wrapper.get('#delete-confirmation').setValue(typed)

  return wrapper.get('.danger__form button')
}

/*
 * Submitted on the form rather than clicked on the button: jsdom does not
 * perform implicit form submission from a click, so a click here would assert
 * nothing about what the page does.
 */
async function confirmDelete(wrapper, typed = 'The Hollow Crown') {
  await type(wrapper, typed)
  await wrapper.get('.danger__form').trigger('submit')
  await flushPromises()
}

describe('CampaignSettingsView', () => {
  beforeEach(() => {
    request.mockReset()
    replace.mockReset()
    forgetCurrentCampaign()
  })

  describe('finding the campaign', () => {
    it('opens on the campaign named in the path', async () => {
      const wrapper = await mountView()

      expect(wrapper.get('#campaign-name').element.value).toBe('The Hollow Crown')
      expect(wrapper.get('#campaign-description').element.value).toBe('A kingdom with no heir.')
    })

    it('asks for the list rather than the campaign, and only once', async () => {
      await mountView()

      /*
       * The list is already in flight or in hand on every path that reaches
       * here, `ensureLoaded` is single-flight, and it is what tells "not yours"
       * from "not there" — a distinction `GET /campaigns/{id}` cannot make,
       * because the API answers 404 for both.
       */
      expect(request).toHaveBeenCalledTimes(1)
      expect(request).toHaveBeenCalledWith('/campaigns/')
    })

    it('says the campaign is gone when it is not in the list', async () => {
      const wrapper = await mountView([SALT])

      expect(wrapper.text()).toContain('That campaign is not here')
      expect(wrapper.find('#campaign-name').exists()).toBe(false)
    })

    it('does not pass a dropped connection off as a campaign that is gone', async () => {
      const wrapper = await mountView(new ApiError(503, null))

      // One is a network that failed and the other is a campaign somebody has
      // lost. Showing the second for the first is the kind of lie that makes
      // people go looking for a backup.
      expect(wrapper.text()).toContain('could not reach this campaign')
      expect(wrapper.text()).not.toContain('That campaign is not here')
    })
  })

  describe('editing', () => {
    it('PUTs both fields when only the name changed', async () => {
      const wrapper = await mountView()
      request.mockResolvedValue({ ...HOLLOW, name: 'The Hollow Throne' })

      await wrapper.get('#campaign-name').setValue('The Hollow Throne')
      await save(wrapper)

      /*
       * The acceptance criterion: `PUT` replaces rather than patches, so an
       * untouched description has to be sent back or saving a new name clears
       * it.
       */
      expect(request).toHaveBeenLastCalledWith('/campaigns/c-1', {
        method: 'PUT',
        json: { name: 'The Hollow Throne', description: 'A kingdom with no heir.' },
      })
    })

    it('says it saved, without going anywhere', async () => {
      const wrapper = await mountView()
      request.mockResolvedValue(HOLLOW)

      await save(wrapper)

      expect(wrapper.get('[role="status"]').text()).toContain('Saved')
      // Editing is not a journey. You stay where you are, on the page you can
      // reload and come back to.
      expect(replace).not.toHaveBeenCalled()
    })

    it('shows a 422 against the field the API named', async () => {
      const wrapper = await mountView()
      request.mockRejectedValue(new ApiError(422, [{ loc: ['body', 'name'], msg: 'nope' }]))

      await save(wrapper)

      expect(wrapper.get('#campaign-name').attributes('aria-invalid')).toBe('true')
      expect(wrapper.text()).toContain('That name was not accepted')
      expect(wrapper.text()).not.toContain('Saved')
    })

    it('explains a campaign deleted in another tab under the edit', async () => {
      const wrapper = await mountView()
      request.mockRejectedValue(new ApiError(404, 'Campaign not found'))

      await save(wrapper)

      expect(wrapper.text()).toContain('no longer there')
    })
  })

  describe('deleting', () => {
    it('will not do it until the name is typed out', async () => {
      const wrapper = await mountView()

      expect((await type(wrapper, '')).attributes('disabled')).toBeDefined()
      expect((await type(wrapper, 'the hollow crown')).attributes('disabled')).toBeDefined()

      /*
       * A typed name rather than a dialog: this takes every character at the
       * table with it and there is no undo, and a modal is dismissed by the
       * reflex aimed at the last one.
       */
      expect((await type(wrapper, 'The Hollow Crown')).attributes('disabled')).toBeUndefined()
    })

    it('refuses a submit that got past the disabled button', async () => {
      const wrapper = await mountView()
      request.mockResolvedValue(null)

      // The button is the visible half of the check; a form can still be
      // submitted by pressing Enter in the field, so the handler holds the rule
      // too rather than trusting the attribute.
      await confirmDelete(wrapper, 'The Hollow')

      expect(request).toHaveBeenCalledTimes(1) // the list, and nothing since
      expect(replace).not.toHaveBeenCalled()
    })

    it('says out loud what goes with it', async () => {
      const wrapper = await mountView()

      expect(wrapper.text()).toContain('every character sheet')
      expect(wrapper.text()).toContain('no undo')
    })

    it('DELETEs it and returns to the chooser', async () => {
      const wrapper = await mountView()
      request.mockResolvedValue(null)

      await confirmDelete(wrapper)

      expect(request).toHaveBeenLastCalledWith('/campaigns/c-1', { method: 'DELETE' })
      // `replace`, so Back does not return to the settings page of a campaign
      // that no longer exists.
      expect(replace).toHaveBeenCalledWith({ name: 'home' })
    })

    it('stops the app opening on a campaign that is gone', async () => {
      rememberCurrentCampaign('c-1')
      const wrapper = await mountView()
      request.mockResolvedValue(null)

      await confirmDelete(wrapper)

      expect(readCurrentCampaign()).toBeNull()
    })

    it('leaves a different remembered campaign alone', async () => {
      rememberCurrentCampaign('c-2')
      const wrapper = await mountView()
      request.mockResolvedValue(null)

      await confirmDelete(wrapper)

      expect(readCurrentCampaign()).toBe('c-2')
    })

    it('stays put and explains itself when the delete fails', async () => {
      const wrapper = await mountView()
      request.mockRejectedValue(new ApiError(500, null))

      await confirmDelete(wrapper)

      expect(wrapper.get('.danger__error').text()).toContain('Something went wrong deleting')
      expect(replace).not.toHaveBeenCalled()
    })

    it('says so plainly when it was already deleted', async () => {
      const wrapper = await mountView()
      request.mockRejectedValue(new ApiError(404, 'Campaign not found'))

      await confirmDelete(wrapper)

      expect(wrapper.get('.danger__error').text()).toContain('already gone')
    })
  })
})
