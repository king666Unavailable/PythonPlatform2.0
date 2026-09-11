<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchStudentAssignments, fetchStudentProfile, fetchGrades } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { statusTone, shortDate } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const profile = ref<Record<string, unknown> | null>(null)
const assignments = ref<Array<Record<string, unknown>>>([])
const grades = ref<Array<Record<string, unknown>>>([])
const averageScore = ref<number | null>(null)
const loading = ref(true)
const error = ref('')

const pending = computed(() => assignments.value.filter((item) => ['待完成', '进行中'].includes(String(item.status))))
const completed = computed(() => assignments.value.filter((item) => String(item.status) === '已完成').length)
const recentGrades = computed(() => grades.value.filter((item) => {
  const status = String(item.status ?? '').trim().toLowerCase()
  return !['draft', 'in_progress', '进行中', '待完成'].includes(status)
}))
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [profileResult, assignmentResult, gradeResult] = await Promise.all([fetchStudentProfile(), fetchStudentAssignments(), fetchGrades()])
    profile.value = profileResult.student as unknown as Record<string, unknown>
    averageScore.value = profileResult.summary.average_score
    assignments.value = assignmentResult.items
    grades.value = gradeResult.items
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '学习概览加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack student-home-page">
    <PageHeader :title="`你好，${String(profile?.name ?? auth.user.value?.name ?? '同学')}`" description="从今天的学习任务开始，保持稳定的练习节奏。" />
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载你的学习概览…</div>
    <template v-else>
      <section class="metric-grid">
        <MetricCard label="待完成作业" :value="pending.length" hint="包括正在进行的作业" tone="blue" />
        <MetricCard label="已完成作业" :value="completed" hint="累计完成记录" tone="green" />
        <MetricCard label="平均成绩" :value="averageScore === null ? '—' : `${averageScore} 分`" hint="来自已批改提交" tone="purple" />
        <MetricCard label="完成率" value="—" hint="学情分析功能待实现" tone="orange" />
      </section>
      <div class="dashboard-grid">
        <section class="content-card prominent-card">
          <div class="section-heading"><div><h3>待完成作业</h3><p>按截止时间优先显示需要处理的任务。</p></div><RouterLink class="text-link" to="/student/assignments">全部作业</RouterLink></div>
          <div v-if="pending.length" class="assignment-list compact-list">
            <article v-for="item in pending.slice(0, 5)" :key="String(item.id)" class="assignment-row">
              <div class="assignment-row-main"><strong>{{ item.title }}</strong><span>截止 {{ shortDate(item.deadline) }}</span></div>
              <StatusBadge :label="String(item.status)" :tone="statusTone(String(item.status))" />
              <RouterLink class="small-button" :to="`/student/assignments/${item.id}`">继续</RouterLink>
            </article>
          </div>
          <EmptyState v-else title="暂时没有待完成作业" description="新的作业发布后会显示在这里。" />
        </section>
        <section class="content-card">
          <div class="section-heading"><div><h3>最近成绩</h3><p>查看最近提交的结果。</p></div><RouterLink class="text-link" to="/student/profile">查看个人成绩</RouterLink></div>
          <div v-if="recentGrades.length" class="score-list">
            <div v-for="item in recentGrades.slice(0, 5)" :key="String(item.id)" class="score-row"><span>{{ item.assignment_title ?? `作业 ${item.assignment_id}` }}</span><strong>{{ item.score ?? '待批改' }}<small v-if="item.score !== undefined"> 分</small></strong></div>
          </div>
          <EmptyState v-else title="还没有成绩记录" description="完成一次作业后，结果会显示在这里。" />
        </section>
      </div>
    </template>
  </div>
</template>
