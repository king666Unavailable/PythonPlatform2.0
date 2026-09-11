<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import { changePassword } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const message = ref('')
const messageTone = ref<'error' | 'success' | 'info'>('info')
const username = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const auth = useAuthStore()

async function submit() {
  message.value = ''
  const normalizedUsername = username.value.trim()
  if (!normalizedUsername) {
    messageTone.value = 'error'
    message.value = '请输入学号。'
    return
  }
  if (!oldPassword.value) {
    messageTone.value = 'error'
    message.value = '请输入原密码。'
    return
  }
  if (newPassword.value.length < 8) {
    messageTone.value = 'error'
    message.value = '新密码长度不能少于 8 位。'
    return
  }
  if (newPassword.value.length > 128) {
    messageTone.value = 'error'
    message.value = '新密码长度不能超过 128 位。'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    messageTone.value = 'error'
    message.value = '两次输入的新密码不一致。'
    return
  }
  if (oldPassword.value === newPassword.value) {
    messageTone.value = 'error'
    message.value = '新密码不能与原密码相同。'
    return
  }

  submitting.value = true
  try {
    const result = await changePassword(normalizedUsername, oldPassword.value, newPassword.value, confirmPassword.value)
    messageTone.value = 'success'
    message.value = result.message || '密码修改成功，请重新登录。'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    if (auth.user.value?.role === 'student' && auth.user.value.username === normalizedUsername) {
      auth.clearSession()
    }
  } catch (cause) {
    messageTone.value = 'error'
    message.value = cause instanceof Error ? cause.message : '密码修改失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card password-card">
      <h1>修改密码</h1>
      <form class="login-form" @submit.prevent="submit">
        <div class="login-form-group">
          <label for="reset-username">学号</label>
          <input id="reset-username" v-model="username" class="login-input" maxlength="64" autocomplete="username" required />
        </div>
        <div class="login-form-group">
          <label for="reset-old-password">原密码</label>
          <div class="login-field-control">
            <input id="reset-old-password" v-model="oldPassword" class="login-input" type="password" maxlength="128" aria-describedby="old-password-help" autocomplete="current-password" required />
            <small id="old-password-help" class="login-help">若忘记原密码，请找管理员重置。</small>
          </div>
        </div>
        <div class="login-form-group">
          <label for="reset-new-password">新密码</label>
          <div class="login-field-control">
            <input id="reset-new-password" v-model="newPassword" class="login-input" type="password" minlength="8" maxlength="128" aria-describedby="new-password-help" autocomplete="new-password" required />
            <small id="new-password-help" class="login-help">至少 8 位，且不能与原密码相同。</small>
          </div>
        </div>
        <div class="login-form-group">
          <label for="reset-confirm-password">确认密码</label>
          <div class="login-field-control">
            <input id="reset-confirm-password" v-model="confirmPassword" class="login-input" type="password" maxlength="128" aria-describedby="confirm-password-help" autocomplete="new-password" required />
            <small id="confirm-password-help" class="login-help">确认密码需与新密码一致。</small>
          </div>
        </div>
        <InlineMessage :message="message" :tone="messageTone" />
        <div class="login-actions password-actions">
          <button class="login-submit" type="submit" :disabled="submitting">{{ submitting ? '提交中…' : '确认修改' }}</button>
          <RouterLink class="login-secondary" to="/login">返回登录</RouterLink>
        </div>
      </form>
    </section>
  </main>
</template>