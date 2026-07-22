import axios from 'axios'

export interface ApiEnvelope<T> { data: T }
export interface PageData<T> { items: T[]; total: number; limit: number; offset: number }

export const api = axios.create({ baseURL: '/api/v2', timeout: 30000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('t2d_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) window.dispatchEvent(new Event('t2d:unauthorized'))
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  const value = error as { response?: { data?: { detail?: { message?: string } | string } } }
  const detail = value?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return '请求失败，请稍后重试'
}
