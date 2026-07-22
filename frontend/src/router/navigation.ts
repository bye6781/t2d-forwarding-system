import type { Component } from 'vue'
import {
  Activity, Bot, Cable, FileClock, FileText, Filter, Image, LayoutDashboard,
  Link, ListChecks, Settings2, ShieldCheck, Users,
} from 'lucide-vue-next'

export interface NavigationItem { key: string; label: string; path: string; icon: Component }
export interface NavigationGroup { label: string; items: NavigationItem[] }
export interface NavigationUser { role: string; is_platform_admin: boolean }

const tenantGroups: NavigationGroup[] = [
  { label: '概览', items: [
    { key: 'dashboard', label: '仪表盘', path: '/dashboard', icon: LayoutDashboard },
  ] },
  { label: '配置管理', items: [
    { key: 'telegram', label: 'Telegram 账号', path: '/telegram', icon: Cable },
    { key: 'dingtalk', label: '钉钉机器人', path: '/dingtalk', icon: Bot },
    { key: 'mappings', label: '转发映射', path: '/mappings', icon: Link },
  ] },
  { label: '运行管理', items: [
    { key: 'forwarding', label: '转发控制', path: '/forwarding', icon: Activity },
    { key: 'records', label: '转发记录', path: '/records', icon: ListChecks },
  ] },
  { label: '高级功能', items: [
    { key: 'audit', label: '审计日志', path: '/audit', icon: FileClock },
    { key: 'filters', label: '过滤规则', path: '/filters', icon: Filter },
    { key: 'templates', label: '消息模板', path: '/templates', icon: FileText },
    { key: 'media', label: '媒体配置', path: '/media', icon: Image },
  ] },
  { label: '团队与订阅', items: [
    { key: 'organization', label: '组织与计费', path: '/organization', icon: Users },
  ] },
]

const systemGroup: NavigationGroup = {
  label: '系统', items: [{ key: 'settings', label: '系统设置', path: '/settings', icon: Settings2 }],
}

export function buildNavigation(user: NavigationUser | null | undefined): NavigationGroup[] {
  if (user?.role === 'viewer' && !user.is_platform_admin) {
    const allowed = new Set(['dashboard', 'telegram', 'dingtalk', 'mappings'])
    return tenantGroups
      .map((group) => ({ ...group, items: group.items.filter((item) => allowed.has(item.key)) }))
      .filter((group) => group.items.length > 0)
  }
  const navigation = tenantGroups.map((group) => ({ ...group, items: [...group.items] }))
  if (user?.is_platform_admin) {
    navigation.push({
      label: '平台', items: [{ key: 'platform', label: '平台管理', path: '/platform', icon: ShieldCheck }],
    })
  }
  navigation.push({ ...systemGroup, items: [...systemGroup.items] })
  return navigation
}
