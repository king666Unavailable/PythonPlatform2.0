<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchClassAnalytics, fetchTeacherClassMastery, fetchTeacherStudentProfile } from '@/api/client'
import EmptyState from '@/components/feedback/EmptyState.vue'
import InlineMessage from '@/components/feedback/InlineMessage.vue'
import ScoreLineChart from '@/components/data-display/ScoreLineChart.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { ClassKnowledgeMasteryResponse, ClassMasteryNode } from '@/types/teacher'

const classId = ref('all')
const data = ref<any>(null)
const student = ref<any>(null)
const loading = ref(true)
const studentLoading = ref(false)
const error = ref('')
const activeTab = ref<'analysis' | 'details' | 'mastery'>('analysis')
const masteryData = ref<ClassKnowledgeMasteryResponse | null>(null)
const masteryLoading = ref(false)
const masteryError = ref('')
const selectedMasteryKey = ref('')

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

function switchTab(tab: 'analysis' | 'details' | 'mastery') {
  activeTab.value = tab
  if (tab === 'details') {
    student.value = null
    studentLoading.value = false
  }
  if (tab === 'mastery' && !masteryData.value) void loadMastery()
}

function openStudentFromDetails(id: string) {
  activeTab.value = 'analysis'
  void openStudent(id)
}

function masteryKey(node: Pick<ClassMasteryNode, 'node_type' | 'node_id'>) {
  return `${node.node_type}:${node.node_id}`
}

const masteryTreeRows = computed(() => {
  const nodes = masteryData.value?.nodes ?? []
  const nodeMap = new Map(nodes.map((node) => [masteryKey(node), node]))
  const children = new Map<string, ClassMasteryNode[]>()
  const roots: ClassMasteryNode[] = []
  for (const node of nodes) {
    const parentKey = node.parent_type && node.parent_id ? `${node.parent_type}:${node.parent_id}` : ''
    if (parentKey && nodeMap.has(parentKey)) {
      const group = children.get(parentKey) ?? []
      group.push(node)
      children.set(parentKey, group)
    } else {
      roots.push(node)
    }
  }
  const order = { class: 0, theme: 1, knowledge: 2, point: 3 }
  const sortNodes = (items: ClassMasteryNode[]) => items.sort((a, b) => (order[a.node_type] - order[b.node_type]) || a.title.localeCompare(b.title, 'zh-CN'))
  const rows: Array<ClassMasteryNode & { depth: number }> = []
  function visit(node: ClassMasteryNode, depth: number) {
    rows.push({ ...node, depth })
    for (const child of sortNodes(children.get(masteryKey(node)) ?? [])) visit(child, depth + 1)
  }
  for (const root of sortNodes(roots)) visit(root, 0)
  return rows
})

const selectedMastery = computed(() => masteryData.value?.selected_node ?? null)

function scoreLabel(score: number | null) {
  return score == null ? '暂无数据' : `${score.toFixed(1)} 分`
}

function scoreTone(score: number | null) {
  if (score == null) return 'mastery-no-data'
  if (score >= 80) return 'mastery-excellent'
  if (score >= 60) return 'mastery-good'
  if (score >= 40) return 'mastery-warning'
  return 'mastery-danger'
}

async function loadMastery(nodeType = '', nodeId = '') {
  masteryLoading.value = true
  masteryError.value = ''
  if (!nodeType) selectedMasteryKey.value = ''
  try {
    masteryData.value = await fetchTeacherClassMastery(nodeType, nodeId)
    if (nodeType && nodeId) selectedMasteryKey.value = `${nodeType}:${nodeId}`
  } catch (cause) {
    masteryError.value = cause instanceof Error ? cause.message : '知识掌握度加载失败。'
  } finally {
    masteryLoading.value = false
  }
}

function selectMasteryNode(node: ClassMasteryNode) {
  selectedMasteryKey.value = masteryKey(node)
  void loadMastery(node.node_type, node.node_id)
}

onMounted(() => void load())
</script>

<template>
  <div class="page-stack">
    <PageHeader title="班级学情" description="查看班级整体趋势，并下钻到需要关注的学生。">
      <template #actions>
        <button class="secondary-button" type="button" :disabled="loading" @click="load">刷新数据</button>
      </template>
    </PageHeader>
    <InlineMessage :message="error" tone="error" />
    <div v-if="loading" class="loading-state">正在加载班级学情…</div>
    <EmptyState v-else-if="!data" title="暂时没有班级数据" description="请确认班级信息后重试。" />
    <template v-else>
      <div class="tabs class-analytics-tabs" role="tablist">
        <button type="button" :class="{ active: activeTab === 'analysis' }" @click="switchTab('analysis')">学习情况分析</button>
        <button type="button" :class="{ active: activeTab === 'details' }" @click="switchTab('details')">作业详情</button>
        <button type="button" :class="{ active: activeTab === 'mastery' }" @click="switchTab('mastery')">知识掌握度</button>
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

      <template v-else-if="activeTab === 'mastery'">
        <InlineMessage :message="masteryError" tone="error" />
        <div v-if="masteryLoading && !masteryData" class="loading-state">正在加载知识掌握度…</div>
        <template v-else-if="masteryData">
          <div class="metric-grid class-mastery-metrics">
            <MetricCard label="课程总体掌握度" :value="masteryData.summary.course_mastery == null ? '—' : masteryData.summary.course_mastery + ' 分'" tone="blue" />
            <MetricCard label="覆盖学生数" :value="`${masteryData.summary.coverage_student_count} / ${masteryData.class.student_count}`" tone="green" />
            <MetricCard label="已作答题数" :value="masteryData.summary.answered_question_count" tone="purple" />
          </div>

          <section class="content-card class-mastery-browser">
            <div class="section-heading"><div><h3>知识掌握度</h3><p>按课程结构查看当前教学班的掌握情况。</p></div><button class="secondary-button" type="button" :disabled="masteryLoading" @click="loadMastery()">刷新数据</button></div>
            <div class="class-mastery-browser-grid">
              <div class="class-mastery-tree" role="tree" aria-label="知识掌握度层级">
                <button v-for="node in masteryTreeRows" :key="masteryKey(node)" type="button" class="class-mastery-tree-row" :class="[{ selected: selectedMasteryKey === masteryKey(node) }, scoreTone(node.mastery_score)]" :style="{ paddingLeft: `${16 + node.depth * 22}px` }" @click="selectMasteryNode(node)">
                  <span class="class-mastery-tree-marker">{{ node.node_type === 'point' ? '•' : node.node_type === 'knowledge' ? '◆' : node.node_type === 'theme' ? '▸' : '▣' }}</span>
                  <span class="class-mastery-tree-title">{{ node.title }}</span>
                  <small>{{ scoreLabel(node.mastery_score) }}</small>
                </button>
                <EmptyState v-if="!masteryTreeRows.length" title="暂无知识节点" description="当前教学班还没有可展示的知识结构。" />
              </div>

              <div class="class-mastery-detail">
                <div v-if="selectedMastery" class="class-mastery-detail-content">
                  <div class="section-heading"><div><span class="mastery-type-label">{{ selectedMastery.node.type_label }}</span><h3>{{ selectedMastery.node.title }}</h3></div><span class="class-mastery-score" :class="scoreTone(selectedMastery.node.mastery_score)">{{ scoreLabel(selectedMastery.node.mastery_score) }}</span></div>
                  <div class="class-mastery-detail-metrics"><div><span>覆盖学生</span><strong>{{ selectedMastery.node.covered_student_count }} 人</strong></div><div><span>覆盖率</span><strong>{{ selectedMastery.node.coverage_rate }}%</strong></div><div><span>关联题目</span><strong>{{ selectedMastery.node.question_count }} 题</strong></div><div><span>作答次数</span><strong>{{ selectedMastery.node.attempted_count }} 次</strong></div></div>
                  <div class="class-mastery-distribution"><h4>掌握度分布</h4><div v-for="item in selectedMastery.distribution" :key="item.label" class="class-mastery-distribution-row"><span>{{ item.label }}</span><i><b :style="{ width: `${masteryData.class.student_count ? item.count / masteryData.class.student_count * 100 : 0}%` }" /></i><strong>{{ item.count }} 人</strong></div></div>
                  <div class="class-mastery-unmastered"><h4>未掌握学生（{{ selectedMastery.unmastered_students.length }}）</h4><div v-if="selectedMastery.unmastered_students.length" class="class-mastery-student-list"><span v-for="item in selectedMastery.unmastered_students" :key="item.username" :class="{ inactive: !item.is_active }">{{ item.name }}（{{ item.username }}）<small>{{ item.score == null ? '暂无记录' : `${item.score} 分` }}</small></span></div><span v-else class="muted">暂无未掌握学生。</span></div>
                </div>
                <EmptyState v-else title="选择一个知识节点" description="点击左侧课程结构，查看掌握度分布和未掌握学生。" />
              </div>
            </div>
          </section>

          <div class="class-mastery-ranking-grid">
            <section class="content-card"><div class="section-heading"><div><h3>薄弱知识点</h3><p>掌握度较低的知识点。</p></div></div><div class="class-mastery-ranking-list"><button v-for="node in masteryData.weak_points" :key="masteryKey(node)" type="button" @click="selectMasteryNode(node)"><span>{{ node.title }}</span><strong class="mastery-danger">{{ scoreLabel(node.mastery_score) }}</strong></button><span v-if="!masteryData.weak_points.length" class="muted">暂无已评分知识点。</span></div></section>
            <section class="content-card"><div class="section-heading"><div><h3>表现较好的知识点</h3><p>掌握度较高的知识点。</p></div></div><div class="class-mastery-ranking-list"><button v-for="node in masteryData.strong_points" :key="masteryKey(node)" type="button" @click="selectMasteryNode(node)"><span>{{ node.title }}</span><strong class="mastery-excellent">{{ scoreLabel(node.mastery_score) }}</strong></button><span v-if="!masteryData.strong_points.length" class="muted">暂无已评分知识点。</span></div></section>
          </div>
        </template>
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
