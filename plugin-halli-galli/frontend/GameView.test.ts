import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import BellButton from './components/BellButton.vue'
import FruitCard from './components/FruitCard.vue'
import MotionLayer from './components/MotionLayer.vue'
import GameView from './GameView.vue'
import type {
  AnimationCue,
  FruitCardView,
  FruitId,
  HalliGalliEvent,
  HalliGalliPlayerView,
  HalliGalliResult,
  HalliGalliView,
} from './types'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async () => true),
  restart: vi.fn(async () => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
  usePluginFullscreen: () => ({ isFullscreen: false, isSupported: true, toggle: vi.fn() }),
}))

enableAutoUnmount(afterEach)

const specs = {
  banana: { name: '香蕉', shape: 'crescent-stem', pattern: 'diagonal-stripe', palette: { base: '#F3C94A', dark: '#8A6512', light: '#FFF1A8' } },
  strawberry: { name: '草莓', shape: 'seeded-heart', pattern: 'dot-seeds', palette: { base: '#E9545B', dark: '#8F2330', light: '#FFC0BD' } },
  lime: { name: '青柠', shape: 'segmented-round', pattern: 'radial-wedge', palette: { base: '#79B94B', dark: '#386A28', light: '#C8E89D' } },
  plum: { name: '李子', shape: 'oval-leaf', pattern: 'offset-highlight', palette: { base: '#7D5AA6', dark: '#432965', light: '#CDB8E8' } },
} as const

function card(fruitId: FruitId, fruitCount: number): FruitCardView {
  const spec = specs[fruitId]
  return {
    faceId: `face-${fruitId}-${fruitCount}`,
    fruitId,
    fruitCount,
    copies: ({ 1: 5, 2: 3, 3: 3, 4: 2, 5: 1 } as Record<number, number>)[fruitCount],
    labelZh: `${spec.name} ×${fruitCount}`,
    altZh: `${fruitCount} 个${spec.name}`,
    shape: spec.shape,
    pattern: spec.pattern,
    palette: spec.palette,
  }
}

function players(count: number): HalliGalliPlayerView[] {
  const names = ['阿梨', '白川', '青禾', '赤岩', '云雀', '墨川']
  const fruits: FruitId[] = ['banana', 'banana', 'strawberry', 'lime', 'plum', 'strawberry']
  const amounts = [2, 3, 4, 1, 2, 1]
  return Array.from({ length: count }, (_, index) => ({
    id: `p${index + 1}`,
    name: names[index],
    seat: index,
    relativeSeat: index,
    isSelf: index === 0,
    isCurrent: index === 0,
    connected: true,
    status: 'eligible',
    displayStatus: index === 0 ? 'current_turn' : 'eligible',
    eliminationReason: null,
    drawCount: 11,
    discardCount: 1,
    ownedCount: 12,
    topCard: card(fruits[index], amounts[index]),
  }))
}

function event(overrides: Partial<HalliGalliEvent> = {}): HalliGalliEvent {
  return {
    seq: 1,
    type: 'card_flipped',
    cue: 'card_flip',
    actorPlayerId: 'p1',
    targetPlayerIds: [],
    messageZh: '阿梨翻开了 2 个香蕉',
    boardEpoch: 12,
    data: { card: card('banana', 2) },
    ...overrides,
  }
}

function baseGame(count = 4, overrides: Partial<HalliGalliView> = {}): HalliGalliView {
  const members = players(count)
  const catalog = (Object.keys(specs) as FruitId[]).flatMap(fruitId => (
    [1, 2, 3, 4, 5].map(amount => card(fruitId, amount))
  ))
  const firstEvent = event()
  const base: HalliGalliView = {
    schemaVersion: 1,
    modelVersion: '1.0.0',
    profileId: 'official_last_bell',
    sceneId: 'playing_self_turn',
    stage: 'playing',
    revision: 7,
    turnNumber: 11,
    boardEpoch: 12,
    startingPlayerId: 'p1',
    currentPlayerId: 'p1',
    selfPlayerId: 'p1',
    finalDuelArmed: count === 2,
    earliestNextFlipAtMs: 0,
    noProgressDeadlineMs: null,
    players: members,
    rules: { playerMin: 2, playerMax: 6, deckSize: 56, bellTarget: 5, profileId: 'official_last_bell', minimumFlipDelayMs: 350, noProgressTimeoutMs: 10_000, faithfulCounting: true },
    actions: { canFlip: true, canFlipWhenReady: true, canRing: true, canSettleNoProgress: false, flipDisabledReason: null, ringDisabledReason: null },
    bell: { boardEpoch: 12, enabled: true, lastResolution: null },
    cardCatalog: catalog,
    fruitLegend: (Object.keys(specs) as FruitId[]).map(fruitId => ({ fruitId, nameZh: specs[fruitId].name, shape: specs[fruitId].shape, palette: specs[fruitId].palette })),
    events: [firstEvent],
    latestEvent: firstEvent,
    result: null,
  }
  return { ...base, ...overrides, actions: { ...base.actions, ...(overrides.actions ?? {}) } }
}

function snapshot(game = baseGame(), phase: 'playing' | 'finished' = 'playing', spectator = false): ArcadeSnapshot {
  return {
    revision: game.revision,
    roomCode: 'HALLI', gameKey: 'plugin-halli-galli', gameName: '德国心脏病', phase,
    statsEligible: true, options: { rulesProfile: 'official_last_bell' }, hostId: 'p1',
    self: { id: 'p1', name: '阿梨', seat: 0 },
    viewer: { mode: spectator ? 'spectator' : 'player', id: 'p1', name: '阿梨', targetPlayerId: 'p1' },
    players: game.players.map(player => ({ id: player.id, name: player.name, seat: player.seat, connected: player.connected, isHost: player.id === 'p1' })),
    requiredPlayers: game.players.length, minimumPlayers: 2, roundNumber: 1,
    winner: phase === 'finished' ? 'cards' : null,
    winnerPlayerIds: phase === 'finished' ? game.result?.winnerPlayerIds ?? [] : [],
    winReason: phase === 'finished' ? game.result?.reasonZh ?? '' : null,
    actions: { canStart: false, canRestart: phase === 'finished', canAct: phase === 'playing' && !spectator },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] }, game,
  } as unknown as ArcadeSnapshot
}

function render(game = baseGame(), phase: 'playing' | 'finished' = 'playing', spectator = false) {
  return mount(GameView, { props: { snapshot: snapshot(game, phase, spectator) } })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('crypto', { randomUUID: () => '00000000-0000-4000-8000-000000000001' })
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('browser-filling 2–6 player scene', () => {
  it.each([2, 3, 4, 5, 6])('renders every top card simultaneously for %i players', (count) => {
    const wrapper = render(baseGame(count))
    expect(wrapper.get('.halli-galli-game').attributes('data-layout')).toBe('browser-fill')
    expect(wrapper.get('.halli-galli-game').attributes('data-player-count')).toBe(String(count))
    expect(wrapper.findAll('.player-seat')).toHaveLength(count)
    expect(wrapper.findAll('[data-zone="top_discard"] .fruit-card')).toHaveLength(count)
    expect(wrapper.findAll('[data-relative-seat]')).toHaveLength(count)
    expect(wrapper.get('[data-zone="bell_zone"]').attributes('disabled')).toBeUndefined()
  })

  it('never displays aggregate fruit totals or highlights the answer', () => {
    const wrapper = render()
    expect(wrapper.text()).not.toContain('香蕉 5')
    expect(wrapper.text()).not.toContain('正确答案')
    expect(wrapper.find('[data-zone="fruit_totals"]').exists()).toBe(false)
    expect(wrapper.find('.exact-five-highlight').exists()).toBe(false)
  })

  it('renders last-chance and eliminated states with text, not color alone', () => {
    const game = baseGame()
    game.players[1] = { ...game.players[1], drawCount: 0, displayStatus: 'last_chance' }
    game.players[2] = { ...game.players[2], drawCount: 0, status: 'eliminated', displayStatus: 'eliminated', eliminationReason: 'discard-captured' }
    const wrapper = render(game)
    expect(wrapper.get('[data-player-id="p2"]').text()).toContain('无牌 · 仍可抢铃')
    expect(wrapper.get('[data-player-id="p3"]').text()).toContain('已退出')
  })
})

describe('fine card model', () => {
  it.each((Object.keys(specs) as FruitId[]).flatMap(fruitId => [1, 2, 3, 4, 5].map(amount => [fruitId, amount] as const))) (
    'renders %s ×%i with exactly the modeled number of vector symbols',
    (fruitId, amount) => {
      const wrapper = mount(FruitCard, { props: { card: card(fruitId, amount) } })
      expect(wrapper.get('.fruit-card').attributes('data-card-face')).toBe(`face-${fruitId}-${amount}`)
      expect(wrapper.findAll('.fruit-symbol')).toHaveLength(amount)
      expect(wrapper.text()).toContain(`×${amount}`)
    },
  )

  it('uses a neutral back that contains no future fruit identity', () => {
    const wrapper = mount(FruitCard, { props: { faceDown: true } })
    expect(wrapper.get('.fruit-card').attributes('data-fruit')).toBe('hidden')
    expect(wrapper.find('.back-frame').exists()).toBe(true)
    expect(wrapper.find('.fruit-field').exists()).toBe(false)
  })

  it('shows all 20 modeled faces in the rules drawer', async () => {
    const wrapper = render()
    await wrapper.get('button[aria-label="打开规则说明"]').trigger('click')
    expect(wrapper.findAll('.catalog-grid .fruit-card')).toHaveLength(20)
    expect(wrapper.text()).toContain('6 或 10 都不算')
    expect(wrapper.text()).toContain('最终二人误按')
  })
})

describe('input protocol and race safeguards', () => {
  it('submits a versioned flip through the deck control', async () => {
    const wrapper = render()
    await wrapper.get('[data-action="flip-deck"]').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('flip_card', {
      actionId: 'flip-00000000-0000-4000-8000-000000000001',
      revision: 7,
      expectedBoardEpoch: 12,
    })
  })

  it('routes Space to the bell and ignores repeat or same-epoch duplicates', async () => {
    const wrapper = render()
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', repeat: false, bubbles: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', repeat: true, bubbles: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', repeat: false, bubbles: true }))
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledTimes(1)
    expect(pluginActions.action).toHaveBeenCalledWith('ring_bell', {
      actionId: 'bell-00000000-0000-4000-8000-000000000001',
      boardEpoch: 12,
      inputMethod: 'keyboard',
    })
    wrapper.unmount()
  })

  it('uses pointerdown for the central bell without a duplicate click', async () => {
    const wrapper = mount(BellButton, { props: { enabled: true } })
    const pointerEvent = new MouseEvent('pointerdown', { button: 0, bubbles: true })
    Object.defineProperty(pointerEvent, 'pointerType', { value: 'mouse' })
    wrapper.get('button').element.dispatchEvent(pointerEvent)
    wrapper.get('button').element.dispatchEvent(new MouseEvent('click', { detail: 1, bubbles: true }))
    await nextTick()
    expect(wrapper.emitted('ring')).toHaveLength(1)
    expect(wrapper.emitted('ring')?.[0]).toEqual(['pointer'])
  })

  it('shows an immediate local bell wave before the server response', async () => {
    const wrapper = render()
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-animation-cue="bell_press_local"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('keeps a spectator completely read-only', async () => {
    const wrapper = render(baseGame(), 'playing', true)
    expect(wrapper.get('[data-action="ring-bell"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-action="flip-card"]').attributes('disabled')).toBeDefined()
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true }))
    await flushPromises()
    expect(pluginActions.action).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})

describe('settlement and animation presentation', () => {
  const cues: AnimationCue[] = [
    'round_deal', 'card_flip', 'bell_press_local', 'bell_confirmed',
    'collect_piles', 'penalty_transfer', 'player_eliminated',
    'final_duel_armed', 'result_enter',
  ]

  it.each(cues)('maps %s to a non-interactive motion layer', (cue) => {
    const motionEvent = event({
      cue,
      type: cue,
      targetPlayerIds: ['p2'],
      data: {
        card: card('banana', 3), winnerPlayerId: 'p2',
        sourceCounts: { p1: 2, p2: 1, p3: 1, p4: 1 },
        penalties: [{ toPlayerId: 'p2', count: 1 }, { toPlayerId: 'p3', count: 1 }],
      },
    })
    const wrapper = mount(MotionLayer, { props: { event: motionEvent, players: players(4) } })
    expect(wrapper.get('.motion-layer').attributes('data-animation-cue')).toBe(cue)
    expect(wrapper.get('.motion-layer').classes()).toContain(`cue-${cue.replaceAll('_', '-')}`)
  })

  it('queues bell confirmation before a newly committed collection animation', async () => {
    vi.useFakeTimers()
    const wrapper = render()
    await nextTick()
    const second = event({
      seq: 2, type: 'bell_correct', cue: 'collect_piles', actorPlayerId: 'p2', targetPlayerIds: [],
      messageZh: '白川正确抢铃，收走 8 张明牌',
      data: { winnerPlayerId: 'p2', capturedCount: 8, sourceCounts: { p1: 2, p2: 2, p3: 2, p4: 2 } },
    })
    const updated = baseGame(4, { events: [event(), second], latestEvent: second, boardEpoch: 13 })
    vi.advanceTimersByTime(300)
    await wrapper.setProps({ snapshot: snapshot(updated) })
    vi.advanceTimersByTime(240)
    await nextTick()
    expect(wrapper.find('[data-animation-cue="bell_confirmed"]').exists()).toBe(true)
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(wrapper.find('[data-animation-cue="collect_piles"]').exists()).toBe(true)
  })

  it('renders shared winners and restarts through the host action', async () => {
    const result: HalliGalliResult = {
      reasonCode: 'final_wrong_bell', reasonZh: '最终二人误按后结算', winnerPlayerIds: ['p1', 'p2'], sharedWin: true,
      rows: [
        { playerId: 'p1', name: '阿梨', seat: 0, status: 'eligible', drawCount: 28, discardCount: 0, totalCount: 28, rank: 1, won: true },
        { playerId: 'p2', name: '白川', seat: 1, status: 'eligible', drawCount: 28, discardCount: 0, totalCount: 28, rank: 1, won: true },
      ],
    }
    const game = baseGame(2, { stage: 'finished', sceneId: 'finished', currentPlayerId: null, result })
    const wrapper = render(game, 'finished')
    expect(wrapper.text()).toContain('并列获胜')
    expect(wrapper.findAll('.ranking .winner')).toHaveLength(2)
    await wrapper.get('[data-action="restart"]').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
  })
})
