<script setup lang="ts">
import { DataSet, Network } from 'vis-network/standalone/esm/vis-network'
import 'vis-network/styles/vis-network.min.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createKnowledgeNode,
  deleteKnowledgeNode,
  fetchKnowledgeManagementNode,
  fetchKnowledgeManagementStructure,
  fetchKnowledgeNodeDeleteImpact,
  updateKnowledgeNode,
} from '@/api/client'
import type { KnowledgeManagementNode } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

type NodeType = KnowledgeManagementNode['type']

const typeLabels: Record<NodeType, string> = { class: '课程', theme: '主题', knowledge: '知识', point: '知识点' }
const apiType: Record<NodeType, string> = { class: 'Class', theme: 'Theme', knowledge: 'Knowledge', point: 'Point' }
const parentType: Record<Exclude<NodeType, 'class'>, NodeType> = { theme: 'class', knowledge: 'theme', point: 'knowledge' }

const nodes = ref<KnowledgeManagementNode[]>([])
const edges = ref<Array<{ source: string; target: string; relation: string }>>([])
const selectedId = ref('')
const detailNode = ref<(KnowledgeManagementNode & { children: KnowledgeManagementNode[] }) | null>(null)
const search = ref('')
const typeFilter = ref<'all' | NodeType>('all')
const viewMode = ref<'graph' | 'tree'>('graph')
const expanded = ref(new Set<string>())
const loading = ref(true)
const detailLoading = ref(false)
const structureInitialized = ref(false)
const error = ref('')
const success = ref('')
const graphElement = ref<HTMLElement | null>(null)
let network: Network | null = null
const modalMode = ref<'create' | 'edit' | null>(null)
const formType = ref<NodeType>('point')
const formTitle = ref('')
const formParentId = ref('')
const saving = ref(false)

const nodeMap = computed(() => new Map(nodes.value.map((node) => [node.id, node])))
const selectedNode = computed(() => nodeMap.value.get(selectedId.value) ?? null)
const parentOptions = computed(() => {
  if (formType.value === 'class') return []
  const required = parentType[formType.value]
  return nodes.value.filter((node) => node.type === required).sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'))
})

const graphNodes = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const matches = nodes.value.filter((node) => (typeFilter.value === 'all' || node.type === typeFilter.value) && (!keyword || node.title.toLowerCase().includes(keyword)))
  if (!keyword && typeFilter.value === 'all') return nodes.value
  const included = new Set(matches.map((node) => node.id))
  for (const node of matches) {
    let parentId = node.parent_id
    while (parentId && nodeMap.value.has(parentId)) {
      included.add(parentId)
      parentId = nodeMap.value.get(parentId)?.parent_id ?? null
    }
  }
  return nodes.value.filter((node) => included.has(node.id))
})

const graphEdges = computed(() => {
  const visible = new Set(graphNodes.value.map((node) => node.id))
  return edges.value.filter((edge) => visible.has(edge.source) && visible.has(edge.target))
})

const treeRows = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const matches = nodes.value.filter((node) => (typeFilter.value === 'all' || node.type === typeFilter.value) && (!keyword || node.title.toLowerCase().includes(keyword)))
  const included = new Set(matches.map((node) => node.id))
  for (const node of matches) {
    let parentId = node.parent_id
    while (parentId && nodeMap.value.has(parentId)) {
      included.add(parentId)
      parentId = nodeMap.value.get(parentId)?.parent_id ?? null
    }
  }
  const children = new Map<string, KnowledgeManagementNode[]>()
  for (const node of nodes.value) {
    if (!included.has(node.id)) continue
    const key = node.parent_id && included.has(node.parent_id) ? node.parent_id : ''
    const group = children.get(key) ?? []
    group.push(node)
    children.set(key, group)
  }
  const order: Record<NodeType, number> = { class: 0, theme: 1, knowledge: 2, point: 3 }
  const sortNodes = (items: KnowledgeManagementNode[]) => items.sort((a, b) => (order[a.type] - order[b.type]) || a.title.localeCompare(b.title, 'zh-CN'))
  const rows: Array<KnowledgeManagementNode & { depth: number }> = []
  function visit(node: KnowledgeManagementNode, depth: number) {
    rows.push({ ...node, depth })
    if (!expanded.value.has(node.id)) return
    for (const child of sortNodes(children.get(node.id) ?? [])) visit(child, depth + 1)
  }
  for (const root of sortNodes(children.get('') ?? [])) visit(root, 0)
  return rows
})

function typeLabel(type: NodeType) {
  return typeLabels[type] ?? type
}

function toggleExpanded(node: KnowledgeManagementNode) {
  const next = new Set(expanded.value)
  if (next.has(node.id)) next.delete(node.id)
  else next.add(node.id)
  expanded.value = next
}

function graphNodeColor(type: NodeType) {
  return {
    class: { background: '#2f6fab', border: '#174d82' },
    theme: { background: '#7b61b8', border: '#5b438f' },
    knowledge: { background: '#199c9c', border: '#087474' },
    point: { background: '#df8d36', border: '#ad631a' },
  }[type]
}

function renderGraph() {
  if (!graphElement.value || viewMode.value !== 'graph') return
  network?.destroy()
  const graphData = new DataSet(graphNodes.value.map((node) => {
    const color = graphNodeColor(node.type)
    return {
      id: node.id,
      label: node.title,
      value: Math.max(12, Math.min(34, 12 + node.question_count / 24)),
      color: { background: color.background, border: color.border, highlight: { background: color.background, border: '#132238' } },
      font: { size: node.type === 'class' ? 17 : node.type === 'theme' ? 15 : 13, color: '#304a65' },
      shape: 'dot',
    }
  }))
  const edgeData = new DataSet(graphEdges.value.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    from: edge.source,
    to: edge.target,
    arrows: { to: { enabled: true, scaleFactor: 0.45 } },
  })))
  network = new Network(graphElement.value, { nodes: graphData, edges: edgeData }, {
    layout: { improvedLayout: false },
    nodes: { shape: 'dot', borderWidth: 2, borderWidthSelected: 4, scaling: { min: 12, max: 34 }, shadow: { enabled: true, color: 'rgba(31,83,128,.18)', size: 8, x: 0, y: 3 } },
    edges: { width: 1.5, color: { color: '#abc0d3', highlight: '#3f83bd' }, smooth: { type: 'dynamic' }, arrows: { to: { enabled: true, scaleFactor: 0.45 } } },
    interaction: { hover: true, tooltipDelay: 160, navigationButtons: true, zoomView: true, dragView: true },
    physics: { enabled: true, stabilization: { enabled: true, fit: false, iterations: 220 }, solver: 'forceAtlas2Based', forceAtlas2Based: { gravitationalConstant: -72, centralGravity: 0.012, springLength: 135, springConstant: 0.08 }, maxVelocity: 120, minVelocity: 1, timestep: 0.35 },
  })
  network.on('click', (params) => {
    const node = nodeMap.value.get(String(params.nodes[0]))
    if (node) void selectNode(node)
  })
  network.on('hoverNode', (params) => {
    const node = nodeMap.value.get(String(params.node))
    if (node && graphElement.value) graphElement.value.title = `${node.title}：${typeLabel(node.type)} · 关联题目 ${node.question_count} 道`
  })
  network.once('stabilized', () => network?.fit({ animation: { duration: 380, easingFunction: 'easeInOutQuad' } }))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchKnowledgeManagementStructure()
    nodes.value = result.graph.nodes
    edges.value = result.graph.edges
    const available = new Set(nodes.value.map((node) => node.id))
    if (!structureInitialized.value) {
      expanded.value = new Set(nodes.value.filter((node) => node.children_count > 0).map((node) => node.id))
      structureInitialized.value = true
    } else {
      expanded.value = new Set([...expanded.value].filter((id) => available.has(id)))
    }
    if (selectedId.value && !available.has(selectedId.value)) {
      selectedId.value = ''
      detailNode.value = null
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '知识图谱结构加载失败。'
  } finally {
    loading.value = false
    if (!error.value && viewMode.value === 'graph') {
      await nextTick()
      renderGraph()
    }
  }
}

async function selectNode(node: KnowledgeManagementNode) {
  selectedId.value = node.id
  detailLoading.value = true
  error.value = ''
  try {
    detailNode.value = (await fetchKnowledgeManagementNode(node.id)).node
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '知识节点详情加载失败。'
  } finally {
    detailLoading.value = false
  }
}

function openCreate() {
  const selected = selectedNode.value
  const childType = selected && selected.type !== 'point' ? Object.entries(parentType).find(([, parent]) => parent === selected.type)?.[0] : undefined
  formType.value = (childType as NodeType | undefined) ?? 'point'
  formTitle.value = ''
  formParentId.value = selected && selected.type === parentType[formType.value as Exclude<NodeType, 'class'>] ? selected.id : ''
  modalMode.value = 'create'
}

function openEdit() {
  if (!selectedNode.value) return
  formType.value = selectedNode.value.type
  formTitle.value = selectedNode.value.title
  formParentId.value = selectedNode.value.parent_id ?? ''
  modalMode.value = 'edit'
}

function closeModal() {
  if (!saving.value) modalMode.value = null
}

async function saveNode() {
  const title = formTitle.value.trim()
  if (!title) {
    error.value = '节点名称不能为空。'
    return
  }
  if (formType.value !== 'class' && !formParentId.value) {
    error.value = `请选择${typeLabel(parentType[formType.value])}父节点。`
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      type: apiType[formType.value],
      title,
      parent_type: formType.value === 'class' ? '' : apiType[parentType[formType.value]],
      parent_id: formType.value === 'class' ? '' : formParentId.value,
    }
    if (modalMode.value === 'create') await createKnowledgeNode(payload)
    else if (selectedId.value) await updateKnowledgeNode(selectedId.value, payload)
    success.value = modalMode.value === 'create' ? '知识节点已创建。' : '知识节点已更新。'
    modalMode.value = null
    await load()
    if (selectedId.value) {
      const refreshed = nodeMap.value.get(selectedId.value)
      if (refreshed) await selectNode(refreshed)
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '知识节点保存失败。'
  } finally {
    saving.value = false
  }
}

async function removeNode() {
  if (!selectedNode.value) return
  try {
    const { impact } = await fetchKnowledgeNodeDeleteImpact(selectedNode.value.id)
    if (!impact.can_delete) {
      error.value = `“${selectedNode.value.title}”仍有 ${impact.children_count} 个下级节点、${impact.question_count} 道关联题目，不能删除。`
      return
    }
    if (!window.confirm(`确定删除“${selectedNode.value.title}”吗？删除后不可恢复。`)) return
    await deleteKnowledgeNode(selectedNode.value.id)
    success.value = '知识节点已删除。'
    selectedId.value = ''
    detailNode.value = null
    await load()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '知识节点删除失败。'
  }
}

watch(viewMode, async (mode) => {
  if (mode === 'graph') {
    await nextTick()
    renderGraph()
  } else {
    network?.destroy()
    network = null
  }
})

watch([search, typeFilter], async () => {
  if (viewMode.value !== 'graph' || loading.value) return
  await nextTick()
  renderGraph()
})

onMounted(() => void load())
onBeforeUnmount(() => network?.destroy())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="知识图谱管理">
      <template #actions><button type="button" @click="openCreate">新增节点</button></template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <InlineMessage :message="success" tone="success" />

    <section class="content-card knowledge-management-toolbar">
      <label>搜索节点<input v-model="search" type="search" placeholder="输入课程、主题、知识或知识点名称" /></label>
      <label>节点层级<select v-model="typeFilter"><option value="all">全部层级</option><option value="class">课程</option><option value="theme">主题</option><option value="knowledge">知识</option><option value="point">知识点</option></select></label>
      <button class="secondary-button" type="button" :disabled="loading" @click="load">刷新结构</button>
      <div class="knowledge-management-view-switch" role="tablist" aria-label="知识图谱视图切换"><button type="button" :class="{ active: viewMode === 'graph' }" role="tab" :aria-selected="viewMode === 'graph'" @click="viewMode = 'graph'">动态图谱</button><button type="button" :class="{ active: viewMode === 'tree' }" role="tab" :aria-selected="viewMode === 'tree'" @click="viewMode = 'tree'">结构树</button></div>
    </section>

    <section class="knowledge-management-layout">
      <section v-if="viewMode === 'tree'" class="content-card knowledge-management-tree-card">
        <div class="section-heading"><div><h3>课程知识结构</h3><p>{{ treeRows.length }} 个节点</p></div></div>
        <div v-if="loading" class="loading-state">正在加载知识结构…</div>
        <div v-else-if="treeRows.length" class="knowledge-management-tree" role="tree">
          <div v-for="node in treeRows" :key="node.id" class="knowledge-management-tree-row-wrap">
            <button type="button" class="knowledge-management-tree-row" :class="{ selected: selectedId === node.id }" :style="{ paddingLeft: `${14 + node.depth * 22}px` }" @click="selectNode(node)">
              <span v-if="node.children_count" class="knowledge-management-expand" role="button" tabindex="0" :aria-label="expanded.has(node.id) ? '收起' : '展开'" @click.stop="toggleExpanded(node)">{{ expanded.has(node.id) ? '⌄' : '›' }}</span><span v-else class="knowledge-management-expand-placeholder" />
              <strong>{{ node.title }}</strong><small :class="`knowledge-type-${node.type}`">{{ typeLabel(node.type) }}</small><em>{{ node.question_count }} 题</em>
            </button>
          </div>
        </div>
        <EmptyState v-else title="没有匹配节点" description="调整搜索词或节点层级后重试。" />
      </section>

      <section v-else class="content-card knowledge-management-graph-card">
        <div class="section-heading"><div><h3>知识图谱</h3><p>{{ graphNodes.length }} 个节点 · {{ graphEdges.length }} 条关系</p></div><span class="knowledge-management-graph-hint">拖拽节点查看结构，滚轮缩放，点击节点查看详情</span></div>
        <div v-if="loading" class="loading-state">正在加载知识结构…</div>
        <div v-else-if="graphNodes.length" ref="graphElement" class="knowledge-management-graph" role="img" aria-label="教师知识图谱" />
        <EmptyState v-else title="没有匹配节点" description="调整搜索词或节点层级后重试。" />
      </section>

      <section class="content-card knowledge-management-detail-card">
        <div v-if="detailLoading" class="loading-state">正在加载节点详情…</div>
        <template v-else-if="selectedNode">
          <div class="section-heading"><div><span class="knowledge-type-badge" :class="`knowledge-type-${selectedNode.type}`">{{ typeLabel(selectedNode.type) }}</span><h3>{{ selectedNode.title }}</h3></div><div class="row-actions"><button class="small-button secondary-button" type="button" @click="openEdit">编辑节点</button><button class="small-button danger-button" type="button" @click="removeNode">删除节点</button></div></div>
          <div class="knowledge-management-stats"><div><span>关联题目</span><strong>{{ detailNode?.question_count ?? selectedNode.question_count }} 道</strong></div><div><span>下级节点</span><strong>{{ detailNode?.children_count ?? selectedNode.children_count }} 个</strong></div><div><span>父级节点</span><strong>{{ selectedNode.parent_id ? (nodeMap.get(selectedNode.parent_id)?.title ?? '已关联') : '顶层节点' }}</strong></div></div>
          <div class="knowledge-management-detail-section"><h4>下级节点</h4><div v-if="detailNode?.children?.length" class="knowledge-management-children"><button v-for="child in detailNode.children" :key="child.id" type="button" @click="selectNode(child)"><span>{{ child.title }}</span><small>{{ typeLabel(child.type) }} · {{ child.question_count }} 题</small></button></div><span v-else class="muted">暂无下级节点。</span></div>
          <div class="knowledge-management-detail-note">节点结构与关系由 Neo4j 维护；关联题目数量用于删除影响提示，不在此处修改题目内容。</div>
        </template>
        <EmptyState v-else title="选择一个知识节点" description="从图谱或结构树选择节点查看详情和维护操作。" />
      </section>
    </section>

    <div v-if="modalMode" class="modal-backdrop"><section class="modal-card knowledge-management-modal"><div class="section-heading"><div><h3>{{ modalMode === 'create' ? '新增知识节点' : '编辑知识节点' }}</h3><p>{{ modalMode === 'create' ? '选择父节点后，节点会直接加入课程结构。' : '修改名称或调整父节点。' }}</p></div><button class="icon-button" type="button" aria-label="关闭" @click="closeModal">×</button></div><label>节点类型<select v-model="formType" :disabled="modalMode === 'edit'"><option value="class">课程</option><option value="theme">主题</option><option value="knowledge">知识</option><option value="point">知识点</option></select></label><label>节点名称<input v-model="formTitle" maxlength="255" placeholder="请输入节点名称" /></label><label v-if="formType !== 'class'">父节点<select v-model="formParentId"><option value="">请选择父节点</option><option v-for="node in parentOptions" :key="node.id" :value="node.id">{{ node.title }}</option></select></label><div class="modal-actions"><button class="secondary-button" type="button" :disabled="saving" @click="closeModal">取消</button><button type="button" :disabled="saving" @click="saveNode">{{ saving ? '保存中…' : '保存' }}</button></div></section></div>
  </div>
</template>
