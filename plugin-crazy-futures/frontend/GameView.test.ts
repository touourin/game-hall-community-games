import { flushPromises, mount } from '@vue/test-utils'
import { vi } from 'vitest'
import GameView from './GameView.vue'
import gameViewSource from './GameView.vue?raw'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'

const actionMock = vi.hoisted(() => vi.fn().mockResolvedValue({ ok: true }))

vi.mock('@game-hall/plugin-sdk', () => ({
  usePluginGameActions: () => ({
    action: actionMock,
    rapidAction: vi.fn(),
    restart: vi.fn(),
  }),
}))

const ladder = [10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,46,52,56,62,68,76,84,92,100,110,122,134,146,162,178,196,216,238,262,286,312,338,366,394,424,454,486,518,552,586,622,658,696,734]
const commodities = [
  ['oil', '原油', '#b8663b'],
  ['gold', '黄金', '#d6a936'],
  ['cotton', '棉花', '#7cae82'],
  ['copper', '铜', '#b97243'],
] as const

function snapshot(playerCount = 4): ArcadeSnapshot {
  const players = Array.from({ length: playerCount }, (_, index) => ({
    id: `p${index + 1}`,
    name: `玩家${index + 1}`,
    seat: index,
    connected: true,
  }))
  const positions = Object.fromEntries(commodities.map(([commodity]) => [
    commodity,
    { quantity: 0, basis: 0, margin: 0 },
  ]))
  return {
    revision: 1,
    roomCode: 'FTRS',
    gameKey: 'plugin-crazy-futures',
    gameName: '疯狂期货',
    phase: 'playing',
    options: {},
    hostId: 'p1',
    self: { id: 'p1', name: '玩家1', seat: 0 },
    players,
    requiredPlayers: 8,
    minimumPlayers: 4,
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
      version: '0.2-balanced-ladder',
      round: 1,
      maxRounds: 8,
      stage: 'loan',
      stageLabel: '借贷阶段',
      currentPlayerId: 'p1',
      starterPlayerId: 'p1',
      turnOrder: players.map((player) => player.id),
      markets: commodities.map(([commodity, name, color]) => ({
        commodity,
        name,
        color,
        spotIndex: 25,
        spotPrice: 100,
        openIndex: 25,
        openPrice: 100,
        currentIndex: 25,
        currentPrice: 100,
        closeIndex: 25,
        closePrice: 100,
        lowLimitIndex: 22,
        lowLimitPrice: 76,
        highLimitIndex: 28,
        highLimitPrice: 134,
        validTradeIndices: [],
        validTradePrices: [],
        seal: null,
      })),
      priceLadder: ladder,
      priceZones: { low: [0, 16], middle: [17, 33], high: [34, 50] },
      ledgers: players.map((player) => ({
        playerId: player.id,
        cash: 100,
        margin: 0,
        loanPrincipal: 0,
        loanInterest: 0,
        exchangeDebt: 0,
        estimatedEquity: 100,
        positions,
        handCount: player.id === 'p1' ? 1 : 2,
        bankrupt: false,
        forfeited: false,
        forcedLiquidations: 0,
        marginBuffer: 0,
        finalScore: null,
      })),
      auction: null,
      initiationNumber: 0,
      initiationTotal: 0,
      publicEvents: [],
      activeEffects: [],
      hand: [{
        instanceId: 'PI-OIL-01#1',
        cardId: 'PI-OIL-01',
        name: 'OPEC 超预期减产',
        kind: 'personal',
        category: '单商品即时信息',
        strength: '普通',
        subtype: '单次上涨',
        targetLabel: '原油',
        timing: '出牌阶段',
        text: '原油现货上涨 1 格。',
        durationText: '本月立即结算；不跨月',
        keywords: ['单次', '上涨'],
      }],
      peekCards: [],
      deckCounts: { personal: 151, personalDiscard: 0, public: 20, publicDiscard: 0 },
      pendingChoice: null,
      legalActions: { canResign: true, borrowAmounts: [0, 10, 20] },
      events: [{ seq: 1, type: 'round_start', message: '第 1 个月开始', data: {} }],
      rankings: [],
    },
  } as unknown as ArcadeSnapshot
}

describe('crazy futures plugin view', () => {
  beforeEach(() => actionMock.mockClear())

  it('renders all modeled boards, commodities, money and personal cards', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.findAll('.commodity-grid article')).toHaveLength(4)
    expect(wrapper.findAll('.price-board .rail')).toHaveLength(2)
    expect(wrapper.findAll('.ledger-scroll article')).toHaveLength(4)
    expect(wrapper.find('.cash-tray img').exists()).toBe(true)
    expect(wrapper.findAll('.hand-cards > button')).toHaveLength(1)
    expect(wrapper.text()).toContain('OPEC 超预期减产')
  })

  it('submits the selected loan amount through the plugin SDK', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    const choices = wrapper.findAll('.amount-grid button')
    await choices[1].trigger('click')
    await wrapper.get('.action-block .primary').trigger('click')
    await flushPromises()

    expect(actionMock).toHaveBeenCalledWith('borrow', { amount: 10 })
  })

  it('submits only a server-authorized card target', async () => {
    const current = snapshot()
    const game = current.game as Record<string, any>
    game.stage = 'card'
    game.stageLabel = '出牌阶段'
    game.legalActions = {
      canResign: true,
      canPassCard: true,
      playableCards: [{
        instanceId: 'PI-OIL-01#1',
        cardId: 'PI-OIL-01',
        commodities: ['oil'],
      }],
    }
    const wrapper = mount(GameView, { props: { snapshot: current } })

    await wrapper.get('.hand-cards > button').trigger('click')
    await flushPromises()
    await wrapper.get('.action-block .primary').trigger('click')
    await flushPromises()

    expect(actionMock).toHaveBeenCalledWith('play_card', {
      instanceId: 'PI-OIL-01#1',
      commodity: 'oil',
    })
  })

  it('marks unavailable cards without disabling their hover details', () => {
    const current = snapshot()
    const game = current.game as Record<string, any>
    game.stage = 'card'
    game.stageLabel = '出牌阶段'
    game.legalActions = { canResign: true, canPassCard: true, playableCards: [] }

    const wrapper = mount(GameView, { props: { snapshot: current } })

    expect(wrapper.get('.hand-cards > button').attributes('aria-disabled')).toBe('true')
    expect(wrapper.get('.hand-cards > button').attributes('disabled')).toBeUndefined()
  })

  it('supports an eight-player public ledger without changing the game shell', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot(8) } })
    expect(wrapper.findAll('.ledger-scroll article')).toHaveLength(8)
    expect(wrapper.text()).toContain('玩家8')
  })

  it('marks a newly received server price event for animation', async () => {
    const initial = snapshot()
    const wrapper = mount(GameView, { props: { snapshot: initial } })
    const updated = structuredClone(initial) as ArcadeSnapshot
    const game = updated.game as Record<string, any>
    game.markets[0].spotIndex = 26
    game.markets[0].spotPrice = 110
    game.events.push({
      seq: 2,
      type: 'spot_move',
      message: '原油现货上涨至 110 万',
      data: { commodity: 'oil', fromIndex: 25, toIndex: 26 },
    })
    await wrapper.setProps({ snapshot: updated })
    await flushPromises()

    expect(wrapper.find('.price-board .marker.oil.up').exists()).toBe(true)
  })

  it('animates only newly received deal, event and cash-flow messages', async () => {
    const initial = snapshot()
    const wrapper = mount(GameView, { props: { snapshot: initial } })
    expect(wrapper.find('.hand-tray.dealing').exists()).toBe(false)
    expect(wrapper.find('.money-stack.gain').exists()).toBe(false)

    const updated = structuredClone(initial) as ArcadeSnapshot
    const game = updated.game as Record<string, any>
    game.ledgers[0].cash = 110
    game.events.push(
      { seq: 2, type: 'deal', message: '玩家1抽牌', data: { playerId: 'p1' } },
      { seq: 3, type: 'public_event', message: '翻开公共事件', data: {} },
      { seq: 4, type: 'loan', message: '玩家1借款', data: { playerId: 'p1', cashDelta: 10 } },
    )
    await wrapper.setProps({ snapshot: updated })
    await flushPromises()

    expect(wrapper.find('.hand-tray.dealing').exists()).toBe(true)
    expect(wrapper.find('.money-stack.gain').exists()).toBe(true)
    expect(wrapper.find('.money-stack > i').text()).toBe('+10')
  })

  it('contains an explicit reduced-motion fallback', () => {
    expect(gameViewSource).toContain('@media (prefers-reduced-motion: reduce)')
  })
})
