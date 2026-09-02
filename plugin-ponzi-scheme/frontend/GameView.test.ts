import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import gameViewSource from './GameView.vue?raw'

const actionMock = vi.hoisted(() => vi.fn().mockResolvedValue({ ok: true }))

vi.mock('@game-hall/plugin-sdk', () => ({
  usePluginGameActions: () => ({
    action: actionMock,
    rapidAction: vi.fn(),
    restart: vi.fn(),
  }),
}))

const industries = [
  { id: 'transportation', name: '交通运输', shortName: '交通', supply: 15, remaining: 15, color: '#6d91aa', icon: 'rail' },
  { id: 'grain', name: '粮食农业', shortName: '粮食', supply: 15, remaining: 15, color: '#c5a15a', icon: 'grain' },
  { id: 'media', name: '新闻媒体', shortName: '媒体', supply: 15, remaining: 15, color: '#8d9b72', icon: 'signal' },
  { id: 'real_estate', name: '地产开发', shortName: '地产', supply: 15, remaining: 15, color: '#9a6574', icon: 'building' },
] as const

function card(amount: number, row: number) {
  return {
    id: `F${String(amount).padStart(3, '0')}`,
    amount,
    period: row === 1 ? 5 : row === 2 ? 4 : 3,
    interest: amount - 1,
    averageBurden: 2,
    yieldPercent: 18,
    kind: amount < 18 ? 'starting' : 'regular',
    isBear: false,
  }
}

function ledger(playerId: string, cash: number | null, hidden: boolean) {
  return {
    playerId,
    cash,
    cashHidden: hidden,
    industries: { transportation: 0, grain: 0, media: 0, real_estate: 0 },
    industryTotal: 0,
    funds: [],
    fundCount: 0,
    luxuries: [],
    interestDueNext: 0,
    cycleInterest: 0,
    bankrupt: false,
    forfeited: false,
    finalScore: null,
  }
}

function snapshot(): ArcadeSnapshot {
  const players = [1, 2, 3].map((number, index) => ({
    id: `p${number}`,
    name: `玩家${number}`,
    seat: index,
    connected: true,
  }))
  return {
    revision: 1,
    roomCode: 'PONZ',
    gameKey: 'plugin-ponzi-scheme',
    gameName: '庞氏骗局',
    phase: 'playing',
    options: {},
    hostId: 'p1',
    self: { id: 'p1', name: '玩家1', seat: 0 },
    players,
    requiredPlayers: 5,
    minimumPlayers: 3,
    roundNumber: 1,
    winner: null,
    winnerPlayerIds: [],
    winReason: null,
    actions: {
      canStart: false,
      canRestart: false,
      canAct: true,
      canKickPlayers: false,
      canDissolve: false,
      canEditRules: false,
      canRequestUndo: false,
      canRequestDraw: false,
      canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 300, messages: [] },
    game: {
      version: '1.1.0',
      ruleset: 'bright-eye-standard',
      round: 1,
      stage: 'funding',
      stageLabel: '募集资金',
      currentPlayerId: 'p1',
      starterPlayerId: 'p1',
      turnOrder: players.map(player => player.id),
      marketRows: [
        [card(9, 1), card(10, 1), card(11, 1)],
        [card(12, 2), card(13, 2), card(14, 2)],
        [card(15, 3), card(16, 3), card(17, 3)],
      ],
      bearCount: 0,
      playerCount: 3,
      deckCounts: { draw: 63, discard: 0, removedStarting: 0 },
      industryCatalog: industries,
      luxuryMarket: [
        { id: 'watch', name: '典藏腕表', cost: 30, points: 1, icon: 'watch' },
        { id: 'roadster', name: '古董跑车', cost: 56, points: 2, icon: 'car' },
        { id: 'yacht', name: '私人游艇', cost: 78, points: 3, icon: 'yacht' },
        { id: 'club', name: '城市会所', cost: 96, points: 4, icon: 'column' },
      ],
      luxuriesEnabled: true,
      scoringMode: 'industry_and_luxury',
      wheelPosition: 0,
      wheelAdvance: 1,
      ledgers: [ledger('p1', 0, false), ledger('p2', null, true), ledger('p3', null, true)],
      pendingTrade: null,
      legalActions: {
        canResign: true,
        fundingOptions: industries.map(industry => ({
          industryId: industry.id,
          industryName: industry.name,
          row: 1,
          cardIds: ['F009', 'F010', 'F011'],
        })),
        canPassFunding: true,
      },
      events: [{ seq: 1, type: 'game_start', message: '玩家1 持有起始玩家标记', data: {} }],
      bankruptPlayerIds: [],
      rankings: [],
      settlement: null,
      privacy: { cash: 'self-only', tradeOffer: 'participants-only', fundsAndIndustries: 'public' },
    },
  } as unknown as ArcadeSnapshot
}

describe('ponzi scheme tabletop view', () => {
  beforeEach(() => actionMock.mockClear())
  afterEach(() => vi.useRealTimers())

  it('renders the complete market, component banks, wheel and player screens', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.findAll('.fund-card')).toHaveLength(9)
    expect(wrapper.findAll('.industry-bank > article')).toHaveLength(4)
    expect(wrapper.findAll('.luxury-bank article')).toHaveLength(4)
    expect(wrapper.findAll('.player-ledger')).toHaveLength(3)
    expect(wrapper.find('.time-wheel').exists()).toBe(true)
    expect(wrapper.find('.player-screen').exists()).toBe(true)
  })

  it('submits only the selected industry and server-authorized market card', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    await wrapper.findAll('.fund-card')[0].trigger('click')
    await flushPromises()

    expect(actionMock).toHaveBeenCalledWith('fund', {
      industryId: 'transportation',
      cardId: 'F009',
    })
  })

  it('keeps opponent money behind a visual screen', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    const ledgers = wrapper.findAll('.player-ledger')

    expect(ledgers[0].text()).toContain('现金 0')
    expect(ledgers[1].text()).toContain('现金 ▧')
    expect(ledgers[1].text()).not.toMatch(/现金 \d/)
  })

  it('models the forced sell-or-counter response without exposing it to spectators', async () => {
    const current = snapshot()
    const game = current.game as Record<string, any>
    game.stage = 'trade_response'
    game.stageLabel = '回应暗盘报价'
    game.currentPlayerId = 'p1'
    game.pendingTrade = {
      proposerId: 'p2',
      targetId: 'p1',
      industryId: 'grain',
      industryName: '粮食农业',
      offer: 7,
      offerKnown: true,
    }
    game.legalActions = { canResign: true, canAcceptOffer: true, canCounterOffer: true }
    const wrapper = mount(GameView, { props: { snapshot: current } })

    expect(wrapper.get('.offer-value').text()).toBe('7')
    await wrapper.findAll('.response-grid button')[1].trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('counter_offer', {})
  })

  it('contains an explicit reduced-motion fallback', () => {
    expect(gameViewSource).toContain('@media (prefers-reduced-motion: reduce)')
  })

  it.each([
    ['fund', 'cue-fund', '.motion-card'],
    ['trade_offer', 'cue-envelope', '.motion-envelope'],
    ['trade_accept', 'cue-transfer', '.motion-envelope'],
    ['luxury', 'cue-luxury', '.motion-luxury'],
    ['market_discard', 'cue-market', '.motion-market-card'],
    ['market_crash', 'cue-crash', '.motion-crash-label'],
    ['crash_discard', 'cue-industry', '.motion-industry'],
    ['interest_paid', 'cue-cash', '.motion-cash'],
    ['wheel', 'cue-wheel', '.motion-wheel'],
    ['bankruptcy', 'cue-bankruptcy', '.motion-bankruptcy'],
    ['marker_pass', 'cue-marker', '.motion-marker'],
  ])('maps %s server events to a bounded tabletop animation', async (eventType, layerClass, objectSelector) => {
    vi.useFakeTimers()
    const initial = snapshot()
    const wrapper = mount(GameView, { props: { snapshot: initial } })
    expect(wrapper.find('.motion-layer').exists()).toBe(false)

    const updated = snapshot()
    const game = updated.game as Record<string, any>
    game.events.push({ seq: 2, type: eventType, message: `动画 ${eventType}`, data: {} })
    await wrapper.setProps({ snapshot: updated })

    expect(wrapper.get('.motion-layer').classes()).toContain(layerClass)
    expect(wrapper.find(objectSelector).exists()).toBe(true)
    expect(wrapper.get('.motion-announcer').text()).toBe(`动画 ${eventType}`)
    vi.advanceTimersByTime(1100)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.motion-layer').exists()).toBe(false)
    wrapper.unmount()
  })

  it('queues all state events in order instead of dropping rapid compound settlement cues', async () => {
    vi.useFakeTimers()
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    const updated = snapshot()
    const game = updated.game as Record<string, any>
    game.events.push(
      { seq: 2, type: 'interest_paid', message: '支付利息', data: {} },
      { seq: 3, type: 'wheel', message: '轮盘推进', data: { steps: 1 } },
    )
    await wrapper.setProps({ snapshot: updated })
    expect(wrapper.get('.motion-layer').classes()).toContain('cue-cash')

    vi.advanceTimersByTime(1100)
    await wrapper.vm.$nextTick()
    vi.advanceTimersByTime(50)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.motion-layer').classes()).toContain('cue-wheel')
    wrapper.unmount()
  })

  it('rotates only the wheel body while the due arrow remains a fixed sibling', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    const updated = snapshot()
    const game = updated.game as Record<string, any>
    game.wheelPosition = 2
    await wrapper.setProps({ snapshot: updated })

    expect(wrapper.get('.time-wheel').attributes('style')).toContain('--wheel: 2')
    expect(wrapper.get('.time-wheel-wrap').element.children[1]).toBe(wrapper.get('.due-arrow').element)
    expect(wrapper.get('.time-wheel').find('.due-arrow').exists()).toBe(false)
  })

  it('renders every final scoring component, shared rank, winner and bankrupt status', () => {
    const current = snapshot()
    current.phase = 'finished'
    current.winnerPlayerIds = ['p1', 'p2']
    current.winReason = '两位玩家同分且最高资金牌相同'
    const game = current.game as Record<string, any>
    game.stage = 'finished'
    game.stageLabel = '破产结算'
    game.ledgers[0].cash = 42
    game.ledgers[0].cashHidden = false
    game.ledgers[0].finalScore = 4
    game.ledgers[1].cash = 18
    game.ledgers[1].cashHidden = false
    game.ledgers[1].finalScore = 4
    game.ledgers[2].cash = 0
    game.ledgers[2].cashHidden = false
    game.ledgers[2].bankrupt = true
    game.settlement = {
      mode: 'industry_and_luxury',
      winnerPlayerIds: ['p1', 'p2'],
      bankruptPlayerIds: ['p3'],
      reason: current.winReason,
      rows: [
        { playerId: 'p1', rank: 1, winner: true, bankrupt: false, industryScore: 3, luxuryScore: 1, wealthScore: null, highestFund: 17, total: 4 },
        { playerId: 'p2', rank: 1, winner: true, bankrupt: false, industryScore: 4, luxuryScore: 0, wealthScore: null, highestFund: 17, total: 4 },
        { playerId: 'p3', rank: null, winner: false, bankrupt: true, industryScore: 0, luxuryScore: 0, wealthScore: null, highestFund: 9, total: 0 },
      ],
    }

    const wrapper = mount(GameView, { props: { snapshot: current } })
    expect(wrapper.findAll('.settlement-grid article')).toHaveLength(3)
    expect(wrapper.findAll('.settlement-grid article.winner')).toHaveLength(2)
    expect(wrapper.findAll('.settlement-grid article.bankrupt')).toHaveLength(1)
    expect(wrapper.get('.settlement-panel').text()).toContain('产业 3')
    expect(wrapper.get('.settlement-panel').text()).toContain('奢侈品 1')
    expect(wrapper.get('.settlement-panel').text()).toContain('最高资金牌 17')
    expect(wrapper.get('.settlement-panel').text()).toContain('4 分')
  })

  it('keeps the visual palette aligned with the approved green-felt and navy-paper model', () => {
    expect(gameViewSource).toContain('linear-gradient(135deg, #17332e, #102824 58%, #0b201e)')
    expect(gameViewSource).toContain('--navy: #1f3440')
    expect(gameViewSource).toContain('--paper: #e9ddc2')
    expect(gameViewSource).toContain('@keyframes envelope-flight')
    expect(gameViewSource).toContain('@keyframes fund-flight')
  })
})
