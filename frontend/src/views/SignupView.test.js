import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import SignupView from './SignupView.vue'
import { ApiError } from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

const router = { replace: vi.fn() }

vi.mock('vue-router', () => ({
  useRouter: () => router,
}))

function mountView() {
  return mount(SignupView, { global: { plugins: [PrimeVue], stubs: { RouterLink: true } } })
}

async function submitWith(view) {
  await view.find('#signup-username').setValue('aragorn')
  await view.find('#signup-email').setValue('aragorn@gondor.test')
  await view.find('#signup-password').setValue('anduril')
  await view.find('form').trigger('submit')
  await Promise.resolve()
  await view.vm.$nextTick()
}

describe('SignupView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    router.replace.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('registers and is signed in afterwards, with no second login step', async () => {
    const auth = useAuthStore()
    vi.spyOn(auth, 'register').mockResolvedValue()

    const view = mountView()
    await submitWith(view)

    expect(auth.register).toHaveBeenCalledWith('aragorn', 'aragorn@gondor.test', 'anduril')
    expect(router.replace).toHaveBeenCalledWith('/')
  })

  it('puts a taken username on the username field, where it can be fixed', async () => {
    vi.spyOn(useAuthStore(), 'register').mockRejectedValue(
      new ApiError(409, 'Username already exists'),
    )

    const view = mountView()
    await submitWith(view)

    const error = view.find('#signup-username-error')
    expect(error.exists()).toBe(true)
    expect(error.text()).toContain('taken')
  })

  it('points the field at its message, so it is not sighted-users-only', async () => {
    /*
     * The half of an error message that is easy to ship broken: without
     * aria-describedby the text is on screen and announced to nobody.
     */
    vi.spyOn(useAuthStore(), 'register').mockRejectedValue(
      new ApiError(409, 'Username already exists'),
    )

    const view = mountView()
    await submitWith(view)

    const field = view.find('#signup-username')
    expect(field.attributes('aria-describedby')).toBe('signup-username-error')
    expect(field.attributes('aria-invalid')).toBe('true')
  })

  it('keys off the status rather than the wording of the conflict', async () => {
    // /users/register has exactly one way to conflict and sends no error code,
    // so 409 *is* the discriminator — and this keeps working if the sentence
    // behind it is ever reworded.
    vi.spyOn(useAuthStore(), 'register').mockRejectedValue(new ApiError(409, 'something else'))

    const view = mountView()
    await submitWith(view)

    expect(view.find('#signup-username-error').exists()).toBe(true)
  })

  it('does not carry an error over from a previous attempt', async () => {
    const register = vi
      .spyOn(useAuthStore(), 'register')
      .mockRejectedValueOnce(new ApiError(409, 'Username already exists'))
      .mockResolvedValueOnce()

    const view = mountView()
    await submitWith(view)
    expect(view.find('#signup-username-error').exists()).toBe(true)

    await submitWith(view)

    expect(register).toHaveBeenCalledTimes(2)
    expect(view.find('#signup-username-error').exists()).toBe(false)
  })

  /*
   * The 422 (#102). Signing up with an address the API refuses used to say
   * "something there was not accepted" and stop — the reason was in the response
   * the whole time, in `loc`.
   */
  describe('a field the API refused', () => {
    // The real body, from `e2e-greyfen@example.test` being turned away for a
    // reserved TLD. `msg` is included precisely because it must not be shown.
    const PYDANTIC_MSG =
      'value is not a valid email address: The part after the @-sign is a ' +
      'special-use or reserved name that cannot be used with email.'

    function refusing(...fields) {
      return new ApiError(
        422,
        fields.map((field) => ({ type: 'value_error', loc: ['body', field], msg: PYDANTIC_MSG })),
      )
    }

    it('puts a refused address on the email field', async () => {
      vi.spyOn(useAuthStore(), 'register').mockRejectedValue(refusing('email'))

      const view = mountView()
      await submitWith(view)

      expect(view.find('#signup-email-error').text()).toContain('email address we can use')
      // The wiring, not just the text: a message announced to nobody is half a
      // message. `FormField` owns it, and this is what keeps it wired here.
      expect(view.find('#signup-email').attributes('aria-describedby')).toBe('signup-email-error')
    })

    it('does not show pydantic’s own words', async () => {
      /* They are written for whoever wrote the request. "The part after the
       * @-sign is a special-use or reserved name" under a text box is not an
       * explanation, it is an apology in a language the reader does not speak. */
      vi.spyOn(useAuthStore(), 'register').mockRejectedValue(refusing('email'))

      const view = mountView()
      await submitWith(view)

      expect(view.text()).not.toContain('@-sign')
      expect(view.text()).not.toContain('special-use')
    })

    it('places one on the username or the password just the same', async () => {
      /* Neither is reachable from this form today — both are bare `str` in
       * `UserCreate` — but a field the API names and the form cannot show is the
       * exact failure this issue is about. */
      vi.spyOn(useAuthStore(), 'register').mockRejectedValue(refusing('username', 'password'))

      const view = mountView()
      await submitWith(view)

      expect(view.find('#signup-username-error').exists()).toBe(true)
      expect(view.find('#signup-password-error').exists()).toBe(true)
    })

    it('falls back to the form when it names a field that is not here', async () => {
      // Otherwise the submit would answer with nothing at all, and the form
      // would look like it had simply not worked.
      vi.spyOn(useAuthStore(), 'register').mockRejectedValue(refusing('timezone'))

      const view = mountView()
      await submitWith(view)

      expect(view.find('[role="alert"]').text()).toContain('not accepted')
      expect(view.find('#signup-email-error').exists()).toBe(false)
    })

    it('says something even when the body is not the shape a 422 promises', async () => {
      vi.spyOn(useAuthStore(), 'register').mockRejectedValue(new ApiError(422, 'not an array'))

      const view = mountView()
      await submitWith(view)

      expect(view.find('[role="alert"]').exists()).toBe(true)
    })

    it('does not leave a field message behind on the next attempt', async () => {
      const register = vi
        .spyOn(useAuthStore(), 'register')
        .mockRejectedValueOnce(refusing('email'))
        .mockResolvedValueOnce()

      const view = mountView()
      await submitWith(view)
      expect(view.find('#signup-email-error').exists()).toBe(true)

      await submitWith(view)

      expect(register).toHaveBeenCalledTimes(2)
      expect(view.find('#signup-email-error').exists()).toBe(false)
    })
  })

  it('shows the registration limit rather than a shrug', async () => {
    const detail = 'Too many accounts created from here. Try again later.'
    vi.spyOn(useAuthStore(), 'register').mockRejectedValue(new ApiError(429, detail))

    const view = mountView()
    await submitWith(view)

    expect(view.find('[role="alert"]').text()).toContain(detail)
  })

  it('asks password managers to offer a new password, not the saved one', () => {
    const view = mountView()

    expect(view.find('label[for="signup-username"]').exists()).toBe(true)
    expect(view.find('label[for="signup-email"]').exists()).toBe(true)
    expect(view.find('label[for="signup-password"]').exists()).toBe(true)
    expect(view.find('#signup-password').attributes('type')).toBe('password')
    expect(view.find('#signup-password').attributes('autocomplete')).toBe('new-password')
  })
})
