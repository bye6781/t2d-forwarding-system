import { describe, expect, it } from 'vitest'
import { limitLabel, planLabel, usageNote } from './entitlements'

describe('entitlement formatting', () => {
  it('renders unlimited platform values as infinity', () => {
    expect(limitLabel(null, true)).toBe('∞')
    expect(planLabel({ plan: 'free', is_unlimited: true })).toBe('平台无限')
    expect(usageNote({ usage_percent: null, is_unlimited: true })).toBe('不限制')
  })

  it('labels the professional plan as unlimited and priced at 19800', () => {
    expect(planLabel({ plan: 'pro', is_unlimited: true })).toBe('专业版无限')
    expect(limitLabel(null, true)).toBe('∞')
  })

  it('keeps normal tenant values numeric', () => {
    expect(limitLabel(75, false)).toBe('75')
    expect(planLabel({ plan: 'free', is_unlimited: false })).toBe('free')
    expect(usageNote({ usage_percent: 25, is_unlimited: false })).toBe('25% 已使用')
  })
})
