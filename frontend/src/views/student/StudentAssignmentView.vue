<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { fetchAssignmentDetail, runCode, saveAssignmentDraft, submitAssignment } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import CodeEditor from '@/components/code/CodeEditor.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatDate } from '@/utils/format'

interface AssignmentQuestion {
  position: number
  id: string
  title: string
  type: string
  type_code: string
  content: string
  answer?: string
  analysis?: string
  programming_submission?: {
    execution_mode?: string
    function_name?: string
    parameter_names?: string[]
    return_variable?: string
  }
}

interface AssignmentDetail {
  id: string
  title: string
  deadline?: string
  time_limit?: number
  questions: AssignmentQuestion[]
  view_mode?: 'answer' | 'result' | 'answers' | 'questions'
  submission_mode?: 'normal' | 'makeup'
  makeup_window_id?: string | null
  can_view_answers?: boolean
  answer_view_message?: string
  draft?: { answers?: Record<string, unknown> | unknown[]; time_spent?: Record<string, unknown> }
  submission?: { answers?: Record<string, unknown> | unknown[]; time_spent?: Record<string, unknown>; score?: number | null; status?: string; grades?: Array<Record<string, unknown>> }
}

const route = useRoute()
const router = useRouter()
const assignment = ref<AssignmentDetail | null>(null)
const answers = reactive<Record<string, string>>({})
const activeIndex = ref(0)
const timeSpent = reactive<Record<string, number>>({})
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const message = ref('')
const codeRunError = ref('')
const saveState = ref('尚未保存')
const codeOutputs = reactive<Record<string, Record<string, unknown>>>({})
const codeRunning = ref(false)
const questionStatementRef = ref<HTMLElement | null>(null)
const showQuestionScrollHint = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | undefined
let timingTimer: ReturnType<typeof setInterval> | undefined
let timingPersistTimer: ReturnType<typeof setInterval> | undefined
let timingPosition: string | null = null
let timingLastTick = 0
let hydrated = false

const currentQuestion = computed(() => assignment.value?.questions[activeIndex.value] ?? null)
const programmingHint = computed(() => {
  const submission = currentQuestion.value?.programming_submission
  const mode = submission?.execution_mode
  const functionName = submission?.function_name?.trim()
  if (mode === 'function' && functionName) {
    return `本题按函数调用判卷：请完整实现函数 ${functionName}(...)，函数名需保持一致，判卷器会用多组参数自动调用它。`
  }
  if (mode === 'wrapped_body') {
    const params = (submission?.parameter_names ?? []).filter(Boolean)
    const returnVariable = submission?.return_variable?.trim()
    const paramNote = params.length ? `可直接使用参数变量 ${params.join('、')}；` : ''
    const variableNote = returnVariable ? `请把最终结果赋值给变量 ${returnVariable}。` : '请按要求计算结果。'
    return `本题按代码片段判卷：只需编写函数体代码，不要写 def ${functionName || '函数'} 行和 return 语句。${paramNote}${variableNote}`
  }
  return ''
})
const answeredCount = computed(() => Object.values(answers).filter((answer) => answer.trim()).length)
const currentQuestionTime = computed(() => {
  const position = currentQuestion.value?.position
  return position === undefined ? 0 : timeSpent[String(position)] ?? 0
})
const unansweredCount = computed(() => Math.max(0, (assignment.value?.questions.length ?? 0) - answeredCount.value))
const viewMode = computed(() => assignment.value?.view_mode ?? 'answer')
const isReadOnly = computed(() => viewMode.value !== 'answer')
const showOwnAnswers = computed(() => viewMode.value === 'result' || viewMode.value === 'answers')
const onlyQuestions = computed(() => viewMode.value === 'questions')
const canViewStandardAnswers = computed(() => Boolean(assignment.value?.can_view_answers))
const answerViewMessage = computed(() => assignment.value?.answer_view_message || '')
const pageDescription = computed(() => {
  const standardAnswerHint = canViewStandardAnswers.value ? '本页包含标准答案和解析。' : answerViewMessage.value || '标准答案暂不开放。'
  return ({
    answer: '按题号完成作答，答案会自动保存。',
    result: '查看本次作业的得分和你的答案。' + standardAnswerHint,
    answers: '查看你已提交的答案。' + standardAnswerHint,
    questions: '查看作业题目。该作业已逾期，当前仅开放题目内容。',
  }[viewMode.value] ?? '查看作业内容。')
})

function updateQuestionScrollHint() {
  const element = questionStatementRef.value
  if (!element) {
    showQuestionScrollHint.value = false
    return
  }
  const hasOverflow = element.scrollHeight > element.clientHeight + 1
  const atBottom = element.scrollTop + element.clientHeight >= element.scrollHeight - 1
  showQuestionScrollHint.value = hasOverflow && !atBottom
}

function scrollQuestionToBottom() {
  questionStatementRef.value?.scrollTo({ top: questionStatementRef.value.scrollHeight, behavior: 'smooth' })
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function tickTiming() {
  if (!timingPosition || isReadOnly.value) return
  const now = Date.now()
  const elapsed = Math.floor((now - timingLastTick) / 1000)
  if (elapsed <= 0) return
  timeSpent[timingPosition] = (timeSpent[timingPosition] ?? 0) + elapsed
  timingLastTick += elapsed * 1000
}

function pauseTiming(shouldScheduleSave = true) {
  tickTiming()
  if (timingTimer) clearInterval(timingTimer)
  timingTimer = undefined
  timingPosition = null
  if (shouldScheduleSave) scheduleSave()
}

function startTiming() {
  if (!hydrated || isReadOnly.value || !currentQuestion.value) return
  if (timingTimer) clearInterval(timingTimer)
  timingPosition = String(currentQuestion.value.position)
  timingLastTick = Date.now()
  timingTimer = setInterval(tickTiming, 1000)
  if (!timingPersistTimer) {
    timingPersistTimer = setInterval(() => {
      if (!hydrated || isReadOnly.value || submitting.value) return
      tickTiming()
      void saveDraft()
    }, 15000)
  }
}

function answerFor(question: AssignmentQuestion) {
  return answers[String(question.position)] ?? ''
}

function gradeFor(question: AssignmentQuestion | null) {
  if (!question) return undefined
  return assignment.value?.submission?.grades?.find((grade) => Number(grade.position) === question.position)
}

function isWrong(question: AssignmentQuestion | null) {
  const grade = gradeFor(question)
  return viewMode.value === 'result' && grade?.status === 'graded' && Number(grade.score) <= 0
}

function setAnswer(question: AssignmentQuestion, value: string) {
  answers[String(question.position)] = value
}

function choiceOptions(question: AssignmentQuestion) {
  const text = question.content ?? ''
  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed.options)) return parsed.options.map((item: unknown, index: number) => ({ label: String.fromCharCode(65 + index), text: String(item) }))
  } catch {
    // Plain text question content is the normal legacy format.
  }
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter((line) => /^[A-D][.、)]/.test(line))
  if (lines.length) return lines.map((line) => ({ label: line.slice(0, 1), text: line.slice(2).trim() }))
  return ['A', 'B', 'C', 'D'].map((label) => ({ label, text: `选项 ${label}` }))
}

function hydrateDraft(draft: AssignmentDetail['draft']) {
  if (!draft?.answers) return
  if (Array.isArray(draft.answers)) draft.answers.forEach((value, index) => { answers[String(index)] = String(value ?? '') })
  else Object.entries(draft.answers).forEach(([key, value]) => { answers[key] = String(value ?? '') })
  if (draft.time_spent) Object.entries(draft.time_spent).forEach(([key, value]) => {
    const seconds = Number(value)
    if (Number.isFinite(seconds) && seconds >= 0) timeSpent[key] = Math.floor(seconds)
  })
}

function hydrateSubmission(submission: AssignmentDetail['submission']) {
  if (!submission?.answers) return
  if (Array.isArray(submission.answers)) submission.answers.forEach((value, index) => { answers[String(index)] = String(value ?? '') })
  else Object.entries(submission.answers).forEach(([key, value]) => { answers[key] = String(value ?? '') })
  if (submission.time_spent) Object.entries(submission.time_spent).forEach(([key, value]) => {
    const seconds = Number(value)
    if (Number.isFinite(seconds) && seconds >= 0) timeSpent[key] = Math.floor(seconds)
  })
}

async function load() {
  loading.value = true
  error.value = ''
  hydrated = false
  try {
    Object.keys(answers).forEach((key) => delete answers[key])
    Object.keys(timeSpent).forEach((key) => delete timeSpent[key])
    const makeupWindowId = typeof route.query.makeup_window_id === 'string' ? route.query.makeup_window_id : undefined
    assignment.value = (await fetchAssignmentDetail(String(route.params.id), makeupWindowId)).assignment as unknown as AssignmentDetail
    hydrateDraft(assignment.value.draft)
    hydrateSubmission(assignment.value.submission)
    activeIndex.value = 0
    hydrated = true
    saveState.value = viewMode.value === 'answer' ? (Object.keys(answers).length ? '已恢复草稿' : '尚未保存') : '只读查看'
    await nextTick()
    startTiming()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '作业加载失败。'
  } finally {
    loading.value = false
  }
}

async function saveDraft(immediate = false) {
  if (!assignment.value || submitting.value) return
  saveState.value = '保存中…'
  try {
    await saveAssignmentDraft(assignment.value.id, { ...answers }, { ...timeSpent }, {
      keepalive: immediate,
      makeupWindowId: assignment.value.makeup_window_id,
      submissionMode: assignment.value.submission_mode ?? 'normal',
    })
    saveState.value = `已保存 ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  } catch (cause) {
    saveState.value = '保存失败，可点击重试'
    error.value = cause instanceof Error ? cause.message : '草稿保存失败。'
  }
}

function scheduleSave() {
  if (!hydrated || !assignment.value || submitting.value || isReadOnly.value) return
  saveState.value = '等待保存…'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => void saveDraft(), 800)
}

async function runQuestion(question: AssignmentQuestion) {
  if (isReadOnly.value || codeRunning.value) return
  const code = answerFor(question)
  if (!code.trim()) { codeRunError.value = '请先输入代码。'; return }
  codeRunError.value = ''
  codeRunning.value = true
  try {
    codeOutputs[question.id] = await runCode({ code, question_id: question.id, language: 'python', version: 'latest' })
  } catch (cause) {
    codeRunError.value = cause instanceof Error ? cause.message : '代码运行失败。'
  } finally {
    codeRunning.value = false
  }
}

async function submit() {
  if (!assignment.value) return
  if (unansweredCount.value > 0 && !window.confirm(`还有 ${unansweredCount.value} 道题未作答，确定要提交吗？`)) return
  if (!window.confirm('提交后将不能继续修改答案，确定提交吗？')) return
  pauseTiming(false)
  submitting.value = true
  error.value = ''
  try {
    // crypto.randomUUID 仅在安全上下文（HTTPS/localhost）可用，班级通过 http://内网IP 访问时需兜底
    const submissionToken = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `tok-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    const result = await submitAssignment(assignment.value.id, { ...answers }, submissionToken, { ...timeSpent }, {
      makeupWindowId: assignment.value.makeup_window_id,
      submissionMode: assignment.value.submission_mode ?? 'normal',
    })
    message.value = result.duplicate ? '检测到重复提交，已返回原提交记录。' : '提交成功，成绩会在批改完成后更新。'
    saveState.value = '已提交'
  window.setTimeout(() => void router.push('/student/profile'), 900)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '提交失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}

watch(answers, scheduleSave, { deep: true })
watch(currentQuestion, () => {
  codeRunError.value = ''
  pauseTiming()
  void nextTick(() => {
    updateQuestionScrollHint()
    startTiming()
  })
})
onMounted(() => {
  window.addEventListener('resize', updateQuestionScrollHint)
  void load()
})
onBeforeUnmount(() => {
  // 路由离开前先结算当前题最后一段耗时，并立即保存一次草稿。
  // 不能先把 hydrated 置为 false，否则 scheduleSave/saveDraft 会被提前拦截。
  const shouldSaveBeforeLeave = Boolean(hydrated && assignment.value && !isReadOnly.value && !submitting.value)
  pauseTiming(false)
  if (saveTimer) clearTimeout(saveTimer)
  if (shouldSaveBeforeLeave) void saveDraft(true)
  hydrated = false
  if (timingPersistTimer) clearInterval(timingPersistTimer)
  timingPersistTimer = undefined
  window.removeEventListener('resize', updateQuestionScrollHint)
})
</script>

<template>
  <div class="page-stack">
    <PageHeader :title="assignment?.title ?? '查看作业'" :description="pageDescription">
      <template #actions><RouterLink class="button-link secondary-button" to="/student/assignments">返回作业列表</RouterLink></template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <InlineMessage :message="message" tone="success" />
    <div v-if="loading" class="loading-state">正在加载题目…</div>
    <EmptyState v-else-if="!assignment" title="暂时无法打开这份作业" description="请返回作业列表重试。" />
    <section v-else class="answer-workspace">
      <aside class="question-sidebar content-card">
        <template v-if="!onlyQuestions">
          <div class="answer-summary"><strong>答题进度</strong><span>{{ answeredCount }}/{{ assignment.questions.length }} 题</span></div>
          <div class="progress-track"><i :style="{ width: `${assignment.questions.length ? answeredCount / assignment.questions.length * 100 : 0}%` }" /></div>
        </template>
        <div class="question-number-grid">
          <button v-for="(question, index) in assignment.questions" :key="question.id" type="button" :class="{ current: index === activeIndex, answered: answerFor(question).trim(), wrong: isWrong(question) }" @click="activeIndex = index">{{ index + 1 }}</button>
        </div>
        <div class="assignment-side-info"><template v-if="assignment.submission_mode === 'makeup'"><span>提交方式</span><strong>补交</strong></template><span>截止时间</span><strong>{{ formatDate(assignment.deadline, '不限') }}</strong><span>限时</span><strong>{{ assignment.time_limit ? `${assignment.time_limit} 分钟` : '不限时' }}</strong></div>
        <div v-if="viewMode === 'result'" class="assignment-score"><span>本次得分</span><strong>{{ assignment.submission?.score ?? '待更新' }}<small v-if="assignment.submission?.score !== null && assignment.submission?.score !== undefined"> 分</small></strong></div>
      </aside>
      <section class="answer-main content-card" :class="{ 'wrong-question-card': isWrong(currentQuestion) }">
        <div class="answer-main-header"><div><div class="question-meta"><span class="question-counter">第 {{ activeIndex + 1 }} 题 / 共 {{ assignment.questions.length }} 题</span><span v-if="!isReadOnly" class="question-timer">本题用时 {{ formatDuration(currentQuestionTime) }}</span></div><h3>{{ currentQuestion?.title }}</h3></div><StatusBadge class="question-type-badge" :label="currentQuestion?.type || '题目'" tone="blue" /></div><InlineMessage v-if="showOwnAnswers && !canViewStandardAnswers && answerViewMessage" :message="answerViewMessage" tone="info" />
        <div v-if="currentQuestion" class="answer-content">
          <div class="question-statement-wrap">
            <div ref="questionStatementRef" class="question-statement" @scroll="updateQuestionScrollHint">{{ currentQuestion.content || '暂无题干' }}</div>
            <button v-if="showQuestionScrollHint" class="question-scroll-arrow" type="button" aria-label="下滑查看完整题目" title="下滑查看完整题目" @click="scrollQuestionToBottom">↓</button>
          </div>
          <div v-if="showOwnAnswers"><div class="answer-review"><span>你的答案</span><strong>{{ answerFor(currentQuestion) || '未作答' }}</strong></div><div v-if="gradeFor(currentQuestion)" class="answer-review grade-review"><span>判卷结果</span><strong>{{ gradeFor(currentQuestion)?.feedback || '已判卷' }}</strong><em v-if="gradeFor(currentQuestion)?.score !== null && gradeFor(currentQuestion)?.score !== undefined">本题得分 {{ gradeFor(currentQuestion)?.score }} 分</em></div><div v-if="canViewStandardAnswers" class="standard-answer-review"><div class="standard-answer-row"><span>标准答案</span><strong>{{ currentQuestion.answer || '暂无标准答案' }}</strong></div><div class="standard-answer-analysis"><span>解析</span><p>{{ currentQuestion.analysis || '暂无解析' }}</p></div></div></div>
          <div v-else-if="onlyQuestions" class="question-only-note">当前为仅查看题目模式，不显示作答内容。</div>
          <div v-else-if="currentQuestion.type_code === '1'" class="choice-list">
            <label v-for="option in choiceOptions(currentQuestion)" :key="option.label" class="choice-option" :class="{ checked: answerFor(currentQuestion) === option.label }"><input type="radio" :name="`question-${currentQuestion.position}`" :value="option.label" :checked="answerFor(currentQuestion) === option.label" @change="setAnswer(currentQuestion, option.label)" /><b>{{ option.label }}</b><span>{{ option.text }}</span></label>
          </div>
          <label v-else-if="currentQuestion.type_code === '2'" class="answer-field">你的答案<input :value="answerFor(currentQuestion)" placeholder="请输入答案" @input="setAnswer(currentQuestion, ($event.target as HTMLInputElement).value)" /></label>
          <div v-else-if="['3', '4'].includes(currentQuestion.type_code)" class="code-answer"><InlineMessage v-if="programmingHint" :message="programmingHint" tone="info" /><div class="code-editor-field"><span>代码编辑器</span><CodeEditor :model-value="answerFor(currentQuestion)" placeholder="在这里编写 Python 代码" @update:model-value="setAnswer(currentQuestion, $event)" /></div><div class="code-actions"><button class="secondary-button" type="button" :disabled="submitting || codeRunning" @click="runQuestion(currentQuestion)">{{ codeRunning ? '运行中…' : '运行代码' }}</button><span>运行结果仅用于预览，不会自动判卷或计入成绩。</span></div><InlineMessage :message="codeRunError" tone="error" /><div v-if="codeOutputs[currentQuestion.id]" class="code-output"><div class="code-output-header"><strong>{{ codeOutputs[currentQuestion.id].status === 'completed' ? '运行完成' : '运行失败' }}</strong><span v-if="codeOutputs[currentQuestion.id].executionTime">耗时 {{ codeOutputs[currentQuestion.id].executionTime }} ms</span></div><pre v-if="codeOutputs[currentQuestion.id].stdout">{{ codeOutputs[currentQuestion.id].stdout }}</pre><pre v-if="codeOutputs[currentQuestion.id].stderr" class="code-output-error">{{ codeOutputs[currentQuestion.id].stderr }}</pre><pre v-if="codeOutputs[currentQuestion.id].error" class="code-output-error">{{ codeOutputs[currentQuestion.id].error }}</pre><span v-if="!codeOutputs[currentQuestion.id].stdout && !codeOutputs[currentQuestion.id].stderr && !codeOutputs[currentQuestion.id].error">程序运行完成，没有输出。</span></div></div>
          <label v-else class="answer-field">你的答案<textarea :value="answerFor(currentQuestion)" rows="7" placeholder="请输入答案" @input="setAnswer(currentQuestion, ($event.target as HTMLTextAreaElement).value)" /></label>
        </div>
        <div class="answer-footer"><span class="save-state">{{ saveState }}</span><div class="answer-actions"><button class="secondary-button" type="button" :disabled="activeIndex === 0" @click="activeIndex -= 1">上一题</button><button v-if="activeIndex < assignment.questions.length - 1" type="button" @click="activeIndex += 1">下一题</button><button v-else-if="!isReadOnly" type="button" :disabled="submitting" @click="submit">{{ submitting ? '提交中…' : '提交作业' }}</button><span v-else class="read-only-hint">{{ onlyQuestions ? '仅查看题目' : viewMode === 'result' ? '已完成 · 只读' : '判卷中 · 只读' }}</span></div></div>
      </section>
    </section>
  </div>
</template>
