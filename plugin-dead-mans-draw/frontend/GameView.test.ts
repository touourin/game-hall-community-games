import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import source from './GameView.vue?raw'
import scoreSource from './components/ScoreBreakdown.vue?raw'
import type { CardView, DeadMansDrawView, SuitId } from './types'

const actionMock = vi.hoisted(() => vi.fn().mockResolvedValue({ ok: true }))
const restartMock = vi.hoisted(() => vi.fn())

vi.mock('@game-hall/plugin-sdk', async importOriginal => {
  const actual = await importOriginal<Record<string, unknown>>()
  return {
    ...actual,
    usePluginGameActions: () => ({ action: actionMock, rapidAction: vi.fn(), restart: restartMock }),
  }
})

const suitRows = [
  ['anchor', '船锚', 'Anchor', '锚', '#2E7480'], ['hook', '抓钩', 'Hook', '钩', '#765642'],
  ['cannon', '火炮', 'Cannon', '炮', '#9D4B3D'], ['key', '钥匙', 'Key', '钥', '#A77B28'],
  ['chest', '宝箱', 'Chest', '箱', '#80612E'], ['map', '藏宝图', 'Map', '图', '#53744E'],
  ['oracle', '水晶球', 'Oracle', '晶', '#615287'], ['sword', '弯刀', 'Sword', '刀', '#5F6D75'],
  ['kraken', '海怪', 'Kraken', '怪', '#345B58'], ['mermaid', '美人鱼', 'Mermaid', '鱼', '#985173'],
] as const

const suits = suitRows.map(([id, nameZh, nameEn, symbol, color]) => ({
  id, nameZh, nameEn, symbol, icon: id, color, summaryZh: `${nameZh}能力说明`,
}))

function card(suit: SuitId, value = suit === 'mermaid' ? 9 : 7): CardView {
  const item = suits.find(row => row.id === suit)!
  return { ...item, suit, id: `loot-${suit}-${value}`, value }
}

function bank() {
  return suits.map(suit => ({
    suit: suit.id, cardIds: [], cards: [], topValue: null, count: 0, subtotal: 0,
  }))
}

function makeSnapshot(count = 4): ArcadeSnapshot {
  const players = Array.from({ length: count }, (_, index) => ({
    id: `p${index + 1}`, name: `玩家${index + 1}`, seat: index, connected: true,
  }))
  const gamePlayers = players.map((player, index) => ({
    id: player.id, seat: player.seat, displayName: player.name, connected: true,
    isActive: index === 0, forfeited: false, traitId: null, trait: null,
    selectingTrait: false, lockerTargetId: null, bank: bank(), liveScore: index * 3, bankCardCount: 0,
  }))
  const game: DeadMansDrawView = {
    schemaVersion: 1, modelVersion: '1.0.0', gameId: 'dead-mans-draw', revision: 1,
    phase: 'turn', rules: { profileId: 'tabletop_base_2015', profileNameZh: '实体基础版', traitsEnabled: true, globalVariantId: null, globalVariantNameZh: null },
    suitCatalog: suits, players: gamePlayers, currentPlayerId: 'p1', turnNumber: 3, drawCount: 31,
    discard: { count: 2, cardIds: ['loot-anchor-2', 'loot-hook-2'], cards: [card('anchor', 2), card('hook', 2)] },
    playArea: [{ entryId: 'entry-1', cardId: 'loot-mermaid-9', card: card('mermaid'), protected: false, protectionLabelsZh: [], sourceLabelZh: '抽牌堆' }],
    turn: { number: 3, actorId: 'p1', krakenDebt: 0, bustKey: 'suit', presentBustKeys: ['mermaid'], oraclePeekCardIds: [], oraclePeekCards: [], mapRevealCardIds: [], mapRevealCards: [], pendingChoice: null },
    self: { playerId: 'p1', traitOffer: [], mustChooseLockerTarget: false },
    actions: { canChooseTrait: false, canChooseLockerTarget: false, canDraw: true, canCollect: true, canResolveEffect: false, canResign: true, disabledReasonZh: null },
    result: null,
    events: [{ seq: 1, type: 'turn_changed', textZh: '轮到玩家1翻牌', data: { playerId: 'p1' } }],
  }
  return {
    revision: 1, roomCode: 'DMD4', gameKey: 'plugin-dead-mans-draw', gameName: '亡命神抽', phase: 'playing',
    options: {}, hostId: 'p1', self: players[0], players, requiredPlayers: count, minimumPlayers: 2,
    roundNumber: 3, winner: null, winnerPlayerIds: [], winReason: null, statsEligible: true,
    actions: { canStart: false, canRestart: false, canAct: true, canKickPlayers: false, canDissolve: false, canEditRules: false, canRequestUndo: false, canRequestDraw: false, canResolveRequest: false },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] }, game,
  } as unknown as ArcadeSnapshot
}

function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) }

describe('Dead Man’s Draw tabletop', () => {
  beforeEach(() => { actionMock.mockClear(); restartMock.mockClear() })
  afterEach(() => vi.useRealTimers())

  it.each([2, 3, 4])('renders %i players without losing any of the ten public bank suits', count => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot(count) } })
    expect(wrapper.get('.dmd-game').attributes('data-player-count')).toBe(String(count))
    expect(wrapper.findAll('.player-bank')).toHaveLength(count)
    expect(wrapper.findAll('.bank-slot')).toHaveLength(count * 10)
    expect(wrapper.findAll('.lane-card')).toHaveLength(1)
  })

  it('submits draw and collect with the visible server revision', async () => {
    const wrapper = mount(GameView, { props: { snapshot: makeSnapshot(3) } })
    await wrapper.get('.draw-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('draw', { revision: 1 })
    await wrapper.get('.collect-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('collect', { revision: 1 })
  })

  it('renders private trait choice and submits only the selected trait id', async () => {
    const snapshot = makeSnapshot(2)
    const game = snapshot.game as unknown as DeadMansDrawView
    game.phase = 'trait_selection'
    game.actions.canChooseTrait = true
    game.actions.canDraw = false
    game.actions.canCollect = false
    game.self!.traitOffer = [
      { id: 'trait-mystic', nameZh: '神秘学家', nameEn: 'Mystic', summaryZh: '查看三张牌。', appliesTo: ['oracle'] },
      { id: 'trait-miser', nameZh: '守财奴', nameEn: 'Miser', summaryZh: '保护抓钩。', appliesTo: ['hook'] },
    ]
    const wrapper = mount(GameView, { props: { snapshot } })
    expect(wrapper.findAll('.trait-options button')).toHaveLength(2)
    await wrapper.findAll('.trait-options button')[0].trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('choose_trait', { traitId: 'trait-mystic', revision: 1 })
  })

  it('renders server-authorized effect options and preserves the choice token', async () => {
    const snapshot = makeSnapshot(2)
    const game = snapshot.game as unknown as DeadMansDrawView
    game.phase = 'effect_choice'
    game.actions.canResolveEffect = true
    game.actions.canDraw = false
    game.actions.canCollect = false
    game.turn!.pendingChoice = {
      choiceId: 'choice-8', kind: 'hook-stack', actorId: 'p1', promptZh: '抓钩必须选择',
      options: [{ optionId: 'option-3', labelZh: '美人鱼 9', cardId: 'loot-mermaid-9', card: card('mermaid'), playerId: 'p1', suit: 'mermaid', entryId: null, causesImmediateBust: true, actionable: true }],
    }
    const wrapper = mount(GameView, { props: { snapshot } })
    expect(wrapper.get('.choice-option').classes()).toContain('danger')
    await wrapper.get('.choice-option').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('resolve_effect', { choiceId: 'choice-8', optionId: 'option-3', revision: 1 })
  })

  it.each(suits.map(suit => suit.id))('maps %s entry to its own bounded visual cue', async suit => {
    vi.useFakeTimers()
    const initial = makeSnapshot(2)
    const wrapper = mount(GameView, { props: { snapshot: initial } })
    const updated = clone(initial)
    const game = updated.game as unknown as DeadMansDrawView
    game.revision = 2
    game.events.push({ seq: 2, type: 'card_entered', textZh: `${suit}进入航道`, data: { card: card(suit) } })
    await wrapper.setProps({ snapshot: updated })
    expect(wrapper.get('.motion-layer').classes()).toContain(`cue-${suit}`)
    expect(wrapper.find('.motion-object').exists()).toBe(true)
    vi.advanceTimersByTime(700)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.motion-layer').exists()).toBe(false)
    wrapper.unmount()
  })

  it('queues compound bust and protected split animations in event order', async () => {
    vi.useFakeTimers()
    const initial = makeSnapshot(2)
    const wrapper = mount(GameView, { props: { snapshot: initial } })
    const updated = clone(initial)
    const game = updated.game as unknown as DeadMansDrawView
    game.events.push(
      { seq: 2, type: 'bust_detected', textZh: '美人鱼重复，发生爆牌', data: { card: card('mermaid') } },
      { seq: 3, type: 'protected_split', textZh: '两张受保护牌进入银行', data: { count: 2 } },
    )
    await wrapper.setProps({ snapshot: updated })
    expect(wrapper.get('.motion-layer').classes()).toContain('cue-bust')
    vi.advanceTimersByTime(850)
    await wrapper.vm.$nextTick()
    vi.advanceTimersByTime(40)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('.motion-layer').classes()).toContain('cue-protected')
    wrapper.unmount()
  })

  it('shows every final score component and a shared winner', () => {
    const snapshot = makeSnapshot(3)
    snapshot.phase = 'finished'
    snapshot.actions.canRestart = true
    const game = snapshot.game as unknown as DeadMansDrawView
    game.phase = 'finished'
    game.result = {
      winnerIds: ['p1', 'p2'], outcome: 'shared-win', reason: 'draw-pile-exhausted', summaryZh: '玩家1、玩家2共享胜利',
      scores: game.players.map((player, index) => ({
        playerId: player.id, suitSubtotals: Object.fromEntries(suits.map(suit => [suit.id, index < 2 ? 1 : 0])) as Record<SuitId, number>,
        cardAdjustments: index === 0 ? 5 : 0, variantAdjustment: 0, total: index < 2 ? 10 : 0,
        eligible: true, bankCardCount: index < 2 ? 5 : 0, rank: index < 2 ? 1 : 2, winner: index < 2,
      })),
    }
    const wrapper = mount(GameView, { props: { snapshot } })
    expect(wrapper.findAll('.score-grid article')).toHaveLength(3)
    expect(wrapper.findAll('.score-grid article.winner')).toHaveLength(2)
    expect(wrapper.findAll('.suit-scores span')).toHaveLength(30)
    expect(wrapper.get('.score-overlay').text()).toContain('特性 +5')
  })

  it('keeps the generated tabletop palette, responsive breakpoints and reduced-motion fallback', () => {
    expect(source).toContain('--table: #173b3a')
    expect(source).toContain('--paper: #efe2c4')
    expect(source).toContain('--danger: #a3473d')
    expect(source).toContain('@media (max-width: 759px)')
    expect(source).toContain('@media (max-width: 390px)')
    expect(source).toContain('@media (prefers-reduced-motion: reduce)')
    expect(source).toContain('grid-template-areas: ". north ." "west center east" ". self ." ". dock ."')
    expect(source).toContain('.oracle-peek { position: static; grid-row: 2')
    expect(source).toContain('.trait-sheet { position: fixed; inset: 8px')
    expect(scoreSource).toContain('.score-overlay { position: fixed; inset: 8px')
    for (const name of ['anchor-lock', 'hook-swing', 'cannon-recoil', 'key-turn', 'chest-open', 'map-unfold', 'oracle-focus', 'sword-slash', 'kraken-rise', 'mermaid-wave']) {
      expect(source).toContain(`@keyframes ${name}`)
    }
  })
})
