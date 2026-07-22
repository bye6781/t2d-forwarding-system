import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const viewerPaths = new Set([
  '/dashboard', '/telegram', '/dingtalk', '/mappings',
  '/connectors', '/connectors/telegram', '/connectors/dingtalk', '/routes',
])

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/', component: () => import('../layouts/AppShell.vue'), children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '仪表盘' } },
      { path: 'telegram', component: () => import('../views/TelegramAccountsView.vue'), meta: { title: 'Telegram 账号' } },
      { path: 'dingtalk', component: () => import('../views/DingTalkBotsView.vue'), meta: { title: '钉钉机器人' } },
      { path: 'mappings', component: () => import('../views/ForwardingMappingsView.vue'), meta: { title: '转发映射' } },
      { path: 'forwarding', component: () => import('../views/ForwardingControlView.vue'), meta: { title: '转发控制' } },
      { path: 'records', component: () => import('../views/ForwardingRecordsView.vue'), meta: { title: '转发记录' } },
      { path: 'audit', component: () => import('../views/AuditView.vue'), meta: { title: '审计日志' } },
      { path: 'filters', component: () => import('../views/FilterRulesView.vue'), meta: { title: '过滤规则' } },
      { path: 'templates', component: () => import('../views/MessageTemplatesView.vue'), meta: { title: '消息模板' } },
      { path: 'media', component: () => import('../views/MediaConfigView.vue'), meta: { title: '媒体配置' } },
      { path: 'organization', component: () => import('../views/OrganizationView.vue'), meta: { title: '组织与计费' } },
      { path: 'platform', component: () => import('../views/PlatformView.vue'), meta: { title: '平台管理', platform: true } },
      { path: 'settings', component: () => import('../views/SystemSettingsView.vue'), meta: { title: '系统设置' } },
      { path: 'connectors', redirect: (to) => to.query.tab === 'dingtalk' ? '/dingtalk' : '/telegram' },
      { path: 'connectors/telegram', redirect: '/telegram' },
      { path: 'connectors/dingtalk', redirect: '/dingtalk' },
      { path: 'routes', redirect: '/mappings' },
      { path: 'runtime', redirect: '/forwarding' },
      { path: 'policies', redirect: '/filters' },
    ] },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return auth.authenticated ? '/dashboard' : true
  if (!auth.authenticated) return '/login'
  if (!auth.user && !(await auth.restore())) return '/login'
  if (to.meta.platform && !auth.user?.is_platform_admin) return '/dashboard'
  if (auth.user?.role === 'viewer' && !auth.user.is_platform_admin && !viewerPaths.has(to.path)) return '/dashboard'
  if (to.path === '/dashboard' && auth.user?.is_platform_admin && to.redirectedFrom?.path === '/') return '/platform'
  return true
})

export default router
