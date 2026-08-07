import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from './App.vue'
import AppShell from './components/AppShell.vue'
import AuthLayout from './components/AuthLayout.vue'
import { useAuthStore } from './stores/auth.js'

/*
 * The first render waits for the boot refresh (#34). Without the gate a
 * returning user watches the shell draw, then the login page, then the page
 * they were actually on — and the fix for that flash is easy to remove by
 * accident, because everything still works without it.
 */

/*
 * Awaits the router before mounting. Until the first navigation resolves,
 * `route.meta` is the empty meta of START_LOCATION — so a layout chosen from it
 * would always be the default, and the auth cases below would pass for the
 * wrong reason.
 */
async function mountApp({ meta = {} } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', name: 'home', component: { template: '<div />' }, meta }],
  })

  router.push('/')
  await router.isReady()

  return mount(App, {
    global: { plugins: [router], stubs: { AppShell: true, AuthLayout: true, RouterView: true } },
  })
}

describe('App', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders nothing until the session has been restored', async () => {
    useAuthStore().ready = false

    expect((await mountApp()).findComponent(AppShell).exists()).toBe(false)
  })

  it('renders the shell once boot has settled', async () => {
    const auth = useAuthStore()
    auth.ready = false
    const app = await mountApp()

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
    expect((await mountApp()).findComponent(AppShell).exists()).toBe(true)
  })

  describe('choosing the chrome', () => {
    /*
     * The shell's sidebar navigates a campaign, which is exactly what someone
     * who has not signed in does not have. A login page inside it would offer a
     * nav where every item is a dead end.
     */
    beforeEach(() => {
      useAuthStore().ready = true
    })

    it('gives a route asking for the auth layout the bare chrome', async () => {
      const app = await mountApp({ meta: { layout: 'auth' } })

      expect(app.findComponent(AuthLayout).exists()).toBe(true)
      expect(app.findComponent(AppShell).exists()).toBe(false)
    })

    it('defaults to the shell, so a page that says nothing is framed as usual', async () => {
      const app = await mountApp()

      expect(app.findComponent(AppShell).exists()).toBe(true)
      expect(app.findComponent(AuthLayout).exists()).toBe(false)
    })

    it('does not leak the shell’s props onto the auth layout', async () => {
      // AuthLayout declares no props, so anything passed lands on its root
      // element — `sections` would arrive in the DOM as a stringified array.
      const app = await mountApp({ meta: { layout: 'auth' } })

      expect(app.findComponent(AuthLayout).attributes('sections')).toBeUndefined()
    })
  })
})
