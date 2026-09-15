export interface LearningProfilePoint {
  title: string
  mastery: number
  attempted_count: number
}

export interface LearningProfileDimension {
  score: number | null
  [key: string]: unknown
}

export interface LearningProfileReport {
  student: {
    username: string
    name: string
    gender: string
    administrative_class: string
    teaching_class: string
    is_active: boolean
  }
  overview: {
    overall_score: number | null
    dimensions: { progress: number | null; habit: number | null; ability: number | null }
    class_average: { progress: number | null; habit: number | null; ability: number | null }
    labels: string[]
  }
  progress: {
    score: number | null
    knowledge_mastery: number | null
    scored_assignment_count: number
    average_score: number | null
    weak_points: LearningProfilePoint[]
    score_curve: Array<{ assignment_id: string; title: string; score: number; submitted_at: string }>
  }
  habit: {
    score: number | null
    submission_rate: number
    on_time_rate: number | null
    active_days: number
    average_question_seconds: number | null
    questionnaire_completed: boolean
    available_assignment_count: number
  }
  ability: {
    score: number | null
    objective_accuracy: number | null
    subjective_accuracy: number | null
    difficulty_accuracy: Array<{ label: string; accuracy: number | null; count: number }>
    question_type_accuracy: Array<{ label: string; accuracy: number | null; count: number }>
    high_difficulty_accuracy: number | null
    programming_included: boolean
  }
  suggestions: Array<{ dimension: string; tone: 'blue' | 'green' | 'orange'; text: string }>
  meta: {
    source: string
    class_id: string
    class_name: string
    generated_at: string
    random_placeholder_data: boolean
    programming_grading_note: string
  }
}
