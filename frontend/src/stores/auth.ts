import { computed, ref } from 'vue'
import { ApiError, fetchCurrentUser, login, logout } from '@/api/client'
import type { User } from '@/types/auth'

const user = ref<User | null>(null)
const ready = ref(false)
const loading = ref(false)
const error = ref('')
let bootstrapPromise: Promise<void> | null = null

async function bootstrap() {
  if (ready.value) return
  if (bootstrapPromise) return bootstrapPromise
  bootstrapPromise = (async () => {
    try {
      user.value = (await fetchCurrentUser()).user
    } catch {
      user.value = null
    } finally {
      ready.value = true
      bootstrapPromise = null
    }
  })()
  return bootstrapPromise
}

async function signIn(username: string, password: string) {
  loading.value = true
  error.value = ''
  try {
    const result = await login(username, password)
    user.value = result.user ?? null
    return result
  } catch (cause) {
    if (cause instanceof ApiError && cause.code === 'ACCOUNT_DISABLED') {
      error.value = '账号已停用，请联系管理员。'
    } else if (cause instanceof ApiError && cause.code === 'ACCOUNT_NOT_FOUND') {
      error.value = '账户不存在，请联系老师注册。'
    } else if (cause instanceof ApiError && cause.status === 401) {
      error.value = '用户名或密码错误。'
    } else {
      error.value = cause instanceof Error ? cause.message : '登录失败，请稍后重试。'
    }
    throw cause
  } finally {
    loading.value = false
  }
}

function clearSession() {
  user.value = null
  ready.value = true
  error.value = ''
}

async function signOut() {
  try {
    await logout()
  } finally {
    clearSession()
  }
}

export function useAuthStore() {
  return {
    user,
    ready,
    loading,
    error,
    isAuthenticated: computed(() => Boolean(user.value)),
    bootstrap,
    signIn,
    signOut,
    clearSession,
  }
}
