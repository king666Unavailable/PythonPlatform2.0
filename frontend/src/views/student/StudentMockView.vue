<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createMockTest, fetchQuestions } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const questions = ref<Array<Record<string, unknown>>>([])
const selected = ref<string[]>([])
const title = ref('')
const timeLimit = ref(30)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const selectedCount = computed(() => selected.value.length)

async function load() { loading.value = true; try { questions.value = (await fetchQuestions('', '', '')).items as unknown as Array<Record<string, unknown>> } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目加载失败。' } finally { loading.value = false } }
async function create() { if (!selected.value.length) { error.value = '请至少选择一道题。'; return }; submitting.value = true; error.value = ''; try { const result = await createMockTest({ title: title.value || '我的模拟练习', questions: selected.value, time_limit: timeLimit.value }); await router.push(`/student/assignments/${result.assignment.id}`) } catch (cause) { error.value = cause instanceof Error ? cause.message : '模拟练习创建失败。' } finally { submitting.value = false } }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="模拟练习" description="从题目练习中选择内容，创建一份属于自己的模拟测试。" /><InlineMessage :message="error" tone="error" /><section v-if="!loading" class="content-card mock-builder"><div class="mock-settings"><label>练习名称<input v-model="title" placeholder="例如：列表与循环复习" /></label><label>答题时长<select v-model="timeLimit"><option :value="0">不限时</option><option :value="20">20 分钟</option><option :value="30">30 分钟</option><option :value="60">60 分钟</option></select></label><button type="button" :disabled="submitting || !selectedCount" @click="create">{{ submitting ? '创建中…' : `开始练习（${selectedCount} 题）` }}</button></div><div class="section-heading"><div><h3>选择题目</h3><p>已选择 {{ selectedCount }} 道</p></div></div><div v-if="questions.length" class="selectable-question-list"><label v-for="question in questions" :key="String(question.id)" class="selectable-question"><input v-model="selected" type="checkbox" :value="String(question.title)" /><span><strong>{{ question.title }}</strong><small>{{ question.type }} · 难度 {{ question.difficulty ?? '未设置' }}</small></span></label></div><EmptyState v-else title="题库暂无题目" description="请稍后再试。" /></section><div v-else class="loading-state">正在加载题目…</div></div>
</template>
