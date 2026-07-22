import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = (file: string) => readFileSync(resolve(__dirname, file), 'utf8')

describe('modular dual-theme visual system', () => {
  it('uses layered surfaces and a cyan accent in both themes', () => {
    const tokens = source('styles/tokens.css')
    const components = [
      source('styles/dashboard.css'),
      source('styles/login.css'),
      source('styles/shell.css'),
    ].join('\n')

    expect(tokens).toContain(':root[data-theme="dark"]')
    expect(tokens).toContain(':root[data-theme="light"]')
    expect(tokens).toContain('--app-accent: #12a8e8')
    expect(tokens).toContain('--content-bg: var(--app-canvas)')
    expect(tokens).toContain('--card-bg: var(--app-surface)')
    expect(components).toContain('.dashboard-grid')
    expect(components).toContain('.flow-chart')
    expect(components).toContain('.donut-layout')
    expect(components).toContain('.login-tabs')
  })

  it('keeps the restored shell and newest organization/platform modules in one theme', () => {
    const shell = source('layouts/AppShell.vue')
    expect(shell).toContain('T2D Cloud')
    expect(shell).toContain('buildNavigation')
    expect(shell).toContain('theme-toggle')
    expect(source('views/OrganizationView.vue')).toContain('组织与计费')
    expect(source('views/PlatformView.vue')).toContain('平台管理')
  })
})
