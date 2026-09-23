<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchClassAnalytics, fetchTeacherAssignments, fetchTeacherClassMastery } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useClassContext } from '@/stores/classContext'
import type { ClassKnowledgeMasteryResponse, ClassMasteryNode } from '@/types/teacher'

const assignments = ref<Array<Record<string, unknown>>>([])
const classData = ref<any>(null)
const masteryData = ref<ClassKnowledgeMasteryResponse | null>(null)
const loading = ref(true)
const error = ref('')
const masteryError = ref('')
const classContext = useClassContext()
const attentionCount = computed(() => classData.value?.summary?.need_care_count ?? 0)
const masteryValue = computed(() => {
  const value = masteryData.value?.summary.course_mastery
  return value == null ? '暂无数据' : `${value.toFixed(1)} 分`
})
const masteryHint = computed(() => {
  if (masteryError.value) return '数据暂不可用，点击查看详情'
  if (!masteryData.value) return '正在读取当前班级数据…'
  return `覆盖学生 ${masteryData.value.summary.coverage_student_count} / ${masteryData.value.class.student_count} 人`
})
const weakPoints = computed<ClassMasteryNode[]>(() => {
  const threshold = masteryData.value?.meta.unmastered_threshold ?? 60
  return (masteryData.value?.nodes ?? [])
    .filter((node) => node.node_type === 'point' && node.attempted_count > 0 && node.mastery_score != null && node.mastery_score < threshold)
    .sort((left, right) => (left.mastery_score ?? 0) - (right.mastery_score ?? 0) || left.title.localeCompare(right.title, 'zh-CN'))
    .slice(0, 5)
})
async function load(classId: string) {
  loading.value = true
  error.value = ''
  masteryError.value = ''
  try {
    const [assignmentResult, classResult] = await Promise.all([
      fetchTeacherAssignments(),
      fetchClassAnalytics(classId),
    ])
    assignments.value = assignmentResult.items
    classData.value = classResult
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '教学概览加载失败。'
  } finally {
    loading.value = false
  }
  try {
    masteryData.value = await fetchTeacherClassMastery()
  } catch (cause) {
    masteryData.value = null
    masteryError.value = cause instanceof Error ? cause.message : '课程总体掌握度暂不可用。'
  }
}

watch(
  () => classContext.current.value?.id,
  (classId) => {
    if (classId) void load(classId)
  },
  { immediate: true },
)
</script>

<template>
  <div class="page-stack">
    <PageHeader title="教学概览" description="掌握班级学习情况，快速处理作业和教学资源。" />
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载教学数据…</div>
    <template v-else>
      <div class="metric-grid">
        <article class="metric-card metric-blue"><span>作业总数</span><strong>{{ assignments.length }}</strong><small>已创建的教学作业</small></article>
        <article class="metric-card metric-green"><span>班级人数</span><strong>{{ classData?.class?.student_count ?? '—' }}</strong><small>当前班级</small></article>
        <article class="metric-card metric-orange"><span>需要关注</span><strong>{{ attentionCount }}</strong><small>建议优先查看</small></article>
        <RouterLink class="teacher-mastery-card-link" to="/teacher/class?tab=mastery" :aria-label="`课程总体掌握度 ${masteryValue}，${masteryHint}，点击查看知识掌握度详情`">
          <article class="metric-card metric-purple"><span>课程总体掌握度</span><strong>{{ masteryValue }}</strong><small>{{ masteryHint }}</small></article>
        </RouterLink>
      </div>
      <div class="dashboard-grid">
        <section class="content-card">
          <div class="section-heading"><div><h3>最近作业</h3><p>近期布置的教学作业。</p></div><RouterLink class="text-link" to="/teacher/assignments">全部作业</RouterLink></div>
          <div v-if="assignments.length" class="assignment-list compact-list">
            <article v-for="item in assignments.slice(0, 5)" :key="String(item.id)" class="assignment-row">
              <div class="assignment-row-main"><strong>{{ item.title }}</strong><span>{{ item.questions?.length ?? 0 }} 道题</span></div>
              <StatusBadge :label="String(item.status === 'published' ? '已发布' : item.status ?? '草稿')" tone="blue" />
            </article>
          </div>
          <EmptyState v-else title="还没有作业" description="创建第一份作业开始教学。" />
        </section>
        <section class="content-card">
          <div class="section-heading"><div><h3>班级提醒</h3><p>需关注的学生与知识点。</p></div><RouterLink class="text-link" to="/teacher/class">查看学情</RouterLink></div>
          <div class="attention-callout"><strong>{{ attentionCount }}</strong><span>名学生需要关注</span></div>
          <p class="muted">&nbsp</p>
          <div class="teacher-home-weak-points">
            <div class="teacher-home-weak-heading"><strong>薄弱知识点</strong><small>已作答且掌握度低于 60 分，最多 5 个</small></div>
            <div v-for="point in weakPoints" :key="`${point.node_type}:${point.node_id}`" class="teacher-home-weak-point">
              <span>{{ point.title }}</span><strong>{{ point.mastery_score?.toFixed(1) }} 分</strong>
            </div>
            <p v-if="!weakPoints.length" class="teacher-home-weak-empty">暂无符合条件的薄弱知识点</p>
            <RouterLink class="teacher-home-weak-more" to="/teacher/class?tab=mastery">查看知识掌握度 <span aria-hidden="true">→</span></RouterLink>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
