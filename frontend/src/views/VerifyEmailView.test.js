import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import VerifyEmailView from './VerifyEmailView.vue'
import { ApiError } from '../api/http.js'
import * as http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

function landOn(query) {
  window.history.replaceState({}, '', `/verify-email${query}`)
}

async function mountView() {
  const view = mount(VerifyEmailView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })
  await flushPromises()
  return view
}

describe('VerifyEmailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('spends the token from the link and says so', async () => {
    const apiFetch = vi
      .spyOn(http, 'apiFetch')
      .mockResolvedValue({ id: 'u-1', username: 'aragorn', email: 'a@g.test' })
    landOn('?token=a-real-token')

    const view = await mountView()

    expect(apiFetch).toHaveBeenCalledWith('/users/verify-email', {
      method: 'POST',
      json: { token: 'a-real-token' },
    })
    expect(view.text()).toContain('Address confirmed')
  })

  it('takes the token out of the address bar once it is spent', async () => {
    /*
     * It is a credential, it verifies an address on its own, and it is sitting
     * where a shoulder can read it and history will keep it. Spent by now, so
     * removing it costs nothing.
     */
    vi.spyOn(http, 'apiFetch').mockResolvedValue({})
    landOn('?token=a-real-token')

    await mountView()

    expect(window.location.search).toBe('')
  })

  it('says the link is finished when the API refuses it', async () => {
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(400, 'This link is no longer valid'))
    landOn('?token=already-used')

    const view = await mountView()

    expect(view.text()).toContain('no longer valid')
  })

  it('does not say which way it was finished', async () => {
    /*
     * The API answers unknown, expired and already-used identically on purpose.
     * A page that guessed between them would hand back what the API withheld —
     * and confirm to whoever is guessing that a token existed.
     */
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(400, 'This link is no longer valid'))
    landOn('?token=already-used')

    const text = (await mountView()).text().toLowerCase()

    expect(text).not.toMatch(/unknown token|never issued|does not exist/)
  })

  it('separates a broken link from a broken server', async () => {
    // "Try again" is right for one and useless for the other, so they cannot
    // share a message: a 500 does not mean the link is spent.
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(500, null))
    landOn('?token=a-real-token')

    const view = await mountView()

    expect(view.text()).toContain('try again')
    expect(view.text()).not.toContain('no longer valid')
  })

  it('handles a link with no token at all', async () => {
    const apiFetch = vi.spyOn(http, 'apiFetch')
    landOn('')

    const view = await mountView()

    expect(apiFetch).not.toHaveBeenCalled()
    expect(view.text()).toContain('no longer valid')
  })

  it('refreshes the signed-in user, so the rest of the app agrees with this page', async () => {
    const auth = useAuthStore()
    auth.user = { id: 'u-1', username: 'aragorn', email_verified: false }
    vi.spyOn(http, 'apiFetch').mockResolvedValue({
      id: 'u-1',
      username: 'aragorn',
      email_verified: true,
    })
    landOn('?token=a-real-token')

    await mountView()

    expect(auth.user.email_verified).toBe(true)
  })

  it('works signed out, which is the common case', async () => {
    // Registered on a laptop, opened the mail on a phone.
    const auth = useAuthStore()
    vi.spyOn(http, 'apiFetch').mockResolvedValue({})
    landOn('?token=a-real-token')

    const view = await mountView()

    expect(auth.isSignedIn).toBe(false)
    expect(view.text()).toContain('Address confirmed')
  })
})
