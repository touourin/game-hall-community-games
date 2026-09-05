import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GameView from './GameView.vue'
import { advanceContinuousPosition } from './movement'
import type { BombGame, BombPlayer } from './types'


const mocks = vi.hoisted(() => ({
  action: vi.fn(),
  rapidAction: vi.fn(),
  restart: vi.fn(),
  toggle: vi.fn(),
  soundUnlock: vi.fn(),
  soundPlay: vi.fn(),
  soundDestroy: vi.fn(),
}))

vi.mock('@game-hall/plugin-sdk', async (original) => {
  const actual = await original<object>()
  const { ref } = await import('vue')
  return {
    ...actual,
    usePluginGameActions: () => ({
      action: mocks.action,
      rapidAction: mocks.rapidAction,
      restart: mocks.restart,
      publishSpectatorFrame: vi.fn(),
    }),
    usePluginFullscreen: () => ({
      isFullscreen: ref(false),
      isSupported: ref(true),
      toggle: mocks.toggle,
    }),
  }
})

vi.mock('./sound', () => ({
  createBombPeopleSound: () => ({
    unlock: mocks.soundUnlock,
    play: mocks.soundPlay,
    destroy: mocks.soundDestroy,
  }),
}))


function player(id: string, seat: number, name: string): BombPlayer {
  return {
    id, seat, name, color: seat ? '#4f8cff' : '#ff5a55', character: seat,
    x: seat ? 18 : 1, y: seat ? 18 : 1, facingX: 0, facingY: 1, moving: false,
    moveIntervalTicks: seat ? 12 : 7.8,
    movementSpeed: seat ? 5 : 7.692,
    carriedBombId: null,
    alive: true, eliminatedBy: null, eliminationReason: null, kills: seat ? 1 : 3,
    stats: { kills: seat ? 4 : 12, championships: seat ? 1 : 4, matches: 5, winRate: seat ? 20 : 80 },
    equipment: {
      bombCapacity: seat ? 1 : 3, blastRange: seat ? 2 : 4, speedLevel: seat ? 0 : 2,
      kick: !seat, punch: !seat, throw: !seat, timer: !seat, chain: false,
      magnet: false, ice: false, shieldCharges: seat ? 0 : 1,
      ghost: false, invincibleTicks: 0, cursedTicks: 0,
    },
  }
}


function snapshot(phase: ArcadeSnapshot['phase'] = 'playing'): ArcadeSnapshot {
  const maps = [
    { key: 'magma_crucible', name: '熔岩熔炉', subtitle: '均衡箱群', pace: '均衡', density: '中密度', spawnMode: 'standard', startingItems: [] },
    { key: 'sky_citadel', name: '云顶激斗场', subtitle: '近距离开局', pace: '激斗', density: '稀疏', spawnMode: 'close', startingItems: ['speed', 'kick'] },
  ]
  const board = Array.from({ length: 20 }, () => Array<number>(20).fill(0))
  board[0]![0] = 1
  board[0]![1] = 2
  const game: BombGame = {
    boardSize: 20, tick: 100, tickRate: 60, snapshotRate: 30,
    playerHitboxRadius: 0.3, solidHalfExtent: 0.48, bombHitboxRadius: 0.34,
    stage: phase === 'lobby' ? 'lobby' : phase === 'finished' ? 'finished' : 'active',
    stageTicksRemaining: 0, roundTicksRemaining: 1_200,
    collapsePlaced: 0, collapseTotal: 400, dangerCells: [],
    selectedMap: 'magma_crucible', nextMap: null, currentMap: maps[0]!, mapCatalog: maps,
    mapRotation: 'consensus_or_random_no_repeat', mapProposal: null, canProposeMap: false, canVoteMap: false,
    board, players: phase === 'lobby' ? [] : [player('p0', 0, '红队'), player('p1', 1, '蓝队')],
    bombs: [{ id: 1, ownerId: 'p0', creditPlayerId: 'p0', x: 3, y: 3, fuseTicks: 90, maxFuseTicks: 120, moving: false, motionX: 0, motionY: 0, carriedBy: null, remote: false }],
    items: [{ id: 1, kind: 'speed', x: 4, y: 4 }],
    flames: [{ x: 5, y: 5, remainingTicks: 4 }], iceTiles: [], events: [], effects: [],
    winnerId: null, clockLeaderId: 'p1', frozen: false, selfInputSequence: 0,
    controls: { move: 'WASD', bomb: 'Space', punch: 'Z', throw: 'X', timer: 'C', kick: 'automatic' },
    itemLabels: {
      bomb_up: '多一个炸弹', flame_up: '火焰增强', speed: '加速靴', kick: '脚踢雷',
      punch: '拳击手套', throw: '扔雷手套', timer: '遥控定时炸弹', chain: '连锁引线',
      shield: '能量护盾', skull: '骷髅诅咒', ghost: '幽灵相位', magnet: '磁力线圈',
      ice: '冰冻核心', swap: '传送交换', star: '无敌星盾',
    },
  }
  return {
    revision: 1, roomCode: 'BOMB', gameKey: 'plugin-bomb-people', gameName: '炸弹超人',
    phase, roundNumber: 1, hostId: 'p0', statsEligible: true,
    self: { id: 'p0', name: '红队', seat: 0 },
    viewer: { mode: 'player', id: 'p0', name: '红队', targetPlayerId: 'p0' },
    players: [
      { id: 'p0', name: '红队', seat: 0, connected: true, isHost: true },
      { id: 'p1', name: '蓝队', seat: 1, connected: true, isHost: false },
    ],
    actions: { canAct: phase === 'playing', canRestart: phase === 'finished' },
    winner: null, winnerPlayerIds: [], winReason: null, game,
  } as unknown as ArcadeSnapshot
}


function render(data = snapshot()) {
  return mount(GameView, {
    props: { snapshot: data },
    attachTo: document.body,
    global: { plugins: [createPinia()], stubs: { Teleport: true } },
  })
}

function playerPosition(piece: ReturnType<ReturnType<typeof render>['get']>): [number, number] {
  const transform = piece.attributes('style').match(
    /translate3d\((-?[\d.]+)%,\s*(-?[\d.]+)%,\s*0\)/,
  )
  if (!transform) throw new Error('player transform is missing')
  return [Number(transform[1]) / 100, Number(transform[2]) / 100]
}

function pointerEvent(type: string, pointerId: number, clientX = 0, clientY = 0) {
  const event = new MouseEvent(type, { bubbles: true, cancelable: true, clientX, clientY })
  Object.defineProperty(event, 'pointerId', { value: pointerId })
  return event
}


beforeEach(() => {
  vi.useFakeTimers()
  mocks.action.mockReset().mockResolvedValue(true)
  mocks.rapidAction.mockReset().mockResolvedValue(true)
  mocks.restart.mockReset().mockResolvedValue(true)
  mocks.toggle.mockReset()
  mocks.soundUnlock.mockReset()
  mocks.soundPlay.mockReset()
  mocks.soundDestroy.mockReset()
})

afterEach(() => {
  document.body.innerHTML = ''
  vi.clearAllTimers()
  vi.useRealTimers()
})


describe('Bomb People arena', () => {
  it('renders the full 20×20 board with distinct hard, soft, bomb, item and flame layers', () => {
    const wrapper = render()
    expect(wrapper.findAll('.tile')).toHaveLength(2)
    expect(wrapper.findAll('.tile.hard')).toHaveLength(1)
    expect(wrapper.findAll('.tile.soft')).toHaveLength(1)
    expect(wrapper.findAll('.bomb')).toHaveLength(1)
    expect(wrapper.findAll('.item')).toHaveLength(1)
    expect(wrapper.findAll('.flame')).toHaveLength(1)
    expect(wrapper.get('.arena-board').attributes('aria-label')).toContain('20×20')
    wrapper.unmount()
  })

  it('renders remote timer bombs as a distinct C-controlled model', () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.bombs.push({
      id: 2, ownerId: 'p0', creditPlayerId: 'p0', x: 6, y: 6,
      fuseTicks: 40, maxFuseTicks: 40, moving: false,
      motionX: 0, motionY: 0, carriedBy: null, remote: true,
    })
    const wrapper = render(data)
    const remote = wrapper.get('.bomb.remote')
    expect(remote.attributes('title')).toContain('按 C 引爆')
    expect(remote.get('small').text()).toBe('C')
    wrapper.unmount()
  })

  it('uses the authoritative doubled kick cadence for bomb interpolation', () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.bombs[0]!.moving = true
    game.bombs[0]!.moveIntervalTicks = 3
    const wrapper = render(data)
    expect(wrapper.get('.bomb').attributes('style')).toContain('--bomb-move-duration: 45ms')
    wrapper.unmount()
  })

  it('mirrors ghost phasing and rounded solid corners in local prediction', () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    const actor = game.players[0]!
    actor.equipment.ghost = true
    actor.x = 5.3
    actor.y = 5
    game.bombs[0]!.x = 6
    game.bombs[0]!.y = 5

    const throughBomb = advanceContinuousPosition(game, actor, 5.3, 5, 1, 0, 0.1)
    expect(throughBomb.x).toBeCloseTo(5.4, 5)
    expect(throughBomb.blocked).toBe(false)

    game.bombs = []
    game.board[6]![6] = 1
    actor.x = actor.y = 5.3
    const aroundCorner = advanceContinuousPosition(game, actor, 5.3, 5.3, 1, 0, 0.01)
    expect(aroundCorner.x).toBeCloseTo(5.31, 5)
    expect(aroundCorner.blocked).toBe(false)
  })

  it('sends WASD and action keys as authoritative input masks', async () => {
    const wrapper = render()
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', cancelable: true }))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 1, inputMask: 1 })
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', cancelable: true }))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 2, inputMask: 17 })
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'Space', cancelable: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyZ', cancelable: true }))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 4, inputMask: 33 })
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyW', cancelable: true }))
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyZ', cancelable: true }))
    wrapper.unmount()
  })

  it('advances held movement on every display frame at a uniform speed', async () => {
    const wrapper = render()
    const self = wrapper.get('.player-piece.self')

    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyD', cancelable: true }))
    const samples = [playerPosition(self)[0]]
    for (let frame = 0; frame < 8; frame += 1) {
      await vi.advanceTimersByTimeAsync(17)
      samples.push(playerPosition(self)[0])
    }

    const deltas = samples.slice(1).map((value, index) => value - samples[index]!)
    expect(self.classes()).toEqual(expect.arrayContaining([
      'walking', 'local-input', 'locally-predicted',
    ]))
    expect(deltas.every(delta => delta > 0.08 && delta < 0.18)).toBe(true)
    expect(Math.max(...deltas) - Math.min(...deltas)).toBeLessThan(0.02)
    expect(samples.at(-1)! - samples[0]!).toBeGreaterThan(0.9)
    expect(self.attributes('style')).toContain('--move-duration: 0ms')

    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyD', cancelable: true }))
    const releasedAt = playerPosition(self)[0]
    await vi.advanceTimersByTimeAsync(34)
    expect(self.classes()).not.toContain('local-input')
    expect(self.classes()).not.toContain('walking')
    expect(playerPosition(self)[0]).toBeCloseTo(releasedAt, 4)

    await vi.advanceTimersByTimeAsync(90)
    const inputPayloads = mocks.rapidAction.mock.calls
      .filter(([action]) => action === 'input')
      .map(([, payload]) => payload)
    expect(inputPayloads).toEqual([
      { sequence: 1, inputMask: 8 },
      { sequence: 2, inputMask: 0 },
      { sequence: 3, inputMask: 0 },
    ])
    wrapper.unmount()
  })

  it('renders a very short tap as one gradual 60 Hz quantum without stacking taps', async () => {
    const wrapper = render()
    const self = wrapper.get('.player-piece.self')

    for (let index = 0; index < 8; index += 1) {
      window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyD', cancelable: true }))
      window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyD', cancelable: true }))
    }

    expect(playerPosition(self)[0]).toBe(1)
    await vi.advanceTimersByTimeAsync(17)
    const firstFrame = playerPosition(self)[0]
    await vi.advanceTimersByTimeAsync(17)
    const completedTap = playerPosition(self)[0]
    await vi.advanceTimersByTimeAsync(50)

    expect(self.classes()).toContain('locally-predicted')
    expect(firstFrame).toBeGreaterThan(1.08)
    expect(firstFrame).toBeLessThan(1.13)
    expect(completedTap).toBeCloseTo(1 + 7.692 / 60, 3)
    expect(playerPosition(self)[0]).toBeCloseTo(completedTap, 4)
    expect(completedTap).toBeLessThan(1.2)
    wrapper.unmount()
  })

  it('changes direction from the exact in-between position without recentering', async () => {
    const wrapper = render()
    const self = wrapper.get('.player-piece.self')

    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyD', cancelable: true }))
    await vi.advanceTimersByTimeAsync(34)
    const beforeTurn = playerPosition(self)
    expect(beforeTurn[0]).toBeGreaterThan(1.2)
    expect(beforeTurn[1]).toBe(1)

    // Players commonly press the new direction just before releasing the old
    // key. The newly pressed key must win immediately from the exact position.
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', cancelable: true }))
    await vi.advanceTimersByTimeAsync(17)
    const turned = playerPosition(self)
    expect(self.classes()).toContain('facing-up')
    expect(turned[0]).toBeCloseTo(beforeTurn[0], 3)
    expect(turned[1]).toBeLessThan(beforeTurn[1])
    expect(beforeTurn[1] - turned[1]).toBeLessThan(0.18)

    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyD', cancelable: true }))
    await vi.advanceTimersByTimeAsync(17)
    const continued = playerPosition(self)
    expect(continued[0]).toBeCloseTo(beforeTurn[0], 3)
    expect(continued[1]).toBeLessThan(turned[1])
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyW', cancelable: true }))
    wrapper.unmount()
  })

  it('stops continuously at a solid edge instead of snapping to a cell centre', async () => {
    const wrapper = render()
    const self = wrapper.get('.player-piece.self')

    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', cancelable: true }))
    await vi.advanceTimersByTimeAsync(100)

    expect(playerPosition(self)[0]).toBe(1)
    expect(playerPosition(self)[1]).toBeCloseTo(0.78, 4)
    expect(self.classes()).toContain('locally-predicted')
    expect(self.classes()).not.toContain('walking')
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyW', cancelable: true }))
    wrapper.unmount()
  })

  it('uses C as the dedicated remote timer trigger', async () => {
    const wrapper = render()
    const trigger = new KeyboardEvent('keydown', { code: 'KeyC', cancelable: true })
    window.dispatchEvent(trigger)
    await flushPromises()
    expect(trigger.defaultPrevented).toBe(true)
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 1, inputMask: 128 })
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyC', cancelable: true }))
    wrapper.unmount()
  })

  it('renders articulated walking and synchronized bomb action effects', () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.players[1]!.moving = true
    const third = player('p2', 2, '黄队')
    third.x = 10
    third.y = 10
    game.players.push(third)
    game.effects = [
      { id: 1, kind: 'bomb_placed', tick: 100, remainingTicks: 5, actorId: 'p0', bombId: 1, x: 3, y: 3, targetX: null, targetY: null, directionX: 0, directionY: 0 },
      { id: 2, kind: 'bomb_exploded', tick: 100, remainingTicks: 7, actorId: 'p0', bombId: 2, x: 5, y: 5, targetX: null, targetY: null, directionX: 0, directionY: 0 },
      { id: 3, kind: 'bomb_punched', tick: 100, remainingTicks: 8, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: 2, targetY: 1, directionX: 1, directionY: 0 },
      { id: 4, kind: 'bomb_kicked', tick: 100, remainingTicks: 8, actorId: 'p1', bombId: 1, x: 18, y: 18, targetX: 17, targetY: 18, directionX: -1, directionY: 0 },
      { id: 5, kind: 'bomb_thrown', tick: 100, remainingTicks: 8, actorId: 'p2', bombId: 1, x: 11, y: 10, targetX: 14, targetY: 10, directionX: 1, directionY: 0 },
    ]

    const wrapper = render(data)
    expect(wrapper.findAll('.player-piece.walking .player-leg')).toHaveLength(2)
    expect(wrapper.findAll('.player-piece.walking .player-arm')).toHaveLength(2)
    expect(wrapper.find('.player-piece.action-punch').exists()).toBe(true)
    expect(wrapper.find('.player-piece.action-kick').exists()).toBe(true)
    expect(wrapper.find('.player-piece.action-throw').exists()).toBe(true)
    expect(wrapper.find('.place-effect').exists()).toBe(true)
    expect(wrapper.find('.explosion-effect').exists()).toBe(true)
    expect(wrapper.find('.punch-impact').exists()).toBe(true)
    expect(wrapper.find('.kick-impact').exists()).toBe(true)
    expect(wrapper.find('.throw-effect').exists()).toBe(true)
    expect(wrapper.get('.bomb').classes()).toEqual(expect.arrayContaining(['just-placed', 'landing']))
    wrapper.unmount()
  })

  it('interpolates fractional authoritative positions at the snapshot cadence', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    const actor = game.players[1]!
    actor.x = 4
    actor.y = 6
    actor.moving = true
    actor.moveIntervalTicks = 12
    const wrapper = render(data)

    const piece = wrapper.get('.player-piece:not(.self)')
    expect(piece.attributes('style')).toContain('transform: translate3d(400%, 600%, 0)')
    expect(piece.attributes('style')).toContain('--move-duration: 42ms')
    expect(piece.attributes('style')).toContain('--walk-step-duration: 200ms')
    expect(piece.find('.player-visual').exists()).toBe(true)

    actor.x = 4.25
    await wrapper.setProps({ snapshot: {
      ...data,
      revision: 2,
      game: { ...game, players: [...game.players] },
    } as unknown as ArcadeSnapshot })
    await flushPromises()
    expect(piece.attributes('style')).toContain('transform: translate3d(425%, 600%, 0)')
    wrapper.unmount()
  })

  it('models pickup, carried walking and the second-press throw as separate states', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    const actor = game.players[0]!
    const bomb = game.bombs[0]!
    actor.x = 5
    actor.y = 6
    actor.moving = true
    actor.carriedBombId = bomb.id
    bomb.x = actor.x
    bomb.y = actor.y
    bomb.carriedBy = actor.id
    game.effects = [
      { id: 6, kind: 'bomb_picked_up', tick: 100, remainingTicks: 10, actorId: actor.id, bombId: bomb.id, x: 6, y: 6, targetX: 5, targetY: 6, directionX: 1, directionY: 0 },
    ]

    const wrapper = render(data)
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyD', cancelable: true }))
    await flushPromises()
    expect(wrapper.get('.player-piece.self').classes()).toEqual(expect.arrayContaining([
      'walking', 'carrying', 'action-pickup',
    ]))
    expect(wrapper.findAll('.carried-bomb-rig .carry-arm')).toHaveLength(2)
    expect(wrapper.get('.carried-bomb-rig').text()).toContain('1.5')
    expect(wrapper.get('.bomb').isVisible()).toBe(false)
    expect(wrapper.get('button[aria-label="扔出手中炸弹"]').text()).toContain('投扔出')

    const thrownPlayers = game.players.map(current => (
      current.id === actor.id ? { ...current, carriedBombId: null } : current
    ))
    const thrownBombs = game.bombs.map(current => (
      current.id === bomb.id ? { ...current, x: 9, carriedBy: null } : current
    ))
    const thrownEffects: BombGame['effects'] = [
      ...game.effects,
      { id: 7, kind: 'bomb_thrown', tick: 101, remainingTicks: 10, actorId: actor.id, bombId: bomb.id, x: 5, y: 6, targetX: 9, targetY: 6, directionX: 1, directionY: 0 },
    ]
    await wrapper.setProps({ snapshot: {
      ...data,
      revision: 2,
      game: { ...game, players: thrownPlayers, bombs: thrownBombs, effects: thrownEffects },
    } as unknown as ArcadeSnapshot })
    await flushPromises()

    expect(wrapper.find('.carried-bomb-rig').exists()).toBe(false)
    expect(wrapper.get('.bomb').isVisible()).toBe(true)
    expect(wrapper.find('.player-piece.self.action-throw').exists()).toBe(true)
    expect(wrapper.find('.throw-effect').exists()).toBe(true)
    expect(wrapper.get('button[aria-label="拿起面前炸弹"]').text()).toContain('拿抱雷')
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyD', cancelable: true }))
    wrapper.unmount()
  })

  it('uses one fixed non-verbal sound for each visible action kind', async () => {
    const data = snapshot()
    const wrapper = render(data)
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', cancelable: true }))
    expect(mocks.soundUnlock).toHaveBeenCalledOnce()

    const game = data.game as unknown as BombGame
    const effects: BombGame['effects'] = [
      { id: 1, kind: 'bomb_placed', tick: 101, remainingTicks: 5, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: null, targetY: null, directionX: 0, directionY: 0 },
      { id: 2, kind: 'bomb_exploded', tick: 101, remainingTicks: 7, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: null, targetY: null, directionX: 0, directionY: 0 },
      { id: 3, kind: 'bomb_kicked', tick: 101, remainingTicks: 8, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: 2, targetY: 1, directionX: 1, directionY: 0 },
      { id: 4, kind: 'bomb_punched', tick: 101, remainingTicks: 8, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: 2, targetY: 1, directionX: 1, directionY: 0 },
      { id: 5, kind: 'bomb_picked_up', tick: 101, remainingTicks: 8, actorId: 'p0', bombId: 1, x: 2, y: 1, targetX: 1, targetY: 1, directionX: 1, directionY: 0 },
      { id: 6, kind: 'bomb_thrown', tick: 101, remainingTicks: 8, actorId: 'p0', bombId: 1, x: 1, y: 1, targetX: 5, targetY: 1, directionX: 1, directionY: 0 },
    ]
    await wrapper.setProps({ snapshot: {
      ...data,
      revision: 2,
      game: { ...game, effects },
    } as unknown as ArcadeSnapshot })
    await flushPromises()

    expect(mocks.soundPlay.mock.calls.map(([kind]) => kind)).toEqual([
      'bomb_placed', 'bomb_exploded', 'bomb_kicked', 'bomb_punched', 'bomb_picked_up', 'bomb_thrown',
    ])
    expect(wrapper.get('.event-list').text()).not.toContain('扔出炸弹')
    wrapper.unmount()
    expect(mocks.soundDestroy).toHaveBeenCalledOnce()
  })

  it('supports browser arrow keys without requiring board focus', async () => {
    const wrapper = render()
    const right = new KeyboardEvent('keydown', { code: 'ArrowRight', cancelable: true })
    window.dispatchEvent(right)
    await flushPromises()
    expect(right.defaultPrevented).toBe(true)
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 1, inputMask: 8 })

    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'ArrowRight', cancelable: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyX', cancelable: true }))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 3, inputMask: 64 })
    wrapper.unmount()
  })

  it('turns mobile joystick drags and action buttons into the same input mask', async () => {
    const wrapper = render()
    const joystick = wrapper.get('.joystick')
    vi.spyOn(joystick.element, 'getBoundingClientRect').mockReturnValue({
      left: 0, top: 0, width: 116, height: 116, right: 116, bottom: 116, x: 0, y: 0,
      toJSON: () => ({}),
    })

    joystick.element.dispatchEvent(pointerEvent('pointerdown', 7, 110, 58))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 1, inputMask: 8 })
    const bombButton = wrapper.get('button[aria-label="放置普通炸弹或部署遥控定时炸弹"]')
    bombButton.element.dispatchEvent(pointerEvent('pointerdown', 8))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 2, inputMask: 24 })
    bombButton.element.dispatchEvent(pointerEvent('pointerup', 8))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 3, inputMask: 8 })
    joystick.element.dispatchEvent(pointerEvent('pointermove', 7, 58, 4))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 4, inputMask: 1 })
    joystick.element.dispatchEvent(pointerEvent('pointerup', 7, 58, 4))
    await flushPromises()
    expect(mocks.rapidAction).toHaveBeenLastCalledWith('input', { sequence: 5, inputMask: 0 })
    wrapper.unmount()
  })

  it('keeps spectators read-only even when watching an alive player', async () => {
    const data = snapshot()
    data.viewer = { mode: 'spectator', id: 'watcher', name: '观众', targetPlayerId: 'p0' }
    const wrapper = render(data)
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', cancelable: true }))
    await flushPromises()
    expect(mocks.rapidAction).not.toHaveBeenCalled()
    expect(wrapper.find('.touch-controls').exists()).toBe(false)
    wrapper.unmount()
  })

  it('uses one elected player as a 30 Hz snapshot clock', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.clockLeaderId = 'p0'
    const wrapper = render(data)
    await vi.advanceTimersByTimeAsync(34)
    expect(mocks.rapidAction).toHaveBeenCalledWith('heartbeat', { sequence: 1 })
    wrapper.unmount()
  })

  it('lets another player refresh the room when the elected clock stalls', async () => {
    const wrapper = render()
    await vi.advanceTimersByTimeAsync(400)
    expect(mocks.rapidAction).toHaveBeenCalledWith('heartbeat', { sequence: 1 })
    wrapper.unmount()
  })

  it('never queues snapshot heartbeats behind a slow request', async () => {
    let resolveHeartbeat: ((accepted: boolean) => void) | undefined
    mocks.rapidAction.mockImplementation((action: string) => (
      action === 'heartbeat'
        ? new Promise<boolean>(resolve => { resolveHeartbeat = resolve })
        : Promise.resolve(true)
    ))
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.clockLeaderId = 'p0'
    const wrapper = render(data)

    await vi.advanceTimersByTimeAsync(400)
    expect(mocks.rapidAction.mock.calls.filter(([action]) => action === 'heartbeat')).toHaveLength(1)

    resolveHeartbeat?.(true)
    await flushPromises()
    await vi.advanceTimersByTimeAsync(50)
    expect(mocks.rapidAction.mock.calls.filter(([action]) => action === 'heartbeat')).toHaveLength(2)
    wrapper.unmount()
  })

  it('shows kills, championships and win rate for every player', () => {
    const wrapper = render()
    const text = wrapper.get('.scoreboard').text()
    expect(text).toContain('3本局击杀')
    expect(text).toContain('4 冠')
    expect(text).toContain('80% 胜率')
    expect(text).toContain('12 总击杀')
    expect(wrapper.findAll('.player-card')).toHaveLength(2)
    wrapper.unmount()
  })

  it('lets the host propose a map and lets every other player vote', async () => {
    const data = snapshot('lobby')
    const game = data.game as unknown as BombGame
    game.canProposeMap = true
    const wrapper = render(data)
    const cards = wrapper.findAll('.map-card')
    expect(cards).toHaveLength(game.mapCatalog.length)
    expect(cards.every(card => card.attributes('disabled') === undefined)).toBe(true)
    expect(wrapper.text()).toContain('房主提议，全员确认后锁定下一局地图')
    await cards[1]!.trigger('click')
    await flushPromises()
    expect(mocks.action).toHaveBeenCalledWith('propose_map', { mapKey: 'sky_citadel' })
    wrapper.unmount()

    const voterData = snapshot('lobby')
    voterData.self = { id: 'p1', name: '蓝队', seat: 1 }
    voterData.viewer = { mode: 'player', id: 'p1', name: '蓝队', targetPlayerId: 'p1' }
    const voterGame = voterData.game as unknown as BombGame
    voterGame.canVoteMap = true
    voterGame.mapProposal = {
      mapKey: 'sky_citadel', proposedBy: 'p0',
      approvedPlayerIds: ['p0'], requiredPlayerIds: ['p0', 'p1'],
      approvalCount: 1, requiredCount: 2,
    }
    const voter = render(voterData)
    expect(voter.text()).toContain('1/2 已同意')
    const voteButtons = voter.findAll('.vote-actions button')
    await voteButtons[1]!.trigger('click')
    await flushPromises()
    expect(mocks.action).toHaveBeenLastCalledWith('vote_map', { accept: true })
    voter.unmount()
  })

  it('renders the rulebook in dark readable text and explains ghost phasing', async () => {
    const wrapper = render()
    expect(wrapper.text()).toContain('幽灵相位获得后本局永久生效')
    expect(wrapper.text()).toContain('可穿过箱墙、炸弹和其他玩家并在箱墙格内放雷')
    expect(wrapper.text()).toContain('不能穿固定石块或决胜落石')
    await wrapper.get('button[aria-label="玩法说明"]').trigger('click')
    await flushPromises()
    expect(['rgb(0, 0, 0)', 'rgb(23, 20, 17)']).toContain(
      getComputedStyle(wrapper.get('.rulebook').element).color,
    )
    expect(wrapper.get('.rulebook').text()).toContain('脚踢雷无需单独按键')
    wrapper.unmount()
  })

  it('shows the spiral-collapse warning and upcoming danger cells', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.stage = 'collapse'
    game.collapsePlaced = 8
    game.dangerCells = [[2, 0], [3, 0]]
    const wrapper = render(data)
    expect(wrapper.text()).toContain('落石决胜')
    expect(wrapper.text()).toContain('落石 8/400')
    expect(wrapper.findAll('.danger-tile')).toHaveLength(2)
    wrapper.unmount()
  })
})
