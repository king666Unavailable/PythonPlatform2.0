<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/navigation/AppIcon.vue'
import { useClassContext } from '@/stores/classContext'
import { useNavigationStore } from '@/stores/navigation'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const profileMenuOpen = ref(false)
const user = computed(() => auth.user.value)
const navigation = useNavigationStore()
const groups = computed(() => user.value ? navigation.groupsForRole(user.value.role) : [])
const pageTitle = computed(() => String(route.meta.title ?? '学习概览'))
const roleLabels = { teacher: '教师', student: '学生', admin: '管理员' } as const
const roleLabel = computed(() => user.value ? roleLabels[user.value.role] : '')
const classContext = useClassContext()
const classOptions = computed(() => classContext.items.value)
const currentClassId = computed(() => classContext.current.value?.id ?? '')
const studentClassChecking = computed(() => user.value?.role === 'student' && !classContext.ready.value)
const studentHasNoClass = computed(() => user.value?.role === 'student' && classContext.ready.value && !classContext.loading.value && !classOptions.value.length && !classContext.error.value)
const studentClassLoadFailed = computed(() => user.value?.role === 'student' && classContext.ready.value && !classContext.loading.value && Boolean(classContext.error.value))

async function handleClassChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value) await classContext.select(value)
}

watch(() => user.value?.username, (username) => {
  if (username && user.value) {
    void classContext.bootstrap(username)
    if (user.value.role === 'admin') navigation.clear()
    else void navigation.bootstrap(user.value.role)
  } else {
    classContext.clear()
    navigation.clear()
  }
}, { immediate: true })

function isActive(to: string) {
  return route.path === to || (to !== '/student' && to !== '/teacher' && to !== '/admin' && route.path.startsWith(`${to}/`))
}

async function signOut() {
  profileMenuOpen.value = false
  await auth.signOut()
  await router.replace('/login')
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target
  if (target instanceof Node && !(target as Element).closest('.topbar-user')) {
    profileMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocumentClick))
</script>

<template>
  <div class="app-layout">
    <div class="mobile-backdrop" :class="{ visible: mobileOpen }" @click="mobileOpen = false" />
    <aside class="app-sidebar" :class="{ open: mobileOpen }">
      <div class="brand-block"><img class="brand-logo" src="/img/csu.gif" alt="中南大学校徽"><div><strong>Python<br>辅助教学平台</strong></div></div>
      <div v-if="user" class="sidebar-user"><span class="sidebar-avatar">{{ user.name.slice(0, 1) }}</span><div class="sidebar-user-info"><strong>{{ user.name }}</strong><span>{{ roleLabel }}</span></div><label v-if="classOptions.length" class="sidebar-class-switcher"><span>当前教学班</span><select :value="currentClassId" :disabled="classContext.loading.value" @change="handleClassChange"><option v-for="item in classOptions" :key="item.id" :value="item.id">{{ item.teaching_class || item.title }}<template v-if="item.academic_year"> · {{ item.academic_year }}</template></option></select></label></div>
      <nav class="sidebar-nav" aria-label="主导航"><section v-for="group in groups" :key="group.label" class="nav-group"><h2>{{ group.label }}</h2><RouterLink v-for="item in group.items" :key="item.id" :to="item.to" class="nav-item" :class="{ active: isActive(item.to) }" @click="mobileOpen = false"><AppIcon :name="item.icon" /><span>{{ item.label }}</span></RouterLink></section></nav>
    </aside>
    <div class="app-main"><header class="topbar"><button class="mobile-menu-button" type="button" aria-label="打开导航" @click="mobileOpen = true">☰</button><div><p class="topbar-kicker">Python辅助教学平台</p><h1>{{ pageTitle }}</h1></div><div v-if="user" class="topbar-user"><button class="topbar-profile-button" type="button" aria-haspopup="menu" :aria-expanded="profileMenuOpen" @click.stop="profileMenuOpen = !profileMenuOpen"><span class="topbar-avatar">{{ user.name.slice(0, 1) }}</span><span class="topbar-user-name">{{ user.name }}</span><span class="profile-chevron" aria-hidden="true">⌄</span></button><div v-if="profileMenuOpen" class="profile-menu" role="menu"><div class="profile-menu-heading"><strong>{{ user.name }}</strong><span>{{ roleLabel }}</span></div><RouterLink v-if="user.role === 'student'" class="profile-menu-link" to="/password-change" role="menuitem" @click="profileMenuOpen = false">修改密码</RouterLink><button class="profile-menu-item" type="button" role="menuitem" @click="signOut">退出登录</button></div></div></header><main class="content-area"><section v-if="studentClassChecking" class="student-class-state content-card"><strong>正在检查可用教学班…</strong></section><section v-else-if="studentHasNoClass" class="student-class-state content-card"><strong>当前没有可用教学班，请联系管理员</strong></section><section v-else-if="studentClassLoadFailed" class="student-class-state content-card"><strong>教学班信息暂不可用，请稍后重试</strong><span>{{ classContext.error.value }}</span></section><RouterView v-else /></main></div>
  </div>
</template>
