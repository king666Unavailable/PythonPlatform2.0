<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from '@/components/feedback/EmptyState.vue'

interface ScorePoint {
  name: string
  score: number
}

const props = defineProps<{
  items: ScorePoint[]
  emptyText: string
}>()

const chartWidth = computed(() => Math.max(520, props.items.length * 120 + 70))
const chartPoints = computed(() => {
  const width = chartWidth.value
  const height = 260
  const left = 46
  const right = 24
  const top = 22
  const bottom = 46
  return props.items.map((item, index) => ({
    ...item,
    x: props.items.length === 1 ? width / 2 : left + (index / (props.items.length - 1)) * (width - left - right),
    y: top + ((100 - item.score) / 100) * (height - top - bottom),
  }))
})

const chartPolyline = computed(() => chartPoints.value.map((point) => `${point.x},${point.y}`).join(' '))
</script>

<template>
  <div v-if="chartPoints.length" class="score-chart-wrap class-score-chart-wrap">
    <svg class="score-chart" :style="{ width: `max(100%, ${chartWidth}px)` }" :viewBox="`0 0 ${chartWidth} 260`" role="img" aria-label="作业平均分折线图">
      <line v-for="level in [0, 25, 50, 75, 100]" :key="level" x1="46" :y1="22 + ((100 - level) / 100) * 192" :x2="chartWidth - 24" :y2="22 + ((100 - level) / 100) * 192" class="chart-grid-line" />
      <text v-for="level in [0, 25, 50, 75, 100]" :key="`label-${level}`" x="8" :y="27 + ((100 - level) / 100) * 192" class="chart-axis-label">{{ level }}</text>
      <polyline :points="chartPolyline" class="chart-line" />
      <g v-for="point in chartPoints" :key="point.name">
        <circle :cx="point.x" :cy="point.y" r="5" class="chart-point" />
        <text :x="point.x" :y="point.y - 12" text-anchor="middle" class="chart-score-label">{{ point.score }}</text>
      </g>
    </svg>
    <div class="score-chart-labels" :style="{ width: `max(100%, ${chartWidth}px)` }"><span v-for="point in chartPoints" :key="`${point.name}-label`" :title="point.name">{{ point.name }}</span></div>
  </div>
  <EmptyState v-else :title="emptyText" />
</template>
