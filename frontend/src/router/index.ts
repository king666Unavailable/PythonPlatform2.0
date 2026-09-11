import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'
import LoginView from '@/views/auth/LoginView.vue'
import PasswordChangeView from '@/views/auth/PasswordChangeView.vue'
import StudentHomeView from '@/views/student/StudentHomeView.vue'
import StudentAssignmentsView from '@/views/student/StudentAssignmentsView.vue'
import StudentAssignmentView from '@/views/student/StudentAssignmentView.vue'
import StudentKnowledgeView from '@/views/student/StudentKnowledgeView.vue'
import StudentQuestionsView from '@/views/student/StudentQuestionsView.vue'
import StudentMockView from '@/views/student/StudentMockView.vue'
import StudentAiView from '@/views/student/StudentAiView.vue'
import StudentProfileView from '@/views/student/StudentProfileView.vue'
import StudentLearningProfileView from '@/views/student/StudentLearningProfileView.vue'
import TeacherHomeView from '@/views/teacher/TeacherHomeView.vue'
import TeacherClassView from '@/views/teacher/TeacherClassView.vue'
import TeacherAssignmentsView from '@/views/teacher/TeacherAssignmentsView.vue'
import TeacherAssignmentStatisticsView from '@/views/teacher/TeacherAssignmentStatisticsView.vue'
import TeacherMakeupWindowsView from '@/views/teacher/TeacherMakeupWindowsView.vue'
import TeacherQuestionBankView from '@/views/teacher/TeacherQuestionBankView.vue'
import TeacherKnowledgeView from '@/views/teacher/TeacherKnowledgeView.vue'
import TeacherExamsView from '@/views/teacher/TeacherExamsView.vue'
import TeacherAiView from '@/views/teacher/TeacherAiView.vue'
import AdminHomeView from '@/views/admin/AdminHomeView.vue'
import AdminAccountsView from '@/views/admin/AdminAccountsView.vue'
import AdminClassesView from '@/views/admin/AdminClassesView.vue'
import AdminAuditView from '@/views/admin/AdminAuditView.vue'
import AdminFeatureVisibilityView from '@/views/admin/AdminFeatureVisibilityView.vue'
import { useAuthStore } from '@/stores/auth'
import { useNavigationStore } from '@/stores/navigation'
import type { UserRole } from '@/types/auth'

function roleHomePath() {
  const role = useAuthStore().user.value?.role
  return role ? (role === 'student' ? '/student' : `/${role}`) : '/login'
}

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true, title: '登录' } },
  { path: '/password-change', name: 'password-change', component: PasswordChangeView, meta: { public: true, title: '修改密码' } },
  {
    path: '/',
    component: AppShell,
    children: [
      { path: '', redirect: roleHomePath },
      { path: 'home', name: 'home', redirect: roleHomePath },
      { path: 'student', name: 'student-home', component: StudentHomeView, meta: { roles: ['student'], featureId: 'student-home', title: '首页' } },
      { path: 'student/assignments', name: 'student-assignments', component: StudentAssignmentsView, meta: { roles: ['student'], featureId: 'student-assignments', title: '我的作业' } },
      { path: 'student/assignments/:id', name: 'student-assignment', component: StudentAssignmentView, meta: { roles: ['student'], featureId: 'student-assignments', title: '完成作业' } },
      { path: 'student/grades', name: 'student-grades', redirect: '/student/profile', meta: { roles: ['student'], featureId: 'student-profile', title: '个人中心' } },
      { path: 'student/knowledge', name: 'student-knowledge', component: StudentKnowledgeView, meta: { roles: ['student'], featureId: 'student-knowledge', title: '知识图谱' } },
      { path: 'student/questions', name: 'student-questions', component: StudentQuestionsView, meta: { roles: ['student'], featureId: 'student-questions', title: '题目练习' } },
      { path: 'student/mock', name: 'student-mock', component: StudentMockView, meta: { roles: ['student'], featureId: 'student-mock', title: '模拟练习' } },
      { path: 'student/ai', name: 'student-ai', component: StudentAiView, meta: { roles: ['student'], featureId: 'student-ai', title: 'AI 助教' } },
      { path: 'student/profile', name: 'student-profile', component: StudentProfileView, meta: { roles: ['student'], featureId: 'student-profile', title: '个人中心' } },
      { path: 'student/learning-profile', name: 'student-learning-profile', component: StudentLearningProfileView, meta: { roles: ['student'], featureId: 'student-learning-profile', title: '学情画像' } },
      { path: 'teacher', name: 'teacher-home', component: TeacherHomeView, meta: { roles: ['teacher'], featureId: 'teacher-home', title: '教学概览' } },
      { path: 'teacher/class', name: 'teacher-class', component: TeacherClassView, meta: { roles: ['teacher'], featureId: 'teacher-class', title: '班级学情' } },
      { path: 'teacher/assignments', name: 'teacher-assignments', component: TeacherAssignmentsView, meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '作业管理' } },
      { path: 'teacher/assignments/:id/statistics', name: 'teacher-assignment-statistics', component: TeacherAssignmentStatisticsView, meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '作业统计' } },
      { path: 'teacher/assignments/:id/makeup-windows', name: 'teacher-assignment-makeups', component: TeacherMakeupWindowsView, meta: { roles: ['teacher'], featureId: 'teacher-assignments', title: '补交设置' } },
      { path: 'teacher/questions', name: 'teacher-question-bank', component: TeacherQuestionBankView, meta: { roles: ['teacher'], featureId: 'teacher-question-bank', title: '题库管理' } },
      { path: 'teacher/knowledge', name: 'teacher-knowledge', component: TeacherKnowledgeView, meta: { roles: ['teacher'], featureId: 'teacher-knowledge', title: '知识节点' } },
      { path: 'teacher/exams', name: 'teacher-exams', component: TeacherExamsView, meta: { roles: ['teacher'], featureId: 'teacher-exams', title: '组卷与考试' } },
      { path: 'teacher/ai', name: 'teacher-ai', component: TeacherAiView, meta: { roles: ['teacher'], featureId: 'teacher-ai', title: 'AI 出题' } },
      { path: 'admin', name: 'admin-home', component: AdminHomeView, meta: { roles: ['admin'], title: '平台概览' } },
      { path: 'admin/accounts', name: 'admin-accounts', component: AdminAccountsView, meta: { roles: ['admin'], title: '账号管理' } },
      { path: 'admin/classes', name: 'admin-classes', component: AdminClassesView, meta: { roles: ['admin'], title: '教学班管理' } },
      { path: 'admin/audit', name: 'admin-audit', component: AdminAuditView, meta: { roles: ['admin'], title: '操作记录' } },
      { path: 'admin/features', name: 'admin-features', component: AdminFeatureVisibilityView, meta: { roles: ['admin'], title: '功能配置' } },
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
