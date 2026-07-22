<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Activity,
  BadgeCheck,
  ChartNoAxesCombined,
  ChartPie,
  ListRestart,
  MessageSquareText,
  RefreshCw,
  Route,
  Smartphone,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import DashboardTrendChart from '../components/dashboard/DashboardTrendChart.vue'
import MessageTypeDonut from '../components/dashboard/MessageTypeDonut.vue'
import DataFlowScene from '../components/visual/DataFlowScene.vue'
import MetricStrip from '../components/MetricStrip.vue'
import PageHeader from '../components/PageHeader.vue'
import { useTheme } from '../composables/useTheme'
import { api, errorMessage } from '../lib/api'
import { limitLabel, planLabel, usageNote } from '../lib/entitlements'

type DashboardStats = {
  today_messages?: number
  successful_forwards?: number
  tg_accounts?: number
  active_routes?: number
  trend: Array<{ date: string; received: number; forwarded: number }>
  type_distribution: Array<{ type: string; count: number }>
  recent_activity: Array<{ id: number | string; title: string; created_at: string; status?: string }>
  system_status: {
    telegram_connected?: number
    dingtalk_configured?: number
    runtime_running?: boolean
  }
  quota: {
    today_messages?: number
    message_quota?: number | null
    remaining?: number | null
    usage_percent?: number | null
    is_unlimited?: boolean
  }
}

const emptyStats = (): DashboardStats => ({
  trend: [],
  type_distribution: [],
  recent_activity: [],
  system_status: {},
  quota: {},
})

const loading = ref(false)
const profile = ref<Record<string, any>>({})
const stats = ref<DashboardStats>(emptyStats())
const quota = computed(() => stats.value.quota || {})
const quotaPercent = computed(() => quota.value.is_unlimited ? 0 : Math.min(100, Math.max(0, Number(quota.value.usage_percent) || 0)))
const running = computed(() => Boolean(stats.value.system_status?.runtime_running))
const { theme } = useTheme()

const metrics = computed(() => [
  {
    label: '今日消息',
    value: quota.value.today_messages ?? stats.value.today_messages ?? 0,
    note: `每日配额 ${limitLabel(quota.value.message_quota, quota.value.is_unlimited)}`,
    tone: 'cyan',
    icon: MessageSquareText,
  },
  {
    label: '剩余配额',
    value: limitLabel(quota.value.remaining, quota.value.is_unlimited),
    note: usageNote(quota.value),
    tone: 'green',
    icon: BadgeCheck,
  },
  {
    label: '已连接账号',
    value: stats.value.system_status?.telegram_connected || 0,
    note: `共 ${stats.value.tg_accounts || 0} 个 TG 账号`,
    tone: 'cyan',
    icon: Smartphone,
  },
  {
    label: '活跃映射',
    value: stats.value.active_routes || 0,
    note: `成功转发 ${stats.value.successful_forwards || 0} 条`,
    tone: 'amber',
    icon: Route,
  },
])

async function load() {
  loading.value = true
  try {
    const [profileResponse, statsResponse] = await Promise.all([
      api.get('/tenant/profile'),
      api.get('/forwarding/dashboard'),
    ])
    profile.value = profileResponse.data.data || {}
    stats.value = statsResponse.data.data || emptyStats()
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="仪表盘" :description="`${profile.name || '当前租户'} · ${planLabel(profile)}`">
    <el-button :loading="loading" @click="load"><RefreshCw :size="15" />刷新</el-button>
  </PageHeader>

  <section class="dashboard-signal-field" aria-label="消息网络状态">
    <DataFlowScene variant="dashboard" :theme="theme" quality="low" />
    <div class="signal-field__copy">
      <span>MESSAGE NETWORK</span>
      <strong>{{ running ? '转发网络正在运行' : '转发网络当前停止' }}</strong>
      <small>{{ stats.system_status?.telegram_connected || 0 }} 个 TG 连接 · {{ stats.system_status?.dingtalk_configured || 0 }} 个钉钉目标</small>
    </div>
    <div class="signal-field__stages" aria-hidden="true"><span>RECEIVE</span><i /><span>PROCESS</span><i /><span>DELIVER</span></div>
  </section>

  <MetricStrip :items="metrics" :loading="loading" />

  <section class="dashboard-grid dashboard-grid--analytics" aria-label="消息分析">
    <article class="data-panel trend-panel">
      <header class="panel-title panel-title--dashboard">
        <span><ChartNoAxesCombined :size="17" />消息趋势</span>
        <small>近 7 天</small>
      </header>
      <div v-if="loading && !stats.trend.length" class="dashboard-chart-skeleton is-trend" aria-label="正在加载消息趋势">
        <i v-for="index in 5" :key="index" />
        <span />
      </div>
      <DashboardTrendChart v-else :rows="stats.trend" />
    </article>

    <article class="data-panel type-panel">
      <header class="panel-title panel-title--dashboard">
        <span><ChartPie :size="17" />消息类型分布</span>
        <small>{{ stats.type_distribution.length ? '按消息数量' : '等待数据' }}</small>
      </header>
      <div v-if="loading && !stats.type_distribution.length" class="dashboard-chart-skeleton is-donut" aria-label="正在加载消息类型分布">
        <i /><span /><b /><small />
      </div>
      <MessageTypeDonut v-else :rows="stats.type_distribution" />
    </article>
  </section>

  <section class="dashboard-grid dashboard-grid--operations" aria-label="运行状态">
    <article class="data-panel status-panel">
      <header class="panel-title panel-title--dashboard">
        <span><Activity :size="17" />系统状态</span>
        <em :class="['runtime-badge', running ? 'is-running' : 'is-stopped']">{{ running ? '运行中' : '已停止' }}</em>
      </header>
      <dl class="status-list status-list--dashboard">
        <div>
          <dt>Telegram</dt>
          <dd><span :class="['status-dot', stats.system_status?.telegram_connected ? 'success' : 'danger']" />{{ stats.system_status?.telegram_connected ? '已连接' : '未连接' }}</dd>
        </div>
        <div>
          <dt>钉钉机器人</dt>
          <dd><span :class="['status-dot', stats.system_status?.dingtalk_configured ? 'success' : 'muted']" />{{ stats.system_status?.dingtalk_configured || 0 }} 个已启用</dd>
        </div>
        <div>
          <dt>转发引擎</dt>
          <dd><span :class="['status-dot', running ? 'success' : 'danger']" />{{ running ? '运行中' : '已停止' }}</dd>
        </div>
        <div class="quota-status">
          <dt>消息配额</dt>
          <dd>{{ limitLabel(quota.remaining, quota.is_unlimited) }} / {{ limitLabel(quota.message_quota, quota.is_unlimited) }}</dd>
          <span v-if="!quota.is_unlimited" class="quota-track"><i :style="{ width: `${quotaPercent}%` }" /></span>
          <span v-else class="quota-unlimited">平台资源不受配额限制</span>
        </div>
      </dl>
    </article>

    <article class="data-panel activity-panel">
      <header class="panel-title panel-title--dashboard">
        <span><ListRestart :size="17" />最近动态</span>
        <small>{{ stats.recent_activity.length ? `${stats.recent_activity.length} 条记录` : '暂无记录' }}</small>
      </header>
      <div class="activity-list activity-list--timeline">
        <article v-for="row in stats.recent_activity" :key="row.id">
          <span :class="['activity-marker', row.status === 'success' ? 'is-success' : 'is-muted']" />
          <div><b>{{ row.title }}</b><small>{{ row.created_at }}</small></div>
        </article>
        <div v-if="!stats.recent_activity.length" class="dashboard-empty dashboard-empty--activity">
          <ListRestart :size="22" />
          <strong>系统已就绪</strong>
          <small>完成 TG 配置和转发映射后，运行事件会显示在这里。</small>
        </div>
      </div>
    </article>
  </section>
</template>
