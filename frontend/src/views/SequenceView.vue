<script setup>
/*
 * One sequence. See `ActView` for why the two levels are two routes over one
 * component, and `GroupingPage` for the one thing this level adds: the sentence
 * that explains the word.
 */
import { useRoute } from 'vue-router'
import GroupingPage from './GroupingPage.vue'

const route = useRoute()
</script>

<template>
  <GroupingPage
    :id="route.params.sequenceId"
    :campaign-id="route.params.campaignId"
    kind="sequence"
  />
</template>
