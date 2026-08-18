import { useToast } from 'primevue/usetoast'
import { t } from '../i18n/index.js'

/*
 * The one sentence the app says when a write is refused.
 *
 * Exported because three places say it — this, `SceneView` and `GroupingPage` —
 * and #111 is as much a complaint about four different answers to one status as
 * it is about the outline's silence. The two forms keep their own `failure` ref:
 * they have somewhere to put a message, beside the thing being saved, and that
 * same ref carries "Give it a title.", which is not a write failure at all. What
 * they stop having is their own wording.
 *
 * It says nothing about why. The API's own detail is written for whoever wrote
 * the request rather than for whoever is using the app — #102 settled that
 * reasoning for the sign-up form, and nothing about it is specific to signing up.
 */
/* A function, not a constant: a constant would be built at import time, before
   `main.js` has resolved the locale, and would be English for the rest of the
   session. */
export const couldNotSave = () => t('write.failed')

/*
 * Telling someone that what they just asked for did not happen.
 *
 * The outline's writes come from a menu and a plus rather than from a form, so a
 * refused move, add, rename, delete or status change has nowhere on the page to
 * report to. Before this they were `try`/`finally` with no `catch`: the spinner
 * stopped, the row stayed where it was, and the only trace was an uncaught
 * `ApiError` in a console no game master has open (#111).
 *
 * A toast rather than a banner on the page, and that is a decision about the
 * app's voice as much as about this bug. An outline runs long: the control that
 * failed is often nowhere near the top of it, and a message up there is a message
 * about something you cannot see. This one appears where the eye already is, and
 * the same words follow the same controls onto the act and sequence pages, which
 * host them too.
 *
 * **Sticky, deliberately.** A toast that fades is the easiest message in any app
 * to miss, and this one is saying that the screen is not what was asked for. It
 * carries its own close button, and nothing here times out, which is also the
 * short way past WCAG 2.2.1.
 */
export function useWriteFailure() {
  const toast = useToast()

  /*
   * Takes no argument on purpose. Every caller has the error in hand and none of
   * them may show it, so accepting one would be offering a door that must stay
   * shut. If a status ever earns its own sentence — a 404 meaning the row is
   * already gone, say — it is one parameter away, added deliberately.
   */
  function failed() {
    toast.add({ severity: 'error', summary: couldNotSave() })
  }

  return { failed }
}
