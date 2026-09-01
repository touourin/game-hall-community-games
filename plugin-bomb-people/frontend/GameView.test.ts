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


function player(id: string, seat: number, name: string): BombPlayer {
  return {
    id, seat, name, color: seat ? '#4f8cff' : '#ff5a55', character: seat,
    x: seat ? 18 : 1, y: seat ? 18 : 1, facingX: 0, facingY: 1,
    alive: true, eliminatedBy: null, eliminationReason: null, kills: seat ? 1 : 3,
    stats: { kills: seat ? 4 : 12, championships: seat ? 1 : 4, matches: 5, winRate: seat ? 20 : 80 },
    equipment: {
      bombCapacity: seat ? 1 : 3, blastRange: seat ? 2 : 4, speedLevel: seat ? 0 : 2,
      kick: !seat, punch: !seat, throw: !seat, timer: !seat, chain: false,
      magnet: false, ice: false, shieldCharges: seat ? 0 : 1,
      ghostTicks: 0, invincibleTicks: 0, cursedTicks: 0,
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
    mapProposal: null, canProposeMap: phase === 'lobby', canVoteMap: false,
    board, players: phase === 'lobby' ? [] : [player('p0', 0, '红队'), player('p1', 1, '蓝队')],
    bombs: [{ id: 1, ownerId: 'p0', creditPlayerId: 'p0', x: 3, y: 3, fuseTicks: 30, maxFuseTicks: 40, moving: false }],
    items: [{ id: 1, kind: 'speed', x: 4, y: 4 }],
    flames: [{ x: 5, y: 5, remainingTicks: 4 }], iceTiles: [], events: [],
    winnerId: null, clockLeaderId: 'p1', frozen: false, selfInputSequence: 0,
    controls: { move: 'WASD', bomb: 'Space', punch: 'Z', throw: 'X', kick: 'automatic' },
    itemLabels: {
      bomb_up: '多一个炸弹', flame_up: '火焰增强', speed: '加速靴', kick: '脚踢雷',
      punch: '拳击手套', throw: '扔雷手套', timer: '定时炸弹', chain: '连锁引线',
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


function buttonByText(wrapper: ReturnType<typeof render>, text: string) {
  return wrapper.findAll('button').find(button => button.text().includes(text))!
}


beforeEach(() => {
  vi.useFakeTimers()
  mocks.action.mockReset().mockResolvedValue(true)
  mocks.rapidAction.mockReset().mockResolvedValue(true)
  mocks.restart.mockReset().mockResolvedValue(true)
  mocks.toggle.mockReset()
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

  it('lets only the host propose a map from the lobby', async () => {
    const data = snapshot('lobby')
    const wrapper = render(data)
    await wrapper.get('button[aria-label^="云顶激斗场"]').trigger('click')
    await flushPromises()
    expect(mocks.action).toHaveBeenCalledWith('propose_map', { mapKey: 'sky_citadel' })
    expect(wrapper.text()).toContain('房主提议，全员确认后自动切图')
    wrapper.unmount()
  })

  it('shows agreement controls to a player who has not voted', async () => {
    const data = snapshot('lobby')
    data.hostId = 'p1'
    const game = data.game as unknown as BombGame
    game.canProposeMap = false
    game.canVoteMap = true
    game.mapProposal = {
      mapKey: 'sky_citadel', proposedBy: 'p1', approvedPlayerIds: ['p1'],
      requiredPlayerIds: ['p0', 'p1'], approvalCount: 1, requiredCount: 2,
    }
    const wrapper = render(data)
    await buttonByText(wrapper, '同意切换').trigger('click')
    await flushPromises()
    expect(mocks.action).toHaveBeenCalledWith('vote_map', { accept: true })
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
