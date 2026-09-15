export type MasteryNodeType = 'class' | 'theme' | 'knowledge' | 'point'

export interface StudentMasteryNode {
  graph_node_id: string | null
  node_type: MasteryNodeType
  node_id: string
  score: number
  accuracy: number
  attempted_count: number
  correct_equivalent: number
  last_answered_at: string
}

export interface StudentMasteryResponse {
  student: {
    username: string
  }
  class_id: string
  nodes: StudentMasteryNode[]
  summary: {
    course_score: number | null
    attempted_questions: number
    scored_node_count: number
  }
  meta: {
    source: string
    calculation_version: string
    score_scale: [number, number]
  }
}
