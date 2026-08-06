import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from './App.vue'
import AppShell from './components/AppShell.vue'
import { useAuthStore } from './stores/auth.js'

/*
 * The first render waits for the boot refresh (#34). Without the gate a
 * returning user watches the shell draw, then the login page, then the page
 * they were actually on — and the fix for that flash is easy to remove by
 * accident, because everything still works without it.
 */

function mountApp() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'home', component: { template: '<div />' } }],
  })
  return mount(App, {
    global: { plugins: [router], stubs: { AppShell: true, RouterView: true } },
  })
}

describe('App', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders nothing until the session has been restored', () => {
    useAuthStore().ready = false

    expect(mountApp().findComponent(AppShell).exists()).toBe(false)
  })

  it('renders the shell once boot has settled', async () => {
    const auth = useAuthStore()
    auth.ready = false
    const app = mountApp()

    auth.ready = true
    await app.vm.$nextTick()

    expect(app.findComponent(AppShell).exists()).toBe(true)
  })

  it('renders the shell for a signed-out visitor too', async () => {
    /* Boot settling is not the same as being signed in. Gating on the wrong one
     * would leave a first-time visitor on a blank page for ever — the login
     * page in #10 has to be able to render. */
    const auth = useAuthStore()
    auth.ready = true

    expect(auth.isSignedIn).toBe(false)
    expect(mountApp().findComponent(AppShell).exists()).toBe(true)
  })
})
