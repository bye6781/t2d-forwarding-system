export interface EntitlementSummary {
  plan?: string
  role?: string
  is_platform_admin?: boolean
  is_unlimited?: boolean
  usage_percent?: number | null
}

export function limitLabel(value: number | null | undefined, isUnlimited = false): string {
  return isUnlimited ? '∞' : String(value ?? 0)
}

export function planLabel(summary: EntitlementSummary): string {
  if (!summary.is_unlimited) return summary.plan || 'free'
  if (summary.is_platform_admin || (!summary.role && summary.plan === 'free')) return '平台无限'
  if (summary.plan === 'pro') return '专业版无限'
  if (summary.plan === 'enterprise') return '企业版无限'
  return '管理员无限'
}

export function usageNote(summary: EntitlementSummary): string {
  return summary.is_unlimited ? '不限制' : `${summary.usage_percent ?? 0}% 已使用`
}

export function planPrice(plan: string): string {
  if (plan === 'pro') return '¥19,800'
  if (plan === 'free') return '免费'
  return '联系平台管理员'
}
