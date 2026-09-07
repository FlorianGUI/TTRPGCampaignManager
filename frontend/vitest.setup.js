/*
 * The three DOM measurements jsdom does not implement, stubbed so the editor
 * can ask for them (#152).
 *
 * CodeMirror measures the text it has drawn — line heights, the width of a
 * character — on an animation frame after every update, and reaches for
 * `Range.getClientRects` to do it. jsdom implements `Range` and not that,
 * because it has no layout to report: every box in it is zero by zero.
 *
 * **Zeroes are the honest answer here, not a lie the tests are built on.**
 * Nothing under test depends on a measurement: what the field promises is that
 * the text reaching the model is the text that was typed, that a button writes
 * at the caret, and that the label is announced — all state, all checkable
 * without a pixel. The stub exists so that measuring *fails quietly* rather
 * than throwing out of a callback no test can catch, which is what an
 * unimplemented method does.
 *
 * Anything that genuinely needs layout — wrapping, the drawn box, where a
 * decoration lands — is checked in a browser by hand, and says so in #152.
 */
const EMPTY_RECT = {
  x: 0,
  y: 0,
  top: 0,
  right: 0,
  bottom: 0,
  left: 0,
  width: 0,
  height: 0,
  toJSON: () => ({}),
}

if (!Range.prototype.getClientRects) {
  Range.prototype.getClientRects = () => Object.assign([], { item: () => null })
  Range.prototype.getBoundingClientRect = () => ({ ...EMPTY_RECT })
}

/*
 * Observed, never measured: the editor watches its own element for a resize so
 * it can re-measure. jsdom fires no such thing, and CodeMirror skips the
 * observer entirely when the constructor is missing — which would leave the
 * code path that runs in every browser untested here. A no-op keeps it taken.
 */
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
