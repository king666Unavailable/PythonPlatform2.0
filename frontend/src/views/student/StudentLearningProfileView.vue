<script setup lang="ts">
import EmptyState from '@/components/feedback/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
</script>

<template>
  <div class="page-stack">
    <PageHeader title="学情画像" />
    <section class="content-card">
      <EmptyState title="学情画像正在建设中" description="后续将展示学习进展、学习习惯、能力分析和个性化建议。" />
    </section>
  </div>
</template>
