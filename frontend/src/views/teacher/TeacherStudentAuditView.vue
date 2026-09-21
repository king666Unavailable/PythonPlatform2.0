<script setup lang="ts">
import { computed, ref } from 'vue'
import { fetchTeacherStudentOperationLogs } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useClassContext } from '@/stores/classContext'
import { formatDate } from '@/utils/format'

const actions = [
  { value: 'student.login.success', label: '登录成功' },
  { value: 'logout.manual', label: '主动退出' },
  { value: 'submission.create', label: '提交作业' },
]
const classContext = useClassContext()
const currentClassLabel = computed(() => {
  const current = classContext.current.value
  if (!current) return '当前教学班'
  return [current.title, current.teaching_class].filter(Boolean).join(' / ')
    + (current.academic_year ? `（${current.academic_year}）` : '')
})
const keyword = ref('')
const action = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const logs = ref<Array<Record<string, unknown>>>([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const currentPage = ref(1)
const total = ref(0)
const totalPages = ref(0)
const jumpPage = ref('')

async function search(page = 1) {
  loading.value = true
  error.value = ''
  searched.value = true
  currentPage.value = page
  try {
    const result = await fetchTeacherStudentOperationLogs({
      q: keyword.value.trim(),
      action: action.value,
      from: dateFrom.value,
      to: dateTo.value,
      page,
    })
    logs.value = result.items
    total.value = result.meta.total
    totalPages.value = result.meta.total_pages
    currentPage.value = result.meta.page
    jumpPage.value = String(result.meta.page)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '学生操作记录加载失败。'
    logs.value = []
    total.value = 0
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  keyword.value = ''
  action.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  logs.value = []
  searched.value = false
  currentPage.value = 1
  total.value = 0
  totalPages.value = 0
  jumpPage.value = ''
  error.value = ''
}

function jumpToPage() {
  const page = Math.min(totalPages.value, Math.max(1, Number.parseInt(jumpPage.value, 10) || 1))
  void search(page)
}

function text(value: unknown) {
  return typeof value === 'string' || typeof value === 'number' ? String(value).trim() : ''
}

function detailOf(log: Record<string, unknown>) {
  return log.detail && typeof log.detail === 'object' ? log.detail as Record<string, unknown> : {}
}

function actionLabel(log: Record<string, unknown>) {
  return actions.find((item) => item.value === text(log.action))?.label || '学生操作'
}

function objectLabel(log: Record<string, unknown>) {
  if (text(log.action) === 'submission.create') {
    const title = text(detailOf(log).assignment_title)
    return title ? `作业「${title}」` : '作业已失效'
  }
  return '学生账号'
}

function description(log: Record<string, unknown>) {
  const actionCode = text(log.action)
  if (actionCode === 'student.login.success') return '学生成功登录系统。'
  if (actionCode === 'logout.manual') return '学生主动退出登录。'
  if (actionCode === 'submission.create') return `已提交作业「${text(detailOf(log).assignment_title) || '作业已失效'}」。`
  return '记录了学生的一项操作。'
}
</script>

<template>
  <div class="page-stack teacher-student-audit-page">
    <PageHeader title="学生操作记录" :description="`查询 ${currentClassLabel} 内学生已记录的操作。`" />
    <form class="content-card audit-filter-card" @submit.prevent="search(1)">
      <label>
        学生 / 作业关键字
        <input v-model="keyword" type="search" placeholder="学生姓名、学号或作业名称" />
      </label>
      <label>
        操作类型
        <select v-model="action">
          <option value="">全部操作</option>
          <option v-for="item in actions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <label>
        开始日期
        <input v-model="dateFrom" type="date" />
      </label>
      <label>
        结束日期
        <input v-model="dateTo" type="date" />
      </label>
      <div class="audit-filter-actions">
        <button class="primary-button" type="submit" :disabled="loading">{{ loading ? '查询中…' : '查询' }}</button>
        <button class="secondary-button" type="button" :disabled="loading" @click="clearFilters">清空</button>
      </div>
    </form>
    <InlineMessage :message="error" tone="error" />

    <section class="content-card flush-card audit-results-card">
      <div v-if="loading" class="loading-state">正在查询学生操作记录…</div>
      <div v-else-if="logs.length" class="audit-table teacher-student-audit-table">
        <div class="audit-table-head"><span>时间</span><span>学生</span><span>操作</span><span>对象与说明</span></div>
        <article v-for="log in logs" :key="String(log.id)" class="audit-table-row">
          <span>{{ formatDate(log.created_at) }}</span>
          <strong>{{ text(log.actor_name) || text(log.actor_username) }}<small>{{ text(log.actor_username) }}</small></strong>
          <span class="audit-action-label">{{ actionLabel(log) }}</span>
          <span class="audit-detail"><strong>{{ objectLabel(log) }}</strong><br>{{ description(log) }}</span>
        </article>
      </div>
      <EmptyState v-else-if="searched" title="没有匹配的学生操作记录" description="请调整筛选条件，或确认当前教学班有符合条件的记录。" />
      <EmptyState v-else title="请设置筛选条件" description="填写学生/作业关键字或选择操作、日期范围，点击查询查看记录。" />
      <div v-if="total > 0" class="pagination audit-pagination">
        <span>共 {{ total }} 条，每页 20 条 · 第 {{ currentPage }} / {{ totalPages }} 页</span>
        <button class="secondary-button" type="button" :disabled="loading || currentPage <= 1" @click="search(1)">首页</button>
        <button class="secondary-button" type="button" :disabled="loading || currentPage <= 1" @click="search(currentPage - 1)">上一页</button>
        <button class="secondary-button" type="button" :disabled="loading || currentPage >= totalPages" @click="search(currentPage + 1)">下一页</button>
        <button class="secondary-button" type="button" :disabled="loading || currentPage >= totalPages" @click="search(totalPages)">末页</button>
        <label class="pagination-jump">跳至<input v-model="jumpPage" type="number" min="1" :max="totalPages" :disabled="loading || totalPages <= 1" @keyup.enter="jumpToPage" />页</label>
        <button class="secondary-button" type="button" :disabled="loading || totalPages <= 1" @click="jumpToPage">跳转</button>
      </div>
    </section>
  </div>
</template>
