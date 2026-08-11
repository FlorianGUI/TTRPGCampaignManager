<script setup>
/*
 * The campaign form, serving both creating and editing.
 *
 * One component rather than two because the two differ in exactly three things
 * — what the fields start as, what the button says, and what the caller does
 * with the values — and none of those is a reason to keep two copies of field
 * wiring and error placement in step by hand.
 *
 * It owns the form and nothing else: the parent makes the call and hands back
 * whatever the API said, through `error`. That split is what lets creating land
 * inside the new campaign and editing stay on the page, without this component
 * knowing that either thing happens.
 *
 * Both fields are always emitted, including a description nobody touched.
 * `PUT /campaigns/{id}` is a full replacement — see the store's `update` — so a
 * form that emitted only what changed would clear the description every time
 * someone fixed a typo in the name.
 */
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import FormField from './FormField.vue'

const props = defineProps({
  // The row being edited, or null when this is a new campaign.
  campaign: { type: Object, default: null },
  submitLabel: { type: String, required: true },
  busy: { type: Boolean, default: false },
  // Whatever the last submit threw, or null. An ApiError in practice.
  error: { type: Object, default: null },
})

const emit = defineEmits(['submit'])

/*
 * The API's ceilings, restated as the ones the fields hold.
 *
 * Unlike the empty-name check below, this *is* the same rule twice — deliberately,
 * because the two say it at different moments. The API's is the one that decides;
 * this one stops a description being written for a minute before a 422 says the
 * minute was wasted. They are kept in step by hand: 200 is the width of
 * `campaigns.name`, and 1000 is `DESCRIPTION_MAX_LENGTH` in the campaign schema.
 * If one moves, the 422 handling below is what catches the drift.
 */
const NAME_MAX_LENGTH = 200
const DESCRIPTION_MAX_LENGTH = 1000

const name = ref('')
const description = ref('')

/*
 * The one thing checked here rather than by the API, and it is not the
 * duplication it looks like.
 *
 * `CampaignCreate.name` is a bare `str`, so an empty one is a shape the backend
 * accepts: it answers 422 for a name that is *missing*, never for one that is
 * blank. Sending "" would succeed and put a nameless card on the chooser. This
 * check is the only thing standing between someone and that campaign, so it
 * stays — and it is deliberately the only rule here, because every other one
 * would be a guess at what the API will accept.
 */
const missingName = ref(false)

/*
 * Immediate, and watching the campaign rather than reading it once. The edit
 * page renders this only once `byId` has an answer, but that answer arrives from
 * a request — binding to the prop at setup time would fill the form with the
 * blanks that were there while the list was still in flight.
 */
watch(
  () => props.campaign,
  (campaign) => {
    name.value = campaign?.name ?? ''
    description.value = campaign?.description ?? ''
    missingName.value = false
  },
  { immediate: true },
)

/*
 * FastAPI's 422 body is an array of `{loc, msg}`, with `loc` ending in the field
 * it objected to. Which field is the part worth keeping — the message is
 * pydantic's, written for whoever wrote the request, and putting "Input should
 * be a valid string" under a text box explains nothing to a game master.
 */
const FIELD_SAYS = {
  name: 'That name was not accepted. Try a different one.',
  description: 'That description was not accepted. Try a shorter one.',
}

const apiErrors = computed(() => {
  if (props.error?.status !== 422 || !Array.isArray(props.error.detail)) return {}

  return Object.fromEntries(
    props.error.detail
      .map((problem) => String(problem?.loc?.at(-1) ?? ''))
      .filter((field) => field in FIELD_SAYS)
      .map((field) => [field, FIELD_SAYS[field]]),
  )
})

const nameError = computed(() =>
  missingName.value ? 'Give the campaign a name.' : (apiErrors.value.name ?? null),
)

const descriptionError = computed(() => apiErrors.value.description ?? null)

/*
 * Anything left over: a 500, a dropped connection, or a 422 about a field this
 * form does not render. The last one is the case that makes this necessary
 * rather than tidy — an error placed nowhere is an error the person never sees,
 * and the form would just look like it did nothing.
 */
const formError = computed(() => {
  if (!props.error) return null

  if (props.error.status === 422) {
    return Object.keys(apiErrors.value).length ? null : 'Something in there was not accepted.'
  }

  if (props.error.status === 404) return 'That campaign is no longer there.'

  return 'Something went wrong saving the campaign. Try again.'
})

function submit() {
  const trimmed = name.value.trim()
  missingName.value = !trimmed

  if (missingName.value) return

  emit('submit', { name: trimmed, description: description.value.trim() })
}
</script>

<template>
  <form class="campaign-form" novalidate @submit.prevent="submit">
    <FormField
      id="campaign-name"
      v-model="name"
      label="Name"
      :maxlength="NAME_MAX_LENGTH"
      :error="nameError"
    />

    <div class="field">
      <label for="campaign-description">Description <span>(optional)</span></label>
      <Textarea
        id="campaign-description"
        v-model="description"
        rows="4"
        auto-resize
        fluid
        :maxlength="DESCRIPTION_MAX_LENGTH"
        :invalid="Boolean(descriptionError)"
        :aria-describedby="descriptionError ? 'campaign-description-error' : undefined"
      />
      <p v-if="descriptionError" id="campaign-description-error" class="field__error" role="alert">
        {{ descriptionError }}
      </p>
      <!--
        The hint says what it is *for*, not where it shows, because for now it
        shows nowhere: #31 is what reads it, to introduce the table to someone
        deciding whether to join it. Promising a place it appears would be a
        promise the app does not yet keep.
      -->
      <p class="campaign-form__hint">
        A line introducing the table, for the people you invite to it. It can change at any time.
      </p>
    </div>

    <p v-if="formError" class="field__error" role="alert">{{ formError }}</p>

    <div class="campaign-form__actions">
      <Button type="submit" :label="submitLabel" :loading="busy" :disabled="busy" />
      <slot name="secondary" />
    </div>
  </form>
</template>

<style scoped>
.campaign-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 34rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.campaign-form label {
  font-family: var(--grimoire-font-display);
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

.campaign-form label span {
  color: var(--p-text-muted-color);
  font-family: var(--grimoire-font-body);
  letter-spacing: normal;
}

.field__error {
  margin: 0;
  color: var(--p-grimoire-form-error-color);
  font-size: 0.9rem;
}

.campaign-form__hint {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: var(--step--1);
}

.campaign-form__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.campaign-form :deep(button) {
  min-height: 44px;
}
</style>
