export interface WorkspaceMetric {
  label: string
  value: string | number
  tone?: string
}

export interface WorkspaceData {
  feature_id: string
  title: string
  source: string
  read_only: boolean
  capabilities: string[]
  status: string
  filters?: string[]
  metrics: WorkspaceMetric[]
  items: Array<Record<string, unknown>>
  detail?: Record<string, unknown> | null
  extra?: Record<string, unknown>
}
