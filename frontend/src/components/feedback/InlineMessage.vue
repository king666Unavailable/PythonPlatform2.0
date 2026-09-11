<script setup lang="ts">
defineProps<{ message: string; tone?: 'error' | 'success' | 'info' }>()
</script>

<template><p v-if="message" class="inline-message" :class="`message-${tone ?? 'info'}`">{{ message }}</p></template>
