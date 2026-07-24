<script setup>
/*
 * Root component: the persistent shell, with the routed view inside it.
 *
 * The shell lives here rather than per-view so the top bar and sidebar are not
 * torn down and rebuilt on navigation — chrome frames the page, it isn't part
 * of it.
 */
import { useRoute } from 'vue-router'
import AppShell from './components/AppShell.vue'
import { sections } from './content/sample.js'

const route = useRoute()
</script>

<template>
  <AppShell :sections="sections" :active="route.meta.title">
    <RouterView />
  </AppShell>
</template>
