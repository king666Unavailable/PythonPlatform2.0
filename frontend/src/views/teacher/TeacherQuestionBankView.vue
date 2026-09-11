<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createQuestion, deleteQuestion, fetchQuestions } from '@/api/client'
import type { QuestionSummary } from '@/types/question'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const questions = ref<QuestionSummary[]>([])
const title = ref('')
const typeCode = ref('1')
const content = ref('')
const answer = ref('')
const points = ref('')
const keyword = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')

async function load() { loading.value = true; error.value = ''; try { questions.value = (await fetchQuestions(keyword.value, '', '')).items } catch (cause) { error.value = cause instanceof Error ? cause.message : '题库加载失败。' } finally { loading.value = false } }
async function add() { if (!title.value.trim() || !content.value.trim() || !answer.value.trim()) { error.value = '请填写题目、题干和参考答案。'; return }; saving.value = true; error.value = ''; try { await createQuestion({ title: title.value.trim(), type_code: typeCode.value, content: content.value.trim(), answer: answer.value.trim(), point_titles: points.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean) }); title.value = ''; content.value = ''; answer.value = ''; points.value = ''; success.value = '题目已加入题库。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目保存失败。' } finally { saving.value = false } }
async function remove(question: QuestionSummary) { if (!window.confirm(`确定删除“${question.title}”吗？`)) return; try { await deleteQuestion(question.id); success.value = '题目已删除。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目删除失败。' } }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="题库管理" description="维护课程题目，按题型和知识点组织教学资源。"><template #actions><button type="button" @click="document.getElementById('question-editor')?.scrollIntoView({ behavior: 'smooth' })">新增题目</button></template></PageHeader><InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" /><section id="question-editor" class="content-card editor-card"><div class="section-heading"><div><h3>新增题目</h3><p>录入后题目会立即出现在题库和组卷选择中。</p></div></div><div class="form-grid two-columns"><label>题目名称<input v-model="title" placeholder="例如：列表切片的结果是什么" /></label><label>题型<select v-model="typeCode"><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select></label></div><label>题干<textarea v-model="content" rows="5" placeholder="输入题目内容和必要的选项、输入输出说明" /></label><div class="form-grid two-columns"><label>参考答案<textarea v-model="answer" rows="3" placeholder="输入参考答案或判题测试用例" /></label><label>知识点<input v-model="points" placeholder="可填写多个知识点，用逗号分隔" /></label></div><button type="button" :disabled="saving" @click="add">{{ saving ? '保存中…' : '保存题目' }}</button></section><section class="content-card flush-card"><div class="section-heading padded-heading"><div><h3>题目列表</h3><p>共 {{ questions.length }} 道当前可用题目。</p></div><form class="compact-search" @submit.prevent="load"><input v-model="keyword" placeholder="搜索题目" /><button class="secondary-button" type="submit">搜索</button></form></div><div v-if="loading" class="loading-state">正在加载题库…</div><div v-else-if="questions.length" class="question-table"><div class="question-table-head"><span>题目</span><span>题型</span><span>难度</span><span>知识点</span><span>操作</span></div><article v-for="question in questions" :key="question.id" class="question-table-row"><div><strong>{{ question.title }}</strong><small>{{ question.question_count }} 次练习 · 正确率 {{ question.rate ?? 0 }}%</small></div><StatusBadge :label="question.type" tone="blue" /><span>{{ question.difficulty ?? '—' }}</span><span class="muted">{{ question.point_titles.join('、') || '未关联' }}</span><button class="small-button danger-button" type="button" @click="remove(question)">删除</button></article></div><EmptyState v-else title="题库暂无题目" description="可以先新增一道题。" /></section></div>
</template>
