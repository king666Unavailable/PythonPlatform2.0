<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchStudentLearningProfile } from '@/api/client'
import type { LearningProfileReport } from '@/types/learningProfile'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const report = ref<LearningProfileReport | null>(null)
const loading = ref(true)
const error = ref('')

const dimensions = computed(() => report.value?.overview.dimensions ?? { progress: null, habit: null, ability: null })
const classAverage = computed(() => report.value?.overview.class_average ?? { progress: null, habit: null, ability: null })
const dimensionValues = computed(() => [dimensions.value.progress, dimensions.value.habit, dimensions.value.ability])
const classValues = computed(() => [classAverage.value.progress, classAverage.value.habit, classAverage.value.ability])

function score(value: number | null | undefined) {
  return value === null || value === undefined ? '暂无数据' : `${value.toFixed(1)} 分`
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? '暂无数据' : `${value.toFixed(1)}%`
}

function radarPoints(values: Array<number | null>) {
  const center = 150
  const radius = 104
  return values.map((value, index) => {
    const angle = -Math.PI / 2 + index * (Math.PI * 2 / 3)
    const ratio = Math.max(0, Math.min(100, value ?? 0)) / 100
    return `${(center + Math.cos(angle) * radius * ratio).toFixed(1)},${(center + Math.sin(angle) * radius * ratio).toFixed(1)}`
  }).join(' ')
}

function radarGrid(level: number) {
  return radarPoints([level, level, level])
}

function formatDate(value: string) {
  if (!value) return '暂无'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function dimensionLabel(value: number | null | undefined) {
  if (value === null || value === undefined) return '暂无数据'
  if (value >= 80) return '表现良好'
  if (value >= 60) return '继续保持'
  return '需要加强'
}

function barWidth(value: number | null | undefined) {
  return `${Math.max(0, Math.min(100, value ?? 0))}%`
}

function questionTypeLabel(value: string) {
  return ({
    '1': '选择题',
    '2': '填空题',
    '3': '编程题',
    '4': '程序填空题',
    choice: '选择题',
    blank: '填空题',
    programming: '编程题',
    code: '编程题',
  } as Record<string, string>)[String(value).trim().toLowerCase()] ?? '其他题型'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    report.value = await fetchStudentLearningProfile()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '学情画像加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack learning-profile-page">
    <PageHeader title="学情画像" />
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在生成学情画像…</div>
    <EmptyState v-else-if="!report" title="暂时没有学情画像数据" description="完成并提交作业后，系统会根据真实学习记录生成画像。" />
    <template v-else>
      <section class="content-card learning-profile-student-card">
        <div><h2>{{ report.student.name }}</h2><p>{{ report.student.username }} · {{ report.student.teaching_class || '未设置教学班' }} · {{ report.student.administrative_class || '未填写行政班' }}</p></div>
        <div class="learning-profile-updated">画像更新时间<br><strong>{{ formatDate(report.meta.generated_at) }}</strong></div>
      </section>

      <section class="content-card learning-profile-overview">
        <div class="section-heading"><div><h3>三维画像总览</h3><p>基于当前教学班的真实作业、答题、掌握度和学习用时数据</p></div><span class="learning-profile-overall">综合评分：<strong>{{ score(report.overview.overall_score) }}</strong></span></div>
        <div class="learning-profile-overview-grid">
          <div class="learning-profile-radar-wrap">
            <div class="learning-profile-legend"><span><i class="profile-dot student" />当前表现</span><span><i class="profile-dot average" />班级平均</span><span><i class="profile-dot reference" />参考线 80 分</span></div>
            <svg class="learning-profile-radar" viewBox="0 0 300 300" role="img" aria-label="学情画像三维雷达图">
              <polygon v-for="level in [20, 40, 60, 80, 100]" :key="level" :points="radarGrid(level)" class="profile-radar-grid" />
              <line x1="150" y1="46" x2="150" y2="254" class="profile-radar-axis" /><line x1="59.9" y1="202" x2="240.1" y2="202" class="profile-radar-axis" /><line x1="240.1" y1="202" x2="59.9" y2="202" class="profile-radar-axis" />
              <polygon :points="radarPoints([80, 80, 80])" class="profile-radar-reference" /><polygon :points="radarPoints(classValues)" class="profile-radar-average" /><polygon :points="radarPoints(dimensionValues)" class="profile-radar-student" />
              <text x="150" y="22" text-anchor="middle">学习进展</text><text x="266" y="218" text-anchor="start">学习习惯</text><text x="34" y="218" text-anchor="end">学习能力</text>
            </svg>
          </div>
          <div class="learning-profile-dimension-cards">
            <article class="profile-dimension-card progress"><div class="profile-dimension-ring"><span>{{ score(dimensions.progress) }}</span></div><h4>学习进展</h4><p>{{ dimensionLabel(dimensions.progress) }}</p></article>
            <article class="profile-dimension-card habit"><div class="profile-dimension-ring"><span>{{ score(dimensions.habit) }}</span></div><h4>学习习惯</h4><p>{{ dimensionLabel(dimensions.habit) }}</p></article>
            <article class="profile-dimension-card ability"><div class="profile-dimension-ring"><span>{{ score(dimensions.ability) }}</span></div><h4>学习能力</h4><p>{{ dimensionLabel(dimensions.ability) }}</p></article>
          </div>
        </div>
      </section>

      <section class="learning-profile-detail-grid">
        <article class="content-card learning-profile-detail-card progress"><div class="learning-profile-card-title"><h3>学习进展</h3><span>掌握与成绩</span></div><div class="profile-metric-row"><span>课程知识掌握度</span><strong>{{ percent(report.progress.knowledge_mastery) }}</strong></div><div class="profile-bar"><i :style="{ width: barWidth(report.progress.knowledge_mastery) }" /></div><div class="profile-metric-row"><span>已出成绩作业</span><strong>{{ report.progress.scored_assignment_count }} 次</strong></div><div class="profile-metric-row"><span>已出成绩平均分</span><strong>{{ score(report.progress.average_score) }}</strong></div><div class="profile-subsection"><h4>薄弱知识点</h4><div v-if="report.progress.weak_points.length" class="profile-weak-list"><div v-for="point in report.progress.weak_points" :key="point.title"><span>{{ point.title }}</span><strong>{{ percent(point.mastery) }}</strong></div></div><p v-else class="muted">暂无足够掌握度记录。</p></div><div class="profile-subsection profile-score-link-section"><h4>成绩曲线</h4><RouterLink class="profile-score-link" to="/student/profile">前往个人中心查看成绩曲线 <span aria-hidden="true">→</span></RouterLink></div></article>

        <article class="content-card learning-profile-detail-card habit"><div class="learning-profile-card-title"><h3>学习习惯</h3><span>提交与投入</span></div><div class="profile-stat-grid"><div><strong>{{ percent(report.habit.submission_rate) }}</strong><span>作业提交率</span></div><div><strong>{{ percent(report.habit.on_time_rate) }}</strong><span>按时提交率</span></div><div><strong>{{ report.habit.active_days }}</strong><span>活跃天数</span></div><div><strong>{{ report.habit.average_question_seconds === null ? '暂无' : `${report.habit.average_question_seconds} 秒` }}</strong><span>平均每题用时</span></div><div class="profile-questionnaire-status"><strong>{{ report.habit.questionnaire_completed ? '已完成' : '未完成' }}</strong><span>问卷完成状态</span></div></div><div class="profile-subsection"><h4>学习行为说明</h4><p class="profile-explanation">学习习惯分综合提交率、按时提交、活跃天数和逐题用时计算；问卷结果仅作为辅助参考，不会替代学习行为数据。</p><p v-if="!report.habit.questionnaire_completed" class="profile-data-note">问卷尚未完成，当前画像不使用自我评价数据。</p></div></article>

        <article class="content-card learning-profile-detail-card ability"><div class="learning-profile-card-title"><h3>学习能力</h3><span>题型与难度</span></div><div class="profile-metric-row"><span>客观题正确率</span><strong>{{ percent(report.ability.objective_accuracy) }}</strong></div><div class="profile-bar"><i :style="{ width: barWidth(report.ability.objective_accuracy) }" /></div><div class="profile-metric-row"><span>主观题/编程题正确率</span><strong>{{ percent(report.ability.subjective_accuracy) }}</strong></div><div class="profile-bar profile-bar-secondary"><i :style="{ width: barWidth(report.ability.subjective_accuracy) }" /></div><div class="profile-subsection"><h4>不同难度正确率</h4><div v-if="report.ability.difficulty_accuracy.length" class="profile-bars-list"><div v-for="item in report.ability.difficulty_accuracy" :key="item.label"><span>{{ item.label }}（{{ item.count }} 题）</span><strong>{{ percent(item.accuracy) }}</strong><i><b :style="{ width: barWidth(item.accuracy) }" /></i></div></div><p v-else class="muted">暂无足够的题目难度数据。</p></div><div class="profile-subsection"><h4>题型表现</h4><div v-if="report.ability.question_type_accuracy.length" class="profile-type-list"><span v-for="item in report.ability.question_type_accuracy" :key="item.label">{{ questionTypeLabel(item.label) }}：{{ percent(item.accuracy) }}</span></div><p v-else class="muted">暂无逐题成绩数据。</p></div><p v-if="report.ability.programming_included" class="profile-data-note">当前作业包含编程题；编程题自动判卷未完成前，不纳入正确率。</p></article>
      </section>

      <section class="content-card learning-profile-suggestions"><div class="section-heading"><div><h3>个性化建议</h3><p>根据当前教学班和本人学习记录生成</p></div></div><div class="profile-suggestion-grid"><article v-for="item in report.suggestions" :key="item.dimension" :class="`profile-suggestion ${item.tone}`"><h4>{{ item.dimension }}</h4><p>{{ item.text }}</p></article></div></section>
    </template>
  </div>
</template>
