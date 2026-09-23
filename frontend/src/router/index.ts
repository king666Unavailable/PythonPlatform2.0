import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'
import { useAuthStore } from '@/stores/auth'
import { useNavigationStore } from '@/stores/navigation'
import type { UserRole } from '@/types/auth'

function roleHomePath() {
  const role = useAuthStore().user.value?.role
  return role ? (role === 'student' ? '/student' : `/${role}`) : '/login'
}

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true, title: '登录' } },
  { path: '/password-change', name: 'password-change', component: () => import('@/views/auth/PasswordChangeView.vue'), meta: { public: true, title: '修改密码' } },
  {
    path: '/',
    component: AppShell,
    children: [
      { path: '', redirect: roleHomePath },
      { path: 'home', name: 'home', redirect: roleHomePath },
      { path: 'student', name: 'student-home', component: () => import('@/views/student/StudentHomeView.vue'), meta: { roles: ['student'], featureId: 'student-home', title: '首页' } },
      { path: 'student/assignments', name: 'student-assignments', component: () => import('@/views/student/StudentAssignmentsView.vue'), meta: { roles: ['student'], featureId: 'student-assignments', title: '我的作业' } },
      { path: 'student/assignments/:id', name: 'student-assignment', component: () => import('@/views/student/StudentAssignmentView.vue'), meta: { roles: ['student'], featureId: 'student-assignments', title: '完成作业' } },
      { path: 'student/grades', name: 'student-grades', redirect: '/student/profile', meta: { roles: ['student'], featureId: 'student-profile', title: '个人中心' } },
      { path: 'student/knowledge', name: 'student-knowledge', component: () => import('@/views/student/StudentKnowledgeView.vue'), meta: { roles: ['student'], featureId: 'student-knowledge', title: '知识图谱' } },
      { path: 'student/questions', name: 'student-questions', component: () => import('@/views/student/StudentQuestionsView.vue'), meta: { roles: ['student'], featureId: 'student-questions', title: '题目练习' } },
      { path: 'student/mock', name: 'student-mock', component: () => import('@/views/student/StudentMockView.vue'), meta: { roles: ['student'], featureId: 'student-mock', title: '模拟练习' } },
      { path: 'student/ai', name: 'student-ai', component: () => import('@/views/student/StudentAiView.vue'), meta: { roles: ['student'], featureId: 'student-ai', title: 'AI 助教' } },
      { path: 'student/profile', name: 'student-profile', component: () => import('@/views/student/StudentProfileView.vue'), meta: { roles: ['student'], featureId: 'student-profile', title: '个人中心' } },
      { path: 'student/learning-profile', name: 'student-learning-profile', component: () => import('@/views/student/StudentLearningProfileView.vue'), meta: { roles: ['student'], featureId: 'student-learning-profile', title: '学情画像' } },
      { path: 'teacher', name: 'teacher-home', component: () => import('@/views/teacher/TeacherHomeView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-home', title: '教学概览' } },
      { path: 'teacher/class', name: 'teacher-class', component: () => import('@/views/teacher/TeacherClassView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-class', title: '班级学情' } },
      { path: 'teacher/students/import', name: 'teacher-student-import', component: () => import('@/views/teacher/TeacherStudentImportView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-student-import', title: '学生导入' } },
      { path: 'teacher/student-audit', name: 'teacher-student-audit', component: () => import('@/views/teacher/TeacherStudentAuditView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-student-audit', title: '学生操作记录' } },
      { path: 'teacher/assignments', name: 'teacher-assignments', component: () => import('@/views/teacher/TeacherAssignmentsView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '作业管理' } },
      { path: 'teacher/assignments/:id/statistics', name: 'teacher-assignment-statistics', component: () => import('@/views/teacher/TeacherAssignmentStatisticsView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '作业统计' } },
      { path: 'teacher/assignments/:id/makeup-windows', name: 'teacher-assignment-makeups', component: () => import('@/views/teacher/TeacherMakeupWindowsView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '补交设置' } },
      { path: 'teacher/questions', name: 'teacher-question-bank', component: () => import('@/views/teacher/TeacherQuestionBankView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-question-bank', title: '题库管理' } },
      { path: 'teacher/knowledge', name: 'teacher-knowledge', component: () => import('@/views/teacher/TeacherKnowledgeView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-knowledge', title: '知识图谱管理' } },
      { path: 'teacher/exams', name: 'teacher-exams', component: () => import('@/views/teacher/TeacherExamsView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-exams', title: '组卷与考试' } },
      { path: 'teacher/ai', name: 'teacher-ai', component: () => import('@/views/teacher/TeacherAiView.vue'), meta: { roles: ['teacher'], featureId: 'teacher-ai', title: 'AI 出题' } },
      { path: 'admin', name: 'admin-home', component: () => import('@/views/admin/AdminHomeView.vue'), meta: { roles: ['admin'], title: '平台概览' } },
      { path: 'admin/accounts', name: 'admin-accounts', component: () => import('@/views/admin/AdminAccountsView.vue'), meta: { roles: ['admin'], title: '账号管理' } },
      { path: 'admin/classes', name: 'admin-classes', component: () => import('@/views/admin/AdminClassesView.vue'), meta: { roles: ['admin'], title: '教学班管理' } },
      { path: 'admin/audit', name: 'admin-audit', component: () => import('@/views/admin/AdminAuditView.vue'), meta: { roles: ['admin'], title: '操作记录' } },
      { path: 'admin/features', name: 'admin-features', component: () => import('@/views/admin/AdminFeatureVisibilityView.vue'), meta: { roles: ['admin'], title: '功能配置' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  document.title = to.name === 'login' ? 'Python教学平台 - 登录' : 'Python教学平台'
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const navigation = useNavigationStore()
  await auth.bootstrap()
  if (to.name === 'login' && auth.user.value) return auth.user.value.role === 'student' ? '/student' : `/${auth.user.value.role}`
  if (to.meta.public) return true
  if (!auth.user.value) return '/login'
  const roles = to.meta.roles as UserRole[] | undefined
  if (roles && !roles.includes(auth.user.value.role)) return `/${auth.user.value.role}`
  if (auth.user.value.role === 'student' || auth.user.value.role === 'teacher') {
    await navigation.bootstrap(auth.user.value.role)
    const featureId = String(to.meta.featureId || '')
    if (featureId && !navigation.groupsForRole(auth.user.value.role).some((group) => group.items.some((item) => item.id === featureId))) {
      return navigation.firstPath(auth.user.value.role)
    }
  }
  return true
})

export default router
