// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MessageTypeDonut from './MessageTypeDonut.vue'

describe('MessageTypeDonut', () => {
  it('renders the total and a count-aware legend for each message type', () => {
    const wrapper = mount(MessageTypeDonut, {
      props: {
        rows: [
          { type: 'text', count: 12 },
          { type: 'photo', count: 6 },
          { type: 'video', count: 2 },
        ],
      },
    })

    expect(wrapper.get('svg').attributes('aria-label')).toContain('消息类型分布，共 20 条')
    expect(wrapper.findAll('[data-donut-segment]')).toHaveLength(3)
    expect(wrapper.get('[data-donut-total]').text()).toBe('20')
    expect(wrapper.text()).toContain('文本消息')
    expect(wrapper.text()).toContain('60%')
    expect(wrapper.text()).toContain('图片')
  })

  it('renders an informative empty state instead of an empty ring', () => {
    const wrapper = mount(MessageTypeDonut, { props: { rows: [] } })

    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.text()).toContain('暂无类型数据')
  })
})
