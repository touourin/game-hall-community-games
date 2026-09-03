import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GameView from './GameView.vue'
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
    moveIntervalTicks: seat ? 4 : 2.6,
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
    boardSize: 20, tick: 100, tickRate: 20,
    stage: phase === 'lobby' ? 'lobby' : phase === 'finished' ? 'finished' : 'active',
    stageTicksRemaining: 0, roundTicksRemaining: 1_200,
    collapsePlaced: 0, collapseTotal: 400, dangerCells: [],
    selectedMap: 'magma_crucible', currentMap: maps[0]!, mapCatalog: maps,
    mapRotation: 'random_no_repeat', mapProposal: null, canProposeMap: false, canVoteMap: false,
    board, players: phase === 'lobby' ? [] : [player('p0', 0, '红队'), player('p1', 1, '蓝队')],
    bombs: [{ id: 1, ownerId: 'p0', creditPlayerId: 'p0', x: 3, y: 3, fuseTicks: 30, maxFuseTicks: 40, moving: false, motionX: 0, motionY: 0, carriedBy: null, remote: false }],
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
    expect(wrapper.findAll('.tile')).toHaveLength(400)
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
    game.players[0]!.moving = true
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

  it('interpolates authoritative grid steps with compositor movement at the real speed', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    const actor = game.players[0]!
    actor.x = 4
    actor.y = 6
    actor.moving = true
    actor.moveIntervalTicks = 4
    const wrapper = render(data)

    const piece = wrapper.get('.player-piece.self')
    expect(piece.attributes('style')).toContain('transform: translate3d(400%, 600%, 0)')
    expect(piece.attributes('style')).toContain('--move-duration: 200ms')
    expect(piece.attributes('style')).toContain('--walk-step-duration: 200ms')
    expect(piece.find('.player-visual').exists()).toBe(true)

    actor.x = 5
    await wrapper.setProps({ snapshot: {
      ...data,
      revision: 2,
      game: { ...game, players: [...game.players] },
    } as unknown as ArcadeSnapshot })
    await flushPromises()
    expect(piece.attributes('style')).toContain('transform: translate3d(500%, 600%, 0)')
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

  it('uses one elected player as the lightweight snapshot clock', async () => {
    const data = snapshot()
    const game = data.game as unknown as BombGame
    game.clockLeaderId = 'p0'
    const wrapper = render(data)
    await vi.advanceTimersByTimeAsync(125)
    expect(mocks.rapidAction).toHaveBeenCalledWith('heartbeat', { sequence: 1 })
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

  it('shows a read-only random map pool with no consecutive repeats', async () => {
    const data = snapshot('lobby')
    const wrapper = render(data)
    const cards = wrapper.findAll('.map-card')
    expect(cards).toHaveLength((data.game as unknown as BombGame).mapCatalog.length)
    expect(cards.every(card => card.attributes('disabled') !== undefined)).toBe(true)
    expect(wrapper.text()).toContain('每局随机抽取，连续两局不会重复')
    expect(wrapper.text()).toContain('上一局地图会暂时排除')
    expect(mocks.action).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('explains permanent ghost wall access and stone restrictions', () => {
    const wrapper = render()
    expect(wrapper.text()).toContain('幽灵相位获得后本局永久生效')
    expect(wrapper.text()).toContain('可穿过箱墙并在箱墙格内放雷')
    expect(wrapper.text()).toContain('不能穿固定石块或决胜落石')
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
    expect(wrapper.findAll('.tile.danger')).toHaveLength(2)
    wrapper.unmount()
  })
})
