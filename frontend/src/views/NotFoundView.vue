<script setup>
import Button from 'primevue/button'
</script>

<template>
  <article class="notfound">
    <p class="label-smallcaps">404</p>
    <h1>That page isn't in this volume</h1>

    <div class="prose">
      <p>
        The link may be mistyped, or it may point at something not written yet. Nothing has been
        lost.
      </p>
    </div>

    <p>
      <!-- `custom` + navigate: render PrimeVue's Button rather than an anchor,
           without losing router navigation. -->
      <RouterLink v-slot="{ navigate }" :to="{ name: 'home' }" custom>
        <Button label="Back to session notes" icon="pi pi-arrow-left" @click="navigate" />
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
