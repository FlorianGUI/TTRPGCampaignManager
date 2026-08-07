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
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/AppShell.vue'
import AuthLayout from './components/AuthLayout.vue'
import { useAuthStore } from './stores/auth.js'
import { sections } from './content/sample.js'

const route = useRoute()
const auth = useAuthStore()

/*
 * Which chrome the current route wants. The shell is the default and `auth` is
 * the exception, rather than every route having to declare one — a page that
 * says nothing gets the campaign frame, which is what all but two of them want.
 *
 * One <component> rather than a v-if pair, so the `ready` gate is written once
 * instead of twice and cannot fall out of step with itself.
 */
const isAuthLayout = computed(() => route.meta.layout === 'auth')
const layout = computed(() => (isAuthLayout.value ? AuthLayout : AppShell))

/*
 * Bound per layout rather than to both. AuthLayout declares no props, so
 * anything passed to it falls through onto its root element — `sections` would
 * land in the DOM as an attribute stringified from an array.
 */
const layoutProps = computed(() =>
  isAuthLayout.value ? {} : { sections, active: route.meta.title },
)
</script>

<template>
  <component :is="layout" v-if="auth.ready" v-bind="layoutProps">
    <RouterView />
  </component>
</template>
