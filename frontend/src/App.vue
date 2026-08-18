<script setup>
/*
 * Root component: the persistent shell, with the routed view inside it.
 *
 * The shell lives here rather than per-view so the top bar and sidebar are not
 * torn down and rebuilt on navigation — chrome frames the page, it isn't part
 * of it.
 *
 * Nothing renders until the boot refresh has settled (#34). A blank moment is
 * the right thing to show for a request that usually takes a fraction of a
 * second: a splash would flash more often than it would reassure, and rendering
 * the shell first means a signed-out user watches the campaign sidebar draw
 * before being sent to the login page.
 *
 * Settled has three answers rather than two, though. If boot never reached the
 * API there is no verdict — the guard has let the navigation stand instead of
 * sending anyone to /login (#68) — and what goes here is the reason, not the
 * app: drawing the shell around pages that cannot load anything would blame the
 * client for a server that is briefly away.
 */
import { computed, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import AppShell from './components/AppShell.vue'
import AuthLayout from './components/AuthLayout.vue'
import BareLayout from './components/BareLayout.vue'
import ServerUnreachable from './components/ServerUnreachable.vue'
import { useAuthStore } from './stores/auth.js'
import { useCampaignsStore } from './stores/campaigns.js'
import { sections } from './content/sample.js'
import { t } from './i18n/index.js'

const route = useRoute()
const auth = useAuthStore()
const campaigns = useCampaignsStore()

/*
 * Which chrome the current route wants. The shell is the default and the named
 * layouts are the exceptions, rather than every route having to declare one — a
 * page that says nothing gets the campaign frame, which is what all but a
 * handful of them want.
 *
 * One <component> rather than a v-if chain, so the `ready` gate is written once
 * instead of three times and cannot fall out of step with itself.
 */
const LAYOUTS = { auth: AuthLayout, bare: BareLayout }

const layout = computed(() => LAYOUTS[route.meta.layout] ?? AppShell)

/*
 * The campaign the top bar names, resolved from the path rather than from
 * storage — the URL is the truth about where you are, and storage only supplies
 * a default for `/` (#59).
 *
 * Loading is triggered here because this is where the id first becomes known,
 * and it costs nothing: `ensureLoaded` is single-flight, so arriving on a
 * campaign page shares the one request the guard or the chooser already made.
 * Until it lands, `byId` is null and the chip simply is not rendered yet.
 */
watchEffect(() => {
  if (route.params.campaignId) campaigns.ensureLoaded()
})

const campaign = computed(() =>
  route.params.campaignId ? campaigns.byId(route.params.campaignId) : null,
)

/*
 * Bound per layout rather than to both. AuthLayout and BareLayout declare no
 * props, so anything passed to them falls through onto their root element —
 * `sections` would land in the DOM as an attribute stringified from an array.
 *
 * `sections()` is called here rather than imported as a value: its labels are
 * copy, and a module-level array would have been built before the locale was
 * resolved. `meta.title` is a catalogue key for the same reason, so the nav is
 * handed the words rather than the key it marks the current page with.
 */
const layoutProps = computed(() =>
  route.meta.layout
    ? {}
    : {
        sections: sections(),
        active: route.meta.title ? t(route.meta.title) : null,
        campaign: campaign.value,
      },
)
</script>

<template>
  <!--
    The one place messages from `useWriteFailure` land, and outside the `ready`
    gate: it renders nothing until something is queued, and a toast that existed
    only once the session had settled would be a toast the boot itself could not
    use. It teleports to the body, so where it sits in this template decides
    nothing about where it appears (#111).
  -->
  <Toast />

  <template v-if="auth.ready">
    <ServerUnreachable v-if="!auth.reachable" />

    <component :is="layout" v-else v-bind="layoutProps">
      <RouterView />
    </component>
  </template>
</template>
