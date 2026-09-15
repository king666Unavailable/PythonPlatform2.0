<script setup lang="ts">
import { computed, ref } from 'vue'
import { createExam, fetchQuestions, generatePaper } from '@/api/client'
import type { QuestionSummary } from '@/types/question'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { toApiDateTime } from '@/utils/format'

const questions = ref<QuestionSummary[]>([])
const selected = ref<string[]>([])
const title = ref('')
const deadline = ref('')
const allowAnswerView = ref(false)
const autoPoint = ref('')
const autoTypeCode = ref('')
const questionKeyword = ref('')
const questionPoint = ref('')
const questionTypeCode = ref('')
const count = ref(10)
const loading = ref(false)
const hasSearched = ref(false)
const working = ref(false)
const error = ref('')
const success = ref('')
const hasQuestionFilter = computed(() => Boolean(questionKeyword.value.trim() || questionPoint.value.trim()))
async function loadQuestions() {
  if (!hasQuestionFilter.value) {
    questions.value = []
    hasSearched.value = false
    return
  }
  loading.value = true
  hasSearched.value = true
  error.value = ''
  try {
    const pageSize = 100
    const firstPage = await fetchQuestions(questionKeyword.value, questionTypeCode.value, questionPoint.value, 1, pageSize)
    const items = [...firstPage.items]
    for (let page = 2; page <= firstPage.pagination.total_pages; page += 1) {
      const nextPage = await fetchQuestions(questionKeyword.value, questionTypeCode.value, questionPoint.value, page, pageSize)
      items.push(...nextPage.items)
    }
    questions.value = items
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '题目加载失败。'
  } finally {
    loading.value = false
  }
}
function resetQuestionSearch() {
  questionKeyword.value = ''
  questionPoint.value = ''
  questionTypeCode.value = ''
  questions.value = []
  hasSearched.value = false
}
function iso(value: string) { return toApiDateTime(value) }
async function createFixed() { if (!title.value.trim() || !selected.value.length) { error.value = '请填写考试名称并选择题目。'; return }; working.value = true; try { await createExam({ title: title.value.trim(), questions: selected.value, deadline: iso(deadline.value), open_state: 'yes', time_limit: 0, allow_answer_view: allowAnswerView.value }); success.value = '考试已创建。'; selected.value = []; allowAnswerView.value = false } catch (cause) { error.value = cause instanceof Error ? cause.message : '考试创建失败。' } finally { working.value = false } }
async function autoCreate() { if (!title.value.trim()) { error.value = '请填写试卷名称。'; return }; working.value = true; try { const result = await generatePaper({ title: title.value.trim(), point_title: autoPoint.value, type_code: autoTypeCode.value, count: count.value, deadline: iso(deadline.value), open_state: 'yes', allow_answer_view: allowAnswerView.value }); success.value = `已完成组卷，共选择 ${result.selected_count} 道题。`; allowAnswerView.value = false } catch (cause) { error.value = cause instanceof Error ? cause.message : '自动组卷失败。' } finally { working.value = false } }
</script>

<template>
  <div class="page-stack"><PageHeader title="组卷与考试" description="选择题目或按知识点自动组卷，确认后发布考试。" /><InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" /><section class="content-card creator-card"><div class="form-grid two-columns"><label>试卷/考试名称<input v-model="title" placeholder="例如：第二章阶段测试" /></label><label>截止时间<input v-model="deadline" type="datetime-local" step="60" lang="zh-CN" /></label><label>自动组卷知识点<input v-model="autoPoint" placeholder="可选，输入知识点" /></label><label>自动组卷题型<select v-model="autoTypeCode"><option value="">全部题型</option><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select></label><label>自动组卷题数<input v-model.number="count" type="number" min="1" max="100" /></label></div><label class="checkbox-field"><input v-model="allowAnswerView" type="checkbox" />允许学生查看标准答案及解析</label><div class="feature-actions"><button type="button" :disabled="working" @click="autoCreate">按条件自动组卷</button><button class="secondary-button" type="button" :disabled="working || !selected.length" @click="createFixed">发布固定题目考试（{{ selected.length }} 题）</button></div></section><section class="content-card flush-card"><div class="section-heading padded-heading"><div><h3>题目选择</h3><p>请输入知识点或题目内容后搜索，搜索结果将显示全部匹配题目。</p></div></div><div class="question-search-toolbar padded-list"><label>题目内容筛选<input v-model="questionKeyword" placeholder="输入题目名称或题目内容" @keyup.enter="loadQuestions" /></label><label>知识点筛选<input v-model="questionPoint" placeholder="输入知识点名称" @keyup.enter="loadQuestions" /></label><label>题型筛选<select v-model="questionTypeCode"><option value="">全部题型</option><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select></label><div class="question-search-actions"><button type="button" :disabled="loading || !hasQuestionFilter" @click="loadQuestions">搜索题目</button><button class="secondary-button" type="button" :disabled="loading" @click="resetQuestionSearch">清空筛选</button></div></div><div v-if="loading" class="loading-state">正在加载题目…</div><div v-else-if="questions.length" class="selectable-question-list padded-list"><label v-for="question in questions" :key="question.id" class="selectable-question"><input v-model="selected" type="checkbox" :value="question.title" /><span><strong>{{ question.title }}</strong><small>{{ question.type }} · 难度 {{ question.difficulty ?? '未设置' }} · {{ question.point_titles.join('、') || '未关联知识点' }}</small></span></label></div><EmptyState v-else-if="!hasSearched" title="请输入筛选条件" description="输入知识点或题目内容后，搜索符合条件的全部题目。" /><EmptyState v-else title="没有符合条件的题目" description="调整筛选条件后再试。" /></section></div>
</template>
