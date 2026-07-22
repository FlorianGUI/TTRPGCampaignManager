<script setup>
defineProps({
  msg: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
    <p>D&D Character Sheet Creator frontend is up and running.</p>
  </div>
</template>

<style scoped>
.hello {
  font-family: system-ui, sans-serif;
  text-align: center;
  margin-top: 4rem;
}
</style>
