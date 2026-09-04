import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import viewSource from './GameView.vue?raw'
import type { BonusVector, DevelopmentCardView, PieceVector, SplendorGameView, StandardColor } from './types'

const actionMock = vi.hoisted(() => vi.fn().mockResolvedValue({ ok: true }))
const restartMock = vi.hoisted(() => vi.fn())

vi.mock('@game-hall/plugin-sdk', () => ({
  usePluginGameActions: () => ({ action: actionMock, rapidAction: vi.fn(), restart: restartMock }),
  usePluginFullscreen: () => ({ isFullscreen: { value: false }, isSupported: { value: true }, toggle: vi.fn() }),
}))

const standardColors: StandardColor[] = ['white', 'blue', 'green', 'red', 'black']
const zeroBonus = (): BonusVector => ({ white: 0, blue: 0, green: 0, red: 0, black: 0 })
const zeroPieces = (): PieceVector => ({ ...zeroBonus(), gold: 0 })

function card(id: string, level: 1 | 2 | 3, bonusColor: StandardColor, prestige = 0): DevelopmentCardView {
  const cost = { white: 0, blue: 1, green: 1, red: 0, black: 0 }
  return {
    id, level, bonusColor, prestige, cost, totalCost: 2, artVariant: 2,
    labelZh: `${level} 级${bonusColor}奖励发展卡`, compactLabelZh: `${level}级 ${bonusColor}`,
    payment: {
      effectiveCost: { ...cost },
      recommendedPayment: { white: 0, blue: 1, green: 1, red: 0, black: 0, gold: 0 },
      minimumGold: 0,
      affordable: true,
    },
    legal: { buy: true, reserve: true },
  }
}

function noble(id: string) {
  return {
    id, prestige: 3,
    requirement: { white: 4, blue: 4, green: 0, red: 0, black: 0 },
    portraitVariant: 1, labelZh: '贵族，钻石和蓝宝石各需 4', eligible: false,
    progress: zeroBonus(),
  }
}

function makeSnapshot(count = 4): ArcadeSnapshot {
  const shellPlayers = Array.from({ length: count }, (_, index) => ({
    id: `p${index + 1}`, name: `玩家${index + 1}`, seat: index, connected: true,
  }))
  const gamePlayers = shellPlayers.map((player, index) => ({
    ...player, forfeited: false, isActive: index === 0, isFirstPlayer: index === 0,
    pieces: { ...zeroPieces(), blue: index === 0 ? 3 : 0, green: index === 0 ? 3 : 0, gold: index === 0 ? 2 : 0 },
    bonuses: index === 0 ? { white: 1, blue: 1, green: 0, red: 0, black: 0 } : zeroBonus(),
    score: index, cardPrestige: index, noblePrestige: 0, purchasedCount: index === 0 ? 2 : 0,
    purchasedCards: index === 0 ? [card('owned-white', 1, 'white'), card('owned-blue', 1, 'blue')] : [],
    nobles: [],
    reservations: index === 0 ? [{ reservationId: 'r-0001', level: 2, source: 'deck' as const, knownToAll: false, card: card('reserved-one', 2, 'red', 2) }] : [],
  }))
  const colors = [
    ['white', '钻石', '◇', '#e8e3d8'], ['blue', '蓝宝石', '◆', '#3a739a'],
    ['green', '祖母绿', '⬟', '#4e8068'], ['red', '红宝石', '⬢', '#a8524b'],
    ['black', '缟玛瑙', '●', '#353a3d'], ['gold', '黄金', '★', '#c79b43'],
  ].map(([id, nameZh, symbol, semanticColor]) => ({ id, nameZh, symbol, semanticColor, pattern: 'functional' }))
  const tiers = ([3, 2, 1] as const).map(level => ({
    level, deckCount: level * 8,
    slots: standardColors.slice(0, 4).map((color, index) => ({ slot: index, card: card(`dev-${level}-${index}`, level, color, level - 1) })),
  }))
  const game: SplendorGameView = {
    schemaVersion: 1, modelVersion: '1.0.0', gameId: 'splendor', rulesProfile: 'base-2024-refresh',
    sceneId: 'turn_idle', phase: 'turn_action', revision: 7, marketRevision: 4,
    roundNumber: 2, actionNumber: 4, turnOrder: shellPlayers.map(player => player.id),
    currentPlayerId: 'p1', firstPlayerId: 'p1', finalRound: null,
    colors: colors as SplendorGameView['colors'],
    supply: { white: 5, blue: 5, green: 5, red: 5, black: 5, gold: 4 },
    tiers, availableNobles: [noble('noble-one'), noble('noble-two')], players: gamePlayers,
    selfPlayerId: 'p1',
    actions: {
      canAct: true, canTakeDifferent: true, requiredDistinctCount: 3,
      differentColors: [...standardColors], sameColors: [...standardColors], canReserve: true,
      blindReserveLevels: [3, 2, 1], canReturnTokens: false, returnCount: 0,
      canChooseNoble: false, eligibleNobleIds: [], canResign: true, disabledReasonZh: null,
    },
    events: [{ seq: 1, type: 'game_started', message: '玩家1 成为首家', data: {} }], result: null,
    rules: { targetPrestige: 15, pieceLimit: 10, reservationLimit: 3, marketCardsPerLevel: 4, noblePrestige: 3 },
  }
  return {
    revision: 7, roomCode: 'SPL4', gameKey: 'plugin-splendor', gameName: '璀璨宝石', phase: 'playing',
    options: {}, hostId: 'p1', self: shellPlayers[0], players: shellPlayers, requiredPlayers: count,
    minimumPlayers: 2, roundNumber: 2, winner: null, winnerPlayerIds: [], winReason: null,
    actions: {
      canStart: false, canRestart: false, canAct: true, canKickPlayers: false, canDissolve: false,
      canEditRules: false, canRequestUndo: false, canRequestDraw: false, canResolveRequest: false,
    },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] }, game,
  } as unknown as ArcadeSnapshot
}

describe('Splendor immersive tabletop', () => {
  beforeEach(() => { actionMock.mockClear(); restartMock.mockClear() })
  afterEach(() => vi.useRealTimers())

  it.each([2, 3, 4])('renders the modeled relative seats for %i players', (count) => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot(count) } })
    expect(wrapper.findAll('#opponent_rail .player-tableau')).toHaveLength(count - 1)
    expect(wrapper.findAll('.market-tier')).toHaveLength(3)
    expect(wrapper.findAll('.market-slot .development-card')).toHaveLength(12)
    expect(wrapper.findAll('.supply-grid .gem-token')).toHaveLength(6)
  })

  it('renders every persistent scene-model zone', () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    for (const id of ['status_bar', 'opponent_rail', 'noble_row', 'tier_3_market', 'tier_2_market', 'tier_1_market', 'gem_supply', 'event_strip', 'self_tableau', 'reserved_drawer', 'action_dock']) {
      expect(wrapper.find(`#${id}`).exists(), id).toBe(true)
    }
  })

  it('submits an exact three-different-color action with revision guard', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.get('#action_dock .primary-action').trigger('click')
    for (const selector of ['.gem-white', '.gem-blue', '.gem-green']) await wrapper.get(selector).trigger('click')
    await wrapper.get('.draft-actions .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('take_different', { revision: 7, colors: ['white', 'blue', 'green'] })
  })

  it('submits the two-same action only after a legal token is selected', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.findAll('#action_dock .secondary-action')[0].trigger('click')
    await wrapper.get('.gem-red').trigger('click')
    await wrapper.get('.draft-actions .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('take_same', { revision: 7, color: 'red' })
  })

  it('uses card details before reserving a public market card', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.get('.market-slot .development-card').trigger('click')
    expect(wrapper.get('.card-detail-sheet').text()).toContain('费用分析')
    await wrapper.get('.card-detail-sheet .secondary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('reserve_face_up', { revision: 7, cardId: 'dev-3-0', marketRevision: 4 })
  })

  it('opens the payment ledger and submits the server-provided exact payment', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.get('.market-slot .development-card').trigger('click')
    await wrapper.get('.card-detail-sheet .primary-action').trigger('click')
    expect(wrapper.find('.payment-composer').exists()).toBe(true)
    await wrapper.get('.payment-composer > footer .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('purchase_face_up', {
      revision: 7, cardId: 'dev-3-0', marketRevision: 4,
      payment: { white: 0, blue: 1, green: 1, red: 0, black: 0, gold: 0 },
    })
  })

  it('allows deliberate gold substitution while matching gems are held', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.get('.market-slot .development-card').trigger('click')
    await wrapper.get('.card-detail-sheet .primary-action').trigger('click')
    const substitute = wrapper.findAll('.payment-row .substitution button').find(button => button.attributes('disabled') === undefined)
    expect(substitute).toBeTruthy()
    await substitute!.trigger('click')
    await wrapper.get('.payment-composer > footer .primary-action').trigger('click')
    await flushPromises()
    const payload = actionMock.mock.calls.at(-1)?.[1]
    expect(payload.payment.blue + payload.payment.green + payload.payment.gold).toBe(2)
    expect(payload.payment.gold).toBe(1)
  })

  it('restores the forced return sheet and submits exactly the overage', async () => {
    const value = makeSnapshot()
    const game = value.game as unknown as SplendorGameView
    game.phase = 'return_tokens'; game.sceneId = 'return_tokens'; game.actions.canAct = false
    game.actions.canReturnTokens = true; game.actions.returnCount = 2
    const self = game.players[0]; self.pieces.white = 3; self.pieces.blue = 4
    const wrapper = mount(GameView, { props: { snapshot: value } })
    const whitePlus = wrapper.findAll('.return-white button')[1]
    await whitePlus.trigger('click'); await whitePlus.trigger('click')
    await wrapper.get('.return-sheet footer .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('return_tokens', {
      revision: 7,
      pieces: { white: 2, blue: 0, green: 0, red: 0, black: 0, gold: 0 },
    })
  })

  it('renders only server-eligible nobles in the mandatory choice sheet', async () => {
    const value = makeSnapshot()
    const game = value.game as unknown as SplendorGameView
    game.phase = 'choose_noble'; game.sceneId = 'choose_noble'; game.actions.canAct = false
    game.actions.canChooseNoble = true; game.actions.eligibleNobleIds = ['noble-two']
    const wrapper = mount(GameView, { props: { snapshot: value } })
    expect(wrapper.findAll('.noble-choice-list .noble-tile')).toHaveLength(1)
    await wrapper.get('.noble-choice-list .noble-tile').trigger('click')
    await wrapper.get('.noble-choice-sheet footer .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('choose_noble', { revision: 7, nobleId: 'noble-two' })
  })

  it('explains a shared victory with both score and card-count comparator', () => {
    const value = makeSnapshot(2)
    value.phase = 'finished'; value.actions.canRestart = true
    const game = value.game as unknown as SplendorGameView
    game.phase = 'finished'; game.sceneId = 'game_finished'
    game.result = {
      winnerIds: ['p1', 'p2'], outcome: 'shared-win', reason: 'final-round-complete',
      summaryZh: '玩家1、玩家2 共同获胜',
      rows: game.players.map(player => ({ player_id: player.id, prestige: 16, card_prestige: 13, noble_prestige: 3, purchased_card_count: 11, rank: 1, winner: true, forfeited: false })),
    }
    const wrapper = mount(GameView, { props: { snapshot: value } })
    expect(wrapper.findAll('.ranking-table article.winner')).toHaveLength(2)
    expect(wrapper.get('.result-sheet').text()).toContain('共同获胜')
    expect(wrapper.get('.result-sheet').text()).toContain('发展卡数量')
  })

  it('opens an accessible rule sheet containing all four actions and tie rule', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot() } })
    await wrapper.get('[aria-label="打开规则摘要"]').trigger('click')
    const dialog = wrapper.get('.rules-sheet[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(dialog.text()).toContain('每回合四选一')
    expect(dialog.text()).toContain('共同获胜')
  })

  it.each([
    ['pieces_taken', '.motion-gem-trail'],
    ['pieces_returned', '.motion-gem-trail'],
    ['card_reserved_public', '.motion-card-model'],
    ['card_reserved_blind', '.motion-card-model'],
    ['card_purchased', '.motion-card-model'],
    ['market_refilled', '.motion-card-model'],
    ['noble_acquired', '.motion-noble-model'],
    ['final_round_triggered', '.motion-final-banner'],
    ['turn_advanced', '.motion-turn-ring'],
    ['game_finished', '.motion-victory-seal'],
  ])('maps %s to a bounded non-interactive animation', async (type, selector) => {
    vi.useFakeTimers()
    const first = makeSnapshot()
    const wrapper = mount(GameView, { props: { snapshot: first } })
    const next = makeSnapshot()
    const nextGame = next.game as unknown as SplendorGameView
    nextGame.revision = 8
    nextGame.events = [...nextGame.events, { seq: 2, type, message: type, data: { level: 2 } }]
    await wrapper.setProps({ snapshot: next })
    expect(wrapper.find(selector).exists()).toBe(true)
    vi.advanceTimersByTime(800)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.motion-layer').exists()).toBe(false)
  })

  it('defines near-viewport geometry, contained motion, compact scrolling and reduced motion', () => {
    expect(viewSource).toContain("import './layout.css'")
    expect(viewSource).toContain("import './motion.css'")
    expect(viewSource).toContain("import './responsive.css'")
    expect(viewSource).toContain('class="motion-layer"')
    expect(viewSource).toContain('usePluginFullscreen')
    expect(viewSource).toContain('class="market-slots"')
  })
})
