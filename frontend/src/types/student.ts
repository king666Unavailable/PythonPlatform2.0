export interface StudentProfile {
  id: string
  username: string
  name: string
  gender: string
  gender_code: number | null
  administrative_class: string
  teaching_class: string
  study_class: string
  question_count: number
  correct_question_count: number
  is_active: boolean
}

export interface StudentAssignmentRecord {
  assignment_id: string
  title: string
  assignment_kind: string
  submission_status: string
  correct_questions: number
  wrong_questions: number
  correct_question_titles: string[]
  wrong_question_titles: string[]
  programming_correct_rate: number | null
  score: number | null
  performance: string
  answered_questions: number
  submitted_at: string
  updated_at: string
  attempt_no: number
}

export interface StudentProfileReport {
  student: StudentProfile
  summary: {
    total_assignments: number
    completed_assignments: number
    pending_assignments: number
    unsubmitted_assignments: number
    average_score: number | null
    question_count: number
    correct_question_count: number
  }
  assignment_records: StudentAssignmentRecord[]
  score_curve: Array<{
    assignment_id: string
    title: string
    assignment_kind: string
    score: number
    submitted_at: string
  }>
  meta: { source: string; read_only: boolean }
}
