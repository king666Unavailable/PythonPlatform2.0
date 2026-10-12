<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchFrozenItems, restoreFrozenEntity } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const items = ref<Array<Record<string, unknown>>>([])
const keyword = ref('')
const type = ref('all')
const loading = ref(true)
const workingId = ref('')
const error = ref('')
const success = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = (await fetchFrozenItems({ type: type.value, q: keyword.value })).items
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '冻结对象加载失败。'
  } finally {
    loading.value = false
  }
}

async function restore(item: Record<string, unknown>) {
  const kind = String(item.entity_type)
  const id = String(item.id)
  if (!window.confirm(`恢复“${item.name}”吗？恢复不会自动启用账号或发布作业。`)) return
  workingId.value = `${kind}:${id}`
  error.value = ''
  success.value = ''
  try {
    await restoreFrozenEntity(kind, id)
    success.value = `已恢复${item.entity_label}“${item.name}”。`
    await load()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '恢复失败。'
  } finally {
    workingId.value = ''
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="冻结管理" description="查看已从日常界面移除的账号、教学班和作业；恢复不会改变对象原有的启用、发布或开放状态。" />
    <section class="account-filters" aria-label="冻结对象筛选">
      <label class="account-search">搜索名称或账号<input v-model="keyword" placeholder="输入姓名、用户名、班级或作业名" @keyup.enter="load" /></label>
      <label>对象类型<select v-model="type" @change="load"><option value="all">全部</option><option value="student">学生账号</option><option value="teacher">教师账号</option><option value="class">教学班</option><option value="assignment">作业</option></select></label>
      <div class="filter-actions"><button type="button" @click="load">查询</button></div>
    </section>
    <section class="content-card flush-card">
      <div class="account-summary"><strong>已删除对象</strong><span>共 {{ items.length }} 项</span></div>
      <InlineMessage :message="error" tone="error" />
      <InlineMessage :message="success" tone="success" />
      <div v-if="loading" class="loading-state">正在加载冻结对象…</div>
      <div v-else-if="items.length" class="account-table frozen-table">
        <div class="account-table-head frozen-table-head"><span>对象类型</span><span>名称 / 标识</span><span>删除时间</span><span>操作</span></div>
        <article v-for="item in items" :key="`${item.entity_type}:${item.id}`" class="account-table-row frozen-table-row">
          <strong>{{ item.entity_label }}</strong>
          <span><strong>{{ item.name }}</strong><small>{{ item.id }}</small></span>
          <span>{{ item.frozen_at || '—' }}</span>
          <div class="row-actions"><button class="small-button" type="button" :disabled="workingId === `${item.entity_type}:${item.id}`" @click="restore(item)">{{ workingId === `${item.entity_type}:${item.id}` ? '恢复中…' : '恢复' }}</button></div>
        </article>
      </div>
      <EmptyState v-else title="没有已删除对象" description="被冻结的对象会显示在这里，可以恢复到日常列表。" />
    </section>
  </div>
</template>

<style scoped>
.account-table.frozen-table { width: max-content; min-width: 0; }
.frozen-table-head,
.frozen-table-row { width: max-content; justify-content: start; grid-template-columns: 150px 400px 210px 120px; }
.frozen-table-row > span:nth-child(2) { display: grid; gap: 4px; }
.frozen-table-row > span:nth-child(3) { white-space: nowrap; }
.frozen-table-row small { color: var(--muted); }
</style>
