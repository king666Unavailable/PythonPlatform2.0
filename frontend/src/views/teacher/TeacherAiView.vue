<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { approveGenerationTask, fetchGenerationTasks, generateQuestions } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatDate } from '@/utils/format'

interface Candidate { title?: string; type_code?: string; content?: string; answer?: string; analysis?: string; difficulty?: number; importance?: number; point_titles?: string[] }
interface GenerationTask { id: string; prompt: string; status: string; result: Candidate[]; created_at: string }
const prompt = ref('')
const tasks = ref<GenerationTask[]>([])
const selected = ref<GenerationTask | null>(null)
const loading = ref(true)
const working = ref(false)
const error = ref('')
const success = ref('')
const pendingTasks = computed(() => tasks.value.filter((task) => task.status === 'pending_review'))
async function load() { loading.value = true; try { tasks.value = (await fetchGenerationTasks()).items as unknown as GenerationTask[]; selected.value = selected.value ? tasks.value.find((task) => task.id === selected.value?.id) ?? null : tasks.value[0] ?? null } catch (cause) { error.value = cause instanceof Error ? cause.message : '生成记录加载失败。' } finally { loading.value = false } }
async function generate() { if (!prompt.value.trim()) { error.value = '请描述出题要求。'; return }; working.value = true; error.value = ''; try { const result = await generateQuestions(prompt.value.trim()); const task = result.task as unknown as GenerationTask; tasks.value.unshift(task); selected.value = task; prompt.value = ''; success.value = '候选题已生成，请逐题检查后入库。' } catch (cause) { error.value = cause instanceof Error ? cause.message : 'AI 出题失败。' } finally { working.value = false } }
async function approve(task: GenerationTask) { if (!window.confirm(`确认将这 ${task.result.length} 道候选题加入题库吗？`)) return; working.value = true; try { const result = await approveGenerationTask(task.id); success.value = `已将 ${result.approved} 道题加入题库。`; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '候选题入库失败。' } finally { working.value = false } }
function typeLabel(code?: string) { return ({ '1': '选择题', '2': '填空题', '3': '编程题', '4': '程序填空题' } as Record<string, string>)[code ?? ''] ?? '题目' }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="AI 出题" description="描述教学目标，生成候选题后逐题审核，再加入题库。"><template #actions><StatusBadge :label="`${pendingTasks.length} 个待审核任务`" tone="orange" /></template></PageHeader><InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" /><section class="content-card ai-prompt-card"><label>出题要求<textarea v-model="prompt" rows="4" placeholder="例如：围绕 Python 列表和循环生成 5 道基础选择题，面向初学者。" /></label><button type="button" :disabled="working" @click="generate">{{ working ? '生成中…' : '生成候选题' }}</button></section><div v-if="loading" class="loading-state">正在加载生成记录…</div><section v-else class="ai-review-layout"><aside class="content-card task-list"><div class="section-heading"><div><h3>生成记录</h3><p>先选择一条任务进行审核。</p></div></div><button v-for="task in tasks" :key="task.id" type="button" :class="{ active: selected?.id === task.id }" @click="selected = task"><span>{{ task.prompt }}</span><StatusBadge :label="task.status === 'pending_review' ? '待审核' : task.status === 'approved' ? '已入库' : '已处理'" :tone="task.status === 'pending_review' ? 'orange' : 'green'" /></button><EmptyState v-if="!tasks.length" title="还没有生成记录" description="输入出题要求开始。" /></aside><section class="content-card review-panel" v-if="selected"><div class="section-heading"><div><h3>候选题审核</h3><p>生成于 {{ formatDate(selected.created_at) }} · {{ selected.result.length }} 道题</p></div><button v-if="selected.status === 'pending_review'" type="button" :disabled="working" @click="approve(selected)">审核通过并入库</button></div><div class="candidate-list"><article v-for="(candidate, index) in selected.result" :key="`${candidate.title}-${index}`" class="candidate-card"><div class="candidate-card-header"><strong>题目 {{ index + 1 }}</strong><StatusBadge :label="typeLabel(candidate.type_code)" tone="blue" /></div><h4>{{ candidate.title || '未命名题目' }}</h4><p>{{ candidate.content || '暂无题干' }}</p><div class="candidate-meta"><span>难度 {{ candidate.difficulty ?? '—' }}</span><span>知识点 {{ candidate.point_titles?.join('、') || '未关联' }}</span></div><details><summary>查看参考答案和解析</summary><div class="candidate-answer"><strong>答案</strong><p>{{ candidate.answer || '暂无' }}</p><strong>解析</strong><p>{{ candidate.analysis || '暂无' }}</p></div></details></article></div></section><EmptyState v-else title="选择一条生成记录" description="候选题会显示在这里。" /></section></div>
</template>
