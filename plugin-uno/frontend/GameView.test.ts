import { flushPromises, mount } from '@vue/test-utils'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async () => true),
  rapidAction: vi.fn(async () => true),
  restart: vi.fn(async () => true),
  publishSpectatorFrame: vi.fn(() => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
}))

function snapshot(gameOverrides: Record<string, unknown> = {}): ArcadeSnapshot {
  return {
    revision: 1,
    phase: 'playing',
    roundNumber: 1,
    self: { id: 'p1', name: '玩家一' },
    viewer: { mode: 'player' },
    players: [
      { id: 'p1', name: '玩家一' },
      { id: 'p2', name: '玩家二' },
      { id: 'p3', name: '玩家三' },
    ],
    actions: { canAct: true, canRestart: false },
    game: {
      colors: [
        { id: 'red', label: '赤红' },
        { id: 'yellow', label: '琥珀' },
        { id: 'green', label: '翠绿' },
        { id: 'blue', label: '湛蓝' },
      ],
      turnOrder: ['p1', 'p2', 'p3'],
      currentPlayerId: 'p1',
      direction: 1,
      activeColor: 'red',
      stage: 'turn',
      topCard: { id: 'red-5-a', color: 'red', kind: 'number', value: 5, label: '赤红 5' },
      hand: [
        { id: 'red-7-a', color: 'red', kind: 'number', value: 7, label: '赤红 7' },
        { id: 'blue-5-a', color: 'blue', kind: 'number', value: 5, label: '湛蓝 5' },
        { id: 'wild-1', color: null, kind: 'wild', value: null, label: '变色' },
        { id: 'green-2-a', color: 'green', kind: 'number', value: 2, label: '翠绿 2' },
      ],
      cardCounts: { p1: 4, p2: 7, p3: 1 },
      drawPileCount: 82,
      discardPileCount: 1,
      drawnCardId: null,
      playableCardIds: ['red-7-a', 'blue-5-a', 'wild-1'],
      pendingDrawTotal: 0,
      pendingDrawTargetPlayerId: null,
      pendingDrawSourcePlayerId: null,
      canTakePenalty: false,
      canDraw: true,
      canKeepDrawn: false,
      canCatchUno: false,
      unoVulnerablePlayerId: null,
      forfeitedPlayerIds: [],
      winnerPlayerIds: [],
      latestEvent: null,
      history: [{ type: 'start', message: '玩家一先手' }],
      ...gameOverrides,
    },
  } as unknown as ArcadeSnapshot
}

describe('UNO prism arena view', () => {
  beforeEach(() => vi.clearAllMocks())

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the arena, card back, hand and opponent counts', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.find('.arena-stage').exists()).toBe(true)
    expect(wrapper.find('.card-back').exists()).toBe(true)
    expect(wrapper.findAll('.hand-fan .prism-card')).toHaveLength(4)
    expect(wrapper.findAll('.hand-fan .is-playable')).toHaveLength(3)
    expect(wrapper.findAll('.player-seat')).toHaveLength(2)
    expect(wrapper.text()).toContain('UNO 警戒')
    wrapper.unmount()
  })

  it('requires a color and submits an exact wild-card payload', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    const wildCard = wrapper.findAll('.hand-fan .prism-card')[2]

    await wildCard.trigger('click')
    expect(wrapper.find('.color-picker').exists()).toBe(true)
    expect(wrapper.get('.primary-action').attributes('disabled')).toBeDefined()

    await wrapper.get('.color-picker .color-blue').trigger('click')
    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledWith('play_card', {
      cardId: 'wild-1',
      chosenColor: 'blue',
      callUno: false,
    })
    wrapper.unmount()
  })

  it('sends draw and keep actions for the two draw stages', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('.secondary-action').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('draw_card')

    await wrapper.setProps({
      snapshot: snapshot({
        stage: 'after_draw',
        canDraw: false,
        canKeepDrawn: true,
        drawnCardId: 'red-7-a',
        playableCardIds: ['red-7-a'],
      }),
    })
    await wrapper.get('.secondary-action').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenLastCalledWith('keep_drawn')
    wrapper.unmount()
  })

  it('shows the mixed draw stack and submits the accumulated penalty action', async () => {
    const wrapper = mount(GameView, {
      props: {
        snapshot: snapshot({
          hand: [
            { id: 'red-draw-two-a', color: 'red', kind: 'draw_two', value: null, label: '赤红 +2' },
            { id: 'wild-draw-four-1', color: null, kind: 'wild_draw_four', value: null, label: '变色 +4' },
            { id: 'green-2-a', color: 'green', kind: 'number', value: 2, label: '翠绿 2' },
          ],
          cardCounts: { p1: 3, p2: 7, p3: 2 },
          playableCardIds: ['red-draw-two-a', 'wild-draw-four-1'],
          pendingDrawTotal: 6,
          pendingDrawTargetPlayerId: 'p1',
          pendingDrawSourcePlayerId: 'p3',
          canTakePenalty: true,
          canDraw: false,
        }),
      },
    })

    expect(wrapper.get('.penalty-reactor').text()).toContain('+6')
    expect(wrapper.findAll('.hand-fan .is-playable')).toHaveLength(2)
    expect(wrapper.text()).toContain('最后打出的牌必须是数字牌')

    await wrapper.get('.penalty-action').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenLastCalledWith('take_penalty')
    wrapper.unmount()
  })

  it('plays the dedicated wild draw-four overlay for a new server event', async () => {
    vi.useFakeTimers()
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.setProps({
      snapshot: snapshot({
        latestEvent: {
          sequence: 8,
          type: 'wild_draw_four',
          playerId: 'p2',
          targetPlayerId: 'p3',
          card: { id: 'wild-draw-four-1', color: null, kind: 'wild_draw_four', value: null, label: '变色 +4' },
          color: 'blue',
          count: 4,
          stackTotal: 6,
          stacked: true,
          calledUno: false,
          message: '玩家二打出变色 +4；惩罚累计至 +6，玩家三可继续叠加或接牌',
        },
      }),
    })

    expect(wrapper.find('.uno-fx--wild-draw-four').exists()).toBe(true)
    expect(wrapper.get('.uno-fx__copy').text()).toContain('棱镜奇点 +4')
    expect(wrapper.get('.uno-fx__stack-total').text()).toBe('累计 +6')
    await vi.advanceTimersByTimeAsync(1_600)
    expect(wrapper.find('.uno-fx').exists()).toBe(false)
    wrapper.unmount()
  })

  it('plays a dedicated accumulated-penalty impact animation', async () => {
    vi.useFakeTimers()
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.setProps({
      snapshot: snapshot({
        latestEvent: {
          sequence: 9,
          type: 'take_penalty',
          playerId: 'p1',
          targetPlayerId: 'p1',
          card: null,
          color: null,
          count: 8,
          stackTotal: 8,
          stacked: false,
          calledUno: false,
          message: '玩家一接下累计惩罚，摸 8 张并跳过',
        },
      }),
    })

    expect(wrapper.find('.uno-fx--take-penalty').exists()).toBe(true)
    expect(wrapper.get('.uno-fx__copy').text()).toContain('累计惩罚坠落')
    expect(wrapper.get('.uno-fx__symbol').text()).toContain('+8')
    wrapper.unmount()
  })
})
