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
import { useRoute } from 'vue-router'
import AppShell from './components/AppShell.vue'
import { useAuthStore } from './stores/auth.js'
import { sections } from './content/sample.js'

const route = useRoute()
const auth = useAuthStore()
</script>

<template>
  <AppShell v-if="auth.ready" :sections="sections" :active="route.meta.title">
    <RouterView />
  </AppShell>
</template>
