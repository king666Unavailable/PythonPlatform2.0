<script setup lang="ts">
defineProps<{ name: string }>()
</script>

<template>
  <svg class="app-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path v-if="name === 'home'" d="m4 10 8-6 8 6v9a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1v-9Z" />
    <path v-else-if="name === 'assignment'" d="M7 3h10a2 2 0 0 1 2 2v14H5V5a2 2 0 0 1 2-2Zm2 4h6M9 11h6M9 15h4" />
    <path v-else-if="name === 'grade'" d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.9-5.4 2.9 1-6-4.4-4.3 6.1-.9L12 3Z" />
    <path v-else-if="name === 'knowledge'" d="M5 5h14v4H5zM5 15h6v4H5zM15 15h4v4h-4zM12 9v3M8 12h8" />
    <path v-else-if="name === 'question'" d="M5 4h14v16H5zM8 8h8M8 12h5M8 16h3" />
    <path v-else-if="name === 'practice'" d="M6 4h12v16H6zM9 8h6M9 12h6M9 16h4" />
    <path v-else-if="name === 'spark'" d="m12 3 1.4 5.6L19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3Zm6 13 .6 2.4L21 19l-2.4.6L18 22l-.6-2.4L15 19l2.4-.6L18 16Z" />
    <path v-else-if="name === 'class'" d="M4 19v-8l8-4 8 4v8M7 19v-5h10v5M9 10V6h6v4" />
    <path v-else-if="name === 'exam'" d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" />
    <path v-else-if="name === 'account'" d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0M19 8h3M20.5 6.5v3" />
    <path v-else-if="name === 'audit'" d="M6 3h9l3 3v15H6zM15 3v4h4M9 11h6M9 15h6M9 19h4" />
    <path v-else-if="name === 'settings'" d="M9.5 4.5 10.8 3h2.4l1.3 1.5 2 .2 1.1-1 1.7 1-0.4 1.5 1 1.7 1.5.4v2.4l-1.5 1.3-.2 2-1 1.1.4 1.5-1.7 1-1.1-1-2 .2L13.2 21h-2.4l-1.3-1.5-2-.2-1.1 1-1.7-1 .4-1.5-1-1.7-1.5-.4v-2.4l1.5-1.3.2-2-1-1.1.4-1.5 1.7-1 1.1 1 2-.2ZM12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
    <path v-else d="M6 12h12" />
  </svg>
</template>
