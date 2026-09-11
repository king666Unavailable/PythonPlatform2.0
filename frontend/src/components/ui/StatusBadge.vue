<script setup lang="ts">
defineProps<{ label: string; tone?: 'blue' | 'green' | 'orange' | 'purple' | 'gray' | 'red' }>()
</script>

<template><span class="status-badge" :class="`tone-${tone ?? 'gray'}`">{{ label }}</span></template>
