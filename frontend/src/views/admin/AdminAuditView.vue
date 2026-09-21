<script setup lang="ts">
import { computed, ref } from 'vue'
import { fetchAuditLogs } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { assignmentKindLabel, formatDate } from '@/utils/format'

const categories = [
  { id: 'all', label: '全部操作' },
  { id: 'login', label: '登录记录' },
  { id: 'assignment', label: '作业记录' },
  { id: 'account', label: '账号记录' },
  { id: 'other', label: '其他操作' },
]
const category = ref('all')
const keyword = ref('')
const actionFilter = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const logs = ref<Array<Record<string, unknown>>>([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const currentPage = ref(1)
const totalRecords = ref(0)
const totalPages = ref(0)
const jumpPage = ref('')

async function search(targetPage = 1) {
  if (category.value === 'all' && !keyword.value.trim() && !actionFilter.value && !dateFrom.value && !dateTo.value) {
    error.value = '全部操作查询请至少填写一个筛选条件，或切换到具体类别后查询。'
    return
  }
  loading.value = true
  error.value = ''
  searched.value = true
  currentPage.value = targetPage
  try {
    const result = await fetchAuditLogs({
      category: category.value,
      q: keyword.value.trim(),
      action: actionFilter.value,
      from: dateFrom.value,
      to: dateTo.value,
      page: targetPage,
    })
    logs.value = result.items
    totalRecords.value = result.meta.total
    totalPages.value = result.meta.total_pages || 0
    currentPage.value = result.meta.page || targetPage
    jumpPage.value = String(currentPage.value)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '操作记录加载失败。'
    logs.value = []
    totalRecords.value = 0
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

function selectCategory(nextCategory: string) {
  category.value = nextCategory
  actionFilter.value = ''
  logs.value = []
  searched.value = false
  currentPage.value = 1
  totalRecords.value = 0
  totalPages.value = 0
  jumpPage.value = ''
  error.value = ''
}

function clearFilters() {
  keyword.value = ''
  actionFilter.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  logs.value = []
  searched.value = false
  currentPage.value = 1
  totalRecords.value = 0
  totalPages.value = 0
  jumpPage.value = ''
  error.value = ''
}

function jumpToPage() {
  const target = Math.min(totalPages.value, Math.max(1, Number.parseInt(jumpPage.value, 10) || 1))
  void search(target)
}

const roleLabels: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
const fieldLabels: Record<string, string> = {
  name: '姓名', gender: '性别', study_class: '行政班', is_active: '状态', password: '登录密码', class_ids: '教学班关系',
  title: '名称', teaching_class: '教学班名称', academic_year: '学年/学期', deadline: '截止时间', time_limit: '答题时长',
  assignment_kind: '作业类型', target_usernames: '开放对象', target_usernames_json: '开放对象', open_to_all: '开放范围',
  allow_view_answers: '标准答案查看权限', analysis: '题目解析', content: '题目内容', answer: '标准答案',
}
const actionLabels: Record<string, string> = {
  'student.login.success': '登录成功', 'teacher.login.success': '登录成功', 'admin.login.success': '登录成功',
  'logout.manual': '主动退出', 'submission.create': '提交作业',
  'question.update': '修改题目', 'question.create': '新增题目', 'question.batch_create': '批量新增题目',
  'account.create': '创建账号', 'account.update': '修改账号', 'account.import': '批量导入账号',
  'class.create': '创建教学班', 'class.update': '修改教学班', 'class.members.update': '调整班级成员',
  'class.student.create': '添加学生', 'class.students.import': '批量导入学生',
  'assignment.create': '创建作业', 'assignment.update': '调整作业',
  'assignment.makeup_window.create': '新增补交机会', 'assignment.makeup_window.update': '调整补交机会',
  'knowledge.create': '新增知识节点', 'ai.approve': '审核通过 AI 题目', 'navigation.visibility.update': '调整功能显示',
}
const actionGroups: Record<string, string[]> = {
  login: ['student.login.success', 'teacher.login.success', 'admin.login.success', 'logout.manual'],
  assignment: [
    'assignment.create', 'assignment.update', 'assignment.makeup_window.create', 'assignment.makeup_window.update', 'submission.create',
  ],
  account: [
    'account.create', 'account.update', 'account.import', 'class.create', 'class.update', 'class.members.update',
    'class.student.create', 'class.students.import',
  ],
  other: ['question.create', 'question.update', 'question.batch_create', 'knowledge.create', 'ai.approve', 'navigation.visibility.update'],
}
const actionOptionLabels: Record<string, string> = {
  'student.login.success': '学生登录成功',
  'teacher.login.success': '教师登录成功',
  'admin.login.success': '管理员登录成功',
}
const hiddenActionFilters = new Set(['navigation.visibility.update'])
const actionOptions = computed(() => {
  const actions = category.value === 'all' ? Object.keys(actionLabels) : actionGroups[category.value] || []
  return actions
    .map((value) => ({ value, label: actionOptionLabels[value] || actionLabels[value] }))
    .filter((item) => item.label && !hiddenActionFilters.has(item.value))
})

function actionCode(log: Record<string, unknown>) { return String(log.action || '') }
function actionLabel(log: Record<string, unknown>) { return actionLabels[actionCode(log)] || '系统操作' }
function detailOf(log: Record<string, unknown>) {
  return log.detail && typeof log.detail === 'object' ? log.detail as Record<string, unknown> : {}
}
function roleLabel(value: unknown) { return roleLabels[String(value || '')] || '用户' }
function text(value: unknown) { return typeof value === 'string' || typeof value === 'number' ? String(value).trim() : '' }
function countOf(value: unknown) { return Array.isArray(value) ? value.length : Number(value || 0) }
function assignmentSettings(detail: Record<string, unknown>) {
  const settings: string[] = []
  if ('deadline' in detail) settings.push(`截止时间：${formatDate(detail.deadline, '不限')}`)
  if ('time_limit' in detail) settings.push(`答题时长：${Number(detail.time_limit) > 0 ? `${Number(detail.time_limit)} 分钟` : '不限时'}`)
  if ('assignment_kind' in detail && text(detail.assignment_kind)) settings.push(`作业类型：${assignmentKindLabel(detail.assignment_kind)}`)
  if ('open_state' in detail || 'target_usernames' in detail) {
    const state = text(detail.open_state).toLowerCase()
    const scope = state === 'no'
      ? '暂不开放'
      : ['some', 'targeted', 'specific'].includes(state)
        ? `指定学生（${countOf(detail.target_usernames)} 人）`
        : '全部学生'
    settings.push(`开放范围：${scope}`)
  }
  if ('allow_answer_view' in detail || 'allow_view_answers' in detail) {
    const allowed = detail.allow_answer_view ?? detail.allow_view_answers
    settings.push(`标准答案权限：${allowed ? '允许查看' : '不允许查看'}`)
  }
  if ('is_active' in detail) settings.push(`补交状态：${detail.is_active ? '开放' : '关闭'}`)
  return settings.join('；')
}
function fieldNames(values: unknown) {
  if (!Array.isArray(values)) return ''
  const names = values.map((value) => fieldLabels[String(value)]).filter(Boolean)
  return [...new Set(names)].join('、')
}
function accountValue(field: string, value: unknown) {
  if (field === 'gender') return ({ 0: '其他', 1: '男', 2: '女' } as Record<number, string>)[Number(value)] || '未填写'
  if (field === 'is_active') return text(value) || '未知'
  if (field === 'class_ids') return Array.isArray(value) ? (value.length ? value.join('、') : '无') : text(value)
  return text(value) || '未填写'
}
function accountChangeSummary(detail: Record<string, unknown>) {
  const changes = Array.isArray(detail.changes) ? detail.changes as Array<Record<string, unknown>> : []
  if (!changes.length) return fieldNames(detail.fields) ? `修改字段：${fieldNames(detail.fields)}` : '修改了账号信息。'
  return changes.map((change) => {
    const field = String(change.field || '')
    const label = fieldLabels[field] || field
    return `${label}：${accountValue(field, change.before)} → ${accountValue(field, change.after)}`
  }).join('；')
}
function classDescription(value: unknown) {
  if (!value || typeof value !== 'object') return ''
  const item = value as Record<string, unknown>
  const title = text(item.title)
  const teachingClass = text(item.teaching_class)
  const year = text(item.academic_year)
  const label = [title, teachingClass].filter(Boolean).join(' / ') || teachingClass
  return `${label}${year ? `（${year}）` : ''}`
}
function importedStudents(detail: Record<string, unknown>) {
  if (!Array.isArray(detail.students)) return ''
  return detail.students
    .map((item) => item && typeof item === 'object' ? item as Record<string, unknown> : {})
    .map((item) => `${text(item.name) || '未命名'}（${text(item.username)}）`)
    .filter((item) => !item.endsWith('（）'))
    .join('、')
}
function displayObject(log: Record<string, unknown>) {
  const action = actionCode(log)
  const detail = detailOf(log)
  const actor = roleLabel(log.actor_role)
  const title = text(detail.title) || text(detail.assignment_title)
  const teachingClass = text(detail.teaching_class)
  if (action.endsWith('.login.success') || action === 'logout.manual') return `${actor}账号「${text(log.actor_username)}」`
  if (action.startsWith('submission.')) return title ? `作业「${title}」` : '作业已失效'
  if (action.startsWith('account.')) return action === 'account.import' ? `${roleLabel(log.resource_type)}账号批量导入` : `${roleLabel(log.resource_type)}账号「${text(log.resource_id)}」`
  if (action === 'class.create') return teachingClass ? `教学班「${teachingClass}」` : '新教学班'
  if (action === 'class.update') return teachingClass ? `教学班「${teachingClass}」` : '教学班设置'
  if (action === 'class.members.update') return `${roleLabel(detail.role)}成员名单`
  if (action === 'class.student.create' || action === 'class.students.import') {
    const target = classDescription(detail.class)
    return target ? `教学班「${target}」学生名单` : '教学班学生名单'
  }
  if (action.startsWith('assignment.makeup_window.')) return title ? `作业「${title}」的补交设置` : '作业已失效'
  if (action.startsWith('assignment.')) return title ? `作业「${title}」` : '作业已失效'
  if (action.startsWith('question.')) return title ? `题目「${title}」` : '题库题目'
  if (action === 'knowledge.create') {
    const nodeLabels: Record<string, string> = { Class: '课程', Theme: '主题', Knowledge: '知识', Point: '知识点' }
    return `${nodeLabels[text(log.resource_type)] || '知识图谱节点'}${title ? `「${title}」` : ''}`
  }
  if (action === 'ai.approve') return 'AI 出题审核'
  if (action === 'navigation.visibility.update') return `${roleLabel(log.resource_id)}端功能配置`
  return '平台业务操作'
}
function describeLog(log: Record<string, unknown>) {
  const action = actionCode(log)
  const detail = detailOf(log)
  const actor = roleLabel(log.actor_role)
  const title = text(detail.title) || text(detail.assignment_title)
  if (action.endsWith('.login.success')) return `${actor}账号验证通过并登录系统。`
  if (action === 'logout.manual') return `${actor}主动退出登录。`
  if (action === 'submission.create') return title ? `已提交作业「${title}」。` : '已提交作业。'
  if (action === 'account.create') {
    const classes = countOf(detail.class_ids)
    return `创建了${roleLabel(log.resource_type)}账号${classes ? `，关联 ${classes} 个教学班` : ''}。`
  }
  if (action === 'account.update') return `修改了${roleLabel(log.resource_type)}账号「${text(log.resource_id)}」：${accountChangeSummary(detail)}`
  if (action === 'account.import') {
    const students = importedStudents(detail)
    const target = text(detail.teaching_class)
    return `成功向教学班「${target || '未记录班级'}」添加 ${countOf(detail.count)} 名学生${students ? `：${students}。` : '。'}`
  }
  if (action === 'class.create') {
    const course = text(detail.title)
    const className = text(detail.teaching_class)
    const year = text(detail.academic_year)
    return `新建${course ? `课程「${course}」` : '课程'}${className ? `下的教学班「${className}」` : '教学班'}${year ? `（${year}）` : ''}。`
  }
  if (action === 'class.update') return `更新了教学班信息${fieldNames(Object.keys(detail)) ? `：${fieldNames(Object.keys(detail))}` : ''}。`
  if (action === 'class.members.update') {
    const added = countOf(detail.added); const removed = countOf(detail.removed)
    return `调整了${roleLabel(detail.role)}成员：新增 ${added} 人，移除 ${removed} 人。`
  }
  if (action === 'class.students.import') {
    const students = importedStudents(detail)
    const target = classDescription(detail.class)
    return `向教学班「${target || text(log.resource_id) || '未知班级'}」添加了 ${countOf(detail.count)} 名学生${students ? `：${students}` : '。'}`
  }
  if (action === 'class.student.create') {
    const student = detail.student && typeof detail.student === 'object' ? detail.student as Record<string, unknown> : {}
    const target = classDescription(detail.class)
    return `向教学班「${target || text(log.resource_id) || '未知班级'}」添加了学生「${text(student.name) || '未命名'}」（${text(student.username)}）。`
  }
  if (action === 'assignment.create') {
    const settings = assignmentSettings(detail)
    return `创建了作业「${title || '未命名作业'}」${settings ? `，初始设置：${settings}` : ''}。`
  }
  if (action === 'assignment.update') {
    const settings = assignmentSettings(detail) || fieldNames(Object.keys(detail))
    return `调整了${title ? `作业「${title}」` : '已失效作业'}${settings ? `：${settings}` : '设置'}。`
  }
  if (action === 'assignment.makeup_window.create' || action === 'assignment.makeup_window.update') {
    const verb = action.endsWith('.create') ? '新增' : '调整'
    const settings = assignmentSettings(detail)
    return `${verb}了作业「${title || '已失效'}」的补交机会${settings ? `：${settings}` : ''}。`
  }
  if (action === 'question.create') return title ? `新增题目「${title}」。` : '新增了一道题目。'
  if (action === 'question.update') return `修改了题目「${title || '未命名题目'}」${fieldNames(detail.fields) ? `：${fieldNames(detail.fields)}` : ''}。`
  if (action === 'question.batch_create') return `成功新增 ${countOf(detail.count)} 道题目。`
  if (action === 'knowledge.create') return title ? `新增知识图谱节点「${title}」。` : '新增了一个知识图谱节点。'
  if (action === 'ai.approve') return `审核通过并入库 ${countOf(detail.count)} 道 AI 生成题目。`
  if (action === 'navigation.visibility.update') return `更新了 ${countOf(detail.items)} 项功能的显示设置。`
  return '操作已完成。'
}
</script>

<template>
  <div class="page-stack admin-audit-page">
    <PageHeader title="操作记录" description="按类别、具体操作、操作人或时间范围查询系统操作记录。" />

    <nav class="audit-tabs" aria-label="操作记录类别">
      <button
        v-for="item in categories"
        :key="item.id"
        type="button"
        class="audit-tab"
        :class="{ active: category === item.id }"
        :aria-selected="category === item.id"
        role="tab"
        @click="selectCategory(item.id)"
      >{{ item.label }}</button>
    </nav>

    <p class="audit-filter-note">姓名仅在该条记录已保存姓名时可搜索，历史记录不保证支持。</p>
    <form class="content-card audit-filter-card" @submit.prevent="search(1)">
      <label>
        操作人 / 对象关键字
        <input v-model="keyword" type="search" placeholder="学号/用户名、作业名称、对象 ID 或记录内容" />
      </label>
      <label>
        具体操作
        <select v-model="actionFilter">
          <option value="">全部操作</option>
          <option v-for="item in actionOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
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
      <div v-if="loading" class="loading-state">正在查询操作记录…</div>
      <div v-else-if="logs.length" class="audit-table">
        <div class="audit-table-head"><span>时间</span><span>操作人</span><span>操作</span><span>对象</span><span>说明</span></div>
        <article v-for="log in logs" :key="String(log.id)" class="audit-table-row">
          <span>{{ formatDate(String(log.created_at || '')) }}</span>
          <strong>{{ log.actor_username }}<small>{{ roleLabel(log.actor_role) }}</small></strong>
          <span class="audit-action-label">{{ actionLabel(log) }}</span>
          <span class="audit-object-label">{{ displayObject(log) }}</span>
          <span class="audit-detail">{{ describeLog(log) }}</span>
        </article>
      </div>
      <EmptyState
        v-else-if="searched"
        title="没有匹配的操作记录"
        description="请调整筛选条件后重试。"
      />
      <EmptyState
        v-else
        title="请设置筛选条件"
        description="选择记录类别并填写筛选条件，点击查询后查看操作记录。"
      />
      <div v-if="totalRecords > 0" class="pagination audit-pagination">
        <span>共 {{ totalRecords }} 条，每页 20 条 · 第 {{ currentPage }} / {{ totalPages }} 页</span>
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
