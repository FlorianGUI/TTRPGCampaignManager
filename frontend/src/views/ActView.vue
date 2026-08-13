<script setup>
/*
 * One act. The route; `GroupingPage` is what it is.
 *
 * A thin wrapper rather than a `:kind` in the path, because an act and a
 * sequence are two resources with two id spaces and the API spells them out that
 * way — a shared route would have to invent a discriminator the data does not
 * have.
 */
import { useRoute } from 'vue-router'
import GroupingPage from './GroupingPage.vue'

const route = useRoute()
</script>

<template>
  <GroupingPage :id="route.params.actId" :campaign-id="route.params.campaignId" kind="act" />
</template>
