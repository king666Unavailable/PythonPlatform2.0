<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createAssignment, fetchQuestions, fetchTeacherAssignments, updateAssignment } from '@/api/client'
import type { QuestionSummary } from '@/types/question'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { assignmentKindLabel, formatDate, formatDateTimeInput, sortAssignmentsByDeadlineDesc, statusTone, toApiDateTime } from '@/utils/format'

const assignments = ref<Array<Record<string, unknown>>>([])
const questions = ref<QuestionSummary[]>([])
const selectedQuestions = ref<string[]>([])
const title = ref('')
const deadline = ref('')
const timeLimit = ref(0)
const assignmentKind = ref('homework')
const openState = ref('yes')
const targetUsernames = ref('')
const keyword = ref('')
const creating = ref(false)
const questionLoading = ref(false)
const showCreator = ref(false)
const loading = ref(true)
const error = ref('')
const success = ref('')
const editing = ref<Record<string, unknown> | null>(null)
const editingTargetUsernames = ref('')
const creatorError = ref('')
const editingError = ref('')
const openStateFilter = ref('all')
const router = useRouter()
const selectedCount = computed(() => selectedQuestions.value.length)
const openStateFilters = [{ label: '全部', value: 'all' }, { label: '全部开放', value: 'yes' }, { label: '部分开放', value: 'some' }, { label: '暂不开放', value: 'no' }]
const filteredAssignments = computed(() => openStateFilter.value === 'all' ? assignments.value : assignments.value.filter((item) => String(item.open_state ?? 'no') === openStateFilter.value))

async function load() {
  loading.value = true; error.value = ''
  try { const result = await fetchTeacherAssignments(); assignments.value = sortAssignmentsByDeadlineDesc(result.items).map((item) => ({ ...item, status: openStateLabel(item.open_state) })) } catch (cause) { error.value = cause instanceof Error ? cause.message : '作业数据加载失败。' } finally { loading.value = false }
}
async function fetchAllQuestionMatches(titleKeyword = '', pointKeyword = '') { const firstPage = await fetchQuestions(titleKeyword, '', pointKeyword, 1, 100); const totalPages = firstPage.pagination?.total_pages ?? 1; const remainingPages = totalPages > 1 ? await Promise.all(Array.from({ length: totalPages - 1 }, (_, index) => fetchQuestions(titleKeyword, '', pointKeyword, index + 2, 100))) : []; return [firstPage, ...remainingPages].flatMap((page) => page.items) }
async function loadQuestions() { const term = keyword.value.trim(); if (!term) { questions.value = []; return }; questionLoading.value = true; error.value = ''; try { const [titleMatches, pointMatches] = await Promise.all([fetchAllQuestionMatches(term), fetchAllQuestionMatches('', term)]); const seen = new Set<string>(); questions.value = [...titleMatches, ...pointMatches].filter((question) => { const id = String(question.id); if (seen.has(id)) return false; seen.add(id); return true }) } catch (cause) { questions.value = []; error.value = cause instanceof Error ? cause.message : '题目搜索失败。' } finally { questionLoading.value = false } }
function toIso(value: string) { return toApiDateTime(value) }
function openStateLabel(value: unknown) { return ({ yes: '全部开放', some: '部分开放', no: '暂不开放' } as Record<string, string>)[String(value)] ?? '暂不开放' }
function timeLimitLabel(value: unknown) { const minutes = Number(value ?? 0); return Number.isFinite(minutes) && minutes > 0 ? `${minutes} 分钟` : '不限时' }
function parseUsernames(value: string) { return [...new Set(value.replaceAll('，', ',').replaceAll('\n', ',').split(',').map((item) => item.trim()).filter(Boolean))] }
function viewStatistics(id: string) { void router.push({ name: 'teacher-assignment-statistics', params: { id } }) }
function openMakeup(item: Record<string, unknown>) { void router.push({ name: 'teacher-assignment-makeups', params: { id: String(item.id) } }) }
function openEdit(item: Record<string, unknown>) { editing.value = { ...item, deadline: formatDateTimeInput(item.deadline) }; editingTargetUsernames.value = Array.isArray(item.target_usernames) ? item.target_usernames.join('\n') : ''; editingError.value = '' }
async function create() { const targets = parseUsernames(targetUsernames.value); creatorError.value = ''; if (!title.value.trim() || !selectedCount.value) { creatorError.value = '请填写作业名称并至少选择一道题。'; return }; if (openState.value === 'some' && !targets.length) { creatorError.value = '请填写至少一名指定学生，或改为立即开放。'; return }; creating.value = true; error.value = ''; success.value = ''; try { await createAssignment({ title: title.value.trim(), questions: selectedQuestions.value, deadline: toIso(deadline.value), time_limit: timeLimit.value, assignment_kind: assignmentKind.value, open_state: openState.value, target_usernames: targets }); title.value = ''; selectedQuestions.value = []; targetUsernames.value = ''; assignmentKind.value = 'homework'; showCreator.value = false; success.value = '作业已发布。'; await load() } catch (cause) { creatorError.value = cause instanceof Error ? cause.message : '作业创建失败。' } finally { creating.value = false } }
async function saveEdit() { if (!editing.value) return; const targets = parseUsernames(editingTargetUsernames.value); editingError.value = ''; if (editing.value.open_state === 'some' && !targets.length) { editingError.value = '请填写至少一名指定学生，或改为开放。'; return }; try { await updateAssignment(String(editing.value.id), { deadline: toIso(String(editing.value.deadline ?? '')), time_limit: Number(editing.value.time_limit ?? 0) || 0, open_state: editing.value.open_state, target_usernames: targets }); editing.value = null; success.value = '作业设置已更新。'; await load() } catch (cause) { editingError.value = cause instanceof Error ? cause.message : '作业设置保存失败。' } }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="作业管理"><template #actions><button type="button" @click="showCreator = !showCreator">{{ showCreator ? '收起创建面板' : '布置新作业' }}</button></template></PageHeader>
    <InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" />
    <div class="tabs assignment-filter-tabs" role="tablist"><button v-for="item in openStateFilters" :key="item.value" type="button" :class="{ active: openStateFilter === item.value }" @click="openStateFilter = item.value">{{ item.label }}</button></div>
    <section v-if="showCreator" class="content-card creator-card">
      <div class="section-heading"><h3>布置新作业</h3><StatusBadge :label="`已选 ${selectedCount} 题`" tone="blue" /></div>
      <InlineMessage :message="creatorError" tone="error" />
      <div class="form-grid two-columns"><label>作业名称<input v-model="title" placeholder="例如：循环结构练习" /></label><label>截止时间<input v-model="deadline" type="datetime-local" step="60" lang="zh-CN" /></label><label>答题时长<select v-model="timeLimit"><option :value="0">不限时</option><option :value="20">20 分钟</option><option :value="30">30 分钟</option><option :value="60">60 分钟</option></select></label><label>作业类型<select v-model="assignmentKind"><option value="offline">线下测试</option><option value="classwork">课堂测试</option><option value="homework">课后作业</option><option value="exam">考试</option></select></label><label>开放范围<select v-model="openState"><option value="yes">全部学生</option><option value="some">指定学生</option><option value="no">暂不开放</option></select></label><label v-if="openState === 'some'" class="full-width-field">指定学生（学号/用户名，逗号或换行分隔）<textarea v-model="targetUsernames" rows="3"></textarea></label></div>
      <div class="picker-heading"><strong>选择题目</strong><label class="compact-search"><input v-model="keyword" placeholder="搜索题目名称或知识点" @change="loadQuestions" @keyup.enter="loadQuestions" /></label></div><div v-if="!keyword.trim()" class="question-picker-hint">请输入题目名称或知识点后搜索。</div><div v-else-if="questionLoading" class="question-picker-hint">正在搜索题目…</div><div v-else-if="!questions.length" class="question-picker-hint">没有找到匹配的题目。</div><div v-else class="question-picker"><label v-for="question in questions" :key="question.id" class="picker-item"><input v-model="selectedQuestions" type="checkbox" :value="question.title" /><span><strong>{{ question.title }}</strong><small>{{ question.type }} · 难度 {{ question.difficulty ?? '未设置' }} · 知识点 {{ question.point_titles?.length ? question.point_titles.join('、') : '未关联' }}</small></span></label></div><button type="button" :disabled="creating" @click="create">{{ creating ? '发布中…' : '发布作业' }}</button>
    </section>
    <div v-if="loading" class="loading-state">正在加载作业…</div>
    <section v-else class="content-card flush-card"><div v-if="filteredAssignments.length" class="assignment-table teacher-table"><div class="assignment-table-head"><span>作业</span><span>截止时间</span><span>答题时长</span><span>开放情况</span><span>操作</span></div><article v-for="item in filteredAssignments" :key="String(item.id)" class="assignment-table-row"><div class="assignment-title-cell"><strong>{{ item.title }}</strong><small>{{ assignmentKindLabel(item.assignment_kind) }}</small></div><span class="assignment-deadline-cell">{{ formatDate(item.deadline, '不限') }}</span><span class="assignment-time-cell">{{ timeLimitLabel(item.time_limit) }}</span><StatusBadge class="assignment-status-cell" :label="item.status === 'published' ? '已发布' : String(item.status ?? '草稿')" :tone="statusTone(String(item.status ?? ''))" /><div class="row-actions assignment-action-cell"><button class="small-button secondary-button" type="button" @click="openEdit(item)">设置</button><button class="small-button" type="button" @click="viewStatistics(String(item.id))">查看统计</button><button class="small-button secondary-button" type="button" @click="openMakeup(item)">补交开放</button></div></article></div><EmptyState v-else title="还没有布置作业" description="请切换开放情况筛选或创建新的作业。" /></section>
    <div v-if="editing" class="modal-backdrop"><section class="modal-card"><div class="section-heading"><h3>调整作业设置</h3><button class="icon-button" type="button" aria-label="关闭" @click="editing = null">×</button></div><InlineMessage :message="editingError" tone="error" /><label>截止时间<input v-model="editing.deadline" type="datetime-local" step="60" lang="zh-CN" /></label><label>答题时长<select v-model.number="editing.time_limit"><option :value="0">不限时</option><option :value="20">20 分钟</option><option :value="30">30 分钟</option><option :value="60">60 分钟</option></select></label><label>开放范围<select v-model="editing.open_state"><option value="yes">全部学生</option><option value="some">指定学生</option><option value="no">关闭</option></select></label><label v-if="editing.open_state === 'some'">指定学生<textarea v-model="editingTargetUsernames" rows="3"></textarea></label><div class="modal-actions"><button class="secondary-button" type="button" @click="editing = null">取消</button><button type="button" @click="saveEdit">保存设置</button></div></section></div>
  </div>
</template>
