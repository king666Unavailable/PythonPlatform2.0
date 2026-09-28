export interface TeachingClass {
  id: string
  title: string
  teaching_class: string
  academic_year: string
  teacher_name: string
  graph_class_id: string | null
  enrollment_type?: string
}

export interface ClassContextResponse {
  items: TeachingClass[]
  current: TeachingClass | null
  meta: Record<string, unknown>
}
