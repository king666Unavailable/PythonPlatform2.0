<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchClassAnalytics, fetchTeacherStudentProfile } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import ScoreLineChart from '@/components/data-display/ScoreLineChart.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const classId = ref('all')
const data = ref<any>(null)
const student = ref<any>(null)
const loading = ref(true)
const studentLoading = ref(false)
const error = ref('')
const activeTab = ref<'analysis' | 'details'>('analysis')

type AveragePoint = { name: string; score: number }

function averagePoints(values: Record<string, unknown> | undefined): AveragePoint[] {
  return Object.entries(values ?? {})
    .map(([name, score]) => ({ name, score: Number(score) }))
    .filter((item) => Number.isFinite(item.score))
}

const classAverage = computed(() => {
  const values = Object.values(data.value?.summary?.averages?.homework ?? {}).map(Number).filter(Number.isFinite)
  return values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : 0
})
const homeworkAverages = computed(() => averagePoints(data.value?.summary?.averages?.homework))
const classworkAverages = computed(() => averagePoints(data.value?.summary?.averages?.classwork))

async function load() {
  loading.value = true
  error.value = ''
  student.value = null
  try {
    data.value = await fetchClassAnalytics(classId.value.trim() || 'all')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '班级学情加载失败。'
  } finally {
    loading.value = false
  }
}

async function openStudent(id: string) {
  studentLoading.value = true
  try {
    student.value = await fetchTeacherStudentProfile(id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '学生资料加载失败。'
  } finally {
    studentLoading.value = false
  }
}

function switchTab(tab: 'analysis' | 'details') {
  activeTab.value = tab
  if (tab === 'details') {
    student.value = null
    studentLoading.value = false
  }
}

function openStudentFromDetails(id: string) {
  activeTab.value = 'analysis'
  void openStudent(id)
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="班级学情" description="查看班级整体趋势，并下钻到需要关注的学生。">
      <template #actions>
        <button type="button" :disabled="loading" @click="load">刷新数据</button>
      </template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载班级学情…</div>
    <EmptyState v-else-if="!data" title="暂时没有班级数据" description="请确认班级信息后重试。" />
    <template v-else>
      <div class="tabs class-analytics-tabs" role="tablist">
        <button type="button" :class="{ active: activeTab === 'analysis' }" @click="switchTab('analysis')">学习情况分析</button>
        <button type="button" :class="{ active: activeTab === 'details' }" @click="switchTab('details')">作业详情</button>
      </div>

      <template v-if="activeTab === 'analysis'">
        <div class="metric-grid">
          <MetricCard label="学生人数" :value="data.class.student_count" />
          <MetricCard label="需要关注" :value="data.summary.need_care_count" tone="orange" />
          <MetricCard label="优秀学生" :value="data.summary.excellent_count" tone="green" />
          <MetricCard label="平均成绩" :value="classAverage ? classAverage + ' 分' : '—'" tone="purple" />
        </div>

        <div class="dashboard-grid">
          <section class="content-card class-alert-card">
            <div class="section-heading"><div><h3>学情提醒</h3><p>点击学生查看个人学习情况。</p></div></div>
            <div class="alert-columns">
              <div class="alert-box warning">
                <strong>需要关注（{{ data.alerts.need_care.length }}）</strong>
                <small class="alert-rule-hint">有未交作业，或不及格率达到 50%</small>
                <button v-for="item in data.alerts.need_care" :key="item.id" type="button" @click="openStudent(item.id)">{{ item.name }}<span>未交 {{ item.unsubmit_count }} 次 · 不及格率 {{ item.fail_rate }}%</span></button>
                <span v-if="!data.alerts.need_care.length" class="muted">暂无</span>
              </div>
              <div class="alert-box success">
                <strong>表现优秀（{{ data.alerts.excellent.length }}）</strong>
                <small class="alert-rule-hint">已判卷作业平均分达到 90 分</small>
                <button v-for="item in data.alerts.excellent" :key="item.id" type="button" @click="openStudent(item.id)">{{ item.name }}<span>平均分 {{ item.average_score ?? '—' }} 分</span></button>
                <span v-if="!data.alerts.excellent.length" class="muted">暂无</span>
              </div>
            </div>
          </section>
          <section v-if="student" class="content-card class-analysis-student-detail-card">
            <h3>{{ student.student.name }}</h3>
            <p class="muted">{{ student.student.username }} · {{ student.student.study_class || '未填写班级' }}</p>
            <div class="student-results-heading"><strong>测试完成情况</strong><span>{{ student.student.assignment_results.length }} 项</span></div>
            <div v-if="student.student.assignment_results.length" class="student-assignment-result-list">
              <article v-for="item in student.student.assignment_results" :key="item.id" class="student-assignment-result" :class="{ failed: item.failed, pending: !item.submitted }">
                <div class="student-assignment-result-main">
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.submitted ? (item.score ?? '待判卷') : '未提交' }}</span>
                </div>
                <span v-if="item.failed" class="student-result-badge">不及格</span>
                <span v-else-if="!item.submitted" class="student-result-badge pending-badge">未提交</span>
              </article>
            </div>
            <span v-else class="student-risk-empty">暂无测试记录</span>
          </section>
          <section v-else class="content-card class-analysis-student-detail-card"><EmptyState :title="studentLoading ? '正在加载学生详情…' : '选择一名学生查看详情'" /></section>
        </div>

        <div class="class-average-grid">
          <section class="content-card">
            <div class="section-heading"><div><h3>课后作业平均分</h3></div></div>
            <ScoreLineChart :items="homeworkAverages" empty-text="暂无课后作业成绩。" />
          </section>
          <section class="content-card">
            <div class="section-heading"><div><h3>课堂测试平均分</h3></div></div>
            <ScoreLineChart :items="classworkAverages" empty-text="暂无课堂测试成绩。" />
          </section>
        </div>
      </template>

      <template v-else>
        <section class="content-card flush-card">
          <div class="section-heading padded-heading"><div><h3>作业详情</h3><p>查看各学生在所有作业和测试中的具体得分。</p></div></div>
          <div class="data-table class-detail-table">
            <div class="data-table-head"><span>序号</span><span>学号</span><span>姓名</span><span>班级</span><span v-for="test in data.tests" :key="test.name">{{ test.name }}<small> 得分</small></span></div>
            <button v-for="(item, index) in data.students" :key="item.id" class="data-table-row" type="button" @click="openStudentFromDetails(item.id)"><span>{{ index + 1 }}</span><span>{{ item.username }}</span><strong class="teacher-student-name">{{ item.name }}<small v-if="item.is_active === false">已停用</small></strong><span>{{ item.study_class || '未填写' }}</span><span v-for="test in data.tests" :key="test.name">{{ item.scores[test.name] ?? '—' }}</span></button>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>
