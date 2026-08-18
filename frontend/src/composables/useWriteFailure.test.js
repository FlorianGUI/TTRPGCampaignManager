import { describe, it, expect, afterEach, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import Toast from 'primevue/toast'
import { couldNotSave, useWriteFailure } from './useWriteFailure.js'

/*
 * The real service and a real `<Toast />`, because the thing worth asserting is
 * that a refused write ends up somewhere a person can see. Everywhere else the
 * toast is a fake — those tests ask whether a call site reports at all, which is
 * a different question and one a mock answers honestly.
 *
 * `<Toast />` is teleported to the body, which is why these read `document`
 * rather than the wrapper.
 */
const Harness = defineComponent({
  setup() {
    const { failed } = useWriteFailure()
    return { failed }
  },
  render() {
    return h('div', [h(Toast), h('button', { onClick: this.failed }, 'break it')])
  },
})

function render() {
  return mount(Harness, { global: { plugins: [PrimeVue, ToastService] } })
}

describe('useWriteFailure', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('puts the failure on screen, which the console was not', async () => {
    /*
     * The whole of #111 in one assertion. Before this, a refused move, add,
     * delete or status change left an uncaught `ApiError` in a console no game
     * master has open, and nothing else at all.
     */
    const wrapper = render()

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(document.body.textContent).toContain(couldNotSave())
  })

  it('announces it, so it is not for sighted users alone', async () => {
    // PrimeVue gives the message `role="alert"` and `aria-live="assertive"`.
    // Worth an assertion rather than an assumption: the message appears after
    // the fact, so without it there is nothing to announce and no way to say so.
    const wrapper = render()

    await wrapper.find('button').trigger('click')
    await nextTick()

    expect(document.querySelector('[role="alert"]')?.textContent).toContain(couldNotSave())
  })

  it('stays put rather than fading', async () => {
    /*
     * No `life`, so PrimeVue starts no timer. A message that fades is the
     * easiest one in any app to miss, and this one is saying that the screen is
     * not what was asked for. A minute is far past any toast default.
     */
    vi.useFakeTimers()
    const wrapper = render()

    await wrapper.find('button').trigger('click')
    await nextTick()
    vi.advanceTimersByTime(60_000)
    await nextTick()

    expect(document.body.textContent).toContain(couldNotSave())
    vi.useRealTimers()
  })

  it('says our sentence and nothing besides', async () => {
    /*
     * `failed` takes no argument, which is the structural half of this: there is
     * no door for a pydantic message or a 500's body to come through. This is
     * the other half — nothing is appended to what we chose to say (#102 settled
     * the reasoning for the sign-up form).
     */
    const wrapper = render()

    await wrapper.find('button').trigger('click')
    await nextTick()

    const alert = document.querySelector('[role="alert"]')
    expect(alert.textContent.replace(/\s+/g, ' ').trim()).toBe(couldNotSave())
  })
})
