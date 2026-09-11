<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createKnowledgeNode, deleteKnowledgeNode, fetchKnowledgeNodes, updateKnowledgeNode } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const type = ref('Point')
const title = ref('')
const nodes = ref<Array<Record<string, unknown>>>([])
const editing = ref<Record<string, unknown> | null>(null)
const editTitle = ref('')
const loading = ref(true)
const error = ref('')
const success = ref('')
async function load() { loading.value = true; error.value = ''; try { nodes.value = (await fetchKnowledgeNodes(type.value)).items } catch (cause) { error.value = cause instanceof Error ? cause.message : '知识节点加载失败。' } finally { loading.value = false } }
async function add() { if (!title.value.trim()) { error.value = '请输入节点名称。'; return }; try { await createKnowledgeNode({ type: type.value, title: title.value.trim() }); title.value = ''; success.value = '知识节点已创建。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '节点创建失败。' } }
function startEdit(node: Record<string, unknown>) { editing.value = node; editTitle.value = String(node.title ?? '') }
async function save() { if (!editing.value) return; try { await updateKnowledgeNode(String(editing.value.id), { title: editTitle.value.trim() }); editing.value = null; success.value = '知识节点已更新。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '节点更新失败。' } }
async function remove(node: Record<string, unknown>) { if (!window.confirm(`确定删除“${node.title}”吗？`)) return; try { await deleteKnowledgeNode(String(node.id)); success.value = '知识节点已删除。'; await load() } catch (cause) { error.value = cause instanceof Error ? cause.message : '节点删除失败。' } }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="知识节点" description="维护课程、主题、知识和知识点，为题目和学习路径提供结构。"><template #actions><button type="button" @click="add">新增节点</button></template></PageHeader><InlineMessage :message="error" tone="error" /><InlineMessage :message="success" tone="success" /><section class="content-card"><div class="toolbar-row"><label>节点类型<select v-model="type" @change="load"><option value="Class">课程</option><option value="Theme">主题</option><option value="Knowledge">知识</option><option value="Point">知识点</option></select></label><label class="wide-field">节点名称<input v-model="title" placeholder="输入新节点名称" @keyup.enter="add" /></label><button type="button" @click="add">创建</button></div></section><section class="content-card flush-card"><div class="section-heading padded-heading"><div><h3>{{ type === 'Point' ? '知识点' : type }}列表</h3><p>共 {{ nodes.length }} 个节点。</p></div></div><div v-if="loading" class="loading-state">正在加载节点…</div><div v-else-if="nodes.length" class="node-table"><div class="node-table-head"><span>名称</span><span>标识</span><span>操作</span></div><article v-for="node in nodes" :key="String(node.id)" class="node-table-row"><strong>{{ node.title }}</strong><span class="muted">{{ node.id }}</span><div class="row-actions"><button class="small-button secondary-button" type="button" @click="startEdit(node)">编辑</button><button class="small-button danger-button" type="button" @click="remove(node)">删除</button></div></article></div><EmptyState v-else title="暂时没有节点" description="创建一个节点开始整理课程结构。" /></section><div v-if="editing" class="modal-backdrop"><section class="modal-card"><div class="section-heading"><div><h3>编辑节点</h3><p>修改名称不会改变已有题目关联。</p></div><button class="icon-button" type="button" aria-label="关闭" @click="editing = null">×</button></div><label>节点名称<input v-model="editTitle" /></label><div class="modal-actions"><button class="secondary-button" type="button" @click="editing = null">取消</button><button type="button" @click="save">保存</button></div></section></div></div>
</template>
