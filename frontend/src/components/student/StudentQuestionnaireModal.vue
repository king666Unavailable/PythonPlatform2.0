<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchStudentProfile, fetchStudentQuestionnaire, saveStudentQuestionnaire } from '@/api/client'
import type { User } from '@/types/auth'
import InlineMessage from '@/components/feedback/InlineMessage.vue'

const props = defineProps<{ open: boolean; user: User; teachingClass: string }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const completed = ref(false)
const identity = ref({ name: '', username: '', gender: '', administrativeClass: '', teachingClass: '' })
const baseLevel = ref('')
const motivations = ref<string[]>([])
const directions = ref<string[]>([])
const expectedLevel = ref('')
const studyTime = ref('')
const resources = ref<string[]>([])
const questionTypes = ref<string[]>([])
const difficultyStrategy = ref('')
const learningStyles = ref<string[]>([])

function asList(value: unknown): string[] { return Array.isArray(value) ? value.map(String) : [] }
function resetResponses(responses: Record<string, unknown>) {
  baseLevel.value = String(responses.base_level ?? '')
  motivations.value = asList(responses.motivations)
  directions.value = asList(responses.directions)
  expectedLevel.value = String(responses.expected_level ?? '')
  studyTime.value = String(responses.study_time ?? '')
  resources.value = asList(responses.resources)
  questionTypes.value = asList(responses.question_types)
  difficultyStrategy.value = String(responses.difficulty_strategy ?? '')
  learningStyles.value = asList(responses.learning_styles)
}
async function load() {
  if (!props.open) return
  loading.value = true; error.value = ''
  identity.value = { name: props.user.name, username: props.user.username, gender: '', administrativeClass: '', teachingClass: props.teachingClass }
  try {
    const [questionnaire, profile] = await Promise.allSettled([fetchStudentQuestionnaire(), fetchStudentProfile()])
    if (questionnaire.status === 'fulfilled') {
      completed.value = questionnaire.value.completed
      resetResponses(questionnaire.value.questionnaire.responses)
    }
    if (profile.status === 'fulfilled') {
      const student = profile.value.student
      identity.value = { name: student.name, username: student.username, gender: student.gender, administrativeClass: student.administrative_class, teachingClass: student.teaching_class || props.teachingClass }
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '问卷加载失败，请稍后重试。'
  } finally { loading.value = false }
}
function close() { emit('close') }
async function save() {
  if (!baseLevel.value || !expectedLevel.value) { error.value = '请至少完成初始基础水平和预期能力等级。'; return }
  saving.value = true; error.value = ''
  try {
    await saveStudentQuestionnaire({
      base_level: baseLevel.value, motivations: motivations.value, directions: directions.value,
      expected_level: expectedLevel.value, study_time: studyTime.value, resources: resources.value,
      question_types: questionTypes.value, difficulty_strategy: difficultyStrategy.value, learning_styles: learningStyles.value,
    })
    completed.value = true
    emit('saved')
    emit('close')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '问卷保存失败，请稍后重试。' } finally { saving.value = false }
}
watch(() => props.open, (open) => { if (open) void load() })
</script>

<template>
  <div v-if="open" class="modal-backdrop questionnaire-backdrop" @click.self="close">
    <section class="modal-card questionnaire-modal-card" role="dialog" aria-modal="true" aria-labelledby="questionnaire-title">
      <div class="questionnaire-modal-header"><div><p class="eyebrow">{{ completed ? '学习信息' : '首次登录' }}</p><h3 id="questionnaire-title">课程学习信息问卷</h3><p>完善学习信息，帮助平台了解你的学习基础和学习偏好。</p></div><button class="icon-button" type="button" aria-label="关闭问卷" @click="close">×</button></div>
      <InlineMessage :message="error" tone="error" />
      <div v-if="loading" class="loading-state">正在加载问卷…</div>
      <div v-else class="questionnaire-content">
        <section class="questionnaire-section"><h4>基本信息</h4><div class="questionnaire-identity-grid"><label>姓名<input :value="identity.name" readonly /></label><label>学号<input :value="identity.username" readonly /></label><label>性别<input :value="identity.gender || '—'" readonly /></label><label>行政班<input :value="identity.administrativeClass || '—'" readonly /></label><label>教学班<input :value="identity.teachingClass || '—'" readonly /></label></div><p class="questionnaire-note">基本信息由账号和教学班资料提供，如需修改请联系管理员。</p></section>
        <section class="questionnaire-section"><h4>学习背景与动机</h4><div class="questionnaire-form-grid"><fieldset><legend>初始基础水平</legend><label v-for="item in ['零基础', '其他编程语言基础']" :key="item" class="questionnaire-option"><input v-model="baseLevel" type="radio" name="base-level" :value="item" />{{ item }}</label></fieldset><fieldset><legend>课程选修动机</legend><label v-for="item in ['考研', '就业', '兴趣', '学分']" :key="item" class="questionnaire-option"><input v-model="motivations" type="checkbox" :value="item" />{{ item }}</label></fieldset><fieldset><legend>Python 应用方向偏好</legend><label v-for="item in ['数据分析', '爬虫', '后端开发', '算法']" :key="item" class="questionnaire-option"><input v-model="directions" type="checkbox" :value="item" />{{ item }}</label></fieldset><fieldset><legend>预期能力等级</legend><label v-for="item in ['入门', '进阶', '竞赛', '就业']" :key="item" class="questionnaire-option"><input v-model="expectedLevel" type="radio" name="expected-level" :value="item" />{{ item }}</label></fieldset></div></section>
        <section class="questionnaire-section"><h4>学习习惯偏好</h4><div class="questionnaire-form-grid"><label class="questionnaire-field">学习时间段分布<textarea v-model="studyTime" rows="3" placeholder="例如：每周一、三、五晚 19:00-21:00" /></label><fieldset><legend>学习资源类型倾向</legend><label v-for="item in ['文档', '视频', '刷题']" :key="item" class="questionnaire-option"><input v-model="resources" type="checkbox" :value="item" />{{ item }}</label></fieldset><fieldset><legend>题目类型倾向</legend><label v-for="item in ['理论细节', '工程项目', '算法设计']" :key="item" class="questionnaire-option"><input v-model="questionTypes" type="checkbox" :value="item" />{{ item }}</label></fieldset><fieldset><legend>难点应对策略倾向</legend><label v-for="item in ['回退复习', '直接跳过', '查看答案']" :key="item" class="questionnaire-option"><input v-model="difficultyStrategy" type="radio" name="difficulty-strategy" :value="item" />{{ item }}</label></fieldset><fieldset><legend>学习方式倾向</legend><label v-for="item in ['预习', '复习', '边刷题边学']" :key="item" class="questionnaire-option"><input v-model="learningStyles" type="checkbox" :value="item" />{{ item }}</label></fieldset></div></section>
      </div>
      <div class="modal-actions questionnaire-modal-actions"><button class="secondary-button" type="button" @click="close">稍后填写</button><button type="button" :disabled="saving || loading" @click="save">{{ saving ? '保存中…' : completed ? '保存修改' : '提交问卷' }}</button></div>
    </section>
  </div>
</template>
