<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createAdminClass, fetchAdminClasses, fetchAdminClassMembers, updateAdminClass, updateAdminClassMembers } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const classes = ref<Array<Record<string, unknown>>>([])
const keyword = ref('')
const status = ref('all')
const appliedKeyword = ref('')
const loading = ref(true)
const working = ref(false)
const error = ref('')
const success = ref('')
const creatorError = ref('')
const showCreator = ref(false)
const title = ref('')
const teachingClass = ref('')
const academicYear = ref('')
const classEditTarget = ref<Record<string, unknown> | null>(null)
const classEditTitle = ref('')
const classEditTeachingClass = ref('')
const classEditAcademicYear = ref('')
const classEditError = ref('')
const editingClass = ref<Record<string, unknown> | null>(null)
const memberLoading = ref(false)
const memberError = ref('')
const memberSuccess = ref('')
const memberRole = ref<'teacher' | 'student'>('teacher')
const memberKeyword = ref('')
const teacherOptions = ref<Array<Record<string, unknown>>>([])
const studentOptions = ref<Array<Record<string, unknown>>>([])
const selectedTeachers = ref<string[]>([])
const selectedStudents = ref<string[]>([])

const selectedUsernames = computed({
  get: () => memberRole.value === 'teacher' ? selectedTeachers.value : selectedStudents.value,
  set: (value: string[]) => {
    if (memberRole.value === 'teacher') selectedTeachers.value = value
    else selectedStudents.value = value
  },
})
const currentOptions = computed(() => memberRole.value === 'teacher' ? teacherOptions.value : studentOptions.value)
const filteredMemberOptions = computed(() => {
  const keyword = memberKeyword.value.trim().toLowerCase()
  if (!keyword) return currentOptions.value
  return currentOptions.value.filter((account) => String(account.name || '').toLowerCase().includes(keyword) || String(account.username || '').toLowerCase().includes(keyword))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchAdminClasses({ q: appliedKeyword.value, status: status.value })
    classes.value = result.items
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '班级加载失败。'
  } finally {
    loading.value = false
  }
}

function search() {
  appliedKeyword.value = keyword.value.trim()
  void load()
}

function reset() {
  keyword.value = ''
  appliedKeyword.value = ''
  status.value = 'all'
  void load()
}

async function create() {
  if (!title.value.trim() || !teachingClass.value.trim()) {
    creatorError.value = '课程名称和教学班名称不能为空。'
    return
  }
  working.value = true
  creatorError.value = ''
  try {
    await createAdminClass({ title: title.value.trim(), teaching_class: teachingClass.value.trim(), academic_year: academicYear.value.trim() })
    title.value = ''; teachingClass.value = ''; academicYear.value = ''; showCreator.value = false
    success.value = '教学班已创建。'
    await load()
  } catch (cause) {
    creatorError.value = cause instanceof Error ? cause.message : '教学班创建失败。'
  } finally {
    working.value = false
  }
}

async function toggle(item: Record<string, unknown>) {
  const active = Boolean(item.is_active)
  if (!window.confirm(`确定${active ? '停用' : '启用'}教学班“${item.teaching_class}”吗？`)) return
  try {
    await updateAdminClass(String(item.id), { is_active: !active })
    success.value = `教学班已${active ? '停用' : '启用'}。`
    await load()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '教学班状态更新失败。'
  }
}

function openClassEdit(item: Record<string, unknown>) {
  classEditTarget.value = item
  classEditTitle.value = String(item.title || '')
  classEditTeachingClass.value = String(item.teaching_class || '')
  classEditAcademicYear.value = String(item.academic_year || '')
  classEditError.value = ''
}

async function saveClassEdit() {
  if (!classEditTarget.value) return
  if (!classEditTitle.value.trim() || !classEditTeachingClass.value.trim()) {
    classEditError.value = '课程名称和教学班名称不能为空。'
    return
  }
  working.value = true
  classEditError.value = ''
  try {
    await updateAdminClass(String(classEditTarget.value.id), {
      title: classEditTitle.value.trim(),
      teaching_class: classEditTeachingClass.value.trim(),
      academic_year: classEditAcademicYear.value.trim(),
    })
    classEditTarget.value = null
    success.value = '教学班资料已更新。'
    await load()
  } catch (cause) {
    classEditError.value = cause instanceof Error ? cause.message : '教学班资料更新失败。'
  } finally {
    working.value = false
  }
}

async function openMembers(item: Record<string, unknown>) {
  editingClass.value = item
  memberKeyword.value = ''
  memberError.value = ''
  memberSuccess.value = ''
  memberLoading.value = true
  try {
    const result = await fetchAdminClassMembers(String(item.id))
    teacherOptions.value = result.options.teachers || []
    studentOptions.value = result.options.students || []
    selectedTeachers.value = (result.members.teachers || []).map((account) => String(account.username))
    selectedStudents.value = (result.members.students || []).map((account) => String(account.username))
  } catch (cause) {
    memberError.value = cause instanceof Error ? cause.message : '班级成员加载失败。'
  } finally {
    memberLoading.value = false
  }
}

async function saveMembers() {
  if (!editingClass.value) return
  working.value = true
  memberError.value = ''
  memberSuccess.value = ''
  try {
    await updateAdminClassMembers(String(editingClass.value.id), memberRole.value, selectedUsernames.value)
    const current = editingClass.value
    await openMembers(current)
    memberSuccess.value = `${memberRole.value === 'teacher' ? '教师' : '学生'}教学班关系已保存。`
    await load()
  } catch (cause) {
    memberError.value = cause instanceof Error ? cause.message : '班级成员保存失败。'
  } finally {
    working.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="教学班管理" description="维护教学班，并管理教师和学生的多教学班关系。">
      <template #actions><button type="button" @click="showCreator = true">新建教学班</button></template>
    </PageHeader>
    <section class="account-filters" aria-label="班级筛选">
      <label class="account-search">搜索课程或教学班<input v-model="keyword" placeholder="输入课程名称、教学班或学年" @keyup.enter="search" /></label>
      <label>状态<select v-model="status" @change="load"><option value="all">全部状态</option><option value="active">启用</option><option value="inactive">停用</option></select></label>
      <div class="filter-actions"><button type="button" @click="search">查询</button><button class="secondary-button" type="button" @click="reset">重置</button></div>
    </section>

    <section class="content-card flush-card">
      <div class="account-summary"><strong>教学班列表</strong><span>共 {{ classes.length }} 个教学班</span></div>
      <InlineMessage :message="error" tone="error" />
      <InlineMessage :message="success" tone="success" />
      <div v-if="loading" class="loading-state">正在加载教学班…</div>
      <div v-else-if="classes.length" class="admin-class-table">
        <div class="admin-class-table-head"><span>课程与教学班</span><span>学年</span><span>教师</span><span>学生</span><span>状态</span><span>操作</span></div>
        <article v-for="item in classes" :key="String(item.id)" class="admin-class-table-row">
          <div><strong>{{ item.teaching_class || '未命名教学班' }}</strong><small>{{ item.title || '未填写课程名称' }}</small></div>
          <span>{{ item.academic_year || '—' }}</span><span>{{ item.teacher_count ?? 0 }} 人</span><span>{{ item.student_count ?? 0 }} 人</span>
          <StatusBadge :label="item.is_active ? '启用' : '未开放'" :tone="item.is_active ? 'green' : 'red'" />
          <div class="row-actions"><button class="small-button secondary-button" type="button" @click="openClassEdit(item)">修改</button><button class="small-button secondary-button" type="button" @click="openMembers(item)">管理成员</button><button class="small-button" type="button" @click="toggle(item)">{{ item.is_active ? '停用' : '启用' }}</button></div>
        </article>
      </div>
      <EmptyState v-else title="暂无教学班" description="可以先创建一个教学班。" />
    </section>

    <div v-if="showCreator" class="modal-backdrop" @click.self="showCreator = false"><section class="modal-card admin-class-modal"><div class="section-heading"><div><h3>新建教学班</h3><p>如果相同课程、教学班和学年已经存在，系统会提示并停止重复创建。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="showCreator = false">×</button></div><InlineMessage :message="creatorError" tone="error" /><label>课程名称<input v-model="title" placeholder="例如：Python程序设计" /></label><label>教学班名称<input v-model="teachingClass" placeholder="例如：Python2026" /></label><label>学年/学期<input v-model="academicYear" placeholder="例如：2026春" /></label><div class="modal-actions"><button class="secondary-button" type="button" @click="showCreator = false">取消</button><button type="button" :disabled="working" @click="create">{{ working ? '创建中…' : '创建教学班' }}</button></div></section></div>

    <div v-if="classEditTarget" class="modal-backdrop" @click.self="classEditTarget = null"><section class="modal-card admin-class-modal"><div class="section-heading"><div><h3>修改教学班</h3><p>成员关系和启用状态不会随基础资料修改。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="classEditTarget = null">×</button></div><InlineMessage :message="classEditError" tone="error" /><label><span class="required-label">课程名称 <b class="required-mark">*</b></span><input v-model="classEditTitle" /></label><label><span class="required-label">教学班名称 <b class="required-mark">*</b></span><input v-model="classEditTeachingClass" /></label><label>学年/学期<input v-model="classEditAcademicYear" placeholder="例如：2026春" /></label><div class="modal-actions"><button class="secondary-button" type="button" @click="classEditTarget = null">取消</button><button type="button" :disabled="working" @click="saveClassEdit">{{ working ? '保存中…' : '保存修改' }}</button></div></section></div>

    <div v-if="editingClass" class="modal-backdrop" @click.self="editingClass = null"><section class="modal-card admin-member-modal"><div class="section-heading"><div><h3>{{ editingClass.teaching_class }} · 管理成员</h3><p>同一账号重复保存不会创建重复关系。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="editingClass = null">×</button></div><div v-if="memberLoading" class="loading-state">正在加载成员…</div><template v-else><InlineMessage :message="memberError" tone="error" /><InlineMessage :message="memberSuccess" tone="success" /><div class="member-tabs"><button type="button" :class="{ active: memberRole === 'teacher' }" @click="memberRole = 'teacher'">教师（{{ selectedTeachers.length }}）</button><button type="button" :class="{ active: memberRole === 'student' }" @click="memberRole = 'student'">学生（{{ selectedStudents.length }}）</button></div><label class="member-search">筛选姓名或账号<input v-model="memberKeyword" placeholder="输入姓名或用户名" /></label><div class="member-picker"><label v-for="account in filteredMemberOptions" :key="String(account.username)" class="member-option"><input v-model="selectedUsernames" type="checkbox" :value="String(account.username)" /><span><strong>{{ account.name }}</strong><small>{{ account.username }}</small></span></label><p v-if="!currentOptions.length" class="muted">暂无可关联的启用账号。</p><p v-else-if="!filteredMemberOptions.length" class="muted">没有找到匹配的账号。</p></div><div class="modal-actions"><button class="secondary-button" type="button" @click="editingClass = null">关闭</button><button type="button" :disabled="working" @click="saveMembers">{{ working ? '保存中…' : '保存当前成员' }}</button></div></template></section></div>
  </div>
</template>
