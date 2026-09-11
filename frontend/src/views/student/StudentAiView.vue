<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createConversation, fetchConversation, fetchConversations, sendConversationMessage } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

interface Conversation { id: string | number; title: string; messages?: Array<{ role: string; content: string }> }
const conversations = ref<Conversation[]>([])
const currentId = ref('')
const messages = ref<Array<{ role: string; content: string }>>([])
const input = ref('')
const loading = ref(true)
const sending = ref(false)
const error = ref('')

async function load() { loading.value = true; try { conversations.value = (await fetchConversations()).items as unknown as Conversation[]; if (conversations.value[0]) await selectConversation(String(conversations.value[0].id)) } catch (cause) { error.value = cause instanceof Error ? cause.message : '会话加载失败。' } finally { loading.value = false } }
async function selectConversation(id: string) { currentId.value = id; try { const result = await fetchConversation(id); messages.value = (result.conversation.messages ?? []) as Array<{ role: string; content: string }> } catch (cause) { error.value = cause instanceof Error ? cause.message : '会话加载失败。' } }
async function newConversation() { try { const result = await createConversation('Python 学习问答'); const item = result.conversation as unknown as Conversation; conversations.value.unshift(item); await selectConversation(String(item.id)) } catch (cause) { error.value = cause instanceof Error ? cause.message : '新建会话失败。' } }
async function send() { if (!input.value.trim() || sending.value) return; if (!currentId.value) await newConversation(); if (!currentId.value) return; const content = input.value.trim(); input.value = ''; sending.value = true; error.value = ''; try { const result = await sendConversationMessage(currentId.value, content); messages.value = (result.conversation.messages ?? []) as Array<{ role: string; content: string }> } catch (cause) { input.value = content; error.value = cause instanceof Error ? cause.message : 'AI 回复失败。' } finally { sending.value = false } }
onMounted(() => void load())
</script>

<template>
  <div class="page-stack"><PageHeader title="AI 助教" description="围绕 Python 学习提问，获取分步骤的思路提示和概念解释。"><template #actions><button type="button" @click="newConversation">新建会话</button></template></PageHeader><InlineMessage :message="error" tone="error" /><div v-if="loading" class="loading-state">正在加载会话…</div><section v-else class="chat-layout content-card"><aside class="conversation-list"><strong>我的会话</strong><button v-for="conversation in conversations" :key="String(conversation.id)" type="button" :class="{ active: currentId === String(conversation.id) }" @click="selectConversation(String(conversation.id))">{{ conversation.title || '未命名会话' }}</button><EmptyState v-if="!conversations.length" title="还没有会话" description="点击右上角开始提问。" /></aside><div class="chat-content"><div v-if="messages.length" class="chat-messages"><article v-for="(message, index) in messages" :key="`${message.role}-${index}`" class="chat-bubble" :class="message.role"><span>{{ message.role === 'user' ? '我' : 'AI 助教' }}</span><p>{{ message.content }}</p></article></div><EmptyState v-else title="开始一次 Python 学习问答" description="例如：请解释列表推导式和普通 for 循环的区别。" /><form class="chat-input" @submit.prevent="send"><textarea v-model="input" rows="3" placeholder="输入你的问题" :disabled="sending" @keydown.enter.exact.prevent="send" /><button type="submit" :disabled="sending || !input.trim()">{{ sending ? '回答中…' : '发送' }}</button></form></div></section></div>
</template>
