import { describe, it, expect, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ForgotPasswordView from './ForgotPasswordView.vue'
import { ApiError } from '../api/http.js'
import * as http from '../api/http.js'

function mountView() {
  return mount(ForgotPasswordView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })
}

async function askFor(view, identifier) {
  await view.find('#forgot-identifier').setValue(identifier)
  await view.find('form').trigger('submit')
  await flushPromises()
}

describe('ForgotPasswordView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends whatever identifier was typed, untouched', async () => {
    /*
     * Either an address or a username (#71) — the page does not guess which, and
     * does not need to. Deciding here would mean two code paths where the API has
     * one, and the API is the thing that must not be able to tell them apart by
     * timing.
     */
    const apiFetch = vi.spyOn(http, 'apiFetch').mockResolvedValue(null)

    await askFor(mountView(), 'aragorn')

    expect(apiFetch).toHaveBeenCalledWith('/users/forgot-password', {
      method: 'POST',
      json: { identifier: 'aragorn' },
    })
  })

  it('accepts an address just as readily', async () => {
    const apiFetch = vi.spyOn(http, 'apiFetch').mockResolvedValue(null)

    await askFor(mountView(), 'aragorn@gondor.test')

    expect(apiFetch.mock.calls[0][1].json.identifier).toBe('aragorn@gondor.test')
  })

  it('says the same thing whatever happened', async () => {
    /*
     * The endpoint answers 204 either way on purpose — it is the one place that
     * could be asked whether an account exists. A page that said "sent!" for one
     * and something else for the other would hand back exactly what the API
     * refused to.
     */
    vi.spyOn(http, 'apiFetch').mockResolvedValue(null)

    const view = mountView()
    await askFor(view, 'definitely-nobody')

    expect(view.text()).toContain('If that matches an account')
  })

  it('never names the address back', async () => {
    vi.spyOn(http, 'apiFetch').mockResolvedValue(null)

    const view = mountView()
    await askFor(view, 'aragorn@gondor.test')

    expect(view.text()).not.toContain('aragorn@gondor.test')
  })

  it('shows the limiter’s sentence when it refuses', async () => {
    const detail = 'Too many password reset requests from here. Try again later.'
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(429, detail))

    const view = mountView()
    await askFor(view, 'aragorn')

    expect(view.find('[role="alert"]').text()).toContain(detail)
  })

  it('keeps the form usable after a failure', async () => {
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(500, null))

    const view = mountView()
    await askFor(view, 'aragorn')

    expect(view.find('form').exists()).toBe(true)
    expect(view.text()).toContain('Try again shortly')
  })

  it('labels its field', () => {
    const view = mountView()

    expect(view.find('label[for="forgot-identifier"]').exists()).toBe(true)
  })
})
