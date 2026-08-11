import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import CampaignForm from './CampaignForm.vue'
import { ApiError } from '../api/http.js'

const HOLLOW = { id: 'c-1', name: 'The Hollow Crown', description: 'A kingdom with no heir.' }

/* Textarea observes its own size to grow with the description; jsdom has no
 * ResizeObserver. Not a fact about this component, only about the environment. */
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

function mountForm(props = {}) {
  return mount(CampaignForm, {
    props: { submitLabel: 'Save changes', ...props },
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })
}

async function submit(wrapper) {
  await wrapper.get('form').trigger('submit')
}

/* What the form emitted, or undefined if it refused to emit anything. */
function submitted(wrapper) {
  return wrapper.emitted('submit')?.at(-1)?.[0]
}

describe('CampaignForm', () => {
  describe('creating, with no campaign to start from', () => {
    it('starts empty', () => {
      const wrapper = mountForm()

      expect(wrapper.get('#campaign-name').element.value).toBe('')
      expect(wrapper.get('#campaign-description').element.value).toBe('')
    })

    it('trims the name, so a stray space is not part of it', async () => {
      const wrapper = mountForm()

      await wrapper.get('#campaign-name').setValue('  The Hollow Crown  ')
      await submit(wrapper)

      expect(submitted(wrapper)).toEqual({ name: 'The Hollow Crown', description: '' })
    })
  })

  describe('editing', () => {
    it('opens on what is there, so an edit starts from the campaign', () => {
      const wrapper = mountForm({ campaign: HOLLOW })

      expect(wrapper.get('#campaign-name').element.value).toBe('The Hollow Crown')
      expect(wrapper.get('#campaign-description').element.value).toBe('A kingdom with no heir.')
    })

    it('fills in when the campaign arrives, rather than staying blank', async () => {
      // The edit page mounts before the campaign list has answered. Reading the
      // prop once at setup would leave the form showing the blanks that were
      // there while the request was in flight.
      const wrapper = mountForm({ campaign: null })

      await wrapper.setProps({ campaign: HOLLOW })

      expect(wrapper.get('#campaign-name').element.value).toBe('The Hollow Crown')
    })

    it('sends the description back untouched when only the name changed', async () => {
      const wrapper = mountForm({ campaign: HOLLOW })

      await wrapper.get('#campaign-name').setValue('The Hollow Throne')
      await submit(wrapper)

      /*
       * The acceptance criterion this form exists for: `PUT /campaigns/{id}` is
       * a full replacement, so a form that emitted only what changed would clear
       * the description of every campaign anyone renamed.
       */
      expect(submitted(wrapper)).toEqual({
        name: 'The Hollow Throne',
        description: 'A kingdom with no heir.',
      })
    })

    it('lets a description be deliberately emptied', async () => {
      const wrapper = mountForm({ campaign: HOLLOW })

      await wrapper.get('#campaign-description').setValue('')
      await submit(wrapper)

      // Clearing has to stay possible: the difference between this and the case
      // above is that someone asked for it.
      expect(submitted(wrapper)).toEqual({ name: 'The Hollow Crown', description: '' })
    })

    it('copes with a campaign that has no description at all', () => {
      const wrapper = mountForm({
        campaign: { id: 'c-2', name: 'Salt & Ashes', description: null },
      })

      // `null` in a text box renders as the string "null" if it is passed
      // straight through.
      expect(wrapper.get('#campaign-description').element.value).toBe('')
    })
  })

  describe('a name that is not there', () => {
    it('refuses to submit, because the API would accept it', async () => {
      const wrapper = mountForm()

      await wrapper.get('#campaign-name').setValue('   ')
      await submit(wrapper)

      /*
       * `CampaignCreate.name` is a bare `str`: the backend answers 422 for a
       * name that is *missing*, never for one that is blank. Without this check
       * an empty name would be saved and put a nameless card on the chooser —
       * which is why the duplication #49 asked about is not duplication.
       */
      expect(submitted(wrapper)).toBeUndefined()
      expect(wrapper.text()).toContain('Give the campaign a name')
    })

    it('announces the complaint rather than only showing it', async () => {
      const wrapper = mountForm()

      await submit(wrapper)

      expect(wrapper.get('[role="alert"]').text()).toContain('Give the campaign a name')
    })

    it('lets go once there is a name', async () => {
      const wrapper = mountForm()
      await submit(wrapper)

      await wrapper.get('#campaign-name').setValue('The Hollow Crown')
      await submit(wrapper)

      expect(wrapper.text()).not.toContain('Give the campaign a name')
      expect(submitted(wrapper)).toEqual({ name: 'The Hollow Crown', description: '' })
    })
  })

  describe('more than the API will take', () => {
    it('holds both fields to the lengths the API accepts', () => {
      const wrapper = mountForm()

      /*
       * The one place the fields say the limit before the API does. `name` is a
       * `String(200)` column — longer than that used to reach a database that
       * could not hold it and come back a 500 — and the description is capped in
       * the schema at 1000. Stopping the typing is kinder than a 422 arriving
       * after a description has been written.
       */
      expect(wrapper.get('#campaign-name').attributes('maxlength')).toBe('200')
      expect(wrapper.get('#campaign-description').attributes('maxlength')).toBe('1000')
    })
  })

  describe('what the API said', () => {
    it('puts a 422 about the name against the name', async () => {
      const wrapper = mountForm({
        campaign: HOLLOW,
        error: new ApiError(422, [
          { loc: ['body', 'name'], msg: 'Input should be a valid string' },
        ]),
      })

      const field = wrapper.get('#campaign-name')

      expect(field.attributes('aria-invalid')).toBe('true')
      expect(wrapper.get(`#${field.attributes('aria-describedby')}`).text()).toContain(
        'That name was not accepted',
      )
    })

    it('puts a 422 about the description against the description', async () => {
      const wrapper = mountForm({
        campaign: HOLLOW,
        error: new ApiError(422, [{ loc: ['body', 'description'], msg: 'Too long' }]),
      })

      expect(wrapper.get('#campaign-description-error').text()).toContain(
        'That description was not accepted',
      )
      // And nowhere else: the name was fine, so it is not described by an error
      // and carries no invalid state.
      expect(wrapper.get('#campaign-name').attributes('aria-describedby')).toBeUndefined()
      expect(wrapper.get('#campaign-name').attributes('aria-invalid')).not.toBe('true')
    })

    it('does not print pydantic’s own wording at a game master', () => {
      const wrapper = mountForm({
        error: new ApiError(422, [
          { loc: ['body', 'name'], msg: 'Input should be a valid string' },
        ]),
      })

      // Which field it was is the part worth keeping. The message is written for
      // whoever wrote the request.
      expect(wrapper.text()).not.toContain('Input should be a valid string')
    })

    it('still says something when a 422 names a field this form does not have', () => {
      const wrapper = mountForm({
        error: new ApiError(422, [{ loc: ['body', 'owner_id'], msg: 'Missing' }]),
      })

      // An error placed nowhere is an error nobody sees, and the form would look
      // like the button simply did nothing.
      expect(wrapper.get('[role="alert"]').text()).toContain('not accepted')
    })

    it('survives a 422 whose body is not the array it usually is', () => {
      const wrapper = mountForm({ error: new ApiError(422, 'something else entirely') })

      expect(wrapper.get('[role="alert"]').exists()).toBe(true)
    })

    it('explains a campaign that went away under the edit', () => {
      const wrapper = mountForm({
        campaign: HOLLOW,
        error: new ApiError(404, 'Campaign not found'),
      })

      expect(wrapper.get('[role="alert"]').text()).toContain('no longer there')
    })

    it('has something to say about anything else', () => {
      const wrapper = mountForm({ campaign: HOLLOW, error: new ApiError(500, null) })

      expect(wrapper.get('[role="alert"]').text()).toContain('Something went wrong saving')
    })
  })

  it('says on the button which of the two things it is doing', () => {
    expect(mountForm({ submitLabel: 'Create campaign' }).text()).toContain('Create campaign')
  })

  it('will not submit twice while the first one is still in flight', () => {
    const wrapper = mountForm({ busy: true })

    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })
})
