import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TimeRangeSelector from '@/components/common/TimeRangeSelector.vue'

describe('TimeRangeSelector', () => {
  it('renders all 5 range options', () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(5)
    const labels = buttons.map((b) => b.text())
    expect(labels).toContain('7d')
    expect(labels).toContain('30d')
    expect(labels).toContain('90d')
    expect(labels).toContain('1y')
    expect(labels).toContain('All')
  })

  it('emits update:modelValue with "7d" when 7d button clicked', async () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const button = wrapper.findAll('button').find((b) => b.text() === '7d')
    await button!.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['7d'])
  })

  it('emits update:modelValue with "90d" when 90d button clicked', async () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const button = wrapper.findAll('button').find((b) => b.text() === '90d')
    await button!.trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['90d'])
  })

  it('emits update:modelValue with "1y" when 1y button clicked', async () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const button = wrapper.findAll('button').find((b) => b.text() === '1y')
    await button!.trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['1y'])
  })

  it('emits update:modelValue with "all" when All button clicked', async () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const button = wrapper.findAll('button').find((b) => b.text() === 'All')
    await button!.trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['all'])
  })

  it('marks the active range button', () => {
    const wrapper = mount(TimeRangeSelector, {
      props: { modelValue: '30d' },
    })
    const buttons = wrapper.findAll('button')
    const activeButton = buttons.find((b) => b.text() === '30d')
    expect(activeButton!.classes()).toContain('active')
  })

  it('has 30d as default when no modelValue provided', () => {
    const wrapper = mount(TimeRangeSelector)
    // Check that 30d button is visually marked active
    const buttons = wrapper.findAll('button')
    const thirtyDayBtn = buttons.find((b) => b.text() === '30d')
    expect(thirtyDayBtn!.classes()).toContain('active')
  })
})
