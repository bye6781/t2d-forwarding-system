import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = (path: string) => readFileSync(resolve(__dirname, path), 'utf8')

describe('phase one visual system', () => {
  it('loads Geist and the modular style entrypoint', () => {
    const main = source('main.ts')
    expect(main).toContain("@fontsource-variable/geist")
    expect(main).toContain("./styles/index.css")
  })

  it('separates theme, shell, component, Element Plus, login, and dashboard styles', () => {
    for (const file of [
      'styles/tokens.css',
      'styles/base.css',
      'styles/shell.css',
      'styles/components.css',
      'styles/element-plus.css',
      'styles/login.css',
      'styles/dashboard.css',
      'styles/responsive.css',
    ]) expect(existsSync(resolve(__dirname, file))).toBe(true)
  })

  it('defines complete dark and light semantic surface tokens', () => {
    const tokens = source('styles/tokens.css')
    expect(tokens).toContain(':root[data-theme="dark"]')
    expect(tokens).toContain(':root[data-theme="light"]')
    for (const token of ['--app-canvas', '--app-surface', '--app-surface-raised', '--app-input', '--app-border', '--app-accent']) {
      expect(tokens.match(new RegExp(token, 'g'))?.length).toBeGreaterThanOrEqual(2)
    }
  })

  it('keeps the shell accessible and theme-aware', () => {
    const shell = source('layouts/AppShell.vue')
    const login = source('views/LoginView.vue')
    expect(shell).toContain('skip-link')
    expect(shell).toContain('useTheme')
    expect(shell).toContain(':aria-label="themeToggleLabel"')
    expect(login).toContain('useTheme')
    expect(login).toContain('login-theme-toggle')
  })

  it('switches to the mobile shell at the required tablet viewport', () => {
    expect(source('styles/responsive.css')).toContain('@media (max-width: 768px)')
  })

  it('uses the reusable data-flow scene to explain the forwarding value', () => {
    const login = source('views/LoginView.vue')
    const styles = source('styles/login.css')
    expect(login).toContain('<DataFlowScene')
    expect(login).toContain('让消息穿越平台')
    expect(login).toContain('login-scene-stages')
    expect(login).not.toContain('route-packet')
    expect(styles).toContain('.login-scene-copy')
    expect(styles).toContain('data-flow-poster-dark.webp')
    expect(source('styles/responsive.css')).toContain('.data-flow-canvas')
  })
})
