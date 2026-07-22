import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const view = (name: string) => readFileSync(resolve(__dirname, 'views', name), 'utf8')

describe('restored original modules', () => {
  it('renders the original dashboard sections from the aggregate endpoint', () => {
    const source = view('DashboardView.vue')
    expect(source).toContain('/forwarding/dashboard')
    expect(source).toContain('stats.trend')
    expect(source).toContain('stats.type_distribution')
    expect(source).toContain('stats.system_status')
    expect(source).toContain('最近动态')
    expect(source).toContain('profileResponse.data.data || {}')
    expect(source).toContain('statsResponse.data.data || emptyStats()')
    expect(source).toContain('DashboardTrendChart')
    expect(source).toContain('MessageTypeDonut')
    expect(source).toContain('dashboard-chart-skeleton')
  })

  it.each([
    ['TelegramAccountsView.vue', '/connectors/telegram/accounts', 'Telegram 账号'],
    ['DingTalkBotsView.vue', '/connectors/dingtalk/bots', '钉钉机器人'],
    ['ForwardingMappingsView.vue', '/forwarding/routes', '转发映射'],
    ['ForwardingControlView.vue', '/forwarding/runtime', '转发控制'],
    ['ForwardingRecordsView.vue', '/forwarding/records', '转发记录'],
    ['AuditView.vue', '/audit/', '审计日志'],
    ['FilterRulesView.vue', '/policies/filters', '过滤规则'],
    ['MessageTemplatesView.vue', '/policies/templates', '消息模板'],
    ['MediaConfigView.vue', '/policies/media', '媒体配置'],
  ])('%s uses the V2 domain endpoint for %s', (file, endpoint, title) => {
    const source = view(file)
    expect(source).toContain(endpoint)
    expect(source).toContain(title)
  })

  it('keeps translation and password changes in system settings without duplicating filters', () => {
    const source = view('SystemSettingsView.vue')
    expect(source).toContain('/policies/translation')
    expect(source).toContain('/auth/password')
    expect(source).not.toContain('/policies/filters')
  })

  it('restores login and tenant registration tabs', () => {
    const source = view('LoginView.vue')
    expect(source).toContain("mode === 'login'")
    expect(source).toContain('创建新团队账户')
    expect(source).toContain('auth.register')
  })
})
