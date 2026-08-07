import { describe, it, expect, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ResetPasswordView from './ResetPasswordView.vue'
import { ApiError } from '../api/http.js'
import * as http from '../api/http.js'

function landOn(query) {
  window.history.replaceState({}, '', `/reset-password${query}`)
}

function mountView() {
  return mount(ResetPasswordView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: true } },
  })
}

async function choose(view, password) {
  await view.find('#reset-password').setValue(password)
  await view.find('form').trigger('submit')
  await flushPromises()
}

describe('ResetPasswordView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState({}, '', '/')
  })

  it('sends the token from the link with the new password', async () => {
    const apiFetch = vi.spyOn(http, 'apiFetch').mockResolvedValue(null)
    landOn('?token=a-real-token')

    const view = mountView()
    await choose(view, 'a-brand-new-password')

    expect(apiFetch).toHaveBeenCalledWith('/users/reset-password', {
      method: 'POST',
      json: { token: 'a-real-token', password: 'a-brand-new-password' },
    })
  })

  it('takes the token out of the address bar before anything else', () => {
    /*
     * Sooner than the verification page does it, and for a stronger reason: this
     * token is still live while the form sits open, so it is a working credential
     * on screen rather than a spent one.
     */
    landOn('?token=a-real-token')

    mountView()

    expect(window.location.search).toBe('')
  })

  it('does not sign anyone in — it points at the login page', async () => {
    /*
     * The reset revoked every session on purpose (#71). Signing one straight back
     * in would quietly undo the part that matters.
     */
    vi.spyOn(http, 'apiFetch').mockResolvedValue(null)
    landOn('?token=a-real-token')

    const view = mountView()
    await choose(view, 'a-brand-new-password')

    expect(view.text()).toContain('signed out')
    expect(view.findComponent({ name: 'Button' }).props('label')).toBe('Sign in')
  })

  it('explains a spent link and offers a new one', async () => {
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(400, 'This link is no longer valid'))
    landOn('?token=already-used')

    const view = mountView()
    await choose(view, 'a-brand-new-password')

    expect(view.text()).toContain('no longer valid')
    expect(view.text()).toContain('ask for a new one')
  })

  it('separates a spent link from a broken server', async () => {
    // One means start over, the other means try the same link again.
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(500, null))
    landOn('?token=a-real-token')

    const view = mountView()
    await choose(view, 'a-brand-new-password')

    expect(view.text()).toContain('Try again shortly')
    expect(view.text()).not.toContain('no longer valid')
  })

  it('handles a link with no token at all', () => {
    landOn('')

    const view = mountView()

    expect(view.find('form').exists()).toBe(false)
    expect(view.text()).toContain('missing its token')
  })

  it('asks password managers for a new password, not the saved one', () => {
    landOn('?token=a-real-token')

    const view = mountView()

    expect(view.find('label[for="reset-password"]').exists()).toBe(true)
    expect(view.find('#reset-password').attributes('type')).toBe('password')
    expect(view.find('#reset-password').attributes('autocomplete')).toBe('new-password')
  })
})
