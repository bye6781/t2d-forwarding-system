import { api } from '../../lib/api'

export interface TelegramConfig {
  id: number
  name: string
  phone: string
  is_authorized: boolean
  connected: boolean
}

export interface TelegramConfigCreate {
  name: string
  api_id: number
  api_hash: string
  phone: string
}

export interface DingTalkConfig {
  id: number
  name: string
  webhook: string
  secret?: string
  enabled: boolean
}

export interface DingTalkConfigWrite {
  name: string
  webhook: string
  secret: string
  enabled: boolean
}

export const connectorApi = {
  async telegramConfigs(): Promise<TelegramConfig[]> {
    return (await api.get('/connectors/telegram/accounts')).data.data
  },
  async createTelegram(payload: TelegramConfigCreate) {
    return (await api.post('/connectors/telegram/accounts', payload)).data.data
  },
  async sendTelegramCode(id: number) {
    return api.post(`/connectors/telegram/accounts/${id}/send-code`, {})
  },
  async verifyTelegram(id: number, code: string, password: string | null) {
    return api.post(`/connectors/telegram/accounts/${id}/verify`, { code, password })
  },
  async disconnectTelegram(id: number) {
    return api.post(`/connectors/telegram/accounts/${id}/disconnect`, {})
  },
  async deleteTelegram(id: number) {
    return api.delete(`/connectors/telegram/accounts/${id}`)
  },
  async dingTalkConfigs(): Promise<DingTalkConfig[]> {
    return (await api.get('/connectors/dingtalk/bots')).data.data
  },
  async createDingTalk(payload: DingTalkConfigWrite) {
    return (await api.post('/connectors/dingtalk/bots', payload)).data.data
  },
  async updateDingTalk(id: number, payload: DingTalkConfigWrite) {
    return (await api.put(`/connectors/dingtalk/bots/${id}`, payload)).data.data
  },
  async testDingTalk(id: number) {
    return api.post(`/connectors/dingtalk/bots/${id}/test`, { message: 'T2D Cloud 测试消息' })
  },
  async deleteDingTalk(id: number) {
    return api.delete(`/connectors/dingtalk/bots/${id}`)
  },
}
