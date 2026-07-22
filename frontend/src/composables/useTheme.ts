import { computed, ref } from 'vue'

export type ThemeMode = 'dark' | 'light'

function storedTheme(): ThemeMode {
  const value = localStorage.getItem('t2d_theme')
  return value === 'light' || value === 'dark' ? value : 'dark'
}

export function useTheme() {
  const theme = ref<ThemeMode>(storedTheme())
  const themeToggleLabel = computed(() => theme.value === 'dark' ? '切换到浅色主题' : '切换到深色主题')

  function applyTheme() {
    document.documentElement.dataset.theme = theme.value
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('t2d_theme', theme.value)
    applyTheme()
  }

  return { theme, themeToggleLabel, applyTheme, toggleTheme }
}
