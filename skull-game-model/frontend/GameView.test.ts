import { flushPromises, mount } from '@vue/test-utils'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import type { SkullGameView, SkullPlayerView, ThemeSlug } from './types'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async (
    _actionName: string,
    _payload: Record<string, unknown> = {},
  ) => true),
  rapidAction: vi.fn(async (
    _actionName: string,
    _payload: Record<string, unknown> = {},
  ) => true),
  restart: vi.fn(async () => true),
  publishSpectatorFrame: vi.fn(() => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
}))

const themeSlugs: ThemeSlug[] = ['ember', 'tide', 'moss', 'orchid', 'ochre', 'slate']
const themeLabels = ['余烬', '潮汐', '苔原', '兰影', '赭石', '岩板']

function players(count = 6): SkullPlayerView[] {
  return Array.from({ length: count }, (_, index) => ({
    id: 'p' + (index + 1),
    displayName: '玩家' + (index + 1),
    seat: index,
    status: 'active',
    challengeWins: index === 0 ? 1 : 0,
    matSide: index === 0 ? 'flower' : 'blank',
    lastChanceUsed: false,
    passedBid: false,
    handCount: index === 0 ? 2 : 3,
    stack: [{
      id: 'opaque-p' + (index + 1) + '-stack-0',
      kind: index === 0 ? 'flower' : 'unknown',
      origin: 'personal',
      faceUp: false,
      knowledge: index === 0 ? 'self' : 'hidden',
    }],
    removedCount: 0,
    removed: [],
    personalDiscCount: 4,
    theme: {
      id: 'player-' + (index + 1),
      slug: themeSlugs[index]!,
      label: themeLabels[index]!,
      patternCode: String.fromCharCode(65 + index) + (index + 1),
    },
  }))
}

function game(overrides: Partial<SkullGameView> = {}): SkullGameView {
  const playerViews = players()
  const base: SkullGameView = {
    schemaVersion: 1,
    gameKey: 'skull',
    sceneId: 'round.commit',
    phase: 'round_setup',
    rules: { targetWins: 2, lastChanceEnabled: true },
    players: playerViews,
    activePlayerIds: playerViews.map((player) => player.id),
    hand: [
      { id: 'p1-flower-1', kind: 'flower', origin: 'personal', faceUp: false, knowledge: 'self' },
      { id: 'p1-skull', kind: 'skull', origin: 'personal', faceUp: false, knowledge: 'self' },
    ],
    round: {
      number: 1,
      firstPlayerId: 'p2',
      currentPlayerId: null,
      committedCount: 5,
      activePlayerCount: 6,
      hasCommitted: false,
      firstPlayerCommitsLast: true,
      totalPlaced: 6,
      currentBid: 0,
      highBidderId: null,
      passedPlayerIds: [],
      challengerId: null,
      targetBid: 0,
      revealedCount: 0,
      failed: false,
      skullOwnerId: null,
      lastChanceHolderId: null,
      lastChanceExpiresAfterRound: null,
      penaltyMode: null,
      penaltyChooserId: null,
      penaltySlots: [],
      selfPenaltyCandidates: [],
      nextFirstPlayerDecisionBy: null,
      eligibleNextFirstPlayerIds: [],
    },
    actions: ['commit_initial'],
    legalRevealOwnerIds: [],
    minimumBid: 1,
    maximumBid: 6,
    lastPrivatePenalty: null,
    publicReveals: [],
    history: [
      { type: 'round_start', message: '第 1 轮开始，玩家2 为首家' },
      { type: 'game_start', message: '六名玩家围桌入座' },
    ],
    stats: {
      roundsPlayed: 1,
      activePlayers: 6,
      eliminatedPlayers: 0,
      challengeWins: { p1: 1, p2: 0, p3: 0, p4: 0, p5: 0, p6: 0 },
    },
    result: null,
  }
  return {
    ...base,
    ...overrides,
    rules: { ...base.rules, ...(overrides.rules ?? {}) },
    round: { ...base.round, ...(overrides.round ?? {}) },
    stats: { ...base.stats, ...(overrides.stats ?? {}) },
  }
}

function snapshot(gameView = game(), phase: 'playing' | 'finished' = 'playing'): ArcadeSnapshot {
  return {
    revision: 1,
    roomCode: 'SKUL',
    gameKey: 'plugin-skull',
    gameName: '骷髅牌',
    phase,
    statsEligible: true,
    options: { lastChanceEnabled: true },
    hostId: 'p1',
    self: { id: 'p1', name: '玩家1', seat: 0 },
    viewer: { mode: 'player', id: 'p1', name: '玩家1', targetPlayerId: 'p1' },
    players: gameView.players.map((player, index) => ({
      id: player.id,
      name: player.displayName,
      seat: index,
      connected: true,
      isHost: index === 0,
    })),
    requiredPlayers: gameView.players.length,
    minimumPlayers: 3,
    roundNumber: 1,
    winner: phase === 'finished' ? 'skull' : null,
    winnerPlayerIds: phase === 'finished' ? ['p1'] : [],
    winReason: phase === 'finished' ? '玩家1 率先完成两次无骷髅挑战' : null,
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
    game: gameView,
  } as unknown as ArcadeSnapshot
}

function buttonWithText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll('button').find((candidate) => candidate.text().includes(text))
  if (!button) throw new Error('Missing button: ' + text)
  return button
}

describe('skull immersive game view', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it.each([3, 4, 5, 6])('renders %i modeled player seats and a full-width private hand', (count) => {
    const playerViews = players(count)
    const modeledGame = game({
      players: playerViews,
      activePlayerIds: playerViews.map((player) => player.id),
      stats: { activePlayers: count } as SkullGameView['stats'],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(modeledGame) } })

    expect(wrapper.findAll('.player-seat')).toHaveLength(count)
    expect(wrapper.findAll('.hand-disc')).toHaveLength(2)
    expect(wrapper.get('.skull-game').attributes('data-game')).toBe('skull')
    expect(wrapper.text()).toContain('计入战绩')
    expect(wrapper.text()).toContain('余烬')
    expect(wrapper.text()).toContain(themeLabels[count - 1])
    wrapper.unmount()
  })

  it('locks an initial disc by sending only its private id', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('[data-disc-id="p1-flower-1"]').trigger('click')
    await buttonWithText(wrapper, '锁定本轮暗置').trigger('click')
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledWith(
      'commit_initial',
      { discId: 'p1-flower-1' },
    )
    wrapper.unmount()
  })

  it('opens a bid and reveals by owner region rather than a hidden card id', async () => {
    const placement = game({
      phase: 'placement',
      sceneId: 'round.place-or-bid',
      actions: ['place_disc', 'open_bid'],
      round: { currentPlayerId: 'p1' } as SkullGameView['round'],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(placement) } })

    await wrapper.get('button[aria-label="叫价加一"]').trigger('click')
    await buttonWithText(wrapper, '开叫').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenLastCalledWith('open_bid', { count: 2 })
    wrapper.unmount()

    const reveal = game({
      phase: 'reveal',
      sceneId: 'challenge.reveal-others',
      actions: ['reveal_disc'],
      legalRevealOwnerIds: ['p2'],
      round: {
        challengerId: 'p1',
        currentPlayerId: 'p1',
        targetBid: 2,
        revealedCount: 1,
      } as SkullGameView['round'],
    })
    const revealWrapper = mount(GameView, { props: { snapshot: snapshot(reveal) } })
    await revealWrapper.get('[data-player-id="p2"] .stack-zone').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenLastCalledWith('reveal_disc', { ownerId: 'p2' })
    expect(pluginActions.action.mock.calls.at(-1)?.[1]).not.toHaveProperty('discId')
    revealWrapper.unmount()
  })

  it('presents pass as temporary for the latest bid', async () => {
    const biddingPlayers = players().map((player, index) => (
      index === 2 ? { ...player, passedBid: true } : player
    ))
    const bidding = game({
      phase: 'bidding',
      sceneId: 'bid.raise-or-pass',
      players: biddingPlayers,
      actions: ['raise_bid', 'pass_bid'],
      round: {
        currentPlayerId: 'p1',
        currentBid: 3,
        highBidderId: 'p2',
        passedPlayerIds: ['p3'],
      } as SkullGameView['round'],
      minimumBid: 4,
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(bidding) } })

    expect(wrapper.text()).toContain('暂不跟价只对当前叫价有效')
    expect(wrapper.get('[data-player-id="p3"] .seat-flags').text()).toContain('本价不跟')
    await buttonWithText(wrapper, '暂不加价').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('pass_bid', {})
    wrapper.unmount()
  })

  it('renders opaque blind slots and submits only the selected slot', async () => {
    const penalty = game({
      phase: 'penalty',
      sceneId: 'penalty.blind-pick',
      actions: ['choose_penalty'],
      round: {
        penaltyMode: 'blind',
        penaltyChooserId: 'p1',
        penaltySlots: ['opaque-1-1', 'opaque-1-2', 'opaque-1-3'],
      } as SkullGameView['round'],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(penalty) } })

    expect(wrapper.findAll('.penalty-slots button')).toHaveLength(3)
    await wrapper.get('[data-slot-id="opaque-1-2"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith(
      'choose_penalty',
      { slotId: 'opaque-1-2' },
    )
    wrapper.unmount()
  })

  it('keeps the public last-chance flower identifiable after reveal', () => {
    const lastChance = game({
      phase: 'reveal',
      sceneId: 'challenge.reveal-own',
      players: players().map((player, index) => index === 0
        ? {
            ...player,
            handCount: 0,
            stack: [{
              id: 'p1-last-chance-2',
              kind: 'last_chance_flower',
              origin: 'last_chance',
              faceUp: true,
              knowledge: 'public',
            }],
          }
        : player),
      round: {
        challengerId: 'p1',
        currentPlayerId: 'p1',
        targetBid: 1,
        revealedCount: 1,
        lastChanceHolderId: 'p1',
        lastChanceExpiresAfterRound: 1,
      } as SkullGameView['round'],
      actions: [],
      hand: [],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(lastChance) } })

    expect(wrapper.get('.last-chance-face').text()).toContain('安全花牌')
    wrapper.unmount()
  })

  it('shows every player remaining card total with the hand and table breakdown', () => {
    const countedPlayers = players().map((player, index) => {
      const personalDiscCount = Math.max(0, 4 - index)
      return {
        ...player,
        handCount: Math.max(0, personalDiscCount - 1),
        stack: personalDiscCount > 0 ? player.stack : [],
        removedCount: 4 - personalDiscCount,
        personalDiscCount,
      }
    })
    const wrapper = mount(GameView, {
      props: { snapshot: snapshot(game({ players: countedPlayers })) },
    })

    const counters = wrapper.findAll('.seat-counters')
    expect(counters).toHaveLength(6)
    expect(wrapper.get('[data-player-id="p1"] .seat-card-total').text()).toBe('剩余 4 张')
    expect(wrapper.get('[data-player-id="p2"] .seat-card-total').text()).toBe('剩余 3 张')
    expect(wrapper.get('[data-player-id="p2"] .seat-card-detail').text()).toBe('手持 2 · 已叠 1 · 失去 1')
    expect(wrapper.get('[data-player-id="p6"] .seat-card-total').text()).toBe('剩余 0 张')
    wrapper.unmount()
  })

  it('shows the ordered public reveal process with flower and skull results', () => {
    const revealPlayers = players().map((player, index) => index === 1
      ? {
          ...player,
          stack: [{
            id: 'opaque-p2-stack-0',
            kind: 'skull' as const,
            origin: 'personal' as const,
            faceUp: true,
            knowledge: 'public' as const,
          }],
        }
      : player)
    const revealed = game({
      phase: 'penalty',
      sceneId: 'penalty.blind-pick',
      players: revealPlayers,
      publicReveals: [
        {
          eventId: 'reveal-2-1',
          round: 2,
          index: 1,
          challengerId: 'p1',
          ownerId: 'p1',
          kind: 'flower',
          message: '玩家1 翻开 玩家1 的牌堆顶部：花牌',
        },
        {
          eventId: 'reveal-2-2',
          round: 2,
          index: 2,
          challengerId: 'p1',
          ownerId: 'p2',
          kind: 'skull',
          message: '玩家1 翻开 玩家2 的牌堆顶部：骷髅牌',
        },
      ],
      round: {
        challengerId: 'p1',
        currentPlayerId: 'p2',
        targetBid: 2,
        revealedCount: 2,
        failed: true,
        skullOwnerId: 'p2',
      } as SkullGameView['round'],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(revealed) } })

    const broadcast = wrapper.get('.reveal-broadcast')
    expect(broadcast.attributes('aria-label')).toBe('全员可见的翻牌过程')
    expect(broadcast.text()).toContain('第 2 轮翻牌公示')
    expect(broadcast.text()).toContain('花牌')
    expect(broadcast.text()).toContain('骷髅牌')
    expect(broadcast.text()).toContain('玩家2 的牌')
    expect(broadcast.findAll('li')).toHaveLength(2)
    expect(broadcast.findAll('li')[1]?.classes()).toContain('latest')
    expect(wrapper.get('[data-player-id="p2"] .table-disc').classes()).toContain('revealed')
    wrapper.unmount()
  })

  it('shows the private result of the most recent penalty', () => {
    const penalized = game({
      lastPrivatePenalty: {
        kind: 'skull',
        message: '你失去了自己的骷髅牌',
      },
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(penalized) } })

    expect(wrapper.get('.private-penalty-note').text()).toContain('最近一次秘密处罚')
    expect(wrapper.get('.private-penalty-note').text()).toContain('你失去了自己的骷髅牌')
    wrapper.unmount()
  })

  it('uses a browser-filling layout without requesting native fullscreen', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.get('.skull-game').attributes('data-layout')).toBe('browser-fill')
    expect(wrapper.find('.fullscreen-button').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([3, 4, 5, 6])('renders the recorded settlement for a %i-player game', async (count) => {
    const settledPlayers = players(count).map((player, index) => ({
      ...player,
      challengeWins: index === 0 ? 2 : 0,
    }))
    const finishedGame = game({
      phase: 'finished',
      sceneId: 'game.finished',
      players: settledPlayers,
      activePlayerIds: settledPlayers.map((player) => player.id),
      actions: [],
      stats: {
        roundsPlayed: 2,
        activePlayers: count,
        eliminatedPlayers: 0,
        challengeWins: Object.fromEntries(
          settledPlayers.map((player) => [player.id, player.challengeWins]),
        ),
      },
      result: {
        winnerIds: ['p1'],
        reason: 'two_challenges',
        summary: '玩家1 率先完成两次无骷髅挑战',
        statsEligible: true,
      },
    })
    const resultWrapper = mount(GameView, {
      props: { snapshot: snapshot(finishedGame, 'finished') },
    })
    expect(resultWrapper.findAll('.player-seat')).toHaveLength(count)
    expect(resultWrapper.text()).toContain('玩家1')
    expect(resultWrapper.text()).toContain('胜场与胜率已保存')
    await buttonWithText(resultWrapper, '再来一局').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
    resultWrapper.unmount()
  })
})
