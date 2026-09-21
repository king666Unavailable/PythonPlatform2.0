<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchAdminAccounts, fetchAuditLogs } from '@/api/client'
import { RouterLink } from 'vue-router'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatDate } from '@/utils/format'

const accounts = ref<Array<Record<string, unknown>>>([])
const accountMeta = ref<Record<string, unknown>>({ total: 0, role_counts: {}, status_counts: {} })
const logs = ref<Array<Record<string, unknown>>>([])
const loading = ref(true)
const error = ref('')
const roleCounts = computed(() => (accountMeta.value.role_counts || {}) as Record<string, number>)
const statusCounts = computed(() => (accountMeta.value.status_counts || {}) as Record<string, number>)
const totalAccounts = computed(() => Number(accountMeta.value.total || 0))
const activeAccounts = computed(() => Number(statusCounts.value.active || 0))
async function load() { loading.value = true; try { const [accountResult, logResult] = await Promise.all([fetchAdminAccounts({ role: 'all', page: 1, pageSize: 100 }), fetchAuditLogs()]); accounts.value = accountResult.items; accountMeta.value = accountResult.meta; logs.value = logResult.items } catch (cause) { error.value = cause instanceof Error ? cause.message : '平台概览加载失败。' } finally { loading.value = false } }

const roleLabels: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
const actionLabels: Record<string, string> = {
  'student.login.success': '学生登录成功', 'teacher.login.success': '教师登录成功', 'admin.login.success': '管理员登录成功',
  'logout.manual': '主动退出登录', 'submission.create': '提交作业', 'account.create': '创建账号',
  'account.update': '修改账号', 'account.import': '批量导入学生', 'class.create': '创建教学班',
  'class.update': '修改教学班', 'class.members.update': '调整教学班成员', 'class.student.create': '添加学生',
  'class.students.import': '批量导入学生', 'assignment.create': '发布作业', 'assignment.update': '调整作业',
  'assignment.makeup_window.create': '新增补交机会', 'assignment.makeup_window.update': '调整补交机会',
  'question.create': '新增题目', 'question.update': '修改题目', 'question.batch_create': '批量新增题目',
  'knowledge.create': '新增知识图谱节点', 'ai.approve': '审核并入库 AI 题目',
  'navigation.visibility.update': '调整功能显示配置',
}
const accountFieldLabels: Record<string, string> = {
  name: '姓名', gender: '性别', study_class: '行政班', is_active: '账号状态', password: '登录密码', class_ids: '教学班关系',
}
function auditDetail(log: Record<string, unknown>) {
  return log.detail && typeof log.detail === 'object' ? log.detail as Record<string, unknown> : {}
}
function auditText(value: unknown) { return typeof value === 'string' || typeof value === 'number' ? String(value).trim() : '' }
function auditRole(value: unknown) { return roleLabels[String(value || '')] || '用户' }
function auditChangeValue(field: string, value: unknown) {
  if (field === 'gender') return ({ 0: '其他', 1: '男', 2: '女' } as Record<number, string>)[Number(value)] || '未填写'
  if (field === 'is_active' && typeof value === 'boolean') return value ? '启用' : '停用'
  if (Array.isArray(value)) return value.length ? value.map(auditText).join('、') : '无'
  return auditText(value) || '未填写'
}
function auditClass(value: unknown) {
  if (!value || typeof value !== 'object') return ''
  const item = value as Record<string, unknown>
  return [auditText(item.title), auditText(item.teaching_class)].filter(Boolean).join(' / ')
}
function recentOperationDescription(log: Record<string, unknown>) {
  const action = String(log.action || '')
  const detail = auditDetail(log)
  const actor = auditRole(log.actor_role)
  const actorName = auditText(log.actor_username)
  const username = auditText(log.resource_id)
  const title = auditText(detail.title) || auditText(detail.assignment_title)
  const targetClass = auditClass(detail.class) || auditText(detail.teaching_class)

  if (action.endsWith('.login.success')) return `${actor}「${actorName}」登录成功`
  if (action === 'logout.manual') return `${actor}「${actorName}」主动退出登录`
  if (action === 'submission.create') return title ? `学生提交作业「${title}」` : '学生提交作业'
  if (action === 'account.update') {
    const changes = Array.isArray(detail.changes) ? detail.changes as Array<Record<string, unknown>> : []
    const summary = changes.map((change) => {
      const field = String(change.field || '')
      return `${accountFieldLabels[field] || field}：${auditChangeValue(field, change.before)} → ${auditChangeValue(field, change.after)}`
    }).join('；')
    const legacyFields = Array.isArray(detail.fields)
      ? detail.fields.map((field) => accountFieldLabels[String(field)] || String(field)).join('、')
      : ''
    return `修改${auditRole(log.resource_type)}账号「${username}」${summary ? `：${summary}` : legacyFields ? `（${legacyFields}）` : ''}`
  }
  if (action === 'account.create') return `创建${auditRole(log.resource_type)}账号「${username}」`
  if (action === 'account.import') return `向教学班「${targetClass || '未记录班级'}」批量添加 ${Number(detail.count || 0)} 名学生`
  if (action === 'class.student.create') {
    const student = detail.student && typeof detail.student === 'object' ? detail.student as Record<string, unknown> : {}
    return `向教学班「${targetClass || '未知班级'}」添加学生「${auditText(student.name)}」（${auditText(student.username)}）`
  }
  if (action === 'class.students.import') return `向教学班「${targetClass || '未知班级'}」批量添加 ${Number(detail.count || 0)} 名学生`
  if (action === 'class.create') return `创建教学班「${targetClass || '未命名教学班'}」`
  if (action === 'class.update') return `修改教学班「${targetClass || username}」`
  if (action === 'class.members.update') return `调整教学班成员名单（${auditRole(detail.role)}）`
  if (action === 'assignment.create') return `发布作业「${title || '未命名作业'}」`
  if (action === 'assignment.update') return `调整作业「${title || '作业已失效'}」`
  if (action.startsWith('assignment.makeup_window.')) return `${action.endsWith('.create') ? '新增' : '调整'}「${title || '作业'}」的补交机会`
  if (action === 'question.create' || action === 'question.update') return `${actionLabels[action]}「${title || '未命名题目'}」`
  if (action === 'question.batch_create') return `批量新增 ${Number(detail.count || 0)} 道题目`
  if (action === 'knowledge.create') return title ? `新增知识图谱节点「${title}」` : '新增知识图谱节点'
  if (action === 'ai.approve') return `审核并入库 ${Number(detail.count || 0)} 道 AI 题目`
  return actionLabels[action] || '平台业务操作'
}
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="平台概览" description="查看账号规模和最近的平台操作。" /><InlineMessage :message="error" tone="error" /><div v-if="loading" class="loading-state">正在加载平台数据…</div><template v-else><div class="metric-grid"><MetricCard label="账号总数" :value="totalAccounts" hint="学生、教师和管理员" /><MetricCard label="启用账号" :value="activeAccounts" hint="当前可登录账号" tone="green" /><MetricCard label="停用账号" :value="Number(statusCounts.inactive || 0)" hint="需要关注的状态" tone="orange" /><MetricCard label="近期操作" :value="logs.length" hint="审计记录" tone="purple" /></div><div class="dashboard-grid"><section class="content-card"><div class="section-heading"><div><h3>账号概览</h3></div><RouterLink class="text-link" to="/admin/accounts">进入账号管理</RouterLink></div><div class="role-count-list"><div><span>学生</span><strong>{{ roleCounts.student || 0 }}</strong></div><div><span>教师</span><strong>{{ roleCounts.teacher || 0 }}</strong></div><div><span>管理员</span><strong>{{ roleCounts.admin || 0 }}</strong></div></div></section><section class="content-card"><div class="section-heading"><div><h3>最近操作</h3><p>用于追踪账号和教学资源变更。</p></div><RouterLink class="text-link" to="/admin/audit">查看全部</RouterLink></div><div v-if="logs.length" class="activity-list"><div v-for="log in logs.slice(0, 5)" :key="String(log.id)" class="activity-row"><span class="admin-recent-operation">{{ recentOperationDescription(log) }}</span><small>{{ formatDate(log.created_at) }}</small></div></div><EmptyState v-else title="暂无操作记录" /></section></div></template></div>
</template>
