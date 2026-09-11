export type KnowledgeNodeType = 'class' | 'theme' | 'knowledge' | 'point'

export interface KnowledgeGraphNode {
  id: string
  label: string
  type: KnowledgeNodeType
  level: number
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  relation: string
}

export interface KnowledgeGraphResponse {
  graph: {
    nodes: KnowledgeGraphNode[]
    edges: KnowledgeGraphEdge[]
  }
  meta: {
    node_count: number
    edge_count: number
  }
}
