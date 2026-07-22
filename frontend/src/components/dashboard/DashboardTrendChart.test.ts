// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DashboardTrendChart from './DashboardTrendChart.vue'

const trend = [
  { date: '2026-07-10', received: 12, forwarded: 9 },
  { date: '2026-07-11', received: 28, forwarded: 24 },
  { date: '2026-07-12', received: 18, forwarded: 16 },
  { date: '2026-07-13', received: 44, forwarded: 39 },
  { date: '2026-07-14', received: 31, forwarded: 27 },
  { date: '2026-07-15', received: 53, forwarded: 48 },
  { date: '2026-07-16', received: 37, forwarded: 34 },
]

describe('DashboardTrendChart', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders two message-flow series and all seven date labels', () => {
    const wrapper = mount(DashboardTrendChart, { props: { rows: trend } })

    expect(wrapper.get('svg').attributes('aria-label')).toContain('近 7 天消息趋势')
    expect(wrapper.find('[data-series="received"]').exists()).toBe(true)
    expect(wrapper.find('[data-series="forwarded"]').exists()).toBe(true)
    expect(wrapper.findAll('[data-date-label]')).toHaveLength(7)
    expect(wrapper.text()).toContain('接收消息')
    expect(wrapper.text()).toContain('转发成功')
  })

  it('keeps a clear empty state when no trend data exists', () => {
    const wrapper = mount(DashboardTrendChart, { props: { rows: [] } })

    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.text()).toContain('暂无消息趋势')
  })

  it('recalculates chart geometry for a narrow container', async () => {
    class ResizeObserverStub {
      constructor(private callback: ResizeObserverCallback) {}
      observe() {
        this.callback([{ contentRect: { width: 340 } } as ResizeObserverEntry], this as unknown as ResizeObserver)
      }
      disconnect() {}
      unobserve() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)

    const wrapper = mount(DashboardTrendChart, { props: { rows: trend } })
    await nextTick()

    expect(wrapper.get('svg').attributes('viewBox')).toBe('0 0 340 248')
  })

  it('keeps responsive geometry when data arrives after the empty state', async () => {
    class ResizeObserverStub {
      constructor(private callback: ResizeObserverCallback) {}
      observe() {
        this.callback([{ contentRect: { width: 340 } } as ResizeObserverEntry], this as unknown as ResizeObserver)
      }
      disconnect() {}
      unobserve() {}
    }
    vi.stubGlobal('ResizeObserver', ResizeObserverStub)

    const wrapper = mount(DashboardTrendChart, { props: { rows: [] } })
    await wrapper.setProps({ rows: trend })

    expect(wrapper.get('svg').attributes('viewBox')).toBe('0 0 340 248')
  })
})
