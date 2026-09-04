import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import EffectLayer from './components/EffectLayer.vue'
import type {
  CardCatalogItem,
  LoveCard,
  LoveEvent,
  LoveLetterView,
  PendingChoiceView,
} from './types'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async () => true),
  restart: vi.fn(async () => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
  usePluginFullscreen: () => ({ isFullscreen: false, isSupported: false, toggle: vi.fn() }),
}))

const catalogSeed = [
  ['spy', 0, '间谍', 'Spy', '眼', '#4B5563', '暗封'],
  ['guard', 1, '卫兵', 'Guard', '盾', '#9A3412', '盘问'],
  ['priest', 2, '牧师', 'Priest', '烛', '#6D28D9', '窥信'],
  ['baron', 3, '男爵', 'Baron', '衡', '#1D4ED8', '比点'],
  ['handmaid', 4, '侍女', 'Handmaid', '封', '#0F766E', '护信'],
  ['prince', 5, '王子', 'Prince', '诏', '#C2410C', '重写'],
  ['chancellor', 6, '大臣', 'Chancellor', '策', '#0369A1', '筹谋'],
  ['king', 7, '国王', 'King', '冠', '#854D0E', '易手'],
  ['queen', 7.5, '皇后', 'Queen', '后', '#7E22CE', '御问'],
  ['countess', 8, '伯爵夫人', 'Countess', '扇', '#9D174D', '缄默'],
  ['princess', 9, '公主', 'Princess', '玺', '#BE123C', '失信'],
] as const

const catalog: CardCatalogItem[] = catalogSeed.map(([typeId, value, nameZh, nameEn, symbol, color, motif], index) => ({
  typeId, value, nameZh, nameEn, symbol, color, motif,
  count: typeId === 'guard' ? 6 : typeId === 'king' || typeId === 'queen' || typeId === 'countess' || typeId === 'princess' ? 1 : 2,
  effectZh: `${nameZh}的完整牌效说明 ${index + 1}`,
}))

function card(typeId: string, suffix = '01'): LoveCard {
  const spec = catalog.find(item => item.typeId === typeId)!
  return { ...spec, id: `${typeId}-${suffix}` }
}

function baseGame(overrides: Partial<LoveLetterView> = {}): LoveLetterView {
  const players = [
    { id: 'p1', name: '阿梨', seat: 0, favorTokens: 2, favorTarget: 4, roundStatus: 'active' as const, protected: false, handCount: 2, visibleHand: [card('guard'), card('queen')], played: [{ card: card('priest', 'played'), turnNumber: 2, reason: 'played' }], isCurrent: true },
    { id: 'p2', name: '白川', seat: 1, favorTokens: 1, favorTarget: 4, roundStatus: 'active' as const, protected: true, handCount: 1, visibleHand: [], played: [{ card: card('handmaid', 'played'), turnNumber: 3, reason: 'played' }], isCurrent: false },
    { id: 'p3', name: '沉舟', seat: 2, favorTokens: 0, favorTarget: 4, roundStatus: 'active' as const, protected: false, handCount: 1, visibleHand: [], played: [{ card: card('spy', 'played'), turnNumber: 1, reason: 'played' }], isCurrent: false },
    { id: 'p4', name: '冬青', seat: 3, favorTokens: 3, favorTarget: 4, roundStatus: 'active' as const, protected: false, handCount: 1, visibleHand: [], played: [], isCurrent: false },
  ]
  const base: LoveLetterView = {
    schemaVersion: 1,
    modelVersion: '1.2.0',
    profileId: 'queen_22',
    sceneId: 'turn_play',
    stage: 'play',
    roundNumber: 2,
    turnNumber: 7,
    currentPlayerId: 'p1',
    startPlayerId: 'p3',
    deckCount: 8,
    sealedCardCount: 0,
    reserveAvailable: true,
    faceUpSetAside: [],
    players,
    cardCatalog: catalog,
    rules: { playerMin: 2, playerMax: 4, deckSize: 22, favorTarget: 4, finalCardSealed: true, roundEndsAtDeckCount: 1, queenValue: 7.5 },
    actions: ['play_card', 'resign'],
    legalCardIds: ['queen-01'],
    pendingChoice: null,
    privateInfo: { knownHands: [{ subjectPlayerId: 'p2', card: card('princess', 'known'), source: 'priest', acquiredTurn: 2, current: false }] },
    events: [{ seq: 1, kind: 'play_card', actorPlayerId: 'p1', targetPlayerIds: [], messageZh: '阿梨打出牧师', data: { card: card('priest', 'played') } }],
    latestEvent: { seq: 1, kind: 'play_card', actorPlayerId: 'p1', targetPlayerIds: [], messageZh: '阿梨打出牧师', data: { card: card('priest', 'played') } },
    roundSummary: null,
    gameWinnerIds: [],
  }
  return { ...base, ...overrides, rules: { ...base.rules, ...(overrides.rules ?? {}) } }
}

function snapshot(game = baseGame(), phase: 'playing' | 'finished' = 'playing'): ArcadeSnapshot {
  return {
    revision: 5,
    roomCode: 'LOVE',
    gameKey: 'plugin-love-letter',
    gameName: '情书 · 密封宫廷',
    phase,
    statsEligible: true,
    hostId: 'p1',
    self: { id: 'p1', name: '阿梨', seat: 0 },
    viewer: { mode: 'player', id: 'p1', name: '阿梨', targetPlayerId: 'p1' },
    players: game.players.map(player => ({ id: player.id, name: player.name, seat: player.seat, connected: true, isHost: player.id === 'p1' })),
    requiredPlayers: game.players.length,
    minimumPlayers: 2,
    roundNumber: game.roundNumber,
    winner: phase === 'finished' ? 'favor' : null,
    winnerPlayerIds: phase === 'finished' ? game.gameWinnerIds : [],
    winReason: phase === 'finished' ? '达到好感阈值' : null,
    actions: { canStart: false, canRestart: phase === 'finished', canAct: phase === 'playing' },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] }, game,
  } as unknown as ArcadeSnapshot
}

function render(game = baseGame(), phase: 'playing' | 'finished' = 'playing') {
  return mount(GameView, { props: { snapshot: snapshot(game, phase) } })
}

function pendingChoice(overrides: Partial<PendingChoiceView> = {}): PendingChoiceView {
  return {
    kind: 'guess', sourceTypeId: 'guard', actorPlayerId: 'p1', isActor: true,
    choiceId: 'choice-2-7-8', promptZh: '选择目标并猜测角色',
    candidatePlayerIds: ['p3', 'p4'], candidateCardTypeIds: ['priest', 'queen', 'princess'], privateCards: [],
    ...overrides,
  }
}

beforeEach(() => vi.clearAllMocks())

describe('immersive court and refined card model', () => {
  it('renders a browser-filling four-seat scene with exact Queen value and hidden hands', () => {
    const wrapper = render()
    expect(wrapper.get('.love-letter-game').attributes('data-layout')).toBe('browser-fill')
    expect(wrapper.get('.love-letter-game').attributes('data-player-count')).toBe('4')
    expect(wrapper.findAll('.opponent-seat')).toHaveLength(3)
    expect(wrapper.findAll('.self-hand .character-card')).toHaveLength(2)
    const queen = wrapper.get('.self-hand [data-card-type="queen"]')
    expect(queen.attributes('data-card-value')).toBe('7.5')
    expect(queen.text()).toContain('7½')
    expect(queen.text()).toContain('皇后')
    expect(wrapper.findAll('.opponent-hand [data-card-type="back"]')).toHaveLength(3)
    expect(wrapper.text()).not.toContain('princess-known')
    expect(wrapper.text()).toContain('手牌已变化，仅作历史')
  })

  it('shows all eleven detailed cards in the rule drawer', async () => {
    const wrapper = render()
    await wrapper.get('button[aria-label="打开规则说明"]').trigger('click')
    expect(wrapper.findAll('.catalog-grid .character-card')).toHaveLength(11)
    expect(wrapper.text()).toContain('最后一张永不翻开')
    expect(wrapper.text()).toContain('2/3/4 人分别达到 6/5/4')
  })

  it('enforces the server-projected legal card and sends turn-numbered play', async () => {
    const wrapper = render()
    expect(wrapper.get('.self-hand [data-card-type="guard"]').attributes('disabled')).toBeDefined()
    await wrapper.get('.self-hand [data-card-type="queen"]').trigger('click')
    await wrapper.get('[data-action="play-card"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('play_card', { cardId: 'queen-01', turnNumber: 7 })
  })

  it('draws through the only deck control and includes current turn number', async () => {
    const game = baseGame({ stage: 'draw', sceneId: 'turn_draw', actions: ['draw_card', 'resign'], legalCardIds: [] })
    const wrapper = render(game)
    await wrapper.get('.draw-zone > button').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('draw_card', { turnNumber: 7 })
  })
})

describe('effect choice controls', () => {
  it('submits a combined Guard target and non-Guard guess', async () => {
    const choice = pendingChoice()
    const wrapper = render(baseGame({ stage: 'choice', sceneId: 'guard_choice', actions: ['resolve_choice', 'resign'], pendingChoice: choice, legalCardIds: [] }))
    await wrapper.get('.target-grid button:nth-child(1)').trigger('click')
    await wrapper.get('.guess-grid [data-card-type="queen"]').trigger('click')
    await wrapper.get('[data-action="resolve-choice"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('resolve_choice', {
      choiceId: choice.choiceId, targetPlayerId: 'p3', cardTypeId: 'queen', turnNumber: 7,
    })
  })

  it('submits a Prince self target', async () => {
    const choice = pendingChoice({ kind: 'target', sourceTypeId: 'prince', candidatePlayerIds: ['p1'], candidateCardTypeIds: [] })
    const wrapper = render(baseGame({ stage: 'choice', sceneId: 'target_choice', actions: ['resolve_choice', 'resign'], pendingChoice: choice }))
    await wrapper.get('.target-grid button').trigger('click')
    await wrapper.get('[data-action="resolve-choice"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('resolve_choice', {
      choiceId: choice.choiceId, targetPlayerId: 'p1', turnNumber: 7,
    })
  })

  it('keeps one Chancellor card and sends every other candidate in visible bottom order', async () => {
    const choice = pendingChoice({
      kind: 'chancellor', sourceTypeId: 'chancellor', candidatePlayerIds: [], candidateCardTypeIds: [],
      privateCards: [card('guard', 'c1'), card('queen', 'c2'), card('princess', 'c3')],
    })
    const wrapper = render(baseGame({ stage: 'choice', sceneId: 'chancellor_choice', actions: ['resolve_choice', 'resign'], pendingChoice: choice }))
    await wrapper.get('.choice-cards [data-card-type="queen"]').trigger('click')
    await wrapper.get('.bottom-order > button').trigger('click')
    await wrapper.get('[data-action="resolve-choice"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('resolve_choice', {
      choiceId: choice.choiceId,
      keepCardId: 'queen-c2',
      bottomCardIds: ['princess-c3', 'guard-c1'],
      turnNumber: 7,
    })
  })
})

describe('sealed round and game results', () => {
  const roundSummary = {
    roundNumber: 2, endReason: 'one-card-left' as const, roundWinnerIds: ['p1', 'p4'],
    revealedHands: [{ playerId: 'p1', card: card('queen', 'reveal') }, { playerId: 'p4', card: card('queen', 'tie') }],
    spyBonusPlayerId: 'p1', rewardDeltas: { p1: 2, p4: 1 }, deckCountAtEnd: 1,
    sealedCardCount: 1, sealedCardRevealed: false as const, reserveRevealed: false as const,
  }

  it('renders tied winners beside a face-down final card and advances the round', async () => {
    const wrapper = render(baseGame({ stage: 'round_summary', sceneId: 'round_result', currentPlayerId: null, actions: ['next_round', 'resign'], deckCount: 1, sealedCardCount: 1, roundSummary }))
    expect(wrapper.text()).toContain('最后一张仍在信封里')
    expect(wrapper.text()).toContain('身份永久保密')
    expect(wrapper.findAll('.revealed-row article.winner')).toHaveLength(2)
    expect(wrapper.find('.sealed-final [data-card-type="back"]').exists()).toBe(true)
    await wrapper.get('[data-action="next-round"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('next_round', { roundNumber: 2, turnNumber: 7 })
  })

  it('renders simultaneous match winners and restart', async () => {
    const game = baseGame({ stage: 'finished', sceneId: 'game_result', currentPlayerId: null, actions: [], gameWinnerIds: ['p1', 'p4'], roundSummary })
    const wrapper = render(game, 'finished')
    expect(wrapper.text()).toContain('阿梨、冬青 赢得宫廷好感')
    expect(wrapper.findAll('.final-favors .winner')).toHaveLength(2)
    await wrapper.get('.game-result button').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
  })
})

describe('animation mapping', () => {
  const animationKinds = [
    'round_deal', 'draw_card', 'play_card', 'spy_mark', 'guess_miss', 'guess_hit',
    'peek_hand', 'compare_hands', 'gain_protection', 'protection_expired', 'force_redraw',
    'prince_princess', 'chancellor_draw', 'chancellor_no_draw', 'bottom_cards',
    'trade_hands', 'queen_escape', 'princess_discard', 'no_legal_target', 'round_end', 'forfeit',
  ]

  it.each(animationKinds)('renders the %s animation without interactive collision surfaces', (kind) => {
    const event: LoveEvent = { seq: 10, kind, actorPlayerId: 'p1', targetPlayerIds: ['p2'], messageZh: `${kind} 动画`, data: {} }
    const wrapper = mount(EffectLayer, { props: { event } })
    expect(wrapper.get('.effect-layer').attributes('data-animation-kind')).toBe(kind)
    expect(wrapper.get('.effect-layer').classes()).toContain(`effect-${kind}`)
    expect(wrapper.get('.effect-path').attributes('aria-hidden')).toBe('true')
    expect(wrapper.text()).toContain(`${kind} 动画`)
  })

  it('queues a new snapshot event for visible cinematic playback', async () => {
    vi.useFakeTimers()
    const wrapper = render()
    await nextTick()
    expect(wrapper.find('[data-animation-kind="play_card"]').exists()).toBe(true)
    const updated = baseGame({
      events: [...baseGame().events, { seq: 2, kind: 'queen_escape', actorPlayerId: 'p1', targetPlayerIds: ['p2'], messageZh: '皇后弃牌重抽', data: {} }],
      latestEvent: { seq: 2, kind: 'queen_escape', actorPlayerId: 'p1', targetPlayerIds: ['p2'], messageZh: '皇后弃牌重抽', data: {} },
    })
    await wrapper.setProps({ snapshot: snapshot(updated) })
    vi.advanceTimersByTime(1120)
    await nextTick()
    expect(wrapper.find('[data-animation-kind="queen_escape"]').exists()).toBe(true)
    vi.useRealTimers()
  })
})
