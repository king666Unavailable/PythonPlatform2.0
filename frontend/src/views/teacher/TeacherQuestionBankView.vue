<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { createQuestion, deleteQuestion, fetchQuestion, fetchQuestions, updateQuestion } from '@/api/client'
import type { QuestionSummary } from '@/types/question'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

interface TestCase {
  case_no: number
  stdin: string
  expected_output: string
  weight: number
  is_hidden: boolean
  comparison_mode: string
  args_text: string
  kwargs_text: string
  expected_value_text: string
}

interface ProgrammingConfig {
  language: string
  version: string
  filename: string
  timeout_ms: number
  comparison_mode: string
  execution_mode: string
  function_name: string
  parameter_names: string
  return_variable: string
  return_type: string
  tolerance: number
  test_cases: TestCase[]
}

const questions = ref<QuestionSummary[]>([])
const title = ref('')
const typeCode = ref('1')
const content = ref('')
const answer = ref('')
const analysis = ref('')
const points = ref('')
const keyword = ref('')
const typeFilter = ref('')
const language = ref('python')
const version = ref('latest')
const filename = ref('main.py')
const timeoutMs = ref(3000)
const comparisonMode = ref('trim_trailing_spaces')
const executionMode = ref('stdio')
const functionName = ref('')
const parameterNames = ref('')
const returnVariable = ref('')
const returnType = ref('json')
const tolerance = ref(0.000001)
const testCases = ref<TestCase[]>([])
const editingId = ref<string | null>(null)
const editorVisible = ref(false)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const isProgramming = computed(() => typeCode.value === '3' || typeCode.value === '4')
const isFunctionMode = computed(() => executionMode.value === 'function' || executionMode.value === 'wrapped_body')
const hasQuestionFilter = computed(() => Boolean(keyword.value.trim() || typeFilter.value))

function newTestCase(caseNo = testCases.value.length + 1): TestCase {
  return { case_no: caseNo, stdin: '', expected_output: '', weight: 1, is_hidden: false, comparison_mode: comparisonMode.value, args_text: '', kwargs_text: '{}', expected_value_text: '' }
}
function resetEditor() {
  editingId.value = null; title.value = ''; typeCode.value = '1'; content.value = ''; answer.value = ''; analysis.value = ''; points.value = ''
  language.value = 'python'; version.value = 'latest'; filename.value = 'main.py'; timeoutMs.value = 3000
  comparisonMode.value = 'trim_trailing_spaces'; executionMode.value = 'stdio'; functionName.value = ''
  parameterNames.value = ''; returnVariable.value = ''; returnType.value = 'json'; tolerance.value = 0.000001
  testCases.value = []
}
function closeEditor() { resetEditor(); editorVisible.value = false }
function openCreate() {
  resetEditor()
  editorVisible.value = true
  void nextTick(() => document.getElementById('question-editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
function addTestCase() { testCases.value.push(newTestCase()) }
function removeTestCase(index: number) { testCases.value.splice(index, 1); testCases.value.forEach((item, itemIndex) => { item.case_no = itemIndex + 1 }) }
function parseJsonField(text: string, label: string, index: number): { value?: unknown; error?: string } {
  const trimmed = text.trim()
  if (!trimmed) return { value: undefined }
  try { return { value: JSON.parse(trimmed) } } catch { return { error: `测试用例 ${index + 1} 的${label}不是合法 JSON。` } }
}
function buildProgrammingConfig(): { config?: ProgrammingConfig; error?: string } {
  if (!isProgramming.value) return {}
  if (isFunctionMode.value && !functionName.value.trim()) return { error: '函数判卷模式需要填写函数名。' }
  if (executionMode.value === 'wrapped_body' && !returnVariable.value.trim()) return { error: '代码片段模式需要填写返回变量名。' }
  const cases: Array<Record<string, unknown>> = []
  for (const [index, item] of testCases.value.entries()) {
    const args = parseJsonField(item.args_text, '参数', index)
    if (args.error) return { error: args.error }
    const kwargs = parseJsonField(item.kwargs_text, '关键字参数', index)
    if (kwargs.error) return { error: kwargs.error }
    const expected = parseJsonField(item.expected_value_text, '期望返回值', index)
    if (expected.error) return { error: expected.error }
    const casePayload: Record<string, unknown> = {
      case_no: index + 1, weight: Math.max(0.01, Number(item.weight) || 1), is_hidden: item.is_hidden,
    }
    if (executionMode.value === 'stdio') {
      casePayload.stdin = item.stdin
      casePayload.expected_output = item.expected_output
      casePayload.comparison_mode = item.comparison_mode || comparisonMode.value
    } else {
      casePayload.args = args.value ?? []
      casePayload.kwargs = (kwargs.value as Record<string, unknown>) ?? {}
      if (expected.value !== undefined) casePayload.expected_value = expected.value
    }
    cases.push(casePayload)
  }
  const config: ProgrammingConfig = {
    language: language.value.trim() || 'python', version: version.value.trim() || 'latest',
    filename: filename.value.trim() || 'main.py', timeout_ms: Math.max(500, Number(timeoutMs.value) || 3000),
    comparison_mode: comparisonMode.value, execution_mode: executionMode.value,
    function_name: functionName.value.trim(), parameter_names: parameterNames.value, return_variable: returnVariable.value.trim(),
    return_type: returnType.value, tolerance: Math.max(0, Number(tolerance.value) || 0), test_cases: cases as TestCase[],
  }
  return { config }
}
async function load() {
  const filter = keyword.value.trim()
  error.value = ''
  if (!hasQuestionFilter.value) {
    questions.value = []
    loading.value = false
    return
  }
  loading.value = true
  try {
    const firstPage = await fetchQuestions(filter, typeFilter.value, '', 1, 100)
    const totalPages = firstPage.pagination?.total_pages ?? 1
    const remainingPages = totalPages > 1
      ? await Promise.all(Array.from({ length: totalPages - 1 }, (_, index) => fetchQuestions(filter, typeFilter.value, '', index + 2, 100)))
      : []
    questions.value = [firstPage, ...remainingPages].flatMap((page) => page.items)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '题库加载失败。'
  } finally {
    loading.value = false
  }
}
async function save() {
  const needsAnswer = !isProgramming.value && !answer.value.trim()
  if (!title.value.trim() || !content.value.trim() || needsAnswer) { error.value = isProgramming.value ? '请填写题目名称和题干。' : '请填写题目、题干和参考答案。'; return }
  const built = buildProgrammingConfig()
  if (built.error) { error.value = built.error; return }
  saving.value = true; error.value = ''; success.value = ''
  const payload: Record<string, unknown> = { title: title.value.trim(), type_code: typeCode.value, content: content.value.trim(), answer: answer.value.trim(), analysis: analysis.value.trim(), point_titles: points.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean) }
  // Explicitly clear stale test cases when a programming question is changed
  // back to an objective type.
  payload.programming_config = built.config ?? null
  try {
    if (editingId.value) { await updateQuestion(editingId.value, payload); success.value = '题目已更新。' } else { await createQuestion(payload); success.value = '题目已加入题库。' }
    closeEditor(); await load()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目保存失败。' } finally { saving.value = false }
}
async function edit(question: QuestionSummary) {
  error.value = ''
  try {
    const detail = (await fetchQuestion(question.id)).question
    editingId.value = question.id; title.value = String(detail.title ?? question.title); typeCode.value = String(detail.type_code ?? question.type_code)
    content.value = String(detail.content ?? ''); answer.value = String(detail.answer ?? ''); analysis.value = String(detail.analysis ?? ''); points.value = Array.isArray(detail.point_titles) ? detail.point_titles.join('、') : ''
    const config = detail.programming_config as Partial<ProgrammingConfig> | undefined
    language.value = String(config?.language ?? 'python'); version.value = String(config?.version ?? 'latest'); filename.value = String(config?.filename ?? 'main.py')
    timeoutMs.value = Number(config?.timeout_ms ?? 3000); comparisonMode.value = String(config?.comparison_mode ?? 'trim_trailing_spaces')
    executionMode.value = String(config?.execution_mode ?? 'stdio'); functionName.value = String(config?.function_name ?? '')
    parameterNames.value = Array.isArray(config?.parameter_names) ? (config?.parameter_names as string[]).join('，') : String(config?.parameter_names ?? '')
    returnVariable.value = String(config?.return_variable ?? ''); returnType.value = String(config?.return_type ?? 'json'); tolerance.value = Number(config?.tolerance ?? 0.000001)
    const rawCases = Array.isArray(config?.test_cases) ? (config.test_cases as unknown as Array<Record<string, unknown>>) : []
    testCases.value = rawCases.map((item, index) => ({
      ...newTestCase(index + 1), case_no: index + 1,
      stdin: String(item.stdin ?? ''), expected_output: String(item.expected_output ?? ''),
      args_text: 'args' in item ? JSON.stringify(item.args ?? [], null, 0) : '',
      kwargs_text: 'kwargs' in item ? JSON.stringify(item.kwargs ?? {}, null, 0) : '{}',
      expected_value_text: item.expected_value !== undefined && item.expected_value !== null ? JSON.stringify(item.expected_value, null, 0) : '',
    }))
    editorVisible.value = true
    await nextTick()
    document.getElementById('question-editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目详情加载失败。' }
}
async function remove(question: QuestionSummary) {
  if (!window.confirm(`确定删除“${question.title}”吗？`)) return
  try { await deleteQuestion(question.id); success.value = '题目已删除。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '题目删除失败。' }
}
onMounted(() => { loading.value = false })
</script>

<template>
  <div class="page-stack">
    <PageHeader title="题库管理" description="维护课程题目，按题型和知识点组织教学资源。"><template #actions><button type="button" @click="editorVisible && !editingId ? closeEditor() : openCreate()">{{ editorVisible && !editingId ? '收起新增题目' : '新增题目' }}</button></template></PageHeader>
    <InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" />
    <div class="question-bank-body">
    <section v-if="editorVisible" id="question-editor" class="content-card editor-card" :class="editingId ? 'edit-editor-card' : 'create-editor-card'">
      <div class="section-heading"><div><h3>{{ editingId ? '修改题目' : '新增题目' }}</h3><p>编程题可在这里配置测试用例；未配置测试用例的题目提交后会保持待配置状态。</p></div><button v-if="editingId" class="secondary-button" type="button" @click="closeEditor">取消修改</button></div>
      <div class="form-grid two-columns"><label>题目名称<input v-model="title" placeholder="例如：列表切片的结果是什么" /></label><label>题型<select v-model="typeCode"><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select></label></div>
      <label>题干<textarea v-model="content" rows="5" placeholder="输入题目内容和必要的选项、输入输出说明" /></label>
      <div class="form-grid two-columns"><label>参考答案<span class="field-hint">客观题必填，编程题可留空</span><textarea v-model="answer" rows="3" placeholder="客观题填写标准答案；编程题通过测试用例判定" /></label><label>题目解析<textarea v-model="analysis" rows="3" placeholder="填写答案解析、解题思路或评分说明" /></label></div>
      <label>知识点<input v-model="points" placeholder="可填写多个知识点，用逗号分隔" /></label>
      <div v-if="isProgramming" class="test-case-editor">
        <div class="section-heading"><div><h4>编程题判题配置</h4><p>代码提交后由 Piston 逐个执行测试用例，按权重计算题目得分。</p></div><button class="secondary-button" type="button" @click="addTestCase">新增测试用例</button></div>
        <div class="form-grid four-columns"><label>语言<input v-model="language" /></label><label>版本<input v-model="version" placeholder="latest" /></label><label>文件名<span class="field-hint">标准输入/输出模式使用</span><input v-model="filename" placeholder="main.py" /></label><label>超时（毫秒）<input v-model.number="timeoutMs" type="number" min="500" step="100" /></label><label>执行模式<select v-model="executionMode"><option value="stdio">标准输入/输出（完整程序）</option><option value="function">函数调用（学生实现完整函数）</option><option value="wrapped_body">代码片段自动包装</option></select><span class="field-hint">学生提交代码的入口形式</span></label><label v-if="executionMode === 'stdio'">输出比较<select v-model="comparisonMode"><option value="trim_trailing_spaces">忽略行尾空格和末尾换行</option><option value="ignore_final_newline">忽略末尾换行</option><option value="exact">完全一致</option></select></label></div>
        <div v-if="isFunctionMode" class="form-grid four-columns"><label>函数名<span class="field-hint">判卷器调用的固定入口</span><input v-model="functionName" placeholder="例如：square_sum" /></label><label v-if="executionMode === 'wrapped_body'">包装函数参数<span class="field-hint">多个参数用逗号分隔</span><input v-model="parameterNames" placeholder="例如：numbers" /></label><label v-if="executionMode === 'wrapped_body'">返回变量<span class="field-hint">学生代码中赋值的结果变量</span><input v-model="returnVariable" placeholder="例如：answer" /></label><label>返回值类型<select v-model="returnType"><option value="json">JSON（列表/字典/嵌套结构）</option><option value="number">数字（支持浮点误差）</option><option value="text">文本（完全一致）</option></select></label><label v-if="returnType === 'number'">浮点误差<input v-model.number="tolerance" type="number" min="0" step="0.000001" /></label></div>
        <div v-if="testCases.length" class="test-case-list"><article v-for="(testCase, index) in testCases" :key="testCase.case_no" class="test-case-row"><div class="test-case-row-header"><strong>测试用例 {{ index + 1 }}</strong><button class="small-button danger-button" type="button" @click="removeTestCase(index)">删除</button></div><div v-if="executionMode === 'stdio'" class="test-case-fields"><label>标准输入<textarea v-model="testCase.stdin" rows="3" placeholder="传给程序的输入，可留空" /></label><label>期望输出<textarea v-model="testCase.expected_output" rows="3" placeholder="程序应输出的内容" /></label><label>权重<input v-model.number="testCase.weight" type="number" min="0.01" step="0.1" /></label></div><div v-else class="test-case-fields"><label>调用参数（JSON 列表）<textarea v-model="testCase.args_text" rows="2" placeholder='例如：[1, 2, 3] 或 [[1, 2, 3]]' /></label><label>关键字参数（JSON 对象）<textarea v-model="testCase.kwargs_text" rows="2" placeholder='例如：{"base": 10}' /></label><label>期望返回值（JSON）<textarea v-model="testCase.expected_value_text" rows="2" placeholder="例如：14 或 [1, 2, 3]" /></label><label>权重<input v-model.number="testCase.weight" type="number" min="0.01" step="0.1" /></label></div><label class="checkbox-field"><input v-model="testCase.is_hidden" type="checkbox" />隐藏测试用例</label></article></div>
        <div v-else class="empty-inline">暂未配置测试用例，保存后该题会标记为 pending_test_cases，不会被判为 0 分。</div>
      </div>
      <button type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : editingId ? '保存修改' : '保存题目' }}</button>
    </section>
    <section class="content-card flush-card question-list-card"><div class="section-heading padded-heading"><div><h3>题目列表</h3><p>{{ hasQuestionFilter ? `找到 ${questions.length} 道匹配题目。` : '请输入筛选条件后查看题目。' }}</p></div><form class="compact-search question-bank-search" @submit.prevent="load"><input v-model="keyword" placeholder="搜索题目名称、题干或知识点" /><select v-model="typeFilter" aria-label="题型筛选"><option value="">全部题型</option><option value="1">选择题</option><option value="2">填空题</option><option value="3">编程题</option><option value="4">程序填空题</option></select><button class="secondary-button" type="submit">搜索</button></form></div><div v-if="loading" class="loading-state">正在加载题库…</div><EmptyState v-else-if="!hasQuestionFilter" title="请输入筛选条件" description="输入题目名称、题干、知识点或选择题型后，搜索符合条件的全部题目。" /><div v-else-if="questions.length" class="question-table"><div class="question-table-head"><span>题目</span><span>题型</span><span>难度</span><span>知识点</span><span>操作</span></div><article v-for="question in questions" :key="question.id" class="question-table-row"><div><strong>{{ question.title }}</strong><small>{{ question.question_count }} 次练习 · 正确率 {{ question.rate ?? 0 }}%</small></div><StatusBadge :label="question.type" tone="blue" /><span>{{ question.difficulty ?? '—' }}</span><span class="muted">{{ question.point_titles.join('、') || '未关联' }}</span><div class="question-actions"><button class="small-button secondary-button" type="button" @click="edit(question)">修改</button><button class="small-button danger-button" type="button" @click="remove(question)">删除</button></div></article></div><EmptyState v-else title="没有匹配题目" description="请更换题目名称、题干、知识点或题型。" /></section>
    </div>
  </div>
</template>
