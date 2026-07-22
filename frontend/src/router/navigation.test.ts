import { describe, expect, it } from 'vitest'
import { buildNavigation } from './navigation'

describe('navigation permissions', () => {
  it('keeps all restored business modules for platform administrators', () => {
    const keys = buildNavigation({ role: 'owner', is_platform_admin: true })
      .flatMap((group) => group.items.map((item) => item.key))
    expect(keys).toEqual([
      'dashboard', 'telegram', 'dingtalk', 'mappings', 'forwarding', 'records',
      'audit', 'filters', 'templates', 'media', 'organization', 'platform', 'settings',
    ])
  })

  it('does not expose platform navigation to tenant users', () => {
    const keys = buildNavigation({ role: 'member', is_platform_admin: false })
      .flatMap((group) => group.items.map((item) => item.key))
    expect(keys).not.toContain('platform')
    expect(keys).toContain('telegram')
    expect(keys).toContain('settings')
  })

  it('restores the original module names and independent paths', () => {
    const items = buildNavigation({ role: 'member', is_platform_admin: false })
      .flatMap((group) => group.items)
    expect(items.find((item) => item.key === 'telegram')).toMatchObject({ label: 'Telegram 账号', path: '/telegram' })
    expect(items.find((item) => item.key === 'dingtalk')).toMatchObject({ label: '钉钉机器人', path: '/dingtalk' })
    expect(items.find((item) => item.key === 'mappings')).toMatchObject({ label: '转发映射', path: '/mappings' })
    expect(items.find((item) => item.key === 'forwarding')).toMatchObject({ label: '转发控制', path: '/forwarding' })
    expect(items.find((item) => item.key === 'records')).toMatchObject({ label: '转发记录', path: '/records' })
  })

  it('only exposes test connectors and mappings to viewers', () => {
    const keys = buildNavigation({ role: 'viewer', is_platform_admin: false })
      .flatMap((group) => group.items.map((item) => item.key))
    expect(keys).toEqual(['dashboard', 'telegram', 'dingtalk', 'mappings'])
  })
})
