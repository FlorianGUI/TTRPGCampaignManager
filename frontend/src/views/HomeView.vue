<script setup>
/*
 * The chooser: which table are you running?
 *
 * This is the screen a signed-in game master lands on, and the whole of what
 * `/` is now — `SpikeView` moved to `/campaigns/:campaignId/sessions`, where it
 * goes on standing in for session notes until that context exists.
 *
 * Campaigns and sources are the only two things in the app that belong to the
 * *user* rather than to a campaign, which is why they are peers here and
 * nowhere else. Two calls, two stores, no aggregate endpoint: the pairing is a
 * fact about this screen, not about the API.
 *
 * You do not usually see this page. `/` redirects into the remembered campaign
 * before it renders (see `enterRememberedCampaign` in router/routes.js), so
 * arriving here means there is deliberately nothing to remember — you just
 * signed in, or you just left a campaign. That is also why no card is marked as
 * current: the only one that could be is the one you are pointedly not in.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import CampaignForm from '../components/CampaignForm.vue'
import { useAuthStore } from '../stores/auth.js'
import { useCampaignsStore } from '../stores/campaigns.js'
import { useSourcesStore } from '../stores/sources.js'
import { rememberCurrentCampaign } from '../stores/currentCampaign.js'

const router = useRouter()
const auth = useAuthStore()
const campaigns = useCampaignsStore()
const sources = useSourcesStore()

/*
 * Both are already in flight when this mounts on the common path: the route
 * guard asks for campaigns before it decides whether to redirect here at all.
 * `ensureLoaded` is single-flight, so this joins that request rather than
 * making a second — and still starts one on the paths where the guard did not
 * (a fresh account, or arriving with nothing remembered).
 */
onMounted(() => {
  campaigns.ensureLoaded()
  sources.ensureLoaded()
})

/*
 * The empty state waits on `loaded`, never on "the list is empty".
 *
 * A request that has not answered yet and an account with no campaigns look
 * identical in the data and mean opposite things — showing "start your first
 * campaign" to someone who owns three, for the half second before the response
 * lands, is the kind of lie that makes a page feel broken.
 */
const isEmpty = computed(() => campaigns.loaded && campaigns.items.length === 0)

/* Initials for the card's sigil. Spread rather than `[0]`, so a name starting
 * with an astral character is not cut in half. */
function sigil(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => [...word][0])
    .join('')
    .toUpperCase()
}

/*
 * Choosing and entering are one gesture — there is no select-then-open — and
 * remembering happens on the way through rather than on a separate control.
 *
 * A real link, not a button: the id is in the URL, so middle-click and
 * open-in-new-tab do the right thing, and the new tab carries the campaign
 * without needing anything in storage.
 */
function campaignRoute(campaign) {
  return { name: 'campaign-sessions', params: { campaignId: campaign.id } }
}

function remember(campaign) {
  rememberCurrentCampaign(campaign.id)
}

/* ---- Creating -------------------------------------------------------- */

/*
 * A dialog, still, and deliberately: #59 put it here because "create your first
 * campaign" is this screen's primary action, and a primary action that leads
 * somewhere else is a worse answer to an empty state than one that resolves in
 * place. Creating is short, it is not resumed, and nobody reloads half way
 * through — the arguments that made *editing* a page (#49) do not carry over.
 *
 * What did change is the body: the fields are `CampaignForm`, the same component
 * the settings page uses. It keeps this dialog and that page from drifting
 * apart, and it is what gives creating the per-field 422 handling #49 asked for.
 *
 * Managing a campaign is not here at all. Editing and deleting live inside the
 * campaign, on the settings route reached from the top bar — this screen is for
 * choosing a table, and the one you want to rename is one click away in it.
 */
const dialogOpen = ref(false)
const failure = ref(null)
const submitting = ref(false)

function openDialog() {
  failure.value = null
  dialogOpen.value = true
}

async function create(values) {
  submitting.value = true
  failure.value = null

  try {
    const campaign = await campaigns.create(values)

    // Straight in. You just made it; being returned to a list to find it again
    // would be a step for its own sake.
    rememberCurrentCampaign(campaign.id)
    dialogOpen.value = false
    router.push(campaignRoute(campaign))
  } catch (error) {
    failure.value = error
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="home">
    <!-- ---- Campaigns ------------------------------------------------ -->

    <template v-if="campaigns.error && !campaigns.loaded">
      <h1 class="home__title">We could not reach your campaigns</h1>
      <p class="home__lede" role="alert">
        The app is signed in, so this is the connection rather than your account.
      </p>
      <Button class="home__retry" label="Try again" @click="campaigns.reload()" />
    </template>

    <template v-else-if="isEmpty">
      <h1 class="home__title">Welcome, {{ auth.user?.username }}</h1>
      <p class="home__lede">One thing to do first.</p>

      <div class="home__empty">
        <i class="pi pi-th-large home__empty-icon" aria-hidden="true" />
        <h2>Start your first campaign</h2>
        <p>
          A campaign holds your session notes, your factions, your locations and the people at your
          table. Everything else in here hangs off one.
        </p>
        <Button label="Create a campaign" icon="pi pi-plus" @click="openDialog" />
      </div>
    </template>

    <template v-else>
      <h1 class="home__title">Which table are you running?</h1>
      <p class="home__lede">Everything else lives inside a campaign.</p>

      <p v-if="campaigns.loading && !campaigns.loaded" class="home__waiting">
        Fetching your campaigns…
      </p>

      <ul v-else class="home__grid">
        <li v-for="campaign in campaigns.items" :key="campaign.id">
          <RouterLink class="card" :to="campaignRoute(campaign)" @click="remember(campaign)">
            <span class="card__sigil" aria-hidden="true">{{ sigil(campaign.name) }}</span>
            <span class="card__name">{{ campaign.name }}</span>
            <span v-if="campaign.description" class="card__description">
              {{ campaign.description }}
            </span>
          </RouterLink>
        </li>

        <li>
          <button type="button" class="card card--new" @click="openDialog">
            <i class="pi pi-plus" aria-hidden="true" />
            <span>New campaign</span>
          </button>
        </li>
      </ul>
    </template>

    <!-- ---- Sources -------------------------------------------------- -->

    <!--
      Read-only, and rendered only when there is something to show. Until #51
      there is no way to add one from here, and an empty shelf with no action
      under it is a dead end wearing a heading. #50 owns the view these will
      eventually link to.
    -->
    <template v-if="sources.items.length">
      <hr class="rule-fleuron" />

      <section class="shelf" aria-labelledby="home-sources">
        <h2 id="home-sources" class="label-smallcaps shelf__label">Your sources</h2>

        <ul class="shelf__row">
          <li v-for="source in sources.items" :key="source.id" class="chip">
            <i class="pi pi-book" aria-hidden="true" />
            <span>{{ source.title }}</span>
          </li>
        </ul>

        <p class="shelf__note">
          Sources belong to you, not to a campaign — every campaign you run can see all of them.
        </p>
      </section>
    </template>

    <!-- ---- Create --------------------------------------------------- -->

    <Dialog v-model:visible="dialogOpen" modal header="New campaign" class="home__dialog">
      <CampaignForm
        class="home__form"
        submit-label="Create campaign"
        :busy="submitting"
        :error="failure"
        @submit="create"
      />
    </Dialog>
  </div>
</template>

<style scoped>
.home__title {
  margin: 0 0 var(--space-1);
  text-align: center;
}

.home__lede {
  margin: 0 0 var(--space-6);
  text-align: center;
  color: var(--p-text-muted-color);
}

.home__waiting {
  text-align: center;
  color: var(--p-text-muted-color);
}

/* ---- The grid --------------------------------------------------- */

.home__grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
  gap: var(--space-3);
}

.home__grid > li {
  display: flex;
}

/*
 * `color` and `text-decoration` are set rather than inherited on purpose. The
 * `app` layer's anchor rule wins over the primevue layer (see frontend/README.md),
 * so a link that does not say otherwise is painted in the accent and underlined
 * — which on a card means an accent-coloured heading and a rule through it.
 */
.card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-4);
  text-align: left;
  color: var(--p-text-color);
  text-decoration: none;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  transition:
    border-color var(--p-transition-duration),
    background var(--p-transition-duration);
}

.card:hover {
  border-color: var(--p-primary-color);
  background: var(--p-content-hover-background);
}

.card:focus-visible {
  outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  outline-offset: var(--p-focus-ring-offset);
}

.card__sigil {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  margin-bottom: var(--space-2);
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  color: var(--p-primary-color);
  background: var(--p-grimoire-chrome-raised-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
}

.card__name {
  font-family: var(--grimoire-font-display);
  font-weight: 700;
  font-size: var(--step-1);
  line-height: 1.2;
}

.card__description {
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
}

.card--new {
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 9rem;
  font-family: var(--grimoire-font-body);
  font-size: var(--step-0);
  color: var(--p-primary-color);
  background: transparent;
  border-style: dashed;
  cursor: pointer;
}

/* ---- Empty state ------------------------------------------------ */

.home__empty {
  padding: var(--space-7) var(--space-5);
  text-align: center;
  border: 1px dashed var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
}

.home__empty-icon {
  font-size: 1.6rem;
  color: var(--p-primary-color);
}

.home__empty h2 {
  margin: var(--space-3) 0 var(--space-2);
  font-size: var(--step-2);
}

.home__empty p {
  max-width: 34rem;
  margin: 0 auto var(--space-5);
  color: var(--p-text-muted-color);
}

/* ---- Sources shelf ---------------------------------------------- */

.shelf__label {
  margin: 0 0 var(--space-3);
}

.shelf__row {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem var(--space-3);
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-sm);
}

.chip .pi {
  font-size: 0.8em;
  color: var(--p-grimoire-context-library);
}

.shelf__note {
  margin: var(--space-3) 0 0;
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
}

/* ---- Create form ------------------------------------------------ */

/* The form sizes itself to the page it is on; in a dialog it needs a floor, or
   it collapses to the width of its own labels. */
.home__form {
  min-width: min(22rem, 70vw);
}
</style>
