export interface QuestionSummary {
  id: string
  title: string
  type_code: string
  type: string
  difficulty: number | null
  importance: number | null
  exam_times: number
  homework_times: number
  question_count: number
  correct_question_count: number
  rate: number
  point_titles: string[]
}

export interface Question extends QuestionSummary {
  content: string
  answer?: string
  analysis?: string
  programming_config?: {
    language: string
    version: string
    filename: string
    timeout_ms: number
    comparison_mode: string
    test_cases: Array<{
      case_no: number
      stdin: string
      expected_output: string
      weight: number
      is_hidden: boolean
      comparison_mode: string
    }>
  }
}

export interface QuestionListResponse {
  items: QuestionSummary[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}
