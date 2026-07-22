import type { IncomingMessage, ServerResponse } from 'node:http'
import type { Plugin } from 'vite'

type DemoUser = { id: number; tenant_id: number; username: string; role: string; is_platform_admin: boolean }

const users: Record<string, DemoUser> = {
  admin: { id: 1, tenant_id: 0, username: 'admin', role: 'admin', is_platform_admin: true },
  demo: { id: 1, tenant_id: 0, username: 'demo', role: 'admin', is_platform_admin: true },
  pro: { id: 2, tenant_id: 8, username: 'pro', role: 'owner', is_platform_admin: false },
  viewer: { id: 3, tenant_id: 12, username: 'viewer', role: 'viewer', is_platform_admin: false },
}

const state = {
  telegram: [
    { id: 1, name: '运营频道账号', phone: '+86 138****1024', status: 'connected', enabled: true, created_at: '2026-07-10 09:22' },
  ],
  bots: [
    { id: 1, name: '技术通知群', webhook: 'https://oapi.dingtalk.com/robot/send?access_token=demo', secret: 'SEC-demo', enabled: true },
    { id: 2, name: '运营协同群', webhook: 'https://oapi.dingtalk.com/robot/send?access_token=demo2', secret: '', enabled: true },
  ],
  mappings: [
    { id: 1, source_chat_id: -1001682034001, source_chat_title: 'Telegram 运营频道', target_bot_ids: [1], target_names: ['技术通知群'], translation_enabled: false, filter_enabled: true, enabled: true },
  ],
  filters: [
    { id: 1, name: '屏蔽推广关键词', rule_type: 'keyword', config: { keywords: ['广告', '推广'] }, description: '过滤包含推广词的消息', priority: 10, enabled: true },
  ],
  templates: [
    { id: 1, name: '标准通知模板', template_text: '【{source}】\n{content}\n{time}', time_format: 'YYYY-MM-DD HH:mm:ss', enabled: true, is_default: true },
  ],
  members: [
    { id: 1, username: 'demo_owner', email: 'owner@t2d.demo', role: 'owner', is_active: true, last_login: '2026-07-16 11:36' },
    { id: 2, username: 'operator', email: 'operator@t2d.demo', role: 'member', is_active: true, last_login: '2026-07-16 10:08' },
  ],
  runtime: { running: true, started_at: '2026-07-16 08:30:00', active_accounts: 1, active_routes: 1 },
}

const dashboard = {
  today_messages: 1286,
  successful_forwards: 1249,
  tg_accounts: 1,
  active_routes: 1,
  trend: [
    { date: '07-10', received: 820, forwarded: 801 },
    { date: '07-11', received: 930, forwarded: 912 },
    { date: '07-12', received: 776, forwarded: 754 },
    { date: '07-13', received: 1120, forwarded: 1094 },
    { date: '07-14', received: 986, forwarded: 961 },
    { date: '07-15', received: 1340, forwarded: 1308 },
    { date: '07-16', received: 1286, forwarded: 1249 },
  ],
  type_distribution: [
    { type: 'text', count: 921 }, { type: 'image', count: 248 },
    { type: 'video', count: 82 }, { type: 'file', count: 35 },
  ],
  recent_activity: [
    { id: 1, title: '运营频道消息已投递至钉钉技术群', created_at: '2026-07-16 11:48:26', status: 'success' },
    { id: 2, title: 'TG 账号连接状态已恢复', created_at: '2026-07-16 11:42:08', status: 'success' },
    { id: 3, title: '过滤规则已重新加载', created_at: '2026-07-16 11:31:14', status: 'success' },
  ],
  system_status: { telegram_connected: 1, dingtalk_configured: 2, runtime_running: true },
}

function userFrom(req: IncomingMessage) {
  const token = String(req.headers.authorization || '').replace('Bearer demo-', '')
  return users[token] || users.admin
}

function json(res: ServerResponse, data: unknown, status = 200) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify({ data }))
}

async function body(req: IncomingMessage) {
  const chunks: Buffer[] = []
  for await (const chunk of req) chunks.push(Buffer.from(chunk))
  if (!chunks.length) return {}
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')) } catch { return {} }
}

function listResult(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 }
}

export function demoApiPlugin(): Plugin {
  return {
    name: 't2d-demo-api',
    configureServer(server) {
      server.middlewares.use('/api/v2', async (req, res) => {
        const method = req.method || 'GET'
        const path = String(req.url || '/').split('?')[0]
        const currentUser = userFrom(req)
        const payload = await body(req)

        if (path === '/auth/login' && method === 'POST') {
          const username = String((payload as { username?: string }).username || 'admin')
          const user = users[username]
          if (!user) return json(res, { code: 'INVALID_CREDENTIALS', message: '演示账号不存在' }, 401)
          return json(res, { access_token: `demo-${username}`, user })
        }
        if (path === '/auth/register' && method === 'POST') return json(res, { access_token: 'demo-pro', user: users.pro })
        if (path === '/auth/me') return json(res, currentUser)
        if (path === '/auth/password') return json(res, { updated: true })

        const unlimited = currentUser.is_platform_admin || currentUser.username === 'pro'
        if (path === '/tenant/profile') return json(res, {
          name: currentUser.is_platform_admin ? 'T2D 平台运营' : currentUser.username === 'viewer' ? '观察者测试空间' : '专业版运营团队',
          plan: currentUser.is_platform_admin ? 'enterprise' : currentUser.username === 'viewer' ? 'free' : 'pro',
          is_unlimited: unlimited,
          message_quota: unlimited ? null : 100,
          telegram_limit: unlimited ? null : 1,
          dingtalk_limit: unlimited ? null : 1,
          route_limit: unlimited ? null : 1,
          member_limit: unlimited ? null : 1,
        })
        if (path === '/tenant/usage') return json(res, { today_messages: currentUser.username === 'viewer' ? 18 : 1286, message_quota: unlimited ? null : 100, remaining: unlimited ? null : 82, usage_percent: unlimited ? null : 18, is_unlimited: unlimited })
        if (path === '/tenant/members' && method === 'GET') return json(res, state.members)
        if (path.startsWith('/tenant/members/')) return json(res, { updated: true })
        if (path === '/tenant/members') return json(res, { id: Date.now(), ...payload })

        if (path === '/forwarding/dashboard') return json(res, {
          ...dashboard,
          tg_accounts: currentUser.username === 'viewer' ? 1 : dashboard.tg_accounts,
          active_routes: currentUser.username === 'viewer' ? 1 : dashboard.active_routes,
          quota: { today_messages: currentUser.username === 'viewer' ? 18 : 1286, message_quota: unlimited ? null : 100, remaining: unlimited ? null : 82, usage_percent: unlimited ? null : 18, is_unlimited: unlimited },
        })
        if (path === '/forwarding/runtime' && method === 'GET') return json(res, state.runtime)
        if (/^\/forwarding\/runtime\/(start|stop)$/.test(path)) {
          state.runtime.running = path.endsWith('/start')
          return json(res, state.runtime)
        }
        if (path.startsWith('/forwarding/records')) return json(res, listResult([
          { id: 1042, source_title: 'Telegram 运营频道', target_name: '技术通知群', message_type: 'text', status: 'success', created_at: '2026-07-16 11:48:26', error_message: '' },
          { id: 1041, source_title: 'Telegram 运营频道', target_name: '技术通知群', message_type: 'image', status: 'success', created_at: '2026-07-16 11:46:03', error_message: '' },
        ]))
        if (path === '/forwarding/routes' && method === 'GET') return json(res, state.mappings)
        if (path.startsWith('/forwarding/routes')) return json(res, { id: Date.now(), ...payload })

        if (path === '/connectors/telegram/accounts' && method === 'GET') return json(res, state.telegram)
        if (path.startsWith('/connectors/telegram/accounts')) return json(res, { id: Date.now(), status: 'pending', ...payload })
        if (path === '/connectors/dingtalk/bots' && method === 'GET') return json(res, state.bots)
        if (path.startsWith('/connectors/dingtalk/bots')) return json(res, { id: Date.now(), ...payload })
        if (path === '/forwarding/mappings' && method === 'GET') return json(res, state.mappings)
        if (path.startsWith('/forwarding/mappings')) return json(res, { id: Date.now(), ...payload })

        if (path === '/policies/filters' && method === 'GET') return json(res, state.filters)
        if (path === '/policies/filters/test') return json(res, { should_filter: String((payload as { text?: string }).text || '').includes('广告'), reason: '命中推广关键词' })
        if (path.startsWith('/policies/filters')) return json(res, { id: Date.now(), ...payload })
        if (path === '/policies/templates' && method === 'GET') return json(res, state.templates)
        if (path === '/policies/templates/preview') return json(res, { preview: '【Telegram 运营频道】\n这是一条模板预览消息\n2026-07-16 12:00:00' })
        if (path.startsWith('/policies/templates')) return json(res, { id: Date.now(), ...payload })
        if (path === '/policies/media' && method === 'GET') return json(res, { enabled: true, max_file_size_mb: 20, allowed_types: ['image', 'video', 'document'], link_fallback: true })
        if (path === '/policies/media/test') return json(res, { allowed: true, reason: '' })
        if (path === '/policies/translation' && method === 'GET') return json(res, { enabled: false, target_language: 'zh-CN', provider: 'google' })
        if (path.startsWith('/policies/')) return json(res, { saved: true, ...payload })

        if (path.startsWith('/audit/') && path !== '/audit/summary' && path !== '/audit/export') return json(res, listResult([
          { id: 1, action: 'forwarding.start', username: currentUser.username, status: 'success', ip_address: '127.0.0.1', created_at: '2026-07-16 11:40:16', method: 'POST', path: '/forwarding/runtime/start', duration_ms: 42 },
          { id: 2, action: 'mapping.update', username: currentUser.username, status: 'success', ip_address: '127.0.0.1', created_at: '2026-07-16 11:31:08', method: 'PUT', path: '/forwarding/mappings/1', duration_ms: 31 },
        ]))
        if (path === '/audit/summary') return json(res, { operations: 28, logins: 6, requests: 184, failures: 2 })
        if (path === '/audit/export') {
          res.statusCode = 200
          res.setHeader('Content-Type', 'text/csv; charset=utf-8')
          return res.end('time,user,action,status\n2026-07-16 11:40:16,admin,forwarding.start,success\n')
        }

        if (path === '/platform/stats') return json(res, { total_tenants: 18, active_users: 46, today_messages: 18420, active_subscriptions: 13 })
        if (path === '/platform/tenants' && method === 'GET') return json(res, [
          { id: 12, name: '华东运营中心', slug: 'east-ops', user_count: 5, plan: 'pro', status: 'active', created_at: '2026-07-08T08:24:00Z' },
          { id: 16, name: '海外业务测试组', slug: 'global-lab', user_count: 2, plan: 'free', status: 'active', created_at: '2026-07-12T13:10:00Z' },
        ])
        if (/^\/platform\/tenants\/\d+\/members$/.test(path) && method === 'GET') return json(res, state.members)
        if (path.startsWith('/platform/tenants/')) return json(res, { updated: true, ...payload })

        return json(res, { ok: true, ...payload })
      })
    },
  }
}
