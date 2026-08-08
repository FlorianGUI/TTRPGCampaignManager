<script setup>
/*
 * The account end of the chrome: density, theme, sign out.
 *
 * Shared by the two top bars — `AppShell` inside a campaign and `BareLayout` on
 * the way in — because these three do the same thing on both and a duplicated
 * copy is how a sign-out ends up with a different label, or a touch target, in
 * one of them and not the other.
 *
 * What is *not* here is anything either bar owns alone: the drawer toggle, the
 * search field, the campaign chip. This is the tail of the row, in the order
 * issue #25 settled — sign out last, because it is the most consequential and
 * least frequent control in the bar, and it should not sit where a thumb
 * reaching for the theme toggle lands.
 */
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useThemeStore } from '../stores/theme.js'
import { useAuthStore } from '../stores/auth.js'

// storeToRefs keeps the two values reactive; actions are taken off the store
// directly, which is the Pinia idiom and what plain destructuring would break.
const themeStore = useThemeStore()
const { theme, density } = storeToRefs(themeStore)
const { toggleTheme, toggleDensity } = themeStore

/*
 * Signing out revokes server-side before it clears anything locally — clearing
 * only the client would leave a working refresh cookie behind, which is the one
 * way to log out that does not log you out (#35).
 *
 * `POST /users/logout` answers 204 whether or not there was a session, so there
 * is no failure state to design here: no confirmation dialog, no error
 * affordance, no disabled-while-pending. It ends the session on this device
 * only — if the copy ever says "everywhere", that is a different endpoint.
 */
const auth = useAuthStore()
const router = useRouter()

async function signOut() {
  await auth.logOut()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="chrome-actions">
    <!--
      Density is a pointer-precision affordance: compact shrinks targets that are
      already at the 44px floor on touch, so it is not offered there (issue #25).
    -->
    <Button
      class="chrome-actions__density"
      text
      rounded
      :icon="density === 'compact' ? 'pi pi-bars' : 'pi pi-align-justify'"
      :aria-label="`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} density`"
      :title="`Density: ${density}`"
      @click="toggleDensity"
    />
    <Button
      text
      rounded
      :icon="theme === 'candlelight' ? 'pi pi-sun' : 'pi pi-moon'"
      :aria-label="`Switch to ${theme === 'candlelight' ? 'parchment' : 'candlelight'} theme`"
      :title="`Theme: ${theme}`"
      @click="toggleTheme"
    />
    <Button
      class="chrome-actions__sign-out"
      text
      rounded
      icon="pi pi-sign-out"
      aria-label="Sign out"
      title="Sign out"
      @click="signOut"
    />
  </div>
</template>

<style scoped>
.chrome-actions {
  display: flex;
  gap: var(--space-1);
}

/*
 * The same 44px floor AppNav sets. These are icon-only targets with no label to
 * widen them, so they are the smallest things in the chrome — and sign out is
 * among them, which is not a control to make people aim at twice.
 *
 * Coarse pointers only: on a mouse the default size is comfortable, and forcing
 * 44px there would space the bar out for no one's benefit.
 */
@media (pointer: coarse) {
  .chrome-actions :deep(button) {
    min-height: 44px;
    min-width: 44px;
  }

  .chrome-actions__density {
    display: none;
  }
}
</style>
