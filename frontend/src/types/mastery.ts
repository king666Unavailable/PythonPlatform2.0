export interface MasteryKnowledge {
  id: string
  title: string
  score: number
}

export interface MasteryTheme {
  id: string
  title: string
  score: number
  knowledge: MasteryKnowledge[]
}

export interface StudentMasteryResponse {
  student: {
    username: string
  }
  mastery: MasteryTheme[]
  meta: {
    theme_count: number
    knowledge_count: number
    score_scale: [number, number]
    source: string
    rule: string
  }
}
