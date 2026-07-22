<script setup lang="ts">
import { computed } from 'vue'

type TypeRow = { type: string; count: number }

const props = defineProps<{ rows: TypeRow[] }>()

const palette = ['#12a8e8', '#16c79a', '#f2a516', '#8b73ea', '#64718b']
const labels: Record<string, string> = {
  text: '文本消息',
  photo: '图片',
  image: '图片',
  video: '视频',
  document: '文件',
  file: '文件',
  audio: '音频',
  other: '其他',
}

const normalized = computed(() => props.rows
  .map((row) => ({ ...row, count: Math.max(0, Number(row.count) || 0) }))
  .filter((row) => row.count > 0))
const total = computed(() => normalized.value.reduce((sum, row) => sum + row.count, 0))
const circumference = 2 * Math.PI * 54
const segments = computed(() => {
  let offset = 0
  return normalized.value.map((row, index) => {
    const fraction = row.count / total.value
    const segment = {
      ...row,
      label: labels[String(row.type).toLowerCase()] || row.type || '其他',
      color: palette[index % palette.length],
      percent: Math.round(fraction * 100),
      dash: `${fraction * circumference} ${circumference}`,
      offset: -offset * circumference,
    }
    offset += fraction
    return segment
  })
})
</script>

<template>
  <div v-if="total" class="donut-layout">
    <div class="donut-chart">
      <svg viewBox="0 0 148 148" role="img" :aria-label="`消息类型分布，共 ${total} 条`">
        <circle class="donut-track" cx="74" cy="74" r="54" />
        <circle
          v-for="segment in segments"
          :key="segment.type"
          data-donut-segment
          class="donut-segment"
          cx="74"
          cy="74"
          r="54"
          :stroke="segment.color"
          :stroke-dasharray="segment.dash"
          :stroke-dashoffset="segment.offset"
        />
      </svg>
      <div class="donut-total"><strong data-donut-total>{{ total }}</strong><span>条消息</span></div>
    </div>
    <div class="donut-legend">
      <div v-for="segment in segments" :key="segment.type">
        <i :style="{ backgroundColor: segment.color }" />
        <span>{{ segment.label }}</span>
        <b>{{ segment.count }}</b>
        <small>{{ segment.percent }}%</small>
      </div>
    </div>
  </div>
  <div v-else class="dashboard-empty dashboard-empty--donut">
    <span class="dashboard-empty__ring" />
    <strong>暂无类型数据</strong>
    <small>收到消息后将自动统计文本、图片、视频和文件。</small>
  </div>
</template>
