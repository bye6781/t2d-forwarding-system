import { describe, expect, it } from 'vitest'
import { errorMessage } from './api'

describe('API errors', () => {
  it('reads the V2 structured error message', () => {
    expect(errorMessage({ response: { data: { detail: { code: 'x', message: '租户不存在' } } } })).toBe('租户不存在')
  })

  it('falls back to a stable generic message', () => {
    expect(errorMessage(new Error('network'))).toBe('请求失败，请稍后重试')
  })
})
