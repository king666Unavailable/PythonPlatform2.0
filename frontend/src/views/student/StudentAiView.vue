<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createConversation, fetchConversation, fetchConversations, renameConversation, sendConversationMessage } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { renderMarkdown } from '@/utils/markdown'

interface SuggestedResource { question_id: string; question_title: string; point_title: string; difficulty: number | null; mastery?: number }
interface ChatMessage { role: string; content: string; sources?: SuggestedResource[]; rag_status?: string; pending?: boolean }
interface Conversation { id: string | number; title: string; messages?: ChatMessage[] }

const conversations = ref<Conversation[]>([])
const currentId = ref('')
const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(true)
const sending = ref(false)
const error = ref('')
const messageList = ref<HTMLDivElement | null>(null)
const editingConversationId = ref('')
const editingTitle = ref('')

async function scrollToLatest() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

async function load() {
  loading.value = true
  try {
    conversations.value = (await fetchConversations()).items as unknown as Conversation[]
    if (conversations.value[0]) await selectConversation(String(conversations.value[0].id))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '会话加载失败。'
  } finally {
    loading.value = false
  }
}

async function selectConversation(id: string) {
  currentId.value = id
  try {
    const result = await fetchConversation(id)
    messages.value = (result.conversation as unknown as Conversation).messages ?? []
    await scrollToLatest()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '会话加载失败。'
  }
}

async function newConversation() {
  try {
    const result = await createConversation('Python 学习问答')
    const item = result.conversation as unknown as Conversation
    conversations.value.unshift(item)
    await selectConversation(String(item.id))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '新建会话失败。'
  }
}

function startRename(conversation: Conversation) {
  editingConversationId.value = String(conversation.id)
  editingTitle.value = conversation.title || ''
  error.value = ''
}

function cancelRename() {
  editingConversationId.value = ''
  editingTitle.value = ''
}

async function saveRename(conversationId: string) {
  const title = editingTitle.value.trim()
  if (!title) {
    error.value = '会话名称不能为空。'
    return
  }
  try {
    const result = await renameConversation(conversationId, title)
    const conversation = conversations.value.find((item) => String(item.id) === conversationId)
    if (conversation) conversation.title = result.conversation.title
    cancelRename()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '会话名称更新失败。'
  }
}

async function send() {
  if (!input.value.trim() || sending.value) return
  if (!currentId.value) await newConversation()
  if (!currentId.value) return

  const content = input.value.trim()
  input.value = ''
  sending.value = true
  error.value = ''
  messages.value.push(
    { role: 'user', content },
    { role: 'assistant', content: '', pending: true },
  )
  await scrollToLatest()

  try {
    const result = await sendConversationMessage(currentId.value, content)
    messages.value = (result.conversation as unknown as Conversation).messages ?? []
    await scrollToLatest()
  } catch (cause) {
    const pending = messages.value.find((message) => message.pending)
    if (pending) {
      pending.pending = false
      pending.content = 'AI 助教暂时无法完成本次回复，请查看上方提示后重试。'
    }
    error.value = cause instanceof Error ? cause.message : 'AI 回复失败。'
  } finally {
    sending.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="AI 助教" description="结合当前教学班题库与已练习的薄弱知识点，提供有依据的 Python 学习辅导。">
      <template #actions><button type="button" @click="newConversation">新建会话</button></template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载会话…</div>
    <section v-else class="chat-layout content-card">
      <aside class="conversation-list">
        <strong>我的会话</strong>
        <div v-for="conversation in conversations" :key="String(conversation.id)" class="conversation-item" :class="{ active: currentId === String(conversation.id) }">
          <form v-if="editingConversationId === String(conversation.id)" class="conversation-rename-form" @submit.prevent="saveRename(String(conversation.id))">
            <input v-model="editingTitle" maxlength="100" aria-label="会话名称" />
            <button type="submit">保存</button>
            <button type="button" @click="cancelRename">取消</button>
          </form>
          <template v-else>
            <button type="button" class="conversation-select" @click="selectConversation(String(conversation.id))">
              {{ conversation.title || '未命名会话' }}
            </button>
            <button type="button" class="conversation-rename" :aria-label="`编辑${conversation.title || '会话'}名称`" :title="`编辑${conversation.title || '会话'}名称`" @click="startRename(conversation)">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15.2 5.2 3.6 3.6M4 20l4.2-.9L19.7 7.6a2.1 2.1 0 0 0-3-3L5.1 16.2 4 20Z" /></svg>
            </button>
          </template>
        </div>
        <EmptyState v-if="!conversations.length" title="还没有会话" description="点击右上角开始提问。" />
      </aside>
      <div class="chat-content">
        <div v-if="messages.length" ref="messageList" class="chat-messages">
          <article v-for="(message, index) in messages" :key="`${message.role}-${index}`" class="chat-bubble" :class="message.role">
            <span>{{ message.role === 'user' ? '我' : 'AI 助教' }}</span>
            <div v-if="message.pending" class="chat-pending" role="status" aria-live="polite">
              正在思考<span class="chat-pending-dots"><i /><i /><i /></span>
            </div>
            <div v-else-if="message.role === 'assistant'" class="chat-markdown" v-html="renderMarkdown(message.content)" />
            <p v-else>{{ message.content }}</p>
            <div v-if="message.role === 'assistant' && message.sources?.length" class="ai-source-list">
              <strong>相关课程资源</strong>
              <RouterLink v-for="(source, sourceIndex) in message.sources" :key="`${source.question_id}-${sourceIndex}`" :to="{ name: 'student-questions', query: { q: source.question_title } }" class="ai-source-card">
                <span>{{ source.question_title }}</span>
                <small>{{ source.point_title || '题库练习' }}<template v-if="source.mastery !== undefined"> · 你的掌握度 {{ source.mastery }} 分</template><template v-if="source.difficulty !== null"> · 难度 {{ source.difficulty }}</template></small>
              </RouterLink>
            </div>
          </article>
        </div>
        <EmptyState v-else title="开始一次 Python 学习问答" description="例如：请解释列表推导式和普通 for 循环的区别。" />
        <form class="chat-input" @submit.prevent="send">
          <textarea v-model="input" rows="3" placeholder="输入你的问题" :disabled="sending" @keydown.enter.exact.prevent="send" />
          <button type="submit" :disabled="sending || !input.trim()">{{ sending ? '回答中…' : '发送' }}</button>
        </form>
      </div>
    </section>
  </div>
</template>
