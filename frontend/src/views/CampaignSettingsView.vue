<script setup>
/*
 * A campaign's own settings: rename it, redescribe it, or take it off the shelf.
 *
 * A route rather than a dialog, which is the whole of #49's first decision.
 * Editing is the case that decides it: it is interrupted, reloaded, bookmarked
 * and opened in a second tab far more often than creating is, and a dialog is
 * none of those things — it is a modal on top of whichever page happened to be
 * underneath, and a reload throws the edit away and lands somewhere else.
 *
 * It lives inside the campaign frame (no `meta.layout`), so the top bar names
 * the campaign being edited. That is also the answer to "which one is this?" —
 * the chip and the form cannot disagree, because both read the id in the path.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import CampaignForm from '../components/CampaignForm.vue'
import { useCampaignsStore } from '../stores/campaigns.js'
import { forgetCurrentCampaign, readCurrentCampaign } from '../stores/currentCampaign.js'

const route = useRoute()
const router = useRouter()
const campaigns = useCampaignsStore()

const campaignId = computed(() => route.params.campaignId)

/*
 * `ensureLoaded` rather than `GET /campaigns/{id}`, and single-flight, so
 * arriving here from the chooser shares the request that drew the cards. It is
 * also what answers "is this mine?": the API reports a campaign belonging to
 * someone else exactly as one that does not exist, so an id missing from the
 * list is the same absence either way and there is nothing a second call could
 * add.
 */
onMounted(() => campaigns.ensureLoaded())

const campaign = computed(() => campaigns.byId(campaignId.value))

const failure = ref(null)
const saving = ref(false)
const saved = ref(false)

async function save(values) {
  saving.value = true
  failure.value = null
  saved.value = false

  try {
    await campaigns.update(campaignId.value, values)
    saved.value = true
  } catch (error) {
    failure.value = error
  } finally {
    saving.value = false
  }
}

/* ---- Deleting ---------------------------------------------------------- */

/*
 * Typing the name, not a dialog with a Delete button in it.
 *
 * Deleting a campaign takes every character at the table with it
 * (`CampaignService.delete`) and the API offers nothing to undo it with. A modal
 * that a practised hand dismisses by reflex is not a check on that; typing the
 * name is, because it cannot be satisfied by muscle memory aimed at the last
 * dialog. It is deliberately not on the chooser either — that is the screen
 * someone lands on straight after signing in, and it puts every campaign's
 * removal one stray click away.
 */
const confirmation = ref('')
const deleting = ref(false)
const deleteFailure = ref(null)

const mayDelete = computed(
  () => Boolean(campaign.value) && confirmation.value.trim() === campaign.value.name,
)

async function remove() {
  if (!mayDelete.value) return

  deleting.value = true
  deleteFailure.value = null

  try {
    await campaigns.remove(campaignId.value)

    // The campaign the app opens on its own cannot be one that no longer
    // exists. Leaving it would send the next visit through `/`, which would
    // find the id missing from the list and clear it anyway — one silent bounce
    // to arrive where this already knows we belong.
    if (readCurrentCampaign() === campaignId.value) forgetCurrentCampaign()

    // `replace`, so Back does not return to the settings page of a campaign
    // that is gone.
    router.replace({ name: 'home' })
  } catch (error) {
    deleteFailure.value =
      error?.status === 404
        ? 'That campaign is already gone.'
        : 'Something went wrong deleting the campaign. Try again.'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="settings">
    <!--
      The three answers the list can give, and they are not the same answer.
      "Could not ask" must never be rendered as "not yours" — one is a dropped
      connection and the other is a campaign someone has lost.
    -->
    <p v-if="!campaigns.loaded && !campaigns.error" class="settings__waiting">
      Fetching this campaign…
    </p>

    <template v-else-if="!campaigns.loaded">
      <h1>We could not reach this campaign</h1>
      <p role="alert">The app is signed in, so this is the connection rather than your account.</p>
      <Button label="Try again" @click="campaigns.reload()" />
    </template>

    <template v-else-if="!campaign">
      <h1>That campaign is not here</h1>
      <p>
        It has been deleted, or it belongs to somebody else. Either way there is nothing to edit.
      </p>
      <Button as="router-link" :to="{ name: 'home' }" label="Back to your campaigns" />
    </template>

    <template v-else>
      <h1 class="settings__title">Campaign settings</h1>
      <p class="settings__lede">Renaming a campaign changes nothing inside it.</p>

      <CampaignForm
        :campaign="campaign"
        submit-label="Save changes"
        :busy="saving"
        :error="failure"
        @submit="save"
      >
        <template #secondary>
          <!-- role="status", not alert: this is the expected outcome, and an
               assertive announcement for "it worked" interrupts for no reason. -->
          <span v-if="saved" class="settings__saved" role="status">
            <i class="pi pi-check" aria-hidden="true" /> Saved
          </span>
        </template>
      </CampaignForm>

      <hr class="rule-fleuron" />

      <section class="danger" aria-labelledby="delete-campaign">
        <h2 id="delete-campaign" class="danger__title">Delete this campaign</h2>
        <p class="danger__warning">
          Everything at this table goes with it, including every character sheet. There is no undo.
        </p>

        <form class="danger__form" novalidate @submit.prevent="remove">
          <label for="delete-confirmation">
            Type <strong>{{ campaign.name }}</strong> to confirm
          </label>
          <InputText
            id="delete-confirmation"
            v-model="confirmation"
            autocomplete="off"
            aria-describedby="delete-campaign"
          />

          <p v-if="deleteFailure" class="danger__error" role="alert">{{ deleteFailure }}</p>

          <Button
            type="submit"
            severity="danger"
            label="Delete campaign"
            :disabled="!mayDelete || deleting"
            :loading="deleting"
          />
        </form>
      </section>
    </template>
  </div>
</template>

<style scoped>
.settings {
  max-width: 40rem;
}

.settings__title {
  margin: 0 0 var(--space-1);
}

.settings__lede {
  margin: 0 0 var(--space-6);
  color: var(--p-text-muted-color);
}

.settings__waiting {
  color: var(--p-text-muted-color);
}

.settings__saved {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: var(--step--1);
  color: var(--p-text-muted-color);
}

/*
 * Bordered rather than filled, and in the error colour only at its edge. A block
 * of red would shout on every visit to a page most people open to fix a typo —
 * the warning belongs to the control, not to the screen.
 */
.danger {
  padding: var(--space-4);
  border: 1px solid var(--p-grimoire-form-error-color);
  border-radius: var(--p-border-radius-md);
}

.danger__title {
  margin: 0 0 var(--space-2);
  font-size: var(--step-1);
}

.danger__warning {
  margin: 0 0 var(--space-4);
  color: var(--p-text-muted-color);
}

.danger__form {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
}

.danger__form label {
  font-family: var(--grimoire-font-display);
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

.danger__form :deep(input) {
  min-height: 44px;
}

.danger__form :deep(button) {
  min-height: 44px;
  margin-top: var(--space-2);
}

.danger__error {
  margin: 0;
  color: var(--p-grimoire-form-error-color);
  font-size: 0.9rem;
}
</style>
