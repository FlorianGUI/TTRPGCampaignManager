<script setup>
/*
 * Who you are, and everything you can do about it: the right-hand end of both
 * top bars (#79).
 *
 * This was three icon buttons — density, theme, sign out — and the bar had
 * accumulated one control per decision until it carried six that between them
 * never said who was signed in. Now it says the one thing that was missing and
 * hides the rest behind it.
 *
 * Still shared by `AppShell` inside a campaign and `BareLayout` on the way in,
 * for the reason it was extracted in the first place: a duplicated copy is how a
 * sign-out ends up with a different label, or a touch target, in one bar and not
 * the other. The campaign is the only thing that differs between them, so it
 * arrives as a prop and the menu grows two items — it is not a second component.
 *
 * The campaign's *name* is not here. It is a label rather than an action, and it
 * belongs at the head of the nav it names — see `CampaignTitle`.
 *
 * ---- Sign out, and #25's rule about it ----
 *
 * #25 decided sign out must hold its place at every width: "an account you
 * cannot leave on a phone is worse than a cramped bar". That was written when
 * the alternative was *folding* it — dropping it from the row as the bar
 * narrowed, so that at some widths it was gone.
 *
 * It is in a menu now, which is a real change to that decision and worth saying
 * out loud rather than deleting. What the rule was protecting still holds: the
 * trigger holds its place at every width, it is the largest target in the bar
 * rather than the smallest, and sign out is always in the menu behind it. What
 * changed is that it costs one tap more — and buys back the thing #25 could not
 * have: sign out is no longer a 44px icon sitting next to another 44px icon,
 * which is how a thumb aiming at the theme toggle ends a session.
 */
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import { useThemeStore } from '../stores/theme.js'
import { useAuthStore } from '../stores/auth.js'
import { forgetCurrentCampaign } from '../stores/currentCampaign.js'
import { t } from '../i18n/index.js'

const props = defineProps({
  // The campaign you are in, or null on every page above one — which is what
  // `BareLayout` always passes.
  campaign: { type: Object, default: null },
})

const router = useRouter()

// storeToRefs keeps the value reactive; actions are taken off the store
// directly, which is the Pinia idiom and what plain destructuring would break.
const themeStore = useThemeStore()
const { theme } = storeToRefs(themeStore)
const { toggleTheme } = themeStore

const auth = useAuthStore()

const menu = ref(null)
const trigger = ref(null)
const open = ref(false)

const MENU_ID = 'chrome-actions-menu'

/*
 * Signing out revokes server-side before it clears anything locally — clearing
 * only the client would leave a working refresh cookie behind, which is the one
 * way to log out that does not log you out (#35).
 *
 * `POST /users/logout` answers 204 whether or not there was a session, so there
 * is no failure state to design here: no confirmation, no error affordance, no
 * disabled-while-pending. It ends the session on this device only — if the copy
 * ever says "everywhere", that is a different endpoint.
 */
async function signOut() {
  await auth.logOut()
  router.push({ name: 'login' })
}

/*
 * Leaving a campaign, unchanged from the × it replaced. Both halves matter:
 * navigating without forgetting would send you to a `/` that redirects straight
 * back into the campaign you just left, which is an exit nobody can use (see
 * `enterRememberedCampaign` in router/routes.js).
 */
function closeCampaign() {
  forgetCurrentCampaign()
  router.push({ name: 'home' })
}

function openSettings() {
  router.push({ name: 'campaign-settings', params: { campaignId: props.campaign.id } })
}

/*
 * One menu for everything you can *do*, which is why the campaign's actions are
 * here rather than beside its name in the sidebar. The name there is a label —
 * it says where you are; this says what you can do about it.
 *
 * The campaign items are added when there is a campaign and absent when there is
 * not — never present-and-dimmed. #59 argued that at length for the sidebar and
 * it holds here: a disabled item reads as broken rather than as
 * not-yet-available, and on `/` there is simply no campaign to close.
 *
 * "Switch theme" rather than the name of the theme it would switch to. Naming
 * the destination needs no state indicator, which is the argument for it, but it
 * reads as a place among a list of verbs. The icon carries the direction: a sun
 * in candlelight, a moon in parchment.
 */
const items = computed(() => [
  {
    label: t('chrome.switchTheme'),
    icon: theme.value === 'candlelight' ? 'pi pi-sun' : 'pi pi-moon',
    command: toggleTheme,
  },
  ...(props.campaign
    ? [
        { label: t('chrome.campaignSettings'), icon: 'pi pi-cog', command: openSettings },
        { label: t('chrome.closeCampaign'), icon: 'pi pi-times', command: closeCampaign },
      ]
    : []),
  { separator: true },
  { label: t('chrome.signOut'), icon: 'pi pi-sign-out', command: signOut },
])

/*
 * `open` is flipped here rather than read back from the menu's `show` event.
 * PrimeVue emits that from the overlay's transition hooks, so it arrives after
 * the animation — and `aria-expanded` describes what the button just did, not
 * what an animation has finished doing. A screen reader should not be told the
 * menu is closed while it is opening.
 *
 * `toggle` mirrors the call it makes: PrimeVue's own toggle opens a closed menu
 * and closes an open one, so flipping alongside it stays in step.
 */
function toggle(event) {
  menu.value.toggle(event)
  open.value = !open.value
}

/*
 * Everything that closes the menu without going through the trigger — Escape,
 * a click outside, choosing an item — lands here, so the flag cannot be left
 * saying "expanded" over a menu that is gone.
 *
 * Focus goes back to the trigger with it. That is the part of a popup menu that
 * is invisible until you are using a keyboard and then is the whole experience:
 * without it, Escape drops focus at the top of the document and the next Tab
 * starts the page again.
 */
function onHide() {
  open.value = false
  trigger.value?.$el?.focus()
}
</script>

<template>
  <div class="chrome-actions">
    <Button
      ref="trigger"
      class="chrome-actions__trigger"
      text
      :label="auth.user?.username"
      icon="pi pi-angle-down"
      icon-pos="right"
      aria-haspopup="menu"
      :aria-controls="MENU_ID"
      :aria-expanded="open"
      @click="toggle"
    />

    <Menu
      :id="MENU_ID"
      ref="menu"
      :model="items"
      popup
      class="chrome-actions__menu"
      @hide="onHide"
    />
  </div>
</template>

<style scoped>
.chrome-actions {
  display: flex;
  gap: var(--space-1);
}

/*
 * The trigger carries a name, so it is the one control in this bar that is not
 * an icon guessing game — and the widest, which is what makes it a comfortable
 * target without the 44px floor having to rescue it.
 */
.chrome-actions__trigger {
  font-family: var(--grimoire-font-display);
  letter-spacing: 0.02em;
  max-width: 12rem;
}

.chrome-actions__trigger :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/*
 * The same 44px floor AppNav sets, and it is a touch guideline rather than
 * anything to do with the density scale that used to shrink these (#79). A
 * finger is the same size whatever the spacing tokens say.
 *
 * Coarse pointers only: on a mouse the default size is comfortable, and forcing
 * 44px there would space the bar out for no one's benefit.
 */
@media (pointer: coarse) {
  .chrome-actions :deep(button) {
    min-height: 44px;
  }
}

/* The name is what gives at phone width; the chevron keeps the control
   recognisable as a menu, and the initial keeps it recognisable as a person. */
@media (max-width: 640px) {
  .chrome-actions__trigger {
    max-width: 8rem;
  }
}
</style>
