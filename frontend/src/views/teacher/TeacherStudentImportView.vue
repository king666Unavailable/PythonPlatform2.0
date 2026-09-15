<script setup lang="ts">
import { computed, ref } from 'vue'
import { confirmTeacherStudentImport, createTeacherClass, createTeacherStudent, previewTeacherStudentImport } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useClassContext } from '@/stores/classContext'

const classContext = useClassContext()
const activeMode = ref<'single' | 'batch'>('single')
const working = ref(false)
const singleError = ref('')
const batchError = ref('')
const success = ref('')
const username = ref('')
const name = ref('')
const gender = ref('')
const administrativeClass = ref('')
const importInput = ref<HTMLInputElement | null>(null)
const importLoading = ref(false)
const importWorking = ref(false)
const importToken = ref('')
const importRows = ref<Array<Record<string, unknown>>>([])
const importErrors = ref<Array<Record<string, unknown>>>([])
const showCreator = ref(false)
const creatorError = ref('')
const createWorking = ref(false)
const createTitle = ref('')
const createTeachingClass = ref('')
const createAcademicYear = ref('')

const currentClassId = computed(() => String(classContext.current.value?.id || ''))
const currentClassLabel = computed(() => {
  const current = classContext.current.value
  return current ? `${current.teaching_class || current.title}${current.academic_year ? ` · ${current.academic_year}` : ''}` : '暂无教学班'
})

function switchMode(mode: 'single' | 'batch') {
  activeMode.value = mode
  singleError.value = ''
  batchError.value = ''
  success.value = ''
}

async function createClass() {
  if (!createTitle.value.trim() || !createTeachingClass.value.trim()) {
    creatorError.value = '课程名称和教学班名称不能为空。'
    return
  }
  createWorking.value = true; creatorError.value = ''; success.value = ''
  try {
    const result = await createTeacherClass({ title: createTitle.value.trim(), teaching_class: createTeachingClass.value.trim(), academic_year: createAcademicYear.value.trim() })
    createTitle.value = ''; createTeachingClass.value = ''; createAcademicYear.value = ''; showCreator.value = false
    await classContext.refresh()
    success.value = `教学班“${result.class.teaching_class || result.class.title}”已创建，并已自动归入当前教师名下。`
  } catch (cause) {
    creatorError.value = cause instanceof Error ? cause.message : '教学班创建失败。'
  } finally {
    createWorking.value = false
  }
}

async function createSingleStudent() {
  if (!currentClassId.value) return
  if (!username.value.trim() || !name.value.trim()) {
    singleError.value = '请填写带 * 的必填项。'
    return
  }
  working.value = true; singleError.value = ''; success.value = ''
  try {
    await createTeacherStudent({
      class_id: currentClassId.value,
      username: username.value.trim(),
      name: name.value.trim(),
      gender: gender.value === '' ? null : Number(gender.value),
      administrative_class: administrativeClass.value.trim(),
    })
    username.value = ''; name.value = ''; gender.value = ''; administrativeClass.value = ''
    success.value = `学生已添加到${currentClassLabel.value}，初始密码为学号。`
  } catch (cause) {
    singleError.value = cause instanceof Error ? cause.message : '学生账号创建失败。'
  } finally {
    working.value = false
  }
}

function chooseImport() { importInput.value?.click() }

async function previewImport(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !currentClassId.value) return
  importLoading.value = true; batchError.value = ''; success.value = ''; importToken.value = ''; importRows.value = []; importErrors.value = []
  try {
    const result = await previewTeacherStudentImport(file, currentClassId.value)
    importToken.value = result.token; importRows.value = result.rows; importErrors.value = result.errors
  } catch (cause) {
    batchError.value = cause instanceof Error ? cause.message : 'Excel 解析失败。'
  } finally {
    importLoading.value = false
    if (importInput.value) importInput.value.value = ''
  }
}

async function confirmImport() {
  if (!importToken.value || importErrors.value.length || !importRows.value.length || !window.confirm(`确定导入 ${importRows.value.length} 个学生到“${currentClassLabel.value}”吗？默认密码为学号。`)) return
  importWorking.value = true; batchError.value = ''; success.value = ''
  try {
    const result = await confirmTeacherStudentImport(importToken.value)
    success.value = `已成功导入 ${result.created} 个学生，并加入${currentClassLabel.value}。`
    importToken.value = ''; importRows.value = []; importErrors.value = []
  } catch (cause) {
    batchError.value = cause instanceof Error ? cause.message : '批量导入失败。'
  } finally {
    importWorking.value = false
  }
}

function importErrorText(item: Record<string, unknown>) { return Array.isArray(item.errors) ? (item.errors as string[]).join('；') : '通过' }
function removeImportError(item: Record<string, unknown>) {
  const row = String(item.row)
  importErrors.value = importErrors.value.filter((candidate) => String(candidate.row) !== row)
  batchError.value = ''
}
</script>

<template>
  <div class="page-stack">
    <PageHeader title="学生导入" description="向当前教学班添加学生账号，支持单个添加和 Excel 批量导入。">
      <template #actions><button type="button" @click="showCreator = true">新建教学班</button><span class="class-context-chip">当前教学班：{{ currentClassLabel }}</span></template>
    </PageHeader>
    <InlineMessage :message="success" tone="success" />
    <EmptyState v-if="!currentClassId" title="暂无可用教学班" description="请先在左侧切换到启用的教学班，或联系管理员配置教学班关系。" />
    <template v-else>
      <div class="tabs teacher-import-tabs" role="tablist" aria-label="学生导入方式"><button type="button" :class="{ active: activeMode === 'single' }" @click="switchMode('single')">单个添加</button><button type="button" :class="{ active: activeMode === 'batch' }" @click="switchMode('batch')">批量导入</button></div>

      <section v-if="activeMode === 'single'" class="content-card teacher-student-single-card">
        <div class="section-heading"><div><h3>单个添加学生</h3><p>学生账号创建后会自动加入当前教学班，默认密码为学号。</p></div></div>
        <InlineMessage :message="singleError" tone="error" />
        <div class="form-grid two-columns"><label><span class="required-label">学号 <b class="required-mark">*</b></span><input v-model="username" placeholder="请输入学生学号" /></label><label><span class="required-label">姓名 <b class="required-mark">*</b></span><input v-model="name" placeholder="请输入学生姓名" /></label><label>性别<select v-model="gender"><option value="">请选择性别</option><option value="1">男</option><option value="2">女</option><option value="0">其他</option></select></label><label>行政班<input v-model="administrativeClass" placeholder="例如：大数据2404" /></label></div>
        <div class="form-actions"><button type="button" :disabled="working" @click="createSingleStudent">{{ working ? '保存中…' : '添加学生' }}</button></div>
      </section>

      <template v-else>
        <section v-if="!importLoading && !importToken" class="content-card import-setup teacher-import-card">
          <div class="section-heading"><div><h3>批量导入学生</h3><p>Excel 中填写学号、姓名、行政班和性别；<strong class="import-target-highlight">导入目标为当前教学班：{{ currentClassLabel }}</strong>。</p></div><a class="text-link" href="/templates/student-account-import-template.xlsx" download>下载模板</a></div>
          <InlineMessage :message="batchError" tone="error" />
          <div class="import-setup-row"><span class="muted">确认预览后才会创建账号。默认密码为学号，已存在的学号不能重复导入。</span><button type="button" @click="chooseImport">选择 Excel 文件</button></div>
          <input ref="importInput" class="visually-hidden" type="file" accept=".xlsx" @change="previewImport" />
        </section>
        <section v-if="importLoading || importToken" class="content-card import-preview teacher-import-card">
          <div class="section-heading"><div><h3>批量导入预览</h3><p v-if="importLoading">正在解析 Excel…</p><p v-else>请核对导入数据，确认无误后再写入数据库。默认密码为学号。</p></div><button v-if="!importLoading" class="secondary-button" type="button" @click="importToken = ''; importRows = []; importErrors = []; batchError = ''">取消预览</button></div>
          <InlineMessage :message="batchError" tone="error" />
          <div v-if="!importLoading"><div class="import-result-summary"><span>可导入 {{ importRows.length }} 条</span><span :class="{ 'import-error-count': importErrors.length }">错误 {{ importErrors.length }} 条</span></div><div v-if="importRows.length || importErrors.length" class="import-table-scroll"><div class="import-table"><div class="import-table-head"><span>行号</span><span>学号</span><span>姓名</span><span>性别</span><span>行政班</span><span>教学班</span><span>校验结果</span><span>处理</span></div><div v-for="item in [...importRows, ...importErrors]" :key="String(item.row)" class="import-table-row"><span>{{ item.row }}</span><span>{{ item.username }}</span><span>{{ item.name }}</span><span>{{ item.gender_label || '—' }}</span><span>{{ item.administrative_class || '—' }}</span><span>{{ item.teaching_class || '—' }}</span><span :class="{ 'import-error-text': item.errors }">{{ importErrorText(item) }}</span><span class="import-row-action"><button v-if="item.errors" class="small-button danger-button" type="button" @click="removeImportError(item)">删除</button><span v-else>—</span></span></div></div></div><button v-if="importRows.length && !importErrors.length" type="button" :disabled="importWorking" @click="confirmImport">{{ importWorking ? '导入中…' : `确认导入 ${importRows.length} 个学生` }}</button></div>
        </section>
      </template>
    </template>
    <div v-if="showCreator" class="modal-backdrop" @click.self="showCreator = false"><section class="modal-card admin-class-modal"><div class="section-heading"><div><h3>新建教学班</h3><p>创建成功后会自动切换到新教学班，并归入你的教师账号名下。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="showCreator = false">×</button></div><InlineMessage :message="creatorError" tone="error" /><label><span class="required-label">课程名称 <b class="required-mark">*</b></span><input v-model="createTitle" placeholder="例如：Python程序设计" /></label><label><span class="required-label">教学班名称 <b class="required-mark">*</b></span><input v-model="createTeachingClass" placeholder="例如：Python2026" /></label><label>学年/学期<input v-model="createAcademicYear" placeholder="例如：2026春" /></label><div class="modal-actions"><button class="secondary-button" type="button" @click="showCreator = false">取消</button><button type="button" :disabled="createWorking" @click="createClass">{{ createWorking ? '创建中…' : '创建教学班' }}</button></div></section></div>
  </div>
</template>
