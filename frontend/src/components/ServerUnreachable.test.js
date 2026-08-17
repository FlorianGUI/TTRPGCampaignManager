import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ServerUnreachable from './ServerUnreachable.vue'
import { useAuthStore } from '../stores/auth.js'

function mountNotice() {
  return mount(ServerUnreachable, { global: { plugins: [PrimeVue] } })
}

describe('ServerUnreachable', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('says the session is intact, because it is', async () => {
    /*
     * The whole point of not redirecting to /login (#68). Somebody who is told
     * nothing assumes they have been signed out and signs in again — which is
     * exactly what this change exists to stop being necessary.
     */
    const text = mountNotice().text()

    expect(text).toContain('not been signed out')
  })

  it('asks again when told to, rather than needing a reload', async () => {
    const auth = useAuthStore()
    vi.spyOn(auth, 'retryBoot').mockResolvedValue()

    const view = mountNotice()
    await view.find('button').trigger('click')

    expect(auth.retryBoot).toHaveBeenCalled()
  })
})
