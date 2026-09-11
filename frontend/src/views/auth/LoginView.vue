<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitted = ref(false)
const formError = ref('')
const authError = computed(() => auth.error.value)
const authLoading = computed(() => auth.loading.value)
const displayError = computed(() => formError.value || authError.value)

async function submit() {
  submitted.value = true
  formError.value = ''
  auth.error.value = ''
  const normalizedUsername = username.value.trim()
  if (!normalizedUsername) {
    formError.value = '请输入用户名。'
    submitted.value = false
    return
  }
  if (!password.value) {
    formError.value = '请输入密码。'
    submitted.value = false
    return
  }
  try {
    const result = await auth.signIn(normalizedUsername, password.value)
    const role = result.user?.role ?? 'student'
    await router.replace(role === 'student' ? '/student' : `/${role}`)
  } catch {
    // The store exposes the actionable message for the form.
  } finally {
    submitted.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <h1>Python教学平台登录</h1>
      <form class="login-form" @submit.prevent="submit">
        <div class="login-form-group">
          <label for="login-username">用户</label>
          <input id="login-username" v-model="username" class="login-input" autocomplete="username" required autofocus />
        </div>
        <div class="login-form-group">
          <label for="login-password">密码</label>
          <div class="login-password-control">
            <input id="login-password" v-model="password" class="login-input" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required />
            <button class="password-visibility-toggle" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" :title="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.3-5 9.5-5 9.5 5 9.5 5-3.3 5-9.5 5-9.5-5-9.5-5Z" /><circle cx="12" cy="12" r="2.5" /></svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2C11.1 6.1 11.5 6 12 6c6.2 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.6M6.1 6.1C3.7 7.7 2.5 12 2.5 12s3.3 6 9.5 6c1 0 1.9-.2 2.7-.4" /></svg>
            </button>
          </div>
        </div>
        <InlineMessage :message="displayError" tone="error" />
        <div class="login-actions">
          <button class="login-submit" type="submit" :disabled="authLoading || submitted">{{ authLoading ? '登录中…' : '立即登录' }}</button>
          <RouterLink class="login-secondary" to="/password-change">修改密码</RouterLink>
        </div>
      </form>
    </section>
  </main>
</template>
