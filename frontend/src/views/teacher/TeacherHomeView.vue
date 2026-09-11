<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchClassAnalytics, fetchTeacherAssignments } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useClassContext } from '@/stores/classContext'

const assignments = ref<Array<Record<string, unknown>>>([])
const classData = ref<any>(null)
const loading = ref(true)
const error = ref('')
const classContext = useClassContext()
const attentionCount = computed(() => classData.value?.summary?.need_care_count ?? 0)
async function load(classId: string) {
  loading.value = true
  error.value = ''
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
  <div class="page-stack"><PageHeader title="教学概览" description="掌握班级学习情况，快速处理作业和教学资源。"><template #actions><RouterLink class="button-link" to="/teacher/assignments">布置作业</RouterLink></template></PageHeader><InlineMessage :message="error" tone="error" /><div v-if="loading" class="loading-state">正在加载教学数据…</div><template v-else><div class="metric-grid"><MetricCard label="作业总数" :value="assignments.length" hint="已创建的教学作业" /><MetricCard label="班级人数" :value="classData?.class?.student_count ?? '—'" hint="当前班级" tone="green" /><MetricCard label="需要关注" :value="attentionCount" hint="建议优先查看" tone="orange" /><MetricCard label="测试数量" :value="classData?.summary?.test_count ?? '—'" hint="作业与测试" tone="purple" /></div><div class="dashboard-grid"><section class="content-card"><div class="section-heading"><div><h3>最近作业</h3><p>管理作业状态并查看提交情况。</p></div><RouterLink class="text-link" to="/teacher/assignments">全部作业</RouterLink></div><div v-if="assignments.length" class="assignment-list compact-list"><article v-for="item in assignments.slice(0, 5)" :key="String(item.id)" class="assignment-row"><div class="assignment-row-main"><strong>{{ item.title }}</strong><span>{{ item.questions?.length ?? 0 }} 道题</span></div><StatusBadge :label="String(item.status === 'published' ? '已发布' : item.status ?? '草稿')" tone="blue" /><RouterLink class="small-button" to="/teacher/assignments">管理</RouterLink></article></div><EmptyState v-else title="还没有作业" description="创建第一份作业开始教学。" /></section><section class="content-card"><div class="section-heading"><div><h3>班级提醒</h3><p>需要关注的学生数量。</p></div><RouterLink class="text-link" to="/teacher/class">查看学情</RouterLink></div><div class="attention-callout"><strong>{{ attentionCount }}</strong><span>名学生需要关注</span></div><p class="muted">根据提交情况和成绩变化自动汇总。</p></section></div></template></div>
</template>
