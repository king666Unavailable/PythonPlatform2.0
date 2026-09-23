import type { User } from '@/types/auth'
import type { StudentProfileReport } from '@/types/student'
import type { KnowledgeGraphResponse } from '@/types/knowledge'
import type { StudentMasteryResponse } from '@/types/mastery'
import type { LearningProfileReport } from '@/types/learningProfile'
import type { LearningPathResponse, StudentAnalyticsResponse } from '@/types/analytics'
import type { Question, QuestionListResponse } from '@/types/question'
import type { ClassAnalyticsResponse, ClassKnowledgeMasteryResponse, TeacherStudentProfileResponse } from '@/types/teacher'
import type { WorkspaceData } from '@/types/workspace'
import type { ClassContextResponse, TeachingClass } from '@/types/classContext'
import type { NavigationVisibilityItem } from '@/types/navigation'

interface AuthResponse {
  message: string
  user?: User
}

interface ErrorPayload {
  message?: string
  detail?: string
  code?: string
  errors?: unknown
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function firstErrorMessage(errors: unknown): string | undefined {
  if (typeof errors === 'string') return errors
  if (Array.isArray(errors)) {
    for (const error of errors) {
      const message = firstErrorMessage(error)
      if (message) return message
    }
  }
  if (errors && typeof errors === 'object') {
    for (const error of Object.values(errors)) {
      const message = firstErrorMessage(error)
      if (message) return message
    }
  }
  return undefined
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 15000, timeoutMessage = '请求超时，请稍后重试。'): Promise<T> {
  const csrfCookie = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      credentials: 'include',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(csrfCookie ? { 'X-CSRFToken': decodeURIComponent(csrfCookie) } : {}),
        ...(options.headers ?? {}),
      },
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') {
      throw new Error(timeoutMessage)
    }
    throw cause
  } finally {
    window.clearTimeout(timeout)
  }

  const payload = (await response.json().catch(() => ({}))) as ErrorPayload
  if (!response.ok) {
    throw new ApiError(payload.message ?? payload.detail ?? firstErrorMessage(payload.errors) ?? '请求失败，请稍后重试。', response.status, payload.code)
  }
  return payload as T
}

export function ensureCsrfToken() {
  return request<{ csrf: string }>('/api/v1/auth/csrf')
}

export async function login(username: string, password: string) {
  await ensureCsrfToken()
  return request<AuthResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function changePassword(username: string, oldPassword: string, newPassword: string, confirmPassword: string) {
  await ensureCsrfToken()
  return request<AuthResponse>('/api/v1/auth/password-change', {
    method: 'POST',
    body: JSON.stringify({
      username,
      old_password: oldPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  })
}

export function fetchCurrentUser() {
  return request<{ user: User }>('/api/v1/auth/me')
}

export function fetchClassContext() {
  return request<ClassContextResponse>('/api/v1/context/classes')
}

export function setCurrentClass(classId: string) {
  return request<{ current: TeachingClass }>('/api/v1/context/classes/current', {
    method: 'POST',
    body: JSON.stringify({ class_id: classId }),
  })
}

export function fetchNavigationSettings() {
  return request<{ items: NavigationVisibilityItem[]; meta: Record<string, unknown> }>('/api/v1/navigation')
}

export async function logout() {
  await ensureCsrfToken()
  return request<AuthResponse>('/api/v1/auth/logout', { method: 'POST' })
}

export function checkRoleAccess(role: 'teacher' | 'student' | 'admin') {
  return request<{ access: string; role: string }>(`/api/v1/auth/access/${role}`)
}

export function fetchStudentProfile() {
  return request<StudentProfileReport>('/api/v1/student/me')
}

export interface StudentQuestionnaireResponse {
  completed: boolean
  responses: Record<string, unknown>
  completed_at: string | null
  updated_at: string | null
}

export function fetchStudentQuestionnaire() {
  return request<{ questionnaire: StudentQuestionnaireResponse; completed: boolean }>('/api/v1/student/questionnaire')
}

export function saveStudentQuestionnaire(responses: Record<string, unknown>) {
  return request<{ questionnaire: StudentQuestionnaireResponse; completed: boolean }>('/api/v1/student/questionnaire', {
    method: 'PUT',
    body: JSON.stringify({ responses }),
  })
}

export function fetchStudentMastery() {
  return request<StudentMasteryResponse>('/api/v1/student/me/mastery')
}

export function fetchStudentLearningProfile() {
  return request<LearningProfileReport>('/api/v1/student/me/learning-profile')
}

export function fetchLearningPath() {
  return request<LearningPathResponse>('/api/v1/student/me/learning-path')
}

export function fetchStudentAnalytics() {
  return request<StudentAnalyticsResponse>('/api/v1/student/me/analytics')
}

export function fetchClassAnalytics(classId = 'all') {
  return request<ClassAnalyticsResponse>(`/api/v1/classes/${encodeURIComponent(classId)}/analytics`)
}

export function fetchTeacherStudentProfile(studentId: string) {
  return request<TeacherStudentProfileResponse>(`/api/v1/students/${encodeURIComponent(studentId)}/profile`)
}

export function fetchTeacherClassMastery(nodeType = '', nodeId = '') {
  const params = new URLSearchParams()
  if (nodeType && nodeId) {
    params.set('node_type', nodeType)
    params.set('node_id', nodeId)
  }
  const query = params.toString()
  return request<ClassKnowledgeMasteryResponse>(`/api/v1/teacher/class/knowledge-mastery${query ? `?${query}` : ''}`)
}

export function fetchTeacherClasses() {
  return request<{ items: Array<Record<string, unknown>>; meta: Record<string, unknown> }>('/api/v1/teacher/classes')
}

export function createTeacherClass(payload: Record<string, unknown>) {
  return request<{ class: Record<string, unknown> }>('/api/v1/teacher/classes/create', { method: 'POST', body: JSON.stringify(payload) })
}

export function createTeacherStudent(payload: Record<string, unknown>) {
  return request<{ created: number; student: Record<string, unknown> }>('/api/v1/teacher/classes/students/create', { method: 'POST', body: JSON.stringify(payload) })
}

export async function previewTeacherStudentImport(file: File, classId: string) {
  await ensureCsrfToken()
  const csrfCookie = document.cookie.split('; ').find((cookie) => cookie.startsWith('csrftoken='))?.split('=')[1]
  const form = new FormData(); form.append('file', file); form.append('class_id', classId)
  const response = await fetch('/api/v1/teacher/classes/import/preview', { method: 'POST', body: form, credentials: 'include', headers: csrfCookie ? { 'X-CSRFToken': decodeURIComponent(csrfCookie) } : {} })
  const payload = await response.json().catch(() => ({})) as ErrorPayload
  if (!response.ok) throw new ApiError(payload.message ?? 'Excel 解析失败。', response.status, payload.code)
  return payload as { token: string; class: Record<string, unknown>; rows: Array<Record<string, unknown>>; errors: Array<Record<string, unknown>>; can_import: boolean; meta: Record<string, unknown> }
}

export function confirmTeacherStudentImport(token: string) {
  return request<{ created: number; class_id: string }>('/api/v1/teacher/classes/import/confirm', { method: 'POST', body: JSON.stringify({ token }) })
}

export function fetchKnowledgeGraph() {
  return request<KnowledgeGraphResponse>('/api/v1/knowledge-graph', {}, 8000)
}

export function fetchQuestions(keyword = '', typeCode = '', pointTitle = '', page = 1, pageSize = 20) {
  const params = new URLSearchParams()
  if (keyword.trim()) params.set('q', keyword.trim())
  if (typeCode) params.set('type', typeCode)
  if (pointTitle.trim()) params.set('point', pointTitle.trim())
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  const query = params.toString()
  return request<QuestionListResponse>(`/api/v1/questions${query ? `?${query}` : ''}`)
}

export function fetchQuestionDetail(questionId: string) {
  return request<{ question: Question }>(`/api/v1/questions/${encodeURIComponent(questionId)}`)
}

export function fetchFeatureWorkspace(featureId: string) {
  return request<WorkspaceData>(`/api/v1/workspaces/${encodeURIComponent(featureId)}`)
}

export function fetchStudentAssignments() {
  return request<{ items: Array<Record<string, unknown>>; meta: Record<string, unknown> }>('/api/v1/student/me/assignments')
}

export function fetchAssignmentDetail(assignmentId: string, makeupWindowId?: string | null) {
  const query = makeupWindowId ? `?makeup_window_id=${encodeURIComponent(makeupWindowId)}` : ''
  return request<{ assignment: Record<string, unknown> }>(`/api/v1/assignments/${encodeURIComponent(assignmentId)}${query}`)
}

export function saveAssignmentDraft(assignmentId: string, answers: unknown, timeSpent: Record<string, number> = {}, options: { keepalive?: boolean; makeupWindowId?: string | null; submissionMode?: string } = {}) {
  return request<{ submission: Record<string, unknown> }>(`/api/v1/assignments/${encodeURIComponent(assignmentId)}/drafts`, {
    method: 'POST',
    body: JSON.stringify({ answers, time_spent: timeSpent, makeup_window_id: options.makeupWindowId ?? null, submission_mode: options.submissionMode ?? 'normal' }),
    keepalive: options.keepalive ?? false,
  })
}

export function submitAssignment(assignmentId: string, answers: unknown, idempotencyKey: string, timeSpent: Record<string, number> = {}, options: { makeupWindowId?: string | null; submissionMode?: string } = {}) {
  return request<{ submission: Record<string, unknown>; duplicate: boolean }>(`/api/v1/assignments/${encodeURIComponent(assignmentId)}/submissions`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ answers, time_spent: timeSpent, makeup_window_id: options.makeupWindowId ?? null, submission_mode: options.submissionMode ?? 'normal' }),
  })
}

export function fetchMySubmissions() {
  return request<{ items: Array<Record<string, unknown>> }>('/api/v1/student/me/submissions')
}

export function fetchGrades() {
  return request<{ items: Array<Record<string, unknown>> }>('/api/v1/grades')
}

export function fetchTeacherAssignments() {
  return request<{ items: Array<Record<string, unknown>> }>('/api/v1/teacher/assignments')
}

export function fetchMakeupWindows(assignmentId: string) {
  return request<{ assignment: Record<string, unknown>; makeup_windows: Array<Record<string, unknown>> }>(`/api/v1/teacher/assignments/${encodeURIComponent(assignmentId)}/makeup-windows`)
}

export function fetchAssignmentStatistics(assignmentId: string) {
  return request<Record<string, unknown>>(`/api/v1/teacher/assignments/${encodeURIComponent(assignmentId)}/statistics`)
}

export function createAssignment(payload: Record<string, unknown>) {
  return request<{ assignment: Record<string, unknown> }>('/api/v1/teacher/assignments/create', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateAssignment(assignmentId: string, payload: Record<string, unknown>) {
  return request<{ assignment: Record<string, unknown> }>(`/api/v1/teacher/assignments/${encodeURIComponent(assignmentId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function createMakeupWindow(assignmentId: string, payload: Record<string, unknown>) {
  return request<{ makeup_window: Record<string, unknown> }>(`/api/v1/teacher/assignments/${encodeURIComponent(assignmentId)}/makeup-windows`, { method: 'POST', body: JSON.stringify(payload) })
}

export function updateMakeupWindow(assignmentId: string, windowId: string, payload: Record<string, unknown>) {
  return request<{ makeup_window: Record<string, unknown> }>(`/api/v1/teacher/assignments/${encodeURIComponent(assignmentId)}/makeup-windows/${encodeURIComponent(windowId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function createExam(payload: Record<string, unknown>) {
  return request<{ assignment: Record<string, unknown> }>('/api/v1/teacher/exams', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function generatePaper(payload: Record<string, unknown>) {
  return request<{ assignment: Record<string, unknown>; selected_count: number }>('/api/v1/teacher/papers/generate', { method: 'POST', body: JSON.stringify(payload) })
}

export function createMockTest(payload: Record<string, unknown>) {
  return request<{ assignment: Record<string, unknown> }>('/api/v1/student/mock-tests', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchKnowledgeNodes(type = 'Point') {
  return request<{ items: Array<Record<string, unknown>> }>(`/api/v1/teacher/knowledge/nodes?type=${encodeURIComponent(type)}`)
}

export interface KnowledgeManagementNode {
  id: string
  title: string
  type: 'class' | 'theme' | 'knowledge' | 'point'
  level: number
  properties: Record<string, unknown>
  parent_type: 'class' | 'theme' | 'knowledge' | null
  parent_id: string | null
  children_count: number
  question_count: number
}

export function fetchKnowledgeManagementStructure() {
  return request<{ graph: { nodes: KnowledgeManagementNode[]; edges: Array<{ source: string; target: string; relation: string }> }; meta: { read_only: boolean; source: string } }>('/api/v1/teacher/knowledge/structure')
}

export function fetchKnowledgeManagementNode(nodeId: string) {
  return request<{ node: KnowledgeManagementNode & { children: KnowledgeManagementNode[] }; meta: Record<string, unknown> }>(`/api/v1/teacher/knowledge/nodes/${encodeURIComponent(nodeId)}/detail`)
}

export function fetchKnowledgeNodeDeleteImpact(nodeId: string) {
  return request<{ impact: { can_delete: boolean; children_count: number; question_count: number } }>(`/api/v1/teacher/knowledge/nodes/${encodeURIComponent(nodeId)}/impact`)
}

export function createKnowledgeNode(payload: Record<string, unknown>) {
  return request<{ node: Record<string, unknown> }>('/api/v1/teacher/knowledge/nodes/create', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateKnowledgeNode(nodeId: string, payload: Record<string, unknown>) {
  return request<{ node: Record<string, unknown> }>(`/api/v1/teacher/knowledge/nodes/${encodeURIComponent(nodeId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deleteKnowledgeNode(nodeId: string) {
  return request<{ deleted: boolean }>(`/api/v1/teacher/knowledge/nodes/${encodeURIComponent(nodeId)}/delete`, { method: 'DELETE' })
}

export function createQuestion(payload: Record<string, unknown>) {
  return request<{ question: Record<string, unknown> }>('/api/v1/teacher/questions', { method: 'POST', body: JSON.stringify(payload) })
}

export function fetchQuestion(questionId: string) {
  return request<{ question: Record<string, unknown> }>(`/api/v1/questions/${encodeURIComponent(questionId)}`)
}

export function batchCreateQuestions(questions: Array<Record<string, unknown>>) {
  return request<{ items: Array<Record<string, unknown>>; created: number }>('/api/v1/teacher/questions/batch', { method: 'POST', body: JSON.stringify({ questions }) })
}

export function updateQuestion(questionId: string, payload: Record<string, unknown>) {
  return request<{ question: Record<string, unknown> }>(`/api/v1/teacher/questions/${encodeURIComponent(questionId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deleteQuestion(questionId: string) {
  return request<{ deleted: boolean }>(`/api/v1/teacher/questions/${encodeURIComponent(questionId)}/delete`, { method: 'DELETE' })
}

export function runCode(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>(
    '/api/v1/code/runs',
    { method: 'POST', body: JSON.stringify(payload) },
    70000,
    '代码运行超时，请检查远程代码运行服务后重试。',
  )
}

export function compareBlankCode(payload: Record<string, unknown>) {
  return request<Record<string, unknown>>('/api/v1/code/runs/compare', { method: 'POST', body: JSON.stringify(payload) })
}

export function submitCode(assignmentId: string, answers: unknown, idempotencyKey: string) {
  return request<{ submission: Record<string, unknown>; duplicate: boolean }>(`/api/v1/assignments/${encodeURIComponent(assignmentId)}/code-submissions`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ answers }),
  })
}

export function fetchConversations() {
  return request<{ items: Array<Record<string, unknown>> }>('/api/v1/ai/conversations')
}

export function createConversation(title = '') {
  return request<{ conversation: Record<string, unknown> }>('/api/v1/ai/conversations', { method: 'POST', body: JSON.stringify({ title }) })
}

export function fetchConversation(conversationId: string) {
  return request<{ conversation: Record<string, unknown> }>(`/api/v1/ai/conversations/${encodeURIComponent(conversationId)}`)
}

export function sendConversationMessage(conversationId: string, content: string) {
  return request<{ conversation: Record<string, unknown>; answer?: string }>(`/api/v1/ai/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

export function generateQuestions(prompt: string) {
  return request<{ task: Record<string, unknown> }>('/api/v1/ai/questions', { method: 'POST', body: JSON.stringify({ prompt }) })
}

export function fetchGenerationTasks() {
  return request<{ items: Array<Record<string, unknown>> }>('/api/v1/ai/generation-tasks')
}

export function approveGenerationTask(taskId: string) {
  return request<{ approved: number; items: Array<Record<string, unknown>> }>(`/api/v1/ai/generation-tasks/${encodeURIComponent(taskId)}/approve`, { method: 'POST', body: '{}' })
}

export function fetchAdminAccounts(filters: { role?: string; q?: string; administrativeClass?: string; teachingClass?: string; studyClass?: string; status?: string; page?: number; pageSize?: number } = {}) {
  const params = new URLSearchParams()
  params.set('role', filters.role || 'all')
  if (filters.q?.trim()) params.set('q', filters.q.trim())
  if (filters.administrativeClass || filters.studyClass) params.set('administrative_class', filters.administrativeClass || filters.studyClass || '')
  if (filters.teachingClass) params.set('teaching_class', filters.teachingClass)
  if (filters.status && filters.status !== 'all') params.set('status', filters.status)
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.pageSize || 20))
  return request<{ items: Array<Record<string, unknown>>; meta: Record<string, unknown> }>(`/api/v1/admin/accounts?${params.toString()}`)
}

export function createAdminAccount(payload: Record<string, unknown>) {
  return request<{ account: Record<string, unknown> }>('/api/v1/admin/accounts/create', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateAdminAccount(role: string, username: string, payload: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/api/v1/admin/accounts/${encodeURIComponent(role)}/${encodeURIComponent(username)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function fetchAdminClasses(filters: { q?: string; status?: string } = {}) {
  const params = new URLSearchParams()
  if (filters.q?.trim()) params.set('q', filters.q.trim())
  if (filters.status && filters.status !== 'all') params.set('status', filters.status)
  return request<{ items: Array<Record<string, unknown>>; meta: Record<string, unknown> }>(`/api/v1/admin/classes?${params.toString()}`)
}

export function createAdminClass(payload: Record<string, unknown>) {
  return request<{ class: Record<string, unknown> }>('/api/v1/admin/classes/create', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateAdminClass(classId: string, payload: Record<string, unknown>) {
  return request<{ class: Record<string, unknown> }>(`/api/v1/admin/classes/${encodeURIComponent(classId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function fetchAdminClassMembers(classId: string) {
  return request<{ class: Record<string, unknown>; members: Record<string, Array<Record<string, unknown>>>; options: Record<string, Array<Record<string, unknown>>> }>(`/api/v1/admin/classes/${encodeURIComponent(classId)}/members`)
}

export function updateAdminClassMembers(classId: string, role: string, usernames: string[]) {
  return request<{ result: Record<string, unknown>; members: Record<string, Array<Record<string, unknown>>> }>(`/api/v1/admin/classes/${encodeURIComponent(classId)}/members`, { method: 'POST', body: JSON.stringify({ role, usernames }) })
}

export async function previewAdminAccountImport(file: File, teachingClass: string) {
  await ensureCsrfToken()
  const csrfCookie = document.cookie.split('; ').find((cookie) => cookie.startsWith('csrftoken='))?.split('=')[1]
  const form = new FormData(); form.append('file', file); form.append('teaching_class', teachingClass)
  const response = await fetch('/api/v1/admin/accounts/import/preview', { method: 'POST', body: form, credentials: 'include', headers: csrfCookie ? { 'X-CSRFToken': decodeURIComponent(csrfCookie) } : {} })
  const payload = await response.json().catch(() => ({})) as ErrorPayload
  if (!response.ok) throw new ApiError(payload.message ?? 'Excel 解析失败。', response.status, payload.code)
  return payload as { token: string; rows: Array<Record<string, unknown>>; errors: Array<Record<string, unknown>>; can_import: boolean; meta: Record<string, unknown> }
}

export function confirmAdminAccountImport(token: string) {
  return request<{ created: number; accounts: Array<Record<string, unknown>> }>('/api/v1/admin/accounts/import/confirm', { method: 'POST', body: JSON.stringify({ token }) })
}

export function fetchAuditLogs(filters: { category?: string; action?: string; q?: string; from?: string; to?: string; limit?: number; page?: number } = {}) {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const queryString = query.toString()
  return request<{ items: Array<Record<string, unknown>>; meta: { total: number; page?: number; page_size?: number; total_pages?: number } }>(`/api/v1/admin/audit-logs${queryString ? `?${queryString}` : ''}`)
}

export function fetchTeacherStudentOperationLogs(filters: { action?: string; q?: string; from?: string; to?: string; page?: number } = {}) {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const queryString = query.toString()
  return request<{
    items: Array<Record<string, unknown>>
    class: { id: string; title: string; teaching_class: string; academic_year: string }
    meta: { total: number; page: number; page_size: number; total_pages: number }
  }>(`/api/v1/teacher/student-operation-logs${queryString ? `?${queryString}` : ''}`)
}

export function fetchAdminNavigationSettings() {
  return request<{ roles: Record<'student' | 'teacher', NavigationVisibilityItem[]> }>('/api/v1/admin/navigation-settings')
}

export function updateAdminNavigationSettings(role: 'student' | 'teacher', items: Array<{ id: string; is_visible: boolean; sort_order: number }>) {
  return request<{ role: string; items: NavigationVisibilityItem[] }>('/api/v1/admin/navigation-settings', {
    method: 'PATCH',
    body: JSON.stringify({ role, items }),
  })
}
