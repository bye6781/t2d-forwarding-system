import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const path = (file: string) => resolve(__dirname, file)
const source = (file: string) => existsSync(path(file)) ? readFileSync(path(file), 'utf8') : ''

describe('future command network visual system', () => {
  it('provides a reusable Three.js data-flow scene contract', () => {
    const component = source('components/visual/DataFlowScene.vue')
    expect(component).toContain("variant: 'login' | 'dashboard'")
    expect(component).toContain("quality: 'auto' | 'high' | 'low'")
    expect(component).toContain('reducedMotion')
    expect(component).toContain("import('three')")
    expect(component).toContain('dispose')
    expect(component).toContain('visibilitychange')
  })

  it('replaces the legacy login route with the full-bleed scene and local fallbacks', () => {
    const login = source('views/LoginView.vue')
    const styles = source('styles/login.css')
    expect(login).toContain('<DataFlowScene')
    expect(login).not.toContain('route-packet')
    expect(styles).toContain('data-flow-poster-dark.webp')
    expect(styles).toContain('data-flow-poster-light.webp')
    expect(styles).toContain('.login-scene-copy')
  })

  it('uses the lightweight scene on the dashboard without changing its analytics structure', () => {
    const dashboard = source('views/DashboardView.vue')
    expect(dashboard).toContain('dashboard-signal-field')
    expect(dashboard).toContain('variant="dashboard"')
    expect(dashboard).toContain('dashboard-grid--analytics')
    expect(dashboard).toContain('dashboard-grid--operations')
  })

  it('adds route transitions and a restrained live-line signal to the shell', () => {
    const shell = source('layouts/AppShell.vue')
    expect(shell).toContain('network-state')
    expect(shell).toContain('<router-view v-slot')
    expect(shell).toContain('<Transition name="route-shift"')
  })

  it('keeps mobile WebGL-free and centralizes the motion layer', () => {
    const styles = source('styles/responsive.css')
    const entry = source('styles/index.css')
    expect(styles).toContain('.data-flow-canvas')
    expect(styles).toContain('display: none')
    expect(entry).toContain("@import './motion.css'")
    expect(source('styles/motion.css')).toContain('prefers-reduced-motion')
  })
})
