import { flushPromises, mount } from '@vue/test-utils'
import CardFace from './CardFace.vue'
import eventFrontSource from '../../image/card-event-front.svg?raw'
import type { CardView } from '../types'

const eventCard: CardView = {
  instanceId: 'PE-05#1',
  cardId: 'PE-05',
  name: '全球央行联合购金',
  kind: 'public',
  category: '一次性事件',
  strength: '危机',
  subtype: '单商品一次性上涨',
  targetLabel: '黄金',
  timing: '翻牌阶段',
  text: '黄金现货上涨 3 格，然后弃置。',
  durationText: '本月翻开时立即结算；不跨月',
  keywords: ['单次', '危机'],
}

describe('crazy futures card face', () => {
  it('renders only the workbook title on the event face', () => {
    const wrapper = mount(CardFace, {
      props: { card: eventCard, kind: 'event' },
    })

    expect(wrapper.get('.card-title').text()).toBe('全球央行联合购金')
    expect(wrapper.get('.card-title').text()).not.toContain('上涨 3 格')
    expect(wrapper.get('img').attributes('src')).toContain('card-event-front')
    expect(eventFrontSource).not.toContain('在此填写标题')
    expect(eventFrontSource).not.toContain('在此填写现货价格变化')
  })

  it('shows the complete rule text when the card is hovered', async () => {
    const wrapper = mount(CardFace, {
      attachTo: document.body,
      props: { card: eventCard, kind: 'event' },
    })

    await wrapper.trigger('mouseenter')
    await flushPromises()

    const detail = document.body.querySelector('.card-detail-popover')
    expect(detail?.textContent).toContain('全球央行联合购金')
    expect(detail?.textContent).toContain('黄金现货上涨 3 格，然后弃置。')
    expect(detail?.textContent).toContain('本月翻开时立即结算；不跨月')

    await wrapper.trigger('mouseleave')
    await flushPromises()
    expect(document.body.querySelector('.card-detail-popover')).toBeNull()
    wrapper.unmount()
  })
})
