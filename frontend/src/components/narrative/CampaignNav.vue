<script setup>
/*
 * What the campaign holds directly, under its name in the sidebar.
 *
 * **Depth one, not "the acts."** The campaign's own children are acts *and* any
 * scene hanging off the campaign itself, in `position` order together — which is
 * what makes a one-shot work with no special case: its sidebar is a list of
 * scenes and nothing had to be written for it. Sequences that skip the act level
 * are left to the structure page, where there is room for three kinds at one
 * indent; in a 15rem column they would read as a mess.
 *
 * It stops there because three levels do not fit. The column is narrower than a
 * lot of campaign names — which is why `CampaignTitle` has a `ResizeObserver` at
 * all — and a scene title at two indents would have a few characters left.
 *
 * Its own component rather than another section handed to `AppNav`, because
 * `AppNav` is a list of links with no opinion about what is in it, and progress
 * derived from scenes is very much an opinion. Keeping it here means the generic
 * nav stays generic and this stays readable.
 *
 * Rendered in both the sidebar and the drawer, like everything else in the nav,
 * so the campaign's shape is reachable at every width.
 */
import { computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ActProgress from './ActProgress.vue'
import SceneStatus from './SceneStatus.vue'
import { actProgress, useStructureStore, titleOf } from '../../stores/structure.js'

const props = defineProps({
  campaign: { type: Object, required: true },
})

defineEmits(['navigate'])

const structure = useStructureStore()

/*
 * Fetched here because this is on every campaign route, and `ensureLoaded` is
 * single-flight — arriving on the structure page shares the one request this
 * already made rather than doubling it.
 */
watch(
  () => props.campaign.id,
  (id) => structure.ensureLoaded(id),
  { immediate: true },
)

const children = computed(() => structure.childrenOf(props.campaign.id))

const tree = computed(() => structure.treeFor(props.campaign.id))

const progressOf = (act) => actProgress(tree.value, act)

/*
 * Each child leads to its own page rather than to the outline. Landing on the
 * structure and then having to find the act you just clicked is the journey this
 * removes — the outline is one click away from there for whoever wants it.
 */
const to = ({ kind, node }) =>
  kind === 'act'
    ? { name: 'campaign-act', params: { campaignId: props.campaign.id, actId: node.id } }
    : { name: 'campaign-scene', params: { campaignId: props.campaign.id, sceneId: node.id } }
</script>

<template>
  <ul v-if="children.length" class="campaign-nav">
    <li v-for="child in children" :key="child.node.id">
      <RouterLink
        class="nav__item"
        :class="{ 'nav__item--scene': child.kind === 'scene' }"
        :to="to(child)"
        :title="titleOf(child.node, child.kind)"
        @click="$emit('navigate')"
      >
        <!--
          Ahead of the title, not after it. The titles here are ellipsised at a
          15rem column, so a trailing dot sat at a different distance from the
          left on every row and read as scattered; leading, they are a column an
          eye can run down, which is the whole reason for using a dot.
        -->
        <ActProgress v-if="child.kind === 'act'" :progress="progressOf(child.node)" />
        <SceneStatus v-else :status="child.node.status" readonly />

        <span class="nav__item-label">{{ titleOf(child.node, child.kind) }}</span>

        <!--
          A scene at this level belongs to no act, and the marker says so: at a
          glance it is otherwise indistinguishable from an act with no scenes.
        -->
        <span
          v-if="child.kind === 'scene'"
          class="nav__item-loose"
          aria-hidden="true"
          title="In no act"
          >↳</span
        >
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.campaign-nav {
  list-style: none;
  margin: 0 0 var(--space-4);
  padding: 0;
}

/*
 * Deliberately the same shape as `AppNav`'s items — this is one list to a
 * reader, and the fact that it is two components is an implementation detail
 * they should never be able to see.
 */
.nav__item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.35rem var(--space-2);
  border-radius: var(--p-border-radius-sm);
  border-left: 2px solid transparent;
  font-size: var(--step--1);
  color: var(--p-navigation-item-color);
  text-decoration: none;
  transition:
    background var(--p-transition-duration),
    color var(--p-transition-duration);
}

.nav__item:hover {
  background: var(--p-navigation-item-hover-background);
  color: var(--p-navigation-item-hover-color);
}

.nav__item:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: calc(-1 * var(--p-focus-ring-width));
}

/* RouterLink supplies this class for the page being read; it is styled like
   Library's active entry so the two lists remain one navigation. */
.nav__item.router-link-active {
  color: var(--p-primary-color);
  border-left-color: var(--p-primary-color);
  background: var(--p-navigation-item-active-background);
  font-weight: 600;
}

.nav__item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav__item-loose {
  flex: none;
  font-family: var(--grimoire-font-mono);
  color: var(--p-grimoire-rule-color);
}

@media (pointer: coarse) {
  .nav__item {
    min-height: 44px;
    padding-block: var(--space-2);
    font-size: var(--step-0);
  }
}
</style>
