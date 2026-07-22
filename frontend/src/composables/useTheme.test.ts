// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { useTheme } from './useTheme'

describe('useTheme', () => {
  it('falls back to dark mode when the stored value is invalid', () => {
    localStorage.setItem('t2d_theme', 'unknown')
    const { theme, applyTheme } = useTheme()
    applyTheme()
    expect(theme.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('toggles and persists both supported themes', () => {
    localStorage.setItem('t2d_theme', 'dark')
    const { theme, toggleTheme, themeToggleLabel } = useTheme()
    toggleTheme()
    expect(theme.value).toBe('light')
    expect(localStorage.getItem('t2d_theme')).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(themeToggleLabel.value).toContain('深色')
  })
})
