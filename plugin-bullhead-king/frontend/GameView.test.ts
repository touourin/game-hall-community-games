import { flushPromises, mount } from '@vue/test-utils'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GameView from './GameView.vue'
import type {
  BullAnimation,
  BullCard,
  BullCardTier,
  BullheadGameView,
} from './types'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async () => true),
  restart: vi.fn(async () => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
}))

function penalty(number: number): 1 | 2 | 3 | 5 | 7 {
  if (number === 55) return 7
  if (number % 11 === 0) return 5
  if (number % 10 === 0) return 3
  if (number % 5 === 0) return 2
  return 1
}

function card(number: number): BullCard {
  const bullheads = penalty(number)
  const tiers: Record<number, BullCardTier> = {
    1: 'single', 2: 'double', 3: 'triple', 5: 'quintuple', 7: 'royal',
  }
  return {
    id: `card-${String(number).padStart(3, '0')}`,
    number,
    bullheads,
    tier: tiers[bullheads]!,
  }
}

function baseGame(overrides: Partial<BullheadGameView> = {}): BullheadGameView {
  const base: BullheadGameView = {
    schemaVersion: 1,
    sceneId: 'turn.select',
    stage: 'select',
    roundNumber: 1,
    turnNumber: 1,
    rules: {
      cardMinimum: 1,
      cardMaximum: 104,
      handSize: 10,
      rowCount: 4,
      rowLimit: 5,
      targetPenalty: 66,
    },
    players: [
      { id: 'p1', name: '青角', seat: 0, status: 'active', handCount: 10, hasSelected: false, roundPenalty: 0, totalPenalty: 3, capturedCount: 0, rank: null },
      { id: 'p2', name: '赤角', seat: 1, status: 'active', handCount: 10, hasSelected: false, roundPenalty: 2, totalPenalty: 12, capturedCount: 1, rank: null },
      { id: 'p3', name: '金角', seat: 2, status: 'active', handCount: 10, hasSelected: true, roundPenalty: 0, totalPenalty: 8, capturedCount: 0, rank: null },
    ],
    activePlayerIds: ['p1', 'p2', 'p3'],
    rows: [
      [card(12), card(14)],
      [card(37)],
      [card(43), card(44), card(55)],
      [card(58), card(61)],
    ],
    hand: [1, 5, 10, 11, 22, 35, 55, 67, 89, 104].map(card),
    committedCard: null,
    committedPlayerIds: ['p3'],
    waitingForPlayerIds: ['p1', 'p2'],
    revealed: [],
    pendingLowCard: null,
    rowChoices: [],
    actions: ['select_card'],
    animation: null,
    roundSummary: null,
    history: [{ type: 'round_start', message: '第 1 轮发牌' }],
    rankings: [],
    canSelect: true,
    canChooseRow: false,
    canStartNextRound: false,
  }
  return {
    ...base,
    ...overrides,
    rules: { ...base.rules, ...(overrides.rules ?? {}) },
  }
}

function snapshot(
  game = baseGame(),
  phase: 'playing' | 'finished' = 'playing',
  viewerMode: 'player' | 'spectator' = 'player',
): ArcadeSnapshot {
  return {
    revision: 1,
    roomCode: 'BULL',
    gameKey: 'plugin-bullhead-king',
    gameName: '谁是牛头王',
    phase,
    statsEligible: true,
    hostId: 'p1',
    self: { id: 'p1', name: '青角', seat: 0 },
    viewer: viewerMode === 'player'
      ? { mode: 'player', id: 'p1', name: '青角', targetPlayerId: 'p1' }
      : { mode: 'spectator', id: 's1', name: '观众', targetPlayerId: null },
    players: game.players.map(player => ({
      id: player.id,
      name: player.name,
      seat: player.seat,
      connected: true,
      isHost: player.id === 'p1',
    })),
    requiredPlayers: game.players.length,
    minimumPlayers: 2,
    roundNumber: game.roundNumber,
    winner: phase === 'finished' ? '最低牛头分' : null,
    winnerPlayerIds: phase === 'finished' ? ['p1'] : [],
    winReason: phase === 'finished' ? '有人达到 66 牛头分；青角以 18 分获胜' : null,
    actions: {
      canStart: false,
      canRestart: phase === 'finished',
      canAct: phase === 'playing',
      canKickPlayers: false,
      canDissolve: false,
      canEditRules: false,
      canRequestUndo: false,
      canRequestDraw: false,
      canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 200, messages: [] },
    game,
  } as unknown as ArcadeSnapshot
}

function render(game = baseGame(), phase: 'playing' | 'finished' = 'playing') {
  return mount(GameView, { props: { snapshot: snapshot(game, phase) } })
}

function buttonWithText(wrapper: ReturnType<typeof render>, text: string) {
  const button = wrapper.findAll('button').find(candidate => candidate.text().includes(text))
  if (!button) throw new Error(`Missing button: ${text}`)
  return button
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('bullhead king table and card model', () => {
  it('renders four stable rows, ten private cards and all penalty tiers', () => {
    const wrapper = render()

    expect(wrapper.findAll('.row-line')).toHaveLength(4)
    expect(wrapper.findAll('.hand-scroll .number-card')).toHaveLength(10)
    const expectedTiers = new Map([
      [1, 'tier-single'],
      [5, 'tier-double'],
      [10, 'tier-triple'],
      [11, 'tier-quintuple'],
      [55, 'tier-royal'],
    ])
    for (const [number, tier] of expectedTiers) {
      expect(wrapper.get(`.hand-scroll [data-card-number="${number}"]`).classes()).toContain(tier)
    }
    expect(wrapper.get('.hand-scroll [data-card-number="55"]').findAll('.bull-pip')).toHaveLength(7)
    expect(wrapper.text()).toContain('66')
    expect(wrapper.get('.bullhead-game').attributes('data-layout')).toBe('browser-fill')
  })

  it('renders a complete eight-player score rail', () => {
    const players = Array.from({ length: 8 }, (_, index) => ({
      id: `p${index + 1}`,
      name: `玩家${index + 1}`,
      seat: index,
      status: 'active' as const,
      handCount: 10,
      hasSelected: index % 2 === 0,
      roundPenalty: index,
      totalPenalty: index * 5,
      capturedCount: index,
      rank: null,
    }))
    const wrapper = render(baseGame({
      players,
      activePlayerIds: players.map(player => player.id),
      committedPlayerIds: players.filter(player => player.hasSelected).map(player => player.id),
      waitingForPlayerIds: players.filter(player => !player.hasSelected).map(player => player.id),
    }))

    expect(wrapper.findAll('.player-chip')).toHaveLength(8)
    expect(wrapper.get('[data-player-id="p8"]').text()).toContain('玩家8')
  })

  it('selects one card locally and sends only card id plus current turn', async () => {
    const wrapper = render()

    await wrapper.get('.hand-scroll [data-card-id="card-022"]').trigger('click')
    expect(wrapper.get('.hand-scroll [data-card-id="card-022"]').attributes('aria-pressed')).toBe('true')
    await buttonWithText(wrapper, '锁定这张牌').trigger('click')
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledExactlyOnceWith('select_card', {
      cardId: 'card-022',
      turnNumber: 1,
    })
  })

  it('shows a committed card only in the private waiting panel', () => {
    const committed = baseGame({
      sceneId: 'turn.waiting',
      hand: baseGame().hand.filter(item => item.number !== 22),
      committedCard: card(22),
      committedPlayerIds: ['p1', 'p3'],
      waitingForPlayerIds: ['p2'],
      actions: [],
      canSelect: false,
      players: baseGame().players.map(player => player.id === 'p1'
        ? { ...player, hasSelected: true }
        : player),
    })
    const wrapper = render(committed)

    expect(wrapper.get('.committed-panel').text()).toContain('你的牌已锁定')
    expect(wrapper.find('.committed-panel [data-card-number="22"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('还差 1 人')
    expect(wrapper.find('.commit-button').exists()).toBe(false)
  })

  it('offers all four rows only to the low-card owner', async () => {
    const lowCardGame = baseGame({
      sceneId: 'turn.choose-row',
      stage: 'choose_row',
      pendingLowCard: { playerId: 'p1', card: card(3) },
      rowChoices: [
        { rowIndex: 0, cardCount: 2, bullheads: 2 },
        { rowIndex: 1, cardCount: 1, bullheads: 1 },
        { rowIndex: 2, cardCount: 3, bullheads: 13 },
        { rowIndex: 3, cardCount: 2, bullheads: 2 },
      ],
      actions: ['take_row'],
      canSelect: false,
      canChooseRow: true,
    })
    const wrapper = render(lowCardGame)

    expect(wrapper.findAll('.take-row-button')).toHaveLength(4)
    await wrapper.get('[data-row-index="1"] .take-row-button').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('take_row', {
      rowIndex: 1,
      turnNumber: 1,
    })
  })

  it('renders reveal order and the authoritative take animation event', () => {
    const animation: BullAnimation = {
      id: 7,
      kind: 'turn_resolution',
      roundNumber: 1,
      turnNumber: 4,
      revealed: [
        { playerId: 'p1', card: card(30) },
        { playerId: 'p3', card: card(62) },
      ],
      steps: [
        {
          id: 'animation-7-30-0',
          type: 'take_full',
          playerId: 'p1',
          card: card(30),
          rowIndex: 0,
          takenCards: [1, 5, 11, 14, 20].map(card),
          penalty: 12,
        },
        {
          id: 'animation-7-62-3',
          type: 'place',
          playerId: 'p3',
          card: card(62),
          rowIndex: 3,
          takenCards: [],
          penalty: 0,
        },
      ],
      pendingChoice: null,
      complete: true,
    }
    const resolving = baseGame({
      sceneId: 'turn.resolve',
      stage: 'resolving',
      turnNumber: 4,
      hand: baseGame().hand.slice(0, 6),
      revealed: animation.revealed,
      animation,
      actions: [],
      canSelect: false,
      rows: [
        [card(30)],
        [card(37)],
        [card(43), card(44), card(55)],
        [card(58), card(61), card(62)],
      ],
    })
    const wrapper = render(resolving)

    expect(wrapper.findAll('.reveal-entry')).toHaveLength(2)
    expect(wrapper.get('.reveal-rail').text()).toContain('30 → 62')
    expect(wrapper.get('[data-row-index="0"]').classes()).toContain('row-line--taken')
    expect(wrapper.findAll('.row-cards .motion-card')).toHaveLength(2)
    expect(wrapper.get('[data-row-index="0"] [data-card-number="30"]').attributes('style')).toContain('--card-motion-delay')
    expect(wrapper.get('[data-row-index="3"] [data-card-number="62"]').attributes('style')).toContain('--card-motion-delay')
    expect(wrapper.get('.take-announcement').text()).toContain('增加 12 牛头分')
    expect(wrapper.get('.bullhead-game').attributes('data-animation-id')).toBe('7')
  })

  it('applies the modeled stagger to round-deal cards', () => {
    const dealt = baseGame({
      animation: {
        id: 3,
        kind: 'round_deal',
        roundNumber: 1,
        turnNumber: 1,
        revealed: [],
        steps: [],
        pendingChoice: null,
        complete: true,
      },
    })
    const wrapper = render(dealt)

    expect(wrapper.findAll('.hand-scroll .deal-card')).toHaveLength(10)
    expect(wrapper.get('.hand-scroll [data-card-number="1"]').attributes('style')).toContain('--deal-delay: 220ms')
    expect(wrapper.findAll('.row-cards .deal-card').length).toBeGreaterThan(0)
  })

  it('starts the next round from the stable summary', async () => {
    const summaryGame = baseGame({
      sceneId: 'round.summary',
      stage: 'round_summary',
      hand: [],
      actions: ['next_round'],
      canSelect: false,
      canStartNextRound: true,
      roundSummary: {
        roundNumber: 1,
        penalties: { p1: 3, p2: 12, p3: 8 },
        totals: { p1: 3, p2: 12, p3: 8 },
        leaderIds: ['p1'],
        thresholdReached: false,
      },
    })
    const wrapper = render(summaryGame)

    await buttonWithText(wrapper, '开始下一轮').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('next_round', { roundNumber: 1 })
  })

  it('shows shared rules and closes the in-plugin dialog', async () => {
    const wrapper = render()

    await buttonWithText(wrapper, '规则').trigger('click')
    expect(wrapper.get('.rules-sheet').text()).toContain('低牌选行')
    expect(wrapper.get('.rules-sheet').text()).toContain('55 = 7 分')
    await wrapper.get('button[aria-label="关闭规则"]').trigger('click')
    expect(wrapper.find('.rules-overlay').exists()).toBe(false)
  })

  it('keeps spectators out of the private hand surface', () => {
    const publicGame = baseGame({ hand: [], actions: [], canSelect: false })
    const wrapper = mount(GameView, {
      props: { snapshot: snapshot(publicGame, 'playing', 'spectator') },
    })

    expect(wrapper.find('.hand-panel').exists()).toBe(false)
    expect(wrapper.get('.spectator-note').text()).toContain('不展示任何玩家手牌')
  })

  it('renders final ranking and uses the host rematch action', async () => {
    const finished = baseGame({
      sceneId: 'game.finished',
      stage: 'finished',
      hand: [],
      actions: [],
      canSelect: false,
      rankings: ['p1', 'p3', 'p2'],
      players: baseGame().players.map((player, index) => ({
        ...player,
        rank: [1, 3, 2][index]!,
        totalPenalty: [18, 70, 35][index]!,
      })),
    })
    const wrapper = render(finished, 'finished')

    expect(wrapper.get('.final-panel').text()).toContain('青角')
    expect(wrapper.get('.final-panel').text()).toContain('18 分')
    await buttonWithText(wrapper, '再来一局').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
  })
})
