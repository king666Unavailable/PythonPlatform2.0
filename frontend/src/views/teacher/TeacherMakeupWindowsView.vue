<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createMakeupWindow, fetchMakeupWindows, updateMakeupWindow } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatDate, formatDateTimeInput, toApiDateTime } from '@/utils/format'

type MakeupWindow = Record<string, unknown>
const route = useRoute()
const assignment = ref<Record<string, unknown> | null>(null)
const windows = ref<MakeupWindow[]>([])
const editingId = ref('')
const editorOpen = ref(false)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const editorError = ref('')
const form = reactive({ deadline: '', timeLimit: 0, kind: 'homework', openState: 'yes', targets: '' })

const assignmentId = computed(() => String(route.params.id))
const sortedWindows = computed(() => [...windows.value].sort((a, b) => String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? ''))))

function toIso(value: string) { return toApiDateTime(value) }
function parseTargets(value: string) { return [...new Set(value.replaceAll('，', ',').replaceAll('\n', ',').split(',').map((item) => item.trim()).filter(Boolean))] }
function kindLabel(value: unknown) { return ({ offline: '线下测试', classwork: '课堂测试', homework: '课后作业', exam: '考试' } as Record<string, string>)[String(value)] ?? '未设置' }
function scopeLabel(item: MakeupWindow) { const state = String(item.open_state ?? 'yes'); if (state === 'yes') return '全部学生'; if (state === 'no') return '暂不开放'; const targets = Array.isArray(item.target_usernames) ? item.target_usernames.map(String) : []; return targets.length ? `指定学生：${targets.join('、')}` : '指定学生（名单为空）' }
function scopeTone(item: MakeupWindow): 'green' | 'orange' | 'red' { const state = String(item.open_state ?? 'yes'); return state === 'yes' ? 'green' : state === 'some' ? 'orange' : 'red' }
function activeLabel(item: MakeupWindow) { return item.is_active ? '开放中' : '未开放' }
function resetForm() { editingId.value = ''; form.deadline = ''; form.timeLimit = 0; form.kind = 'homework'; form.openState = 'yes'; form.targets = ''; editorError.value = ''; editorOpen.value = true }
function openEdit(item: MakeupWindow) { editingId.value = String(item.id); form.deadline = formatDateTimeInput(item.deadline); form.timeLimit = Number(item.time_limit ?? 0) || 0; form.kind = String(item.assignment_kind || 'homework'); form.openState = String(item.open_state || 'yes'); form.targets = Array.isArray(item.target_usernames) ? item.target_usernames.join('\n') : ''; editorError.value = ''; editorOpen.value = true }
function closeEditor() { editorOpen.value = false; editingId.value = '' }

async function load() {
  loading.value = true; error.value = ''
  try { const result = await fetchMakeupWindows(assignmentId.value); assignment.value = result.assignment; windows.value = result.makeup_windows } catch (cause) { error.value = cause instanceof Error ? cause.message : '补交设置加载失败。' } finally { loading.value = false }
}

async function save() {
  const targets = parseTargets(form.targets)
  editorError.value = ''
  if (!form.deadline) { editorError.value = '请填写补交截止时间。'; return }
  if (form.openState === 'some' && !targets.length) { editorError.value = '请填写指定学生名单。'; return }
  saving.value = true; error.value = ''; success.value = ''
  const payload = { deadline: toIso(form.deadline), time_limit: form.timeLimit, assignment_kind: form.kind, open_state: form.openState, target_usernames: targets, is_active: true }
  try { if (editingId.value) await updateMakeupWindow(assignmentId.value, editingId.value, payload); else await createMakeupWindow(assignmentId.value, payload); closeEditor(); success.value = '补交设置已保存。'; await load() } catch (cause) { editorError.value = cause instanceof Error ? cause.message : '补交设置保存失败。' } finally { saving.value = false }
}

async function setActive(item: MakeupWindow, active: boolean) {
  if (!active && !window.confirm('确定关闭这条补交机会吗？已有提交记录不会被删除。')) return
  saving.value = true; error.value = ''; success.value = ''
  try { await updateMakeupWindow(assignmentId.value, String(item.id), { deadline: item.deadline, time_limit: item.time_limit, assignment_kind: item.assignment_kind, open_state: item.open_state, target_usernames: item.target_usernames, is_active: active }); success.value = active ? '补交机会已开放。' : '补交机会已关闭。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : (active ? '补交机会开放失败。' : '补交机会关闭失败。') } finally { saving.value = false }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack makeup-page">
    <PageHeader title="补交设置">
      <template #actions><RouterLink class="secondary-button button-link" to="/teacher/assignments">返回作业管理</RouterLink></template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <InlineMessage :message="success" tone="success" />
    <div v-if="loading" class="loading-state">正在加载补交设置…</div>
    <template v-else>
      <section class="content-card makeup-heading-card"><div><h2>{{ assignment?.title }}</h2></div><button type="button" @click="resetForm">新增补交</button></section>
      <div v-if="editorOpen" class="modal-backdrop" @click.self="closeEditor">
        <section class="modal-card makeup-editor" role="dialog" aria-modal="true" aria-labelledby="makeup-editor-title">
          <div class="section-heading"><h3 id="makeup-editor-title">{{ editingId ? '修改补交' : '新增补交' }}</h3><button class="icon-button" type="button" aria-label="关闭" @click="closeEditor">×</button></div><InlineMessage :message="editorError" tone="error" />
          <div class="form-grid two-columns"><label>补交截止时间<input v-model="form.deadline" type="datetime-local" step="60" lang="zh-CN" /></label><label>答题时长<select v-model="form.timeLimit"><option :value="0">沿用原作业设置</option><option :value="20">20 分钟</option><option :value="30">30 分钟</option><option :value="60">60 分钟</option></select></label><label>作业类型<select v-model="form.kind"><option value="offline">线下测试</option><option value="classwork">课堂测试</option><option value="homework">课后作业</option><option value="exam">考试</option></select></label><label>开放范围<select v-model="form.openState"><option value="yes">全部开放</option><option value="some">部分开放</option><option value="no">暂不开放</option></select></label><label v-if="form.openState === 'some'" class="full-width-field">开放对象（学号/用户名，逗号或换行分隔）<textarea v-model="form.targets" rows="4" placeholder="例如：jyw, 20260001"></textarea></label></div>
          <div class="modal-actions"><button class="secondary-button" type="button" @click="closeEditor">取消</button><button type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存设置' }}</button></div>
        </section>
      </div>
      <section class="content-card flush-card"><div v-if="sortedWindows.length" class="makeup-window-table"><div class="makeup-window-head"><span>补交截止时间</span><span>答题时长</span><span>作业类型</span><span>开放对象</span><span>状态</span><span>操作</span></div><article v-for="item in sortedWindows" :key="String(item.id)" class="makeup-window-row"><strong>{{ formatDate(item.deadline, '不限') }}</strong><span>{{ Number(item.time_limit) ? `${item.time_limit} 分钟` : '沿用原作业设置' }}</span><span>{{ kindLabel(item.assignment_kind) }}</span><StatusBadge :label="scopeLabel(item)" :tone="scopeTone(item)" /><StatusBadge :label="activeLabel(item)" :tone="item.is_active ? 'green' : 'red'" /><div class="row-actions"><button class="small-button secondary-button" type="button" @click="openEdit(item)">修改</button><button v-if="item.is_active" class="small-button" type="button" :disabled="saving" @click="setActive(item, false)">关闭</button><button v-else class="small-button" type="button" :disabled="saving" @click="setActive(item, true)">开放</button></div></article></div><EmptyState v-else title="还没有补交机会" description="点击右上角“新增补交”创建第一条补交设置。" /></section>
    </template>
  </div>
</template>

<style scoped>
.makeup-heading-card { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.makeup-heading-card h2 { margin: 0; color: var(--ink); font-size: 22px; }
.makeup-heading-card p { margin: 8px 0 0; color: var(--muted); font-size: 15px; }
.makeup-page .flush-card { overflow-x: auto; }
.makeup-editor { display: grid; width: min(760px, calc(100vw - 40px)); max-height: min(760px, calc(100vh - 40px)); overflow-y: auto; gap: 20px; }
.makeup-window-table { width: max-content; min-width: 100%; overflow-x: auto; }
.makeup-window-head, .makeup-window-row { display: grid; grid-template-columns: 190px 160px 150px 300px 110px 190px; justify-content: start; align-items: center; gap: 16px; padding: 17px 26px; }
.makeup-window-head { color: var(--muted); background: #f8fafc; font-size: 16px; font-weight: 700; }
.makeup-window-row { min-height: 76px; border-top: 1px solid #edf1f6; color: #35445a; font-size: 16px; }
.makeup-window-row strong { color: var(--ink); font-size: 18px; }
.makeup-window-row .status-badge { min-height: 34px; padding: 5px 12px; font-size: 16px; }
.makeup-window-row .row-actions { flex-wrap: nowrap; gap: 10px; }
.makeup-window-row .small-button { min-height: 42px; padding: 8px 14px; font-size: 15px; white-space: nowrap; }
@media (max-width: 900px) { .makeup-heading-card { align-items: stretch; flex-direction: column; } .makeup-window-table { min-width: 1100px; } }
</style>
