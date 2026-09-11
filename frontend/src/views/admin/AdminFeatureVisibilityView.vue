<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchAdminNavigationSettings, updateAdminNavigationSettings } from '@/api/client'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { NavigationVisibilityItem } from '@/types/navigation'

type ConfigRole = 'student' | 'teacher'

const selectedRole = ref<ConfigRole>('student')
const roleItems = ref<Record<ConfigRole, NavigationVisibilityItem[]>>({ student: [], teacher: [] })
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')

const roleLabel: Record<ConfigRole, string> = { student: '学生端', teacher: '教师端' }
const currentItems = computed(() => roleItems.value[selectedRole.value])
const groups = computed(() => {
  const result: Array<{ label: string; items: NavigationVisibilityItem[] }> = []
  for (const item of currentItems.value) {
    let group = result.find((candidate) => candidate.label === item.group)
    if (!group) { group = { label: item.group, items: [] }; result.push(group) }
    group.items.push(item)
  }
  return result
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchAdminNavigationSettings()
    roleItems.value = { student: result.roles.student || [], teacher: result.roles.teacher || [] }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '功能配置加载失败。'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!currentItems.value.some((item) => item.is_visible)) {
    error.value = '每个角色至少需要保留一个可用功能。'
    return
  }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const result = await updateAdminNavigationSettings(selectedRole.value, currentItems.value.map((item) => ({ id: item.id, is_visible: item.is_visible })))
    roleItems.value[selectedRole.value] = result.items
    success.value = `${roleLabel[selectedRole.value]}功能显示配置已保存。`
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '功能配置保存失败。'
  } finally {
    saving.value = false
  }
}

function switchRole(role: ConfigRole) {
  selectedRole.value = role
  error.value = ''
  success.value = ''
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="功能配置" />
    <InlineMessage :message="error" tone="error" />
    <InlineMessage :message="success" tone="success" />
    <section class="content-card feature-visibility-card">
      <div class="feature-role-tabs" role="tablist" aria-label="选择用户端">
        <button type="button" :class="{ active: selectedRole === 'student' }" @click="switchRole('student')">学生端</button>
        <button type="button" :class="{ active: selectedRole === 'teacher' }" @click="switchRole('teacher')">教师端</button>
      </div>
      <div v-if="loading" class="loading-state">正在加载功能配置…</div>
      <template v-else>
        <div class="feature-visibility-heading"><div><h3>{{ roleLabel[selectedRole] }}导航功能</h3><p>关闭后，该功能不会显示在导航栏，也不能通过地址直接访问。</p></div><button type="button" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        <div class="feature-setting-groups">
          <section v-for="group in groups" :key="group.label" class="feature-setting-group">
            <h4>{{ group.label }}</h4>
            <label v-for="item in group.items" :key="item.id" class="feature-setting-option">
              <input v-model="item.is_visible" type="checkbox" />
              <span><strong>{{ item.label }}</strong><small>{{ item.path }}</small></span>
              <em :class="item.is_visible ? 'is-on' : 'is-off'">{{ item.is_visible ? '显示' : '隐藏' }}</em>
            </label>
          </section>
        </div>
      </template>
    </section>
  </div>
</template>
