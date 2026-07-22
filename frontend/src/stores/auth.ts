import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../lib/api'

export interface SessionUser {
  id: number
  tenant_id: number
  username: string
  email?: string
  role: string
  is_platform_admin: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('t2d_token') || '')
  const user = ref<SessionUser | null>(null)
  const authenticated = computed(() => Boolean(token.value))

  async function login(username: string, password: string) {
    const response = await api.post('/auth/login', { username, password })
    token.value = response.data.data.access_token
    user.value = response.data.data.user
    localStorage.setItem('t2d_token', token.value)
  }

  async function register(tenant_name: string, username: string, password: string, email?: string) {
    const response = await api.post('/auth/register', { tenant_name, username, password, email: email || null })
    token.value = response.data.data.access_token
    user.value = response.data.data.user
    localStorage.setItem('t2d_token', token.value)
  }

  async function restore() {
    if (!token.value) return false
    try {
      const response = await api.get('/auth/me')
      user.value = response.data.data
      return true
    } catch {
      logout()
      return false
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('t2d_token')
  }

  return { token, user, authenticated, login, register, restore, logout }
})
