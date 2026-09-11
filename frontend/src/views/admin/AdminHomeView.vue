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
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="平台概览" description="查看账号规模和最近的平台操作。" /><InlineMessage :message="error" tone="error" /><div v-if="loading" class="loading-state">正在加载平台数据…</div><template v-else><div class="metric-grid"><MetricCard label="账号总数" :value="totalAccounts" hint="学生、教师和管理员" /><MetricCard label="启用账号" :value="activeAccounts" hint="当前可登录账号" tone="green" /><MetricCard label="停用账号" :value="Number(statusCounts.inactive || 0)" hint="需要关注的状态" tone="orange" /><MetricCard label="近期操作" :value="logs.length" hint="审计记录" tone="purple" /></div><div class="dashboard-grid"><section class="content-card"><div class="section-heading"><div><h3>账号概览</h3></div><RouterLink class="text-link" to="/admin/accounts">进入账号管理</RouterLink></div><div class="role-count-list"><div><span>学生</span><strong>{{ roleCounts.student || 0 }}</strong></div><div><span>教师</span><strong>{{ roleCounts.teacher || 0 }}</strong></div><div><span>管理员</span><strong>{{ roleCounts.admin || 0 }}</strong></div></div></section><section class="content-card"><div class="section-heading"><div><h3>最近操作</h3><p>用于追踪账号和教学资源变更。</p></div><RouterLink class="text-link" to="/admin/audit">查看全部</RouterLink></div><div v-if="logs.length" class="activity-list"><div v-for="log in logs.slice(0, 5)" :key="String(log.id)" class="activity-row"><span>{{ log.action || '平台操作' }}</span><small>{{ formatDate(log.created_at) }}</small></div></div><EmptyState v-else title="暂无操作记录" /></section></div></template></div>
</template>
