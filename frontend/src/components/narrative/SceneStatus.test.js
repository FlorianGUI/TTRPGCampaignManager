import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Tooltip from 'primevue/tooltip'
import SceneStatus from './SceneStatus.vue'

/*
 * The dot on a scene: what it says, and what pressing it does.
 *
 * Marking prep off is something a game master does forty times while working
 * through an act, which is why it is one press from the outline rather than a
 * page each time.
 */

function render(props) {
  return mount(SceneStatus, { props, global: { directives: { tooltip: Tooltip } } })
}

const dot = (wrapper) => wrapper.get('.status__dot')

describe('a scene’s status', () => {
  it('cycles to do → done → cut → to do', async () => {
    /*
     * A loop, not a line: a scene brought back from the cut pile takes one press
     * rather than three, and there is never an end of the list to notice.
     */
    for (const [from, to] of [
      ['planned', 'done'],
      ['done', 'skipped'],
      ['skipped', 'planned'],
    ]) {
      const wrapper = render({ status: from })

      await dot(wrapper).trigger('click')

      expect(wrapper.emitted('cycle')[0]).toEqual([to])
    }
  })

  it('says what pressing it will do, not only what it is', async () => {
    // The next state is the thing worth knowing before pressing; the current one
    // is already visible in the dot.
    expect(dot(render({ status: 'planned' })).attributes('aria-label')).toBe('to do — set to done')
  })

  it('calls a cut scene cut rather than skipped', () => {
    // The stored value is unchanged; `skipped` is a word about a process and
    // `cut` is what a game master calls the scene.
    expect(render({ status: 'skipped', withLabel: true }).text()).toBe('cut')
  })

  it('is a plain mark where something else already sets it', async () => {
    /*
     * The scene's own page shows this beside a Select that sets the same field.
     * Two controls for one value is one too many, and the quieter one should not
     * be the one that also works.
     */
    const wrapper = render({ status: 'planned', readonly: true })

    expect(wrapper.find('button').exists()).toBe(false)
    expect(dot(wrapper).attributes('role')).toBe('img')
    expect(dot(wrapper).attributes('aria-label')).toBe('to do')
  })

  it('does not carry the row it sits in along with the press', async () => {
    // Every outline row is a link to its own page. Without stopping the event,
    // marking a scene off would navigate away from the list being worked through.
    const wrapper = render({ status: 'planned' })

    await dot(wrapper).trigger('click')

    expect(wrapper.emitted('cycle')).toHaveLength(1)
  })
})
