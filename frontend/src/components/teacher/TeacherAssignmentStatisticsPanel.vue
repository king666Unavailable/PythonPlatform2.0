<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ statistics: any }>()

const assignment = computed(() => props.statistics.assignment || {})
const questions = computed(() => props.statistics.questions || [])
const scoreSummary = computed(() => props.statistics.score_summary || {})
const scoreRows = computed(() => [...(props.statistics.scoreboard || [])].sort((a, b) => {
  const scoreA = a.score == null ? -1 : Number(a.score)
  const scoreB = b.score == null ? -1 : Number(b.score)
  return scoreB - scoreA || String(a.student_username).localeCompare(String(b.student_username))
}))
const exportScoreRows = computed(() => [...scoreRows.value].sort((a, b) => String(a.student_username).localeCompare(String(b.student_username), undefined, { numeric: true, sensitivity: 'base' })))

function statusLabel(status: unknown) {
  return status === 'graded' ? '已批改' : status === 'grading' ? '批改中' : status === 'unsubmitted' ? '未提交' : '待处理'
}

function formatDate(value: unknown) {
  if (!value) return '—'
  const date = new Date(String(value))
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function assignmentKindLabel(kind: unknown) {
  return ({ offline: '线下测试', classwork: '课堂测试', homework: '课后作业', exam: '考试', mock: '模拟测试' } as Record<string, string>)[String(kind)] || '未设置'
}

function questionTypeLabel(type: unknown) {
  return ({ '1': '选择题', '2': '填空题', '3': '编程题', '4': '程序填空题' } as Record<string, string>)[String(type)] || '题目'
}

function scoreLabel(value: unknown) {
  return value == null ? '待更新' : `${value} 分`
}

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function downloadCsv(filename: string, rows: unknown[][]) {
  const content = '\ufeff' + rows.map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n'
  downloadFile(filename, content, 'text/csv;charset=utf-8')
}

function csvCell(value: unknown) {
  return `"${String(value ?? '').replaceAll('"', '""')}"`
}

function downloadSubmissionCsv() {
  const rows = [['序号', '姓名', '成绩'], ...exportScoreRows.value.map((item, index) => [index + 1, item.student_name, item.score ?? 0])]
  downloadCsv('学生成绩表.csv', rows)
}

function downloadQuestionCsv() {
  const rows = [['题目名称', '题干内容', '答案', '正确人次', '错误人次'], ...questions.value.map((item) => [item.title, item.content, item.answer, item.correct_count, item.wrong_count])]
  downloadCsv('作业信息表.csv', rows)
}

function downloadQuestionPackage() {
  const content = questions.value.map((item, index) => `第${index + 1}题：${item.title || ''}\n题干：${item.content || ''}\n答案：${item.answer || ''}\n`).join('\n')
  downloadFile('完整作业内容.txt', content, 'text/plain;charset=utf-8')
}
</script>

<template>
  <div class="assignment-statistics-panel">
    <div class="assignment-statistics-toolbar">
      <div>
        <h3>{{ assignment.title || '作业统计' }}</h3>
        <p>{{ assignmentKindLabel(assignment.assignment_kind) }} · 截止 {{ formatDate(assignment.deadline) }} · 共 {{ questions.length }} 道题</p>
      </div>
      <div class="row-actions">
        <button class="small-button secondary-button" type="button" @click="downloadQuestionCsv">下载信息表</button>
        <button class="small-button secondary-button" type="button" @click="downloadSubmissionCsv">导出成绩单</button>
        <button class="small-button secondary-button" type="button" @click="downloadQuestionPackage">完整题目包</button>
      </div>
    </div>

    <div class="assignment-statistics-layout">
      <section class="content-card assignment-question-stat-card">
        <div class="section-heading">
          <div><h3>题目详情</h3><p>查看每道题的题干、答案解析和作答情况。</p></div>
          <span class="muted">共 {{ questions.length }} 题</span>
        </div>
        <div v-if="questions.length" class="assignment-question-table">
          <div class="assignment-question-table-head"><span>序号</span><span>题目名称</span><span>题干内容</span><span>正确答案</span><span>解析</span><span>正确人次</span><span>错误人次</span></div>
          <div v-for="item in questions" :key="item.position" class="assignment-question-table-row">
            <span>{{ item.position + 1 }}</span>
            <div><strong>{{ item.title }}</strong><small>{{ questionTypeLabel(item.question_type) }}</small></div>
            <p class="question-stat-content">{{ item.content || '—' }}</p>
            <p class="question-stat-content">{{ item.answer || '—' }}</p>
            <p class="question-stat-content">{{ item.analysis || '—' }}</p>
            <strong class="correct-stat">{{ item.correct_count }}</strong>
            <strong class="wrong-stat">{{ item.wrong_count }}</strong>
          </div>
        </div>
        <p v-else class="muted assignment-statistics-empty">暂时没有题目详情。</p>
      </section>

      <section class="content-card assignment-score-board-card">
        <div class="section-heading">
          <div><h3>学生成绩榜</h3><p>按成绩从高到低显示全体学生。</p></div>
          <span class="muted">平均分：{{ scoreSummary.average_score ?? '—' }}</span>
        </div>
        <div v-if="scoreRows.length" class="assignment-score-board">
          <div class="assignment-score-row score-board-header"><span>序号</span><span>学生姓名</span><span>得分</span></div>
          <div v-for="(item, index) in scoreRows" :key="item.student_username" class="assignment-score-row"><span class="score-board-rank">{{ index + 1 }}</span><span>{{ item.student_name }}</span><strong>{{ scoreLabel(item.score) }}</strong></div>
        </div>
        <p v-else class="muted assignment-statistics-empty">暂时没有学生提交记录。</p>
      </section>
    </div>
  </div>
</template>
