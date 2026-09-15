<script setup lang="ts">
import { DataSet, Network } from 'vis-network/standalone/esm/vis-network'
import 'vis-network/styles/vis-network.min.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchKnowledgeGraph, fetchStudentMastery } from '@/api/client'
import type { KnowledgeGraphNode, KnowledgeGraphResponse } from '@/types/knowledge'
import type { StudentMasteryNode, StudentMasteryResponse } from '@/types/mastery'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

type MasteryValue = number | null
type ViewNode = KnowledgeGraphNode & {
  mastery: MasteryValue
  accuracy: MasteryValue
  attemptedCount: number
  correctEquivalent: number
}
type ColorValue = { background: string; border: string }

const graph = ref<KnowledgeGraphResponse | null>(null)
const mastery = ref<StudentMasteryResponse | null>(null)
const loading = ref(true)
const error = ref('')
const selectedNodeId = ref('')
const showPath = ref(false)
const graphElement = ref<HTMLElement | null>(null)
let network: Network | null = null
const DEFAULT_GRAPH_SCALE = 1
const DEFAULT_GRAPH_POSITION = { x: 0, y: 0 }

const masteryByGraphNodeId = computed(() => new Map(
  (mastery.value?.nodes ?? [])
    .filter((item): item is StudentMasteryNode & { graph_node_id: string } => Boolean(item.graph_node_id))
    .map((item) => [item.graph_node_id, item]),
))
const graphNodes = computed<ViewNode[]>(() => (graph.value?.graph.nodes ?? []).map((node) => {
  const item = masteryByGraphNodeId.value.get(node.id)
  return {
    ...node,
    mastery: item?.score ?? null,
    accuracy: item?.accuracy ?? null,
    attemptedCount: item?.attempted_count ?? 0,
    correctEquivalent: item?.correct_equivalent ?? 0,
  }
}))
const nodeMap = computed(() => new Map(graphNodes.value.map((node) => [node.id, node])))
const graphEdges = computed(() => graph.value?.graph.edges ?? [])
const selectedNode = computed(() => nodeMap.value.get(selectedNodeId.value) ?? null)
const prerequisiteNodes = computed(() => graphEdges.value.filter((edge) => edge.target === selectedNodeId.value).map((edge) => nodeMap.value.get(edge.source)).filter(Boolean) as ViewNode[])
const subsequentNodes = computed(() => graphEdges.value.filter((edge) => edge.source === selectedNodeId.value).map((edge) => nodeMap.value.get(edge.target)).filter(Boolean) as ViewNode[])

function getNodeColor(mastery: MasteryValue): ColorValue {
  if (mastery === null) return { background: '#94A3B8', border: '#64748B' }
  if (mastery >= 80) return { background: '#10B981', border: '#059669' }
  if (mastery >= 60) return { background: '#3B82F6', border: '#2563EB' }
  if (mastery >= 40) return { background: '#F59E0B', border: '#D97706' }
  return { background: '#EF4444', border: '#DC2626' }
}

function levelLabel(node: ViewNode) {
  return ['课程', '主题', '知识', '知识点'][node.level] ?? '知识内容'
}

function masteryLabel(mastery: MasteryValue) {
  return mastery === null ? '暂无记录' : `${mastery.toFixed(1)}%`
}

function accuracyLabel(accuracy: MasteryValue) {
  return accuracy === null ? '暂无记录' : `${accuracy.toFixed(1)}%`
}

function renderNetwork() {
  if (!graphElement.value || !graph.value) return
  network?.destroy()

  const nodes = new DataSet(graphNodes.value.map((node, index) => {
    const color = getNodeColor(node.mastery)
    const angle = (index / Math.max(graphNodes.value.length, 1)) * Math.PI * 2
    return {
      id: node.id,
      label: node.label,
      x: 180 * Math.cos(angle),
      y: 180 * Math.sin(angle),
      value: 25,
      level: node.level,
      mastery: node.mastery,
      color: { background: color.background, border: color.border, highlight: { background: color.background, border: '#111827' } },
      shape: 'dot',
    }
  }))
  const edges = new DataSet(graphEdges.value.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    from: edge.source,
    to: edge.target,
    arrows: { to: { enabled: true } },
  })))

  network = new Network(graphElement.value, { nodes, edges }, {
    layout: { improvedLayout: false },
    nodes: { shape: 'dot', size: 25, font: { size: 14, color: '#333' }, borderWidth: 2, borderWidthSelected: 3 },
    edges: { width: 2, color: { color: '#ccc', highlight: '#999' }, arrows: { to: { enabled: true } } },
    interaction: { hover: true, tooltipDelay: 200, navigationButtons: false, zoomView: true, dragView: true },
    physics: {
      enabled: true,
      stabilization: { enabled: true, fit: false, iterations: 200 },
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -26, centralGravity: 0.005, springLength: 230, springConstant: 0.18 },
      maxVelocity: 146,
      minVelocity: 1,
      timestep: 0.35,
    },
  })
  network.on('click', (params) => {
    const nodeId = params.nodes[0]
    if (nodeId) {
      selectedNodeId.value = String(nodeId)
      showPath.value = false
    }
  })
  network.on('hoverNode', (params) => {
    const node = nodeMap.value.get(String(params.node))
    if (node && graphElement.value) graphElement.value.title = `${node.label}：掌握度 ${masteryLabel(node.mastery)}`
  })
  network.moveTo({ scale: DEFAULT_GRAPH_SCALE, position: DEFAULT_GRAPH_POSITION })
  network.once('stabilized', () => network?.moveTo({ scale: DEFAULT_GRAPH_SCALE, position: DEFAULT_GRAPH_POSITION }))
}

function zoomIn() {
  if (!network) return
  network.moveTo({ scale: network.getScale() * 1.2 })
}

function zoomOut() {
  if (!network) return
  network.moveTo({ scale: network.getScale() / 1.2 })
}

function resetView() {
  network?.moveTo({ scale: DEFAULT_GRAPH_SCALE, position: DEFAULT_GRAPH_POSITION })
}

function openLearningPath() {
  if (selectedNode.value) showPath.value = true
}

function closeDetail() {
  selectedNodeId.value = ''
  showPath.value = false
}

function closePath() {
  showPath.value = false
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    graph.value = await fetchKnowledgeGraph()
    try {
      mastery.value = await fetchStudentMastery()
    } catch (cause) {
      error.value = cause instanceof Error ? `图谱已加载，但个人掌握度暂不可用：${cause.message}` : '图谱已加载，但个人掌握度暂不可用。'
    }
    loading.value = false
    await nextTick()
    renderNetwork()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '知识图谱加载失败。'
    loading.value = false
  }
}

onMounted(() => void load())
onBeforeUnmount(() => network?.destroy())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="知识图谱" />
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载知识图谱…</div>
    <section v-else-if="graph" class="knowledge-path-layout">
      <div class="knowledge-path-graph-card">
        <div class="knowledge-path-card-heading">
          <div>
            <h2>知识图谱</h2>
            <p v-if="mastery?.summary.course_score != null" class="knowledge-path-overview">课程掌握度 {{ mastery?.summary.course_score }}% · 已作答 {{ mastery?.summary.attempted_questions }} 题</p>
          </div>
          <div class="knowledge-path-actions">
            <button type="button" title="放大" aria-label="放大" @click="zoomIn">＋</button>
            <button type="button" title="缩小" aria-label="缩小" @click="zoomOut">－</button>
            <button type="button" title="重置视图" aria-label="重置视图" @click="resetView">↻</button>
          </div>
        </div>
        <div ref="graphElement" class="knowledge-path-network" role="img" aria-label="学生知识图谱" />
      </div>

      <div class="knowledge-path-side">
        <section class="knowledge-path-info-card is-visible">
          <div class="knowledge-path-info-heading">
            <div>
              <h3>{{ selectedNode?.label ?? '选择一个知识点' }}</h3>
              <p>{{ selectedNode ? `${levelLabel(selectedNode)} · 点击图谱节点查看详情` : '点击知识图谱中的节点查看详情' }}</p>
            </div>
            <button v-if="selectedNode" type="button" class="knowledge-path-close" aria-label="关闭详情" @click="closeDetail">×</button>
          </div>

          <div class="knowledge-path-metrics">
            <div class="knowledge-fish-tank">
              <div class="knowledge-water-level" :style="{ height: `${selectedNode?.mastery ?? 0}%` }" />
              <div class="knowledge-fish" />
            </div>
            <div class="knowledge-mastery-value">{{ masteryLabel(selectedNode?.mastery ?? null) }}<span>掌握程度</span></div>
            <div class="knowledge-path-progress-list">
              <div><span>已作答题目</span><strong>{{ selectedNode?.attemptedCount ?? 0 }} 道</strong></div>
              <div class="knowledge-progress"><i :style="{ width: `${selectedNode?.mastery ?? 0}%` }" /></div>
              <div><span>答题正确率</span><strong>{{ accuracyLabel(selectedNode?.accuracy ?? null) }}</strong></div>
              <div class="knowledge-progress progress-green"><i :style="{ width: `${selectedNode?.accuracy ?? 0}%` }" /></div>
            </div>
          </div>

          <div class="knowledge-resource-section">
            <h4>推荐学习资源</h4>
            <p class="knowledge-empty-note">当前知识节点暂无学习资源。</p>
          </div>
          <button v-if="selectedNode" type="button" class="primary-button knowledge-learning-path-button" @click="openLearningPath">查看学习路径</button>
        </section>

        <section v-if="showPath && selectedNode" class="knowledge-path-info-card learning-path-card">
          <div class="knowledge-path-info-heading">
            <div><h3>学习路径</h3><p>{{ selectedNode.label }}的前置和后置知识点</p></div>
            <button type="button" class="knowledge-path-close" aria-label="关闭学习路径" @click="closePath">×</button>
          </div>
          <div class="learning-path-section"><h4 class="path-before">↑ 前置知识点</h4><div class="learning-path-nodes"><span v-for="node in prerequisiteNodes" :key="node.id">{{ node.label }}</span><em v-if="!prerequisiteNodes.length">暂无</em></div></div>
          <div class="learning-path-section"><h4 class="path-after">↓ 后置知识点</h4><div class="learning-path-nodes"><span v-for="node in subsequentNodes" :key="node.id">{{ node.label }}</span><em v-if="!subsequentNodes.length">暂无</em></div></div>
        </section>
      </div>
    </section>
    <EmptyState v-else title="暂时没有知识内容" description="请稍后再试。" />
  </div>
</template>
