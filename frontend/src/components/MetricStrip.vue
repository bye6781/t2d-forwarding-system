<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  items: Array<{ label: string; value: string | number; note?: string; tone?: string; icon?: Component }>
  loading?: boolean
}>()
</script>

<template>
  <section :class="['metric-strip', { 'is-loading': loading }]" aria-label="关键指标" aria-live="polite">
    <article v-for="item in items" :key="item.label" :class="['metric-item', `is-${item.tone || 'cyan'}`]">
      <div class="metric-copy">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </div>
      <component :is="item.icon" v-if="item.icon" class="metric-icon" :size="36" :stroke-width="1.4" aria-hidden="true" />
    </article>
  </section>
</template>
