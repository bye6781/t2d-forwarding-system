<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type TrendRow = { date: string; received: number; forwarded: number }

const props = defineProps<{ rows: TrendRow[] }>()

const chartWidth = ref(720)
const chartCanvas = ref<HTMLElement | null>(null)
const height = 248
const plot = { left: 44, right: 16, top: 18, bottom: 36 }
const plotWidth = computed(() => chartWidth.value - plot.left - plot.right)
const plotHeight = height - plot.top - plot.bottom
let resizeObserver: ResizeObserver | undefined

const rows = computed(() => props.rows.map((row) => ({
  ...row,
  received: finite(row.received),
  forwarded: finite(row.forwarded),
})))

const maxValue = computed(() => Math.max(1, ...rows.value.flatMap((row) => [row.received, row.forwarded])))
const gridValues = computed(() => Array.from({ length: 5 }, (_, index) => Math.round(maxValue.value * (4 - index) / 4)))

function finite(value: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0
}

function pointsFor(key: 'received' | 'forwarded') {
  const count = Math.max(1, rows.value.length - 1)
  return rows.value.map((row, index) => ({
    x: plot.left + (index / count) * plotWidth.value,
    y: plot.top + plotHeight - (row[key] / maxValue.value) * plotHeight,
  }))
}

function smoothPath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return ''
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`
  return points.slice(1).reduce((path, point, index) => {
    const previous = points[index]
    const midX = (previous.x + point.x) / 2
    return `${path} C ${midX} ${previous.y}, ${midX} ${point.y}, ${point.x} ${point.y}`
  }, `M ${points[0].x} ${points[0].y}`)
}

function linePath(key: 'received' | 'forwarded') {
  return smoothPath(pointsFor(key))
}

function areaPath(key: 'received' | 'forwarded') {
  const points = pointsFor(key)
  if (!points.length) return ''
  return `${smoothPath(points)} L ${points.at(-1)?.x} ${plot.top + plotHeight} L ${points[0].x} ${plot.top + plotHeight} Z`
}

function dateLabel(date: string) {
  const [, month, day] = String(date).split('-')
  return month && day ? `${Number(month)}/${Number(day)}` : date
}

onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !chartCanvas.value) return
  resizeObserver = new ResizeObserver(([entry]) => {
    chartWidth.value = Math.max(300, Math.round(entry.contentRect.width))
  })
  resizeObserver.observe(chartCanvas.value)
})

onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<template>
  <div ref="chartCanvas" class="flow-chart">
    <div v-if="rows.length" class="flow-chart__canvas">
      <svg :viewBox="`0 0 ${chartWidth} ${height}`" role="img" aria-label="近 7 天消息趋势：接收消息与转发成功">
        <defs>
          <linearGradient id="received-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#12a8e8" stop-opacity=".26" />
            <stop offset="1" stop-color="#12a8e8" stop-opacity="0" />
          </linearGradient>
          <linearGradient id="forwarded-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#16c79a" stop-opacity=".16" />
            <stop offset="1" stop-color="#16c79a" stop-opacity="0" />
          </linearGradient>
        </defs>
        <g class="flow-chart__grid">
          <g v-for="(value, index) in gridValues" :key="value">
            <line :x1="plot.left" :x2="chartWidth - plot.right" :y1="plot.top + index * plotHeight / 4" :y2="plot.top + index * plotHeight / 4" />
            <text :x="plot.left - 10" :y="plot.top + index * plotHeight / 4 + 4">{{ value }}</text>
          </g>
        </g>
        <path :d="areaPath('received')" fill="url(#received-area)" />
        <path :d="areaPath('forwarded')" fill="url(#forwarded-area)" />
        <path data-series="received" class="flow-chart__line is-received" :d="linePath('received')" />
        <path data-series="forwarded" class="flow-chart__line is-forwarded" :d="linePath('forwarded')" />
        <g v-for="(row, index) in rows" :key="row.date">
          <circle class="flow-chart__point is-received" :cx="pointsFor('received')[index].x" :cy="pointsFor('received')[index].y" r="3" />
          <circle class="flow-chart__point is-forwarded" :cx="pointsFor('forwarded')[index].x" :cy="pointsFor('forwarded')[index].y" r="3" />
          <text data-date-label class="flow-chart__date" :x="pointsFor('received')[index].x" :y="height - 10">{{ dateLabel(row.date) }}</text>
        </g>
      </svg>
    </div>
    <div v-else class="dashboard-empty dashboard-empty--chart">
      <span class="dashboard-empty__trace" />
      <strong>暂无消息趋势</strong>
      <small>开始转发后，这里会显示接收与成功转发的变化。</small>
    </div>
    <div class="chart-legend" aria-label="图例">
      <span><i class="legend-dot is-received" />接收消息</span>
      <span><i class="legend-dot is-forwarded" />转发成功</span>
    </div>
  </div>
</template>
