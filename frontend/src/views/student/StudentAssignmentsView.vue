<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchStudentAssignments } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { assignmentKindLabel, shortDate, sortAssignmentsByDeadlineDesc, statusTone } from '@/utils/format'

const assignments = ref<Array<Record<string, unknown>>>([])
const filter = ref('全部')
const loading = ref(true)
const error = ref('')
const tabs = ['全部', '进行中', '判卷中', '已完成', '已逾期']
const filtered = computed(() => filter.value === '全部' ? assignments.value : assignments.value.filter((item) => String(item.status) === filter.value))

function actionLabel(status: unknown) {
  return { 进行中: '去完成', 已完成: '查看结果', 判卷中: '查看结果', 已逾期: '查看题目' }[String(status)] ?? '查看题目'
}

function timeLimitLabel(value: unknown) {
  const minutes = Number(value ?? 0)
  return Number.isFinite(minutes) && minutes > 0 ? `${minutes} 分钟` : '不限时'
}

async function load() {
  loading.value = true
  error.value = ''
  try { assignments.value = sortAssignmentsByDeadlineDesc((await fetchStudentAssignments()).items) } catch (cause) { error.value = cause instanceof Error ? cause.message : '作业加载失败。' } finally { loading.value = false }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="我的作业" description="查看作业进度、截止时间和提交结果，点击作业即可继续答题。">
      <template #actions><RouterLink class="button-link secondary-button" to="/student/mock">开始模拟练习</RouterLink></template>
    </PageHeader>
    <div class="tabs" role="tablist"><button v-for="tab in tabs" :key="tab" type="button" :class="{ active: filter === tab }" @click="filter = tab">{{ tab }}</button></div>
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载作业…</div>
    <section v-else class="content-card flush-card">
      <div v-if="filtered.length" class="assignment-table student-assignment-table">
        <div class="assignment-table-head"><span>作业</span><span>截止时间</span><span>答题时长</span><span>状态</span><span>操作</span></div>
        <article v-for="item in filtered" :key="String(item.id)" class="assignment-table-row">
          <div class="assignment-title-cell"><strong>{{ item.title }}</strong><small>{{ assignmentKindLabel(item.assignment_kind) }}<em v-if="item.can_makeup"> · 补交开放</em></small></div>
          <span class="assignment-deadline-cell">{{ shortDate(item.deadline) }}</span>
          <span class="assignment-time-cell">{{ timeLimitLabel(item.time_limit) }}</span>
          <StatusBadge class="assignment-status-cell" :label="String(item.status)" :tone="statusTone(String(item.status))" />
          <RouterLink v-if="item.available !== false" class="small-button assignment-action-button assignment-action-cell" :to="{ path: `/student/assignments/${item.id}`, query: item.can_makeup && item.makeup_window_id ? { makeup_window_id: String(item.makeup_window_id) } : {} }">{{ item.can_makeup && item.status === '已逾期' ? '去补交' : actionLabel(item.status) }}</RouterLink>
          <span v-else class="muted assignment-action-cell">暂不可用</span>
        </article>
      </div>
      <EmptyState v-else title="没有符合条件的作业" description="可以切换其他状态查看。" />
    </section>
  </div>
</template>
