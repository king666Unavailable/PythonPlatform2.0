<script setup lang="ts">
defineProps<{ label: string; value: string | number; hint?: string; tone?: 'blue' | 'green' | 'orange' | 'purple' }>()
</script>

<template>
  <article class="metric-card" :class="`metric-${tone ?? 'blue'}`">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
    <small v-if="hint">{{ hint }}</small>
  </article>
</template>
