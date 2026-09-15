<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { confirmAdminAccountImport, createAdminAccount, fetchAdminAccounts, fetchAdminClasses, previewAdminAccountImport, updateAdminAccount } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const accounts = ref<Array<Record<string, unknown>>>([])
const meta = ref<Record<string, unknown>>({ total: 0, page: 1, page_size: 20, total_pages: 1, administrative_classes: [], teaching_classes: [] })
const allAdministrativeClasses = ref<string[]>([])
const allTeachingClasses = ref<string[]>([])
const classOptions = ref<Array<Record<string, unknown>>>([])
const role = ref('all'); const keyword = ref(''); const administrativeClass = ref(''); const teachingClass = ref(''); const accountStatus = ref('all'); const appliedKeyword = ref('')
const showCreator = ref(false); const editTarget = ref<Record<string, unknown> | null>(null); const resetTarget = ref<Record<string, unknown> | null>(null); const classTarget = ref<Record<string, unknown> | null>(null); const createRole = ref('student')
const username = ref(''); const name = ref(''); const createGender = ref(''); const password = ref(''); const createAdministrativeClass = ref(''); const createClassIds = ref<string[]>([]); const editClassIds = ref<string[]>([]); const newPassword = ref('')
const editName = ref(''); const editGender = ref(''); const editAdministrativeClass = ref('')
const loading = ref(true); const working = ref(false); const error = ref(''); const success = ref('')
const creatorError = ref(''); const editModalError = ref(''); const classModalError = ref(''); const resetModalError = ref(''); const importError = ref('')
const jumpPage = ref('1')
const importInput = ref<HTMLInputElement | null>(null); const showImporter = ref(false); const importTeachingClass = ref(''); const importToken = ref(''); const importRows = ref<Array<Record<string, unknown>>>([]); const importErrors = ref<Array<Record<string, unknown>>>([]); const importLoading = ref(false)
const roleLabels: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
const page = computed(() => Number(meta.value.page || 1)); const totalPages = computed(() => Number(meta.value.total_pages || 1))
const selectableClasses = computed(() => classOptions.value.filter((item) => Boolean(item.is_active)))

async function load(nextPage = 1) {
  loading.value = true; error.value = ''
  try {
    const result = await fetchAdminAccounts({ role: role.value, q: appliedKeyword.value, administrativeClass: administrativeClass.value, teachingClass: teachingClass.value, status: accountStatus.value, page: nextPage, pageSize: 20 })
    accounts.value = result.items; meta.value = result.meta; jumpPage.value = String(result.meta.page || nextPage)
    allAdministrativeClasses.value = Array.isArray(result.meta.administrative_classes) ? result.meta.administrative_classes as string[] : []
    allTeachingClasses.value = Array.isArray(result.meta.teaching_classes) ? result.meta.teaching_classes as string[] : []
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '账号加载失败。' } finally { loading.value = false }
}
async function loadClassOptions() {
  try { classOptions.value = (await fetchAdminClasses({ status: 'active' })).items } catch (cause) { error.value = cause instanceof Error ? cause.message : '教学班加载失败。' }
}
function search() { appliedKeyword.value = keyword.value.trim(); void load(1) }
function resetFilters() { keyword.value = ''; appliedKeyword.value = ''; role.value = 'all'; administrativeClass.value = ''; teachingClass.value = ''; accountStatus.value = 'all'; void load(1) }
function jump() { const target = Math.min(totalPages.value, Math.max(1, Number.parseInt(jumpPage.value, 10) || 1)); void load(target) }
function classLabel(item: Record<string, unknown>) { return `${item.teaching_class || '未命名教学班'}${item.academic_year ? ` · ${item.academic_year}` : ''}` }
function resetCreator() { username.value = ''; name.value = ''; createGender.value = ''; password.value = ''; createAdministrativeClass.value = ''; createClassIds.value = []; creatorError.value = '' }
async function create() {
  if (!username.value.trim() || !name.value.trim()) { creatorError.value = '请填写带 * 的必填项。'; return }
  if (createRole.value !== 'admin' && !createClassIds.value.length) { creatorError.value = '请至少选择一个现有教学班；如需新建，请前往教学班管理。'; return }
  working.value = true
  creatorError.value = ''
  try {
    await createAdminAccount({ role: createRole.value, username: username.value.trim(), name: name.value.trim(), gender: createRole.value === 'student' && createGender.value ? Number(createGender.value) : null, password: password.value, study_class: createRole.value === 'student' ? createAdministrativeClass.value : '', stu_classify: '', class_ids: createRole.value === 'admin' ? [] : createClassIds.value })
    resetCreator(); showCreator.value = false; success.value = '账号已创建。'; await load(1); await loadClassOptions()
  } catch (cause) { creatorError.value = cause instanceof Error ? cause.message : '账号创建失败。' } finally { working.value = false }
}
async function toggle(account: Record<string, unknown>) {
  const active = String(account.status) === '启用'; if (!window.confirm(`确定${active ? '停用' : '启用'}账号“${account.name}”吗？`)) return
  try { await updateAdminAccount(String(account.role), String(account.username), { is_active: !active }); success.value = '账号状态已更新。'; await load(page.value) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '账号状态更新失败。' }
}
function openEdit(account: Record<string, unknown>) {
  editTarget.value = account
  editName.value = String(account.name || '')
  editGender.value = account.gender_code === null || account.gender_code === undefined ? '' : String(account.gender_code)
  editAdministrativeClass.value = String(account.administrative_class || '')
  editModalError.value = ''
}
async function saveEdit() {
  if (!editTarget.value) return
  if (!editName.value.trim()) { editModalError.value = '姓名不能为空。'; return }
  working.value = true; editModalError.value = ''
  const target = editTarget.value
  const payload: Record<string, unknown> = { name: editName.value.trim() }
  if (target.role === 'student') {
    payload.gender = editGender.value === '' ? null : Number(editGender.value)
    payload.administrative_class = editAdministrativeClass.value.trim()
  }
  try {
    await updateAdminAccount(String(target.role), String(target.username), payload)
    editTarget.value = null; success.value = '账号资料已更新。'; await load(page.value)
  } catch (cause) { editModalError.value = cause instanceof Error ? cause.message : '账号资料更新失败。' } finally { working.value = false }
}
async function reset() {
  if (!resetTarget.value || !newPassword.value) { resetModalError.value = '请输入新密码。'; return }; working.value = true; resetModalError.value = ''
  try { await updateAdminAccount(String(resetTarget.value.role), String(resetTarget.value.username), { password: newPassword.value }); newPassword.value = ''; resetTarget.value = null; success.value = '密码已重置。' }
  catch (cause) { resetModalError.value = cause instanceof Error ? cause.message : '密码重置失败。' } finally { working.value = false }
}
function openClasses(account: Record<string, unknown>) { classTarget.value = account; classModalError.value = ''; editClassIds.value = Array.isArray(account.class_ids) ? account.class_ids.map((value) => String(value)) : [] }
async function saveClasses() {
  if (!classTarget.value) return; working.value = true
  classModalError.value = ''
  try { await updateAdminAccount(String(classTarget.value.role), String(classTarget.value.username), { class_ids: editClassIds.value }); classTarget.value = null; success.value = '教学班关系已保存。'; await load(page.value) }
  catch (cause) { classModalError.value = cause instanceof Error ? cause.message : '教学班关系保存失败。' } finally { working.value = false }
}
function chooseImport() { importInput.value?.click() }
async function previewImport(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return
  importLoading.value = true; importError.value = ''; success.value = ''; importRows.value = []; importErrors.value = []; importToken.value = ''
  try { const result = await previewAdminAccountImport(file, importTeachingClass.value); importToken.value = result.token; importRows.value = result.rows; importErrors.value = result.errors }
  catch (cause) { importError.value = cause instanceof Error ? cause.message : 'Excel 解析失败。' }
  finally { importLoading.value = false; if (importInput.value) importInput.value.value = '' }
}
async function confirmImport() {
  if (!importToken.value || importErrors.value.length || !importRows.value.length || !window.confirm(`确定导入 ${importRows.value.length} 个学生账号吗？默认密码为学号。`)) return
  working.value = true; importError.value = ''
  try { const result = await confirmAdminAccountImport(importToken.value); success.value = `已成功导入 ${result.created} 个学生账号。`; importToken.value = ''; importRows.value = []; importErrors.value = []; await load(1); await loadClassOptions() }
  catch (cause) { importError.value = cause instanceof Error ? cause.message : '批量导入失败。' } finally { working.value = false }
}
function importErrorText(item: Record<string, unknown>) { return Array.isArray(item.errors) ? (item.errors as string[]).join('；') : '通过' }
function removeImportError(item: Record<string, unknown>) {
  const row = String(item.row)
  importErrors.value = importErrors.value.filter((candidate) => String(candidate.row) !== row)
  importError.value = ''
}
onMounted(() => { void Promise.all([load(), loadClassOptions()]) })
</script>

<template>
  <div class="page-stack">
    <PageHeader title="账号管理" description="查看和维护平台中的学生、教师与管理员账号。"><template #actions><button type="button" @click="showCreator = !showCreator">{{ showCreator ? '收起' : '创建账号' }}</button><button class="secondary-button" type="button" @click="showImporter = !showImporter">{{ showImporter ? '收起导入' : '批量导入学生' }}</button><a class="text-link" href="/templates/student-account-import-template.xlsx" download>下载模板</a><input ref="importInput" class="visually-hidden" type="file" accept=".xlsx" @change="previewImport" /></template></PageHeader>
    <section v-if="showCreator" class="content-card creator-card"><div class="section-heading"><div><h3>创建账号</h3></div></div><InlineMessage :message="creatorError" tone="error" /><div class="form-grid three-columns"><label><span class="required-label">账号角色 <b class="required-mark">*</b></span><select v-model="createRole"><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option></select></label><label><span class="required-label">用户名 <b class="required-mark">*</b></span><input v-model="username" placeholder="登录用户名，默认为学号" /></label><label><span class="required-label">姓名 <b class="required-mark">*</b></span><input v-model="name" placeholder="用户姓名" /></label></div><div v-if="createRole === 'student'" class="form-grid three-columns"><label>性别<select v-model="createGender"><option value="">请选择性别</option><option value="1">男</option><option value="2">女</option><option value="0">其他</option></select></label><label>行政班<input v-model="createAdministrativeClass" placeholder="例如：大数据2404" /></label></div><label>初始密码<input v-model="password" type="password" placeholder="可留空，使用系统默认初始密码" /></label><div v-if="createRole !== 'admin'" class="class-picker"><strong class="required-label">关联教学班 <b class="required-mark">*</b></strong><span class="muted">教师和学生可一次关联多个已有教学班；只能选择已有教学班；如需新建，请前往“教学班管理”。</span><div class="class-picker-grid"><label v-for="item in selectableClasses" :key="String(item.id)" class="class-picker-item"><input v-model="createClassIds" type="checkbox" :value="String(item.id)" /><span>{{ classLabel(item) }}</span></label></div><p v-if="!selectableClasses.length" class="muted">暂无启用教学班，请先到教学班管理创建。</p></div><button type="button" :disabled="working" @click="create">{{ working ? '创建中…' : '创建账号' }}</button></section>
    <section v-if="showImporter && !importLoading && !importToken" class="content-card import-setup"><div class="section-heading"><div><h3>批量导入学生账号</h3><p>Excel 中填写学号、姓名、班级名称（行政班）和性别；本批次统一使用下方教学班。</p></div></div><InlineMessage :message="importError" tone="error" /><div class="import-setup-row"><label>本批次统一教学班<input v-model="importTeachingClass" placeholder="例如：Python2026" /></label><button type="button" @click="chooseImport">选择 Excel 文件</button></div></section>
    <section v-if="importLoading || importToken" class="content-card import-preview"><div class="section-heading"><div><h3>批量导入预览</h3><p v-if="importLoading">正在解析 Excel…</p><p v-else>请核对导入数据，确认无误后再写入数据库。默认密码为学号。</p></div><button v-if="!importLoading" class="secondary-button" type="button" @click="importToken = ''; importRows = []; importErrors = []; importError = ''">取消预览</button></div><InlineMessage :message="importError" tone="error" /><div v-if="!importLoading"><div class="import-result-summary"><span>可导入 {{ importRows.length }} 条</span><span :class="{ 'import-error-count': importErrors.length }">错误 {{ importErrors.length }} 条</span></div><div v-if="importRows.length || importErrors.length" class="import-table-scroll"><div class="import-table"><div class="import-table-head"><span>行号</span><span>学号</span><span>姓名</span><span>性别</span><span>行政班</span><span>教学班</span><span>校验结果</span><span>处理</span></div><div v-for="item in [...importRows, ...importErrors]" :key="String(item.row)" class="import-table-row"><span>{{ item.row }}</span><span>{{ item.username }}</span><span>{{ item.name }}</span><span>{{ item.gender_label || '—' }}</span><span>{{ item.administrative_class || '—' }}</span><span>{{ item.teaching_class || '—' }}</span><span :class="{ 'import-error-text': item.errors }">{{ importErrorText(item) }}</span><span class="import-row-action"><button v-if="item.errors" class="small-button danger-button" type="button" @click="removeImportError(item)">删除</button><span v-else>—</span></span></div></div></div><button v-if="importRows.length && !importErrors.length" type="button" :disabled="working" @click="confirmImport">{{ working ? '导入中…' : `确认导入 ${importRows.length} 个账号` }}</button></div></section>
    <section class="account-filters" aria-label="账号筛选"><label class="account-search">搜索账号或姓名<input v-model="keyword" placeholder="输入用户名或姓名" @keyup.enter="search" /></label><label>角色<select v-model="role"><option value="all">全部角色</option><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option></select></label><label>行政班<select v-model="administrativeClass"><option value="">全部行政班</option><option v-for="item in allAdministrativeClasses" :key="item" :value="item">{{ item }}</option></select></label><label>教学班<select v-model="teachingClass"><option value="">全部教学班</option><option v-for="item in allTeachingClasses" :key="item" :value="item">{{ item }}</option></select></label><label>账号状态<select v-model="accountStatus"><option value="all">全部状态</option><option value="active">启用</option><option value="inactive">停用</option></select></label><div class="filter-actions"><button type="button" @click="search">查询</button><button class="secondary-button" type="button" @click="resetFilters">重置</button></div></section>
    <section class="content-card flush-card"><div class="account-summary"><strong>账号列表</strong><span>共 {{ meta.total || 0 }} 个账号</span></div><InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" /><div v-if="loading" class="loading-state">正在加载账号…</div><div v-else-if="accounts.length" class="account-table"><div class="account-table-head"><span>用户名</span><span>姓名</span><span>角色</span><span>行政班</span><span>教学班</span><span>状态</span><span>操作</span></div><article v-for="account in accounts" :key="`${account.role}-${account.username}`" class="account-table-row"><strong>{{ account.username }}</strong><strong>{{ account.name || '—' }}</strong><StatusBadge :label="String(account.role_label || roleLabels[String(account.role)] || '—')" :tone="account.role === 'teacher' ? 'purple' : account.role === 'admin' ? 'orange' : 'blue'" /><span>{{ account.administrative_class || '—' }}</span><span>{{ account.teaching_class || '—' }}</span><StatusBadge :label="String(account.status ?? '未知')" :tone="account.status === '启用' ? 'green' : 'red'" /><div class="row-actions"><button class="small-button secondary-button" type="button" @click="openEdit(account)">修改</button><button v-if="account.role !== 'admin'" class="small-button secondary-button" type="button" @click="openClasses(account)">教学班</button><button class="small-button secondary-button" type="button" @click="resetTarget = account">重置密码</button><button class="small-button" type="button" @click="toggle(account)">{{ account.status === '启用' ? '停用' : '启用' }}</button></div></article></div><EmptyState v-else title="没有符合条件的账号" description="请调整筛选条件后重试。" /><div v-if="totalPages > 1" class="pagination"><button class="secondary-button" :disabled="page <= 1" type="button" @click="load(1)">首页</button><button class="secondary-button" :disabled="page <= 1" type="button" @click="load(page - 1)">上一页</button><span>第 {{ page }} / {{ totalPages }} 页</span><button class="secondary-button" :disabled="page >= totalPages" type="button" @click="load(page + 1)">下一页</button><button class="secondary-button" :disabled="page >= totalPages" type="button" @click="load(totalPages)">末页</button><label class="pagination-jump">跳至<input v-model="jumpPage" type="number" min="1" :max="totalPages" @keyup.enter="jump" />页</label><button class="secondary-button" type="button" @click="jump">跳转</button></div></section>
    <div v-if="editTarget" class="modal-backdrop" @click.self="editTarget = null"><section class="modal-card"><div class="section-heading"><div><h3>修改账号资料</h3><p>{{ roleLabels[String(editTarget.role)] }} · {{ editTarget.username }}</p></div><button class="icon-button" type="button" aria-label="关闭" @click="editTarget = null">×</button></div><InlineMessage :message="editModalError" tone="error" /><p class="muted">用户名和角色不能修改。</p><label><span class="required-label">姓名 <b class="required-mark">*</b></span><input v-model="editName" /></label><template v-if="editTarget.role === 'student'"><label>性别<select v-model="editGender"><option value="">未填写</option><option value="1">男</option><option value="2">女</option><option value="0">其他</option></select></label><label>行政班<input v-model="editAdministrativeClass" placeholder="例如：大数据2404" /></label></template><div class="modal-actions"><button class="secondary-button" type="button" @click="editTarget = null">取消</button><button type="button" :disabled="working" @click="saveEdit">{{ working ? '保存中…' : '保存修改' }}</button></div></section></div>
    <div v-if="classTarget" class="modal-backdrop" @click.self="classTarget = null"><section class="modal-card account-class-modal"><div class="section-heading"><div><h3>配置教学班</h3><p>{{ classTarget.name }}（{{ classTarget.username }}）</p></div><button class="icon-button" type="button" aria-label="关闭" @click="classTarget = null">×</button></div><InlineMessage :message="classModalError" tone="error" /><div class="class-picker-grid"><label v-for="item in selectableClasses" :key="String(item.id)" class="class-picker-item"><input v-model="editClassIds" type="checkbox" :value="String(item.id)" /><span>{{ classLabel(item) }}</span></label></div><div class="modal-actions"><button class="secondary-button" type="button" @click="classTarget = null">取消</button><button type="button" :disabled="working" @click="saveClasses">{{ working ? '保存中…' : '保存关系' }}</button></div></section></div>
    <div v-if="resetTarget" class="modal-backdrop"><section class="modal-card"><div class="section-heading"><div><h3>重置密码</h3><p>{{ resetTarget.name }}（{{ resetTarget.username }}）</p></div><button class="icon-button" type="button" aria-label="关闭" @click="resetTarget = null">×</button></div><InlineMessage :message="resetModalError" tone="error" /><label>新密码<input v-model="newPassword" type="password" placeholder="请输入新密码" /></label><div class="modal-actions"><button class="secondary-button" type="button" @click="resetTarget = null">取消</button><button type="button" :disabled="working" @click="reset">确认重置</button></div></section></div>
  </div>
</template>
