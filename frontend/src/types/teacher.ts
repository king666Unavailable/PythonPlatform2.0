export interface TeacherClassStudent {
  id: string
  username: string
  name: string
  gender: string
  gender_code: number | null
  study_class: string
  question_count: number
  correct_question_count: number
  is_active: boolean
  assignment_results: Array<{
    id: string
    title: string
    score: number | null
    submitted: boolean
    failed: boolean
  }>
  unsubmitted_assignments: string[]
  failed_assignments: string[]
  scores: Record<string, number>
  needs_attention: boolean
  excellent: boolean
}

export interface TeacherAlertStudent {
  id: string
  name: string
  average_score?: number | null
  unsubmit_count?: number
  fail_rate?: number
}

export interface ClassAnalyticsResponse {
  class: {
    id: string
    name: string
    student_count: number
  }
  summary: {
    need_care_count: number
    excellent_count: number
    test_count: number
    averages: {
      homework: Record<string, number>
      classwork: Record<string, number>
    }
  }
  tests: Array<{ name: string; category: 'homework' | 'classwork' }>
  alerts: {
    need_care: TeacherAlertStudent[]
    excellent: TeacherAlertStudent[]
  }
  students: TeacherClassStudent[]
  meta: {
    read_only: boolean
    source: string
  }
}

export interface TeacherStudentProfileResponse {
  student: TeacherClassStudent
  meta: {
    read_only: boolean
    source: string
  }
}
