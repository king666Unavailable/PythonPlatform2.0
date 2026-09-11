<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchQuestionDetail, fetchQuestions } from '@/api/client'
import type { Question, QuestionListResponse } from '@/types/question'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

withDefaults(defineProps<{ showSolution?: boolean }>(), { showSolution: false })
const keyword = ref('')
const typeCode = ref('')
const results = ref<QuestionListResponse | null>(null)
const selected = ref<Question | null>(null)
const loading = ref(false)
const detailLoading = ref(false)
const error = ref('')

async function loadQuestions() {
  loading.value = true
  error.value = ''
  try {
    results.value = await fetchQuestions(keyword.value, typeCode.value)
    selected.value = null
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '题目加载失败。'
  } finally {
    loading.value = false
  }
}

async function openQuestion(id: string) {
  detailLoading.value = true
  error.value = ''
  try {
    selected.value = (await fetchQuestionDetail(id)).question
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '题目详情加载失败。'
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => void loadQuestions())
</script>

<template>
  <section class="browser-panel">
    <form class="filter-bar" @submit.prevent="loadQuestions">
      <label class="filter-search">搜索题目<input v-model="keyword" placeholder="输入题目名称或关键词" /></label>
      <label>题型<select v-model="typeCode"><option value="">全部题型</option><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select></label>
      <button type="submit" :disabled="loading">{{ loading ? '查询中' : '查询' }}</button>
    </form>
    <InlineMessage :message="error" tone="error" />
    <div v-if="results" class="question-browser-layout">
      <div class="question-results">
        <div class="panel-heading-row"><strong>题目列表</strong><span>{{ results.pagination.total }} 道题</span></div>
        <button v-for="question in results.items" :key="question.id" type="button" class="question-result-item" :class="{ selected: selected?.id === question.id }" @click="openQuestion(question.id)">
          <strong>{{ question.title }}</strong>
          <span>{{ question.type }} · 难度 {{ question.difficulty ?? '未设置' }}</span>
        </button>
        <EmptyState v-if="!results.items.length" title="没有找到相关题目" description="可以更换关键词或题型后再试。" />
      </div>
      <article class="question-detail-card">
        <p v-if="detailLoading" class="loading-state">正在加载题目…</p>
        <EmptyState v-else-if="!selected" title="选择一道题" description="题目内容会显示在这里。" />
        <template v-else>
          <div class="detail-title-row"><h3>{{ selected.title }}</h3><StatusBadge :label="selected.type" tone="blue" /></div>
          <p class="muted">难度：{{ selected.difficulty ?? '未设置' }} · 知识点：{{ selected.point_titles.join('、') || '未关联' }}</p>
          <div class="rich-text">{{ selected.content || '暂无题干' }}</div>
          <template v-if="showSolution && selected.answer !== undefined">
            <div class="answer-section"><strong>参考答案</strong><div class="rich-text">{{ selected.answer || '暂无答案' }}</div></div>
            <div class="answer-section"><strong>解析</strong><div class="rich-text">{{ selected.analysis || '暂无解析' }}</div></div>
          </template>
          <p v-else class="muted">学生练习只展示题目内容，提交后可查看结果。</p>
        </template>
      </article>
    </div>
  </section>
</template>
