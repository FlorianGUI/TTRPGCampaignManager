<script setup>
import Button from 'primevue/button'
import { t } from '../i18n/index.js'
</script>

<template>
  <article class="notfound">
    <p class="label-smallcaps">404</p>
    <h1>{{ t('notFound.title') }}</h1>

    <div class="prose">
      <p>{{ t('notFound.detail') }}</p>
    </div>

    <p>
      <!-- `custom` + navigate: render PrimeVue's Button rather than an anchor,
           without losing router navigation. -->
      <RouterLink v-slot="{ navigate }" :to="{ name: 'home' }" custom>
        <Button :label="t('notFound.back')" icon="pi pi-arrow-left" @click="navigate" />
      </RouterLink>
    </p>
  </article>
</template>

<style scoped>
.notfound {
  max-width: var(--measure);
}

.notfound h1 {
  margin-bottom: var(--space-4);
}
</style>
