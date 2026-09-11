<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchStudentProfile } from '@/api/client'
import type { StudentProfileReport } from '@/types/student'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { assignmentKindLabel, statusTone } from '@/utils/format'

const report = ref<StudentProfileReport | null>(null)
const error = ref('')
const loading = ref(true)

const profile = computed(() => report.value?.student)
const summary = computed(() => report.value?.summary)
const records = computed(() => report.value?.assignment_records ?? [])
const scoreCurve = computed(() => report.value?.score_curve ?? [])
const chartWidth = computed(() => Math.max(760, scoreCurve.value.length * 120 + 70))

const chartPoints = computed(() => {
  const width = chartWidth.value
  const height = 260
  const left = 46
  const right = 24
  const top = 22
  const bottom = 46
  const values = scoreCurve.value
  return values.map((item, index) => ({
    ...item,
    x: values.length === 1 ? width / 2 : left + (index / (values.length - 1)) * (width - left - right),
    y: top + ((100 - Number(item.score)) / 100) * (height - top - bottom),
  }))
})

const chartPolyline = computed(() => chartPoints.value.map((point) => `${point.x},${point.y}`).join(' '))

function scoreLabel(score: number | null) {
  return score === null || score === undefined ? '—' : `${score} 分`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    report.value = await fetchStudentProfile()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '个人资料加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack profile-page">
    <PageHeader title="个人中心" />
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载个人资料…</div>
    <EmptyState v-else-if="!report || !profile" title="暂时无法加载个人资料" description="请稍后刷新重试。" />
    <template v-else>
      <section class="profile-hero content-card">
        <div class="profile-avatar">{{ String(profile.name ?? '?').slice(0, 1) }}</div>
        <div class="profile-hero-main">
          <h3>{{ profile.name }}</h3>
          <div class="profile-hero-facts">
            <span>学号：{{ profile.username }}</span>
            <span>性别：{{ profile.gender || '未填写' }}</span>
            <span>班级：{{ profile.administrative_class || '未填写' }}</span>
          </div>
        </div>
      </section>

      <div class="metric-grid metric-grid-three">
        <MetricCard label="已完成作业" :value="summary?.completed_assignments ?? 0" tone="green" />
        <MetricCard label="已作答题目" :value="summary?.question_count ?? 0" />
        <MetricCard label="平均成绩" :value="summary?.average_score === null || summary?.average_score === undefined ? '—' : `${summary.average_score} 分`" tone="purple" />
      </div>

      <section class="profile-learning-grid">
        <section class="content-card profile-test-card">
          <div class="section-heading">
            <div><h3>测试完成情况</h3><p>共 {{ records.length }} 次作业或测试</p></div>
          </div>
          <div v-if="records.length" class="profile-test-table">
            <div class="profile-test-table-head"><span>作业名称</span><span>提交状态</span><span>得分</span></div>
            <article v-for="record in records" :key="record.assignment_id" class="profile-test-table-row">
              <div class="profile-assignment-title"><strong>{{ record.title }}</strong><small>{{ assignmentKindLabel(record.assignment_kind) }}</small></div>
              <StatusBadge :label="record.submission_status" :tone="statusTone(record.submission_status)" />
              <strong class="profile-score">{{ scoreLabel(record.score) }}</strong>
            </article>
          </div>
          <EmptyState v-else title="还没有作业或测试记录" description="提交作业后，完成情况会显示在这里。" />
        </section>

        <section class="content-card score-chart-card">
          <div class="section-heading"><div><h3>成绩曲线</h3><p>按提交时间展示已出成绩</p></div></div>
          <div v-if="chartPoints.length" class="score-chart-wrap">
            <svg class="score-chart" :style="{ width: `max(100%, ${chartWidth}px)` }" :viewBox="`0 0 ${chartWidth} 260`" role="img" aria-label="成绩曲线">
              <line v-for="level in [0, 25, 50, 75, 100]" :key="level" x1="46" :y1="22 + ((100 - level) / 100) * 192" :x2="chartWidth - 24" :y2="22 + ((100 - level) / 100) * 192" class="chart-grid-line" />
              <text v-for="level in [0, 25, 50, 75, 100]" :key="`label-${level}`" x="8" :y="27 + ((100 - level) / 100) * 192" class="chart-axis-label">{{ level }}</text>
              <polyline :points="chartPolyline" class="chart-line" />
              <g v-for="point in chartPoints" :key="`${point.assignment_id}-${point.submitted_at}`">
                <circle :cx="point.x" :cy="point.y" r="5" class="chart-point" />
                <text :x="point.x" :y="point.y - 12" text-anchor="middle" class="chart-score-label">{{ point.score }}</text>
              </g>
            </svg>
            <div class="score-chart-labels" :style="{ width: `max(100%, ${chartWidth}px)` }"><span v-for="point in chartPoints" :key="`${point.assignment_id}-label`" :title="point.title">{{ point.title }}</span></div>
          </div>
          <EmptyState v-else title="暂无成绩曲线" description="完成并批改作业后，成绩趋势会显示在这里。" />
        </section>
      </section>
    </template>
  </div>
</template>
