import { ref } from 'vue'
import { fetchClassContext, setCurrentClass } from '@/api/client'
import type { TeachingClass } from '@/types/classContext'

const items = ref<TeachingClass[]>([])
const current = ref<TeachingClass | null>(null)
const loading = ref(false)
const ready = ref(false)
const error = ref('')
let lastUser = ''

async function bootstrap(userKey = '') {
  if (ready.value && lastUser === userKey) return
  if (lastUser !== userKey) {
    items.value = []
    current.value = null
    ready.value = false
  }
  lastUser = userKey
  loading.value = true
  error.value = ''
  try {
    const result = await fetchClassContext()
    items.value = result.items
    current.value = result.current
    ready.value = true
  } catch (cause) {
    items.value = []
    current.value = null
    error.value = cause instanceof Error ? cause.message : '教学班数据加载失败。'
    ready.value = true
  } finally {
    loading.value = false
  }
}

async function select(classId: string) {
  loading.value = true
  try {
    const result = await setCurrentClass(classId)
    current.value = result.current
    window.dispatchEvent(new CustomEvent('teaching-class-changed', { detail: result.current }))
    // All page data is scoped by the server-side session; a full refresh keeps
    // every dashboard and nested route on the same selected class.
    window.location.reload()
  } finally {
    loading.value = false
  }
}

function clear() {
  items.value = []
  current.value = null
  error.value = ''
  ready.value = false
  lastUser = ''
}

export function useClassContext() {
  return { items, current, loading, ready, error, bootstrap, select, clear }
}
