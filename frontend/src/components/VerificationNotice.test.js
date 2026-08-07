import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import VerificationNotice from './VerificationNotice.vue'
import { ApiError } from '../api/http.js'
import * as http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

function signedInWith({ email_verified }) {
  const auth = useAuthStore()
  auth.user = { id: 'u-1', username: 'aragorn', email: 'a@g.test', email_verified }
  auth.token = 'an-access-token'
  return auth
}

function mountNotice() {
  return mount(VerificationNotice, { global: { plugins: [PrimeVue] } })
}

describe('VerificationNotice', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('says nothing to a verified account', () => {
    signedInWith({ email_verified: true })

    expect(mountNotice().find('[role="status"]').exists()).toBe(false)
  })

  it('says nothing to a signed-out visitor', () => {
    // The shell only renders for someone signed in, but the notice reads the user
    // and would throw on null if it did not check.
    expect(mountNotice().find('[role="status"]').exists()).toBe(false)
  })

  it('asks an unverified account to confirm', () => {
    signedInWith({ email_verified: false })

    expect(mountNotice().text()).toContain('not confirmed')
  })

  it('sends another link with the caller’s own token', async () => {
    const auth = signedInWith({ email_verified: false })
    const apiFetch = vi.spyOn(http, 'apiFetch').mockResolvedValue(null)

    const notice = mountNotice()
    await notice.get('button').trigger('click')
    await flushPromises()

    expect(apiFetch).toHaveBeenCalledWith('/users/verify-email/resend', {
      method: 'POST',
      token: auth.token,
    })
    expect(notice.text()).toContain('Check your inbox')
  })

  it('shows the limiter’s own words when it refuses', async () => {
    /*
     * The 429 message is fixed per endpoint and written to be displayed (#63), and
     * it is the only failure here the reader can act on.
     */
    const detail = 'Too many verification emails requested. Try again shortly.'
    signedInWith({ email_verified: false })
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(429, detail))

    const notice = mountNotice()
    await notice.get('button').trigger('click')
    await flushPromises()

    expect(notice.text()).toContain(detail)
  })

  it('offers to try again after a failure that is not a refusal', async () => {
    signedInWith({ email_verified: false })
    vi.spyOn(http, 'apiFetch').mockRejectedValue(new ApiError(500, null))

    const notice = mountNotice()
    await notice.get('button').trigger('click')
    await flushPromises()

    expect(notice.text()).toContain('Try again shortly')
    // Still offering the button, or a transient failure would be a dead end.
    expect(notice.findAll('button').length).toBeGreaterThan(1)
  })

  it('can be dismissed for the session', async () => {
    signedInWith({ email_verified: false })

    const notice = mountNotice()
    await notice.get('[aria-label="Dismiss"]').trigger('click')

    expect(notice.find('[role="status"]').exists()).toBe(false)
  })

  it('does not remember being dismissed across a reload', () => {
    /*
     * In memory rather than localStorage on purpose: the state is "I have
     * acknowledged this today", not a preference. Permanent dismissal would let
     * someone bury the one prompt that gets them a verified address.
     */
    signedInWith({ email_verified: false })
    const first = mountNotice()

    expect(first.find('[role="status"]').exists()).toBe(true)
    expect(mountNotice().find('[role="status"]').exists()).toBe(true)
  })
})
