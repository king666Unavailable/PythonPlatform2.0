export type NavigationRole = 'teacher' | 'student' | 'admin'

export interface NavigationItem {
  id: string
  label: string
  icon: string
  to: string
}

export interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

const studentGroups: NavigationGroup[] = [
  {
    label: '学习中心',
    items: [
      { id: 'student-home', label: '首页', icon: 'home', to: '/student' },
      { id: 'student-assignments', label: '我的作业', icon: 'assignment', to: '/student/assignments' },
      { id: 'student-knowledge', label: '知识图谱', icon: 'knowledge', to: '/student/knowledge' },
      { id: 'student-profile', label: '个人中心', icon: 'account', to: '/student/profile' },
      { id: 'student-learning-profile', label: '学情画像', icon: 'grade', to: '/student/learning-profile' },
    ],
  },
  {
    label: '练习与答疑',
    items: [
      { id: 'student-questions', label: '题目练习', icon: 'question', to: '/student/questions' },
      { id: 'student-mock', label: '模拟练习', icon: 'practice', to: '/student/mock' },
      { id: 'student-ai', label: 'AI 助教', icon: 'spark', to: '/student/ai' },
    ],
  },
]

const teacherGroups: NavigationGroup[] = [
  {
    label: '教学工作台',
    items: [
      { id: 'teacher-home', label: '教学概览', icon: 'home', to: '/teacher' },
      { id: 'teacher-class', label: '班级学情', icon: 'class', to: '/teacher/class' },
      { id: 'teacher-student-import', label: '学生导入', icon: 'account', to: '/teacher/students/import' },
      { id: 'teacher-assignments', label: '作业管理', icon: 'assignment', to: '/teacher/assignments' },
      { id: 'teacher-exams', label: '组卷与考试', icon: 'exam', to: '/teacher/exams' },
    ],
  },
  {
    label: '课程资源',
    items: [
      { id: 'teacher-question-bank', label: '题库管理', icon: 'question', to: '/teacher/questions' },
      { id: 'teacher-knowledge', label: '知识节点', icon: 'knowledge', to: '/teacher/knowledge' },
      { id: 'teacher-ai', label: 'AI 出题', icon: 'spark', to: '/teacher/ai' },
    ],
  },
]

const adminGroups: NavigationGroup[] = [
  {
    label: '平台管理',
    items: [
      { id: 'admin-home', label: '平台概览', icon: 'home', to: '/admin' },
      { id: 'admin-accounts', label: '账号管理', icon: 'account', to: '/admin/accounts' },
      { id: 'admin-classes', label: '教学班管理', icon: 'class', to: '/admin/classes' },
      { id: 'admin-audit', label: '操作记录', icon: 'audit', to: '/admin/audit' },
      { id: 'admin-feature-settings', label: '功能配置', icon: 'settings', to: '/admin/features' },
    ],
  },
]

export function navigationForRole(role: NavigationRole, visibleIds?: Set<string>): NavigationGroup[] {
  const groups = role === 'student' ? studentGroups : role === 'teacher' ? teacherGroups : adminGroups
  if (!visibleIds) return groups
  return groups
    .map((group) => ({ ...group, items: group.items.filter((item) => visibleIds.has(item.id)) }))
    .filter((group) => group.items.length)
}
