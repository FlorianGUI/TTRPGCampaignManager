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
