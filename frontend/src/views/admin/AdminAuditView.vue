<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAuditLogs } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatDate } from '@/utils/format'

const logs = ref<Array<Record<string, unknown>>>([])
const loading = ref(true)
const error = ref('')
async function load() { loading.value = true; try { logs.value = (await fetchAuditLogs()).items } catch (cause) { error.value = cause instanceof Error ? cause.message : '操作记录加载失败。' } finally { loading.value = false } }
onMounted(() => void load())
</script>

<template><div class="page-stack"><PageHeader title="操作记录" description="查看账号、作业和教学资源的最近变更。" /><InlineMessage :message="error" tone="error" /><section class="content-card flush-card"><div v-if="loading" class="loading-state">正在加载操作记录…</div><div v-else-if="logs.length" class="audit-table"><div class="audit-table-head"><span>时间</span><span>操作人</span><span>操作</span><span>对象</span><span>说明</span></div><article v-for="log in logs" :key="String(log.id)" class="audit-table-row"><span>{{ formatDate(log.created_at) }}</span><strong>{{ log.actor_username }}</strong><span>{{ log.action }}</span><span>{{ log.resource_type || '—' }}</span><span class="muted">{{ log.detail || '—' }}</span></article></div><EmptyState v-else title="暂无操作记录" description="发生账号或资源变更后会显示在这里。" /></section></div></template>
