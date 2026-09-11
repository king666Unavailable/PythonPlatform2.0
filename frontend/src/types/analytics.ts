export interface LearningGroup {
  id: string
  label: string
  parallel_nodes: string[]
  requires?: string[]
  note?: string
}

export interface LearningPhase {
  id: number
  name: string
  description: string
  groups: LearningGroup[]
  requires_phase?: number[]
}

export interface LearningPathResponse {
  learning_path: {
    title: string
    description: string
    phases: LearningPhase[]
  }
  meta: {
    phase_count: number
    node_count: number
    source: string
  }
}

export interface PhaseAnalytics {
  id: number
  name: string
  description: string
  configured_knowledge_count: number
  knowledge_count: number
  completion_rate: number
  passing_rate: number
}

export interface WeakKnowledge {
  phase_id: number
  phase_name: string
  title: string
  score: number
}

export interface StudentAnalyticsResponse {
  student: {
    username: string
  }
  analytics: {
    completion_rate: number
    passing_rate: number
    pass_threshold: number
    phases: PhaseAnalytics[]
    weak_knowledge: WeakKnowledge[]
  }
  meta: {
    phase_count: number
    node_count: number
    source: string
    completion_rule: string
    passing_rule: string
  }
}
