import { ref } from 'vue'
import { fetchNavigationSettings } from '@/api/client'
import { navigationForRole, type NavigationGroup, type NavigationRole } from '@/navigation/features'
import type { NavigationVisibilityItem } from '@/types/navigation'

const items = ref<NavigationVisibilityItem[]>([])
const loading = ref(false)
const ready = ref(false)
const error = ref('')
let lastRole: NavigationRole | '' = ''

async function bootstrap(role: NavigationRole) {
  if (role === 'admin' || (ready.value && lastRole === role)) return
  if (lastRole !== role) {
    items.value = []
    ready.value = false
  }
  lastRole = role
  loading.value = true
  error.value = ''
  try {
    const result = await fetchNavigationSettings()
    items.value = result.items
  } catch (cause) {
    // Keep the built-in complete menu when the optional settings service is unavailable.
    items.value = []
    error.value = cause instanceof Error ? cause.message : '功能配置加载失败。'
  } finally {
    ready.value = true
    loading.value = false
  }
}

function visibleIds(role: NavigationRole) {
  if (!items.value.length || lastRole !== role) return undefined
  return new Set(items.value.filter((item) => item.is_visible).map((item) => item.id))
}

function sortOrders(role: NavigationRole) {
  if (!items.value.length || lastRole !== role) return undefined
  return new Map(items.value.map((item) => [item.id, item.sort_order]))
}

function groupsForRole(role: NavigationRole): NavigationGroup[] {
  return navigationForRole(role, visibleIds(role), sortOrders(role))
}

function firstPath(role: NavigationRole) {
  return groupsForRole(role).flatMap((group) => group.items)[0]?.to ?? (role === 'student' ? '/student' : `/${role}`)
}

function clear() {
  items.value = []
  loading.value = false
  ready.value = false
  error.value = ''
  lastRole = ''
}

export function useNavigationStore() {
  return { items, loading, ready, error, bootstrap, groupsForRole, firstPath, clear }
}
