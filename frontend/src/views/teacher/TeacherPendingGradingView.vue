<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchManualGradeReport, fetchPendingManualGrades, saveManualGradeReport } from '@/api/client'
import type { PendingManualGradeItem, TeacherAssignmentGradeReport } from '@/types/teacher'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const router = useRouter()
const items = ref<PendingManualGradeItem[]>([])
const page = ref(1)
const totalPages = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const success = ref('')
const selected = ref<PendingManualGradeItem | null>(null)
const report = ref<TeacherAssignmentGradeReport | null>(null)
const reportLoading = ref(false)
const saving = ref(false)
const editorError = ref('')

const scoreInputsValid = computed(() => Boolean(
  report.value?.items.length
  && report.value.items.every((item) => item.score !== null && Number.isFinite(Number(item.score)) && Number(item.score) >= 0 && Number(item.score) <= 100),
))
const scorePreview = computed(() => {
  const gradeItems = report.value?.items ?? []
  if (!gradeItems.length || !gradeItems.every((item) => item.score !== null && Number.isFinite(Number(item.score)))) return null
  const weighted = gradeItems.every((item) => item.max_score !== null && Number.isFinite(Number(item.max_score)) && Number(item.max_score) >= 0)
    && gradeItems.reduce((sum, item) => sum + Number(item.max_score), 0) > 0
  if (weighted) {
    const max = gradeItems.reduce((sum, item) => sum + Number(item.max_score), 0)
    const score = gradeItems.reduce((sum, item) => sum + Number(item.score) / 100 * Number(item.max_score), 0)
    return { score: Math.round(score * 100) / 100, max: Math.round(max * 100) / 100, weighted: true }
  }
  const score = gradeItems.reduce((sum, item) => sum + Number(item.score), 0) / gradeItems.length
  return { score: Math.round(score * 100) / 100, max: 100, weighted: false }
})

async function load(targetPage = page.value) {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchPendingManualGrades(targetPage)
    items.value = result.items
    page.value = result.meta.page
    total.value = result.meta.total
    totalPages.value = result.meta.total_pages
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '待批改列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function openGrading(item: PendingManualGradeItem) {
  selected.value = item
  report.value = null
  editorError.value = ''
  reportLoading.value = true
  try {
    report.value = (await fetchManualGradeReport(item.submission_id)).grade_report
  } catch (cause) {
    editorError.value = cause instanceof Error ? cause.message : '提交详情加载失败。'
  } finally {
    reportLoading.value = false
  }
}

async function saveGrades() {
  if (!report.value) return
  saving.value = true
  editorError.value = ''
  try {
    const grades = report.value.items.map((item) => ({ position: item.position, score: Number(item.score) }))
    await saveManualGradeReport(report.value.submission_id, grades)
    selected.value = null
    report.value = null
    success.value = '判卷已完成，逐题成绩和总分已更新。'
    await load(page.value)
  } catch (cause) {
    editorError.value = cause instanceof Error ? cause.message : '保存判卷结果失败。'
  } finally {
    saving.value = false
  }
}

function closeEditor() {
  if (saving.value) return
  selected.value = null
  report.value = null
  editorError.value = ''
}

function formatDate(value: string | null) {
  if (!value) return '时间未记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

function questionType(code: string) {
  return ({ '1': '选择题', '2': '填空题', '3': '编程题', '4': '程序填空题' } as Record<string, string>)[code] ?? '未知题型'
}

function gradeStatus(item: TeacherAssignmentGradeReport['items'][number]) {
  if (item.score !== null && ['graded', 'code_structure_error', 'function_not_found'].includes(item.status)) return '已自动判卷，可复核'
  if (item.status === 'pending_test_cases') return '未配置测试用例'
  if (item.status === 'grading_unavailable') return '自动判题服务不可用'
  if (item.status === 'code_structure_error') return '代码结构异常，待教师评分'
  if (item.status === 'function_not_found') return '未找到函数，待教师评分'
  return '待教师判卷'
}

function answerText(value: unknown) {
  if (value == null || value === '') return '未作答'
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

onMounted(() => void load(1))
</script>

<template>
  <div class="page-stack">
    <PageHeader title="待批改作业" description="查看当前教学班尚未完成判卷的提交，逐题评分后完成判卷。">
      <template #actions>
        <button class="secondary-button" type="button" @click="router.push('/teacher/assignments')">返回作业管理</button>
        <button class="secondary-button" type="button" :disabled="loading" @click="load(page)">刷新列表</button>
      </template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <InlineMessage :message="success" tone="success" />

    <section class="content-card flush-card">
      <div class="section-heading padded-heading"><div><h3>待批改提交</h3><p>共 {{ total }} 份提交；按提交时间从早到晚排列。</p></div></div>
      <div v-if="loading" class="loading-state">正在加载待批改列表…</div>
      <div v-else-if="items.length" class="assignment-table pending-grading-table">
        <div class="assignment-table-head"><span>作业</span><span>学生</span><span>提交时间</span><span>提交方式</span><span>待处理题数</span><span>操作</span></div>
        <article v-for="item in items" :key="item.submission_id" class="assignment-table-row">
          <div class="assignment-title-cell"><strong>{{ item.assignment_title }}</strong><small>第 {{ item.pending_item_count }} 题待处理</small></div>
          <div class="assignment-title-cell"><strong>{{ item.student_name }}</strong><small>{{ item.student_username }}</small></div>
          <span class="assignment-deadline-cell">{{ formatDate(item.submitted_at) }}</span>
          <StatusBadge :label="item.submission_mode === 'makeup' ? '补交' : '正常提交'" :tone="item.submission_mode === 'makeup' ? 'orange' : 'blue'" />
          <span>{{ item.pending_item_count }} 题</span>
          <div class="row-actions"><button class="small-button" type="button" @click="openGrading(item)">开始批改</button></div>
        </article>
      </div>
      <EmptyState v-else-if="!loading" title="目前没有待批改提交" description="本教学班所有提交均已完成判卷。" />
      <div v-if="totalPages > 1" class="pagination">
        <span>共 {{ total }} 份，第 {{ page }} / {{ totalPages }} 页</span>
        <button class="secondary-button" type="button" :disabled="loading || page <= 1" @click="load(page - 1)">上一页</button>
        <button class="secondary-button" type="button" :disabled="loading || page >= totalPages" @click="load(page + 1)">下一页</button>
      </div>
    </section>

    <div v-if="selected" class="modal-backdrop pending-grade-backdrop" @click.self="closeEditor">
      <section class="modal-card pending-grade-modal" role="dialog" aria-modal="true" aria-labelledby="pending-grade-title">
        <div class="section-heading">
          <div>
            <h3 id="pending-grade-title">教师手动判卷</h3>
            <p>{{ selected.assignment_title }} · {{ selected.student_name }}（{{ selected.student_username }}）· {{ selected.submission_mode === 'makeup' ? '补交' : '正常提交' }} · {{ formatDate(selected.submitted_at) }}</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" :disabled="saving" @click="closeEditor">×</button>
        </div>
        <InlineMessage :message="editorError" tone="error" />
        <div v-if="reportLoading" class="loading-state">正在读取作答内容…</div>
        <template v-else-if="report">
          <p class="grade-editor-hint">逐题按百分制输入得分（0–100）。已有自动判卷分数会预填；待判题请按作答内容评分。保存后整份提交标记为已判卷。</p>
          <div class="pending-grade-items">
            <article v-for="item in report.items" :key="item.position" class="pending-grade-item">
              <header><div><strong>第 {{ item.position + 1 }} 题：{{ item.title }}</strong><span>{{ questionType(item.type_code || '') }}<template v-if="item.time_spent_seconds != null"> · 作答 {{ item.time_spent_seconds }} 秒</template></span></div><StatusBadge :label="gradeStatus(item)" :tone="item.score == null ? 'orange' : 'green'" /></header>
              <div class="pending-grade-answer"><strong>学生作答</strong><pre>{{ answerText(item.answer) }}</pre></div>
              <p v-if="item.feedback" class="pending-grade-feedback">系统提示：{{ item.feedback }}</p>
              <label class="pending-grade-score">逐题得分 <span><input v-model.number="item.score" type="number" min="0" max="100" step="0.01" placeholder="请输入 0–100" /><i>%</i></span><small v-if="item.max_score != null">本题分值 {{ item.max_score }} 分</small></label>
            </article>
          </div>
          <p class="grade-editor-current-total">
            {{ scorePreview?.weighted ? '按题目分值加权总分' : '百分制平均分（题目分值未完整设置）' }}：
            {{ scorePreview ? scorePreview.score + ' / ' + scorePreview.max + ' 分' : '待完成逐题评分' }}
          </p>
        </template>
        <div class="modal-actions">
          <button class="secondary-button" type="button" :disabled="saving" @click="closeEditor">取消</button>
          <button type="button" :disabled="saving || reportLoading || !report || !scoreInputsValid" @click="saveGrades">{{ saving ? '保存中…' : '保存并完成判卷' }}</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.pending-grading-table { min-width: 920px; }
.pending-grading-table .assignment-table-head,
.pending-grading-table .assignment-table-row { grid-template-columns: minmax(150px, 1.4fr) minmax(130px, 1fr) minmax(160px, 1fr) minmax(100px, .7fr) minmax(90px, .6fr) minmax(100px, .6fr); }
.pending-grade-backdrop { z-index: 100; }
.pending-grade-modal { width: min(1100px, calc(100vw - 40px)); max-height: calc(100vh - 40px); overflow: auto; }
.pending-grade-items { display: grid; gap: 14px; max-height: 58vh; overflow: auto; padding: 2px 4px 2px 0; }
.pending-grade-item { display: grid; gap: 10px; border: 1px solid var(--border-color, #dbe3ef); border-radius: 12px; padding: 14px 16px; }
.pending-grade-item > header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.pending-grade-item > header div { display: grid; gap: 5px; }
.pending-grade-item > header span, .pending-grade-feedback, .pending-grade-score small { color: var(--muted, #64748b); font-size: 13px; }
.pending-grade-answer { display: grid; gap: 6px; }
.pending-grade-answer pre { margin: 0; padding: 12px; border-radius: 8px; background: var(--surface-muted, #f3f6fa); white-space: pre-wrap; overflow-wrap: anywhere; font: 13px/1.5 ui-monospace, Consolas, monospace; max-height: 220px; overflow: auto; }
.pending-grade-feedback { margin: 0; }
.pending-grade-score { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pending-grade-score > span { display: inline-flex; align-items: center; gap: 6px; }
.pending-grade-score input { width: 130px; }
.pending-grade-score i { font-style: normal; }
@media (max-width: 700px) {
  .pending-grade-modal { width: calc(100vw - 20px); max-height: calc(100vh - 20px); }
  .pending-grade-item > header { flex-direction: column; }
}
</style>
