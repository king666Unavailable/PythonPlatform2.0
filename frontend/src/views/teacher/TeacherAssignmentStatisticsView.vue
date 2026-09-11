<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchAssignmentStatistics } from '@/api/client'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import TeacherAssignmentStatisticsPanel from '@/components/teacher/TeacherAssignmentStatisticsPanel.vue'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const statistics = ref<any>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    statistics.value = await fetchAssignmentStatistics(String(route.params.id))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '统计加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="作业统计">
      <template #actions>
        <RouterLink class="secondary-button button-link" to="/teacher/assignments">返回作业管理</RouterLink>
      </template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载作业统计…</div>
    <section v-else-if="statistics" class="content-card">
      <TeacherAssignmentStatisticsPanel :statistics="statistics" />
    </section>
  </div>
</template>
