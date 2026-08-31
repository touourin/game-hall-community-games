import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GameView from './GameView.vue'
import { CORNERS, PIECES, findPlacement, placementError, transform, type BlokusGame, type Cell } from './rules'

const mocks = vi.hoisted(() => ({ action: vi.fn(), restart: vi.fn() }))
vi.mock('@game-hall/plugin-sdk', async (original) => ({
  ...await original<object>(),
  usePluginGameActions: () => ({ action: mocks.action, restart: mocks.restart }),
}))

function snapshot(): ArcadeSnapshot {
  const colors = ['blue', 'yellow', 'red', 'green'] as const
  const game: BlokusGame = {
    boardSize: 20,
    board: Array.from({ length: 20 }, () => Array<number>(20).fill(-1)),
    players: colors.map((color, index) => ({
      id: `p${index}`, color, colorName: ['蓝', '黄', '红', '绿'][index]!,
      corner: CORNERS[index]!, remainingPieces: PIECES.map(piece => piece.id),
      remainingSquares: 89, placedSquares: 0, status: 'active', rank: null, points: null,
    })),
    currentPlayerId: 'p0', isMyTurn: true, turnNumber: 1, moveCount: 0, lastMove: null,
    events: [], rankings: [], rankPoints: [2, 1, 0, -1],
  }
  return {
    revision: 1, roomCode: 'BLOK', gameKey: 'plugin-blokus', gameName: '四人方格',
    phase: 'playing', roundNumber: 1, statsEligible: true,
    self: { id: 'p0', name: '玩家1', seat: 0 }, viewer: { mode: 'player' },
    players: colors.map((_, index) => ({ id: `p${index}`, name: `玩家${index + 1}`, seat: index, connected: true })),
    actions: { canAct: true, canRestart: false }, game,
  } as unknown as ArcadeSnapshot
}

function render(data = snapshot()) {
  return mount(GameView, { props: { snapshot: data }, global: { plugins: [createPinia()], stubs: { Teleport: true } } })
}

function button(wrapper: ReturnType<typeof render>, label: string) {
  return wrapper.findAll('button').find(element => element.text() === label)!
}

beforeEach(() => {
  mocks.action.mockReset().mockResolvedValue(true)
  mocks.restart.mockReset().mockResolvedValue(true)
})

describe('Blokus geometry previews', () => {
  it('contains every size group and 89 squares without reflected duplicate pieces', () => {
    expect(PIECES).toHaveLength(21)
    expect(PIECES.reduce((sum, piece) => sum + piece.size, 0)).toBe(89)
    const identities = PIECES.map(piece => {
      const variants = [false, true].flatMap(flipped => [0, 1, 2, 3].map(rotation => JSON.stringify(transform(piece.cells, rotation, flipped))))
      return variants.sort()[0]
    })
    expect(new Set(identities).size).toBe(21)
  })

  it('rejects edge contact but allows diagonal and other-color edge contact', () => {
    const board = Array.from({ length: 20 }, () => Array<number>(20).fill(-1))
    board[0]![0] = 0
    expect(placementError(board, 0, [[1, 0], [2, 0]], false)).toContain('边接')
    expect(placementError(board, 0, [[1, 1], [2, 1]], false)).toBeNull()
    board[1]![3] = 1
    expect(placementError(board, 0, [[1, 1], [2, 1]], false)).toBeNull()
    expect(placementError(board, 0, [[3, 1]], false)).toContain('重叠')
    expect(placementError(board, 0, [[20, 1]], false)).toContain('超出')
  })

  it('finds a rotated or flipped opening covering each assigned corner', () => {
    const board = Array.from({ length: 20 }, () => Array<number>(20).fill(-1))
    const piece = PIECES.find(piece => piece.id === 'L5')!
    for (let color = 0; color < 4; color += 1) {
      const move = findPlacement(board, color, piece, true)!
      expect(move).not.toBeNull()
      const cells: Cell[] = transform(piece.cells, move.rotation, move.flipped).map(([x, y]) => [x + move.x, y + move.y])
      expect(cells).toContainEqual(CORNERS[color])
      expect(placementError(board, color, cells, true)).toBeNull()
    }
  })
})

describe('four-player game interface', () => {
  it('shows the whole inventory, four corners, and scoring instructions', () => {
    const wrapper = render()
    expect(wrapper.findAll('.piece-button')).toHaveLength(21)
    for (const corner of ['左上角', '右上角', '右下角', '左下角']) expect(wrapper.text()).toContain(corner)
    expect(wrapper.text()).toContain('89')
    expect(wrapper.text()).toContain('+2 / +1 / 0 / −1')
  })

  it('previews without sending a move and submits only on confirmation', async () => {
    const wrapper = render()
    await wrapper.get('button[aria-label="L5，5 格"]').trigger('click')
    expect(wrapper.findAll('.preview-tile')).toHaveLength(5)
    expect(mocks.action).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('位置合法')
    await button(wrapper, '确认落子').trigger('click')
    await flushPromises()
    expect(mocks.action).toHaveBeenCalledExactlyOnceWith('place', {
      pieceId: 'L5', x: 0, y: 0, rotation: 0, flipped: false, turnNumber: 1,
    })
    expect(wrapper.findAll('.preview-tile')).toHaveLength(0)
  })

  it('supports rotation, reflection, nudging, and keyboard controls', async () => {
    const wrapper = render()
    await wrapper.get('button[aria-label="L5，5 格"]').trigger('click')
    await button(wrapper, '旋转').trigger('click')
    const rotated = wrapper.findAll('.preview-tile').map(cell => [cell.attributes('x'), cell.attributes('y')])
    expect(new Set(rotated.map(([x]) => x)).size).toBe(4)
    await button(wrapper, '翻转').trigger('click')
    await wrapper.get('[aria-label="向右一格"]').trigger('click')
    expect(wrapper.text()).toContain('2 列 / 1 行')
    expect(button(wrapper, '确认落子').attributes('disabled')).toBeDefined()
    await wrapper.get('.board-svg').trigger('keydown', { key: 'ArrowLeft' })
    await button(wrapper, '找落点').trigger('click')
    await wrapper.get('.board-svg').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(mocks.action).toHaveBeenCalledTimes(1)
  })

  it('prevents double submissions while awaiting the server', async () => {
    let resolve!: (value: boolean) => void
    mocks.action.mockReturnValue(new Promise<boolean>(done => { resolve = done }))
    const wrapper = render()
    await wrapper.get('button[aria-label="M1，1 格"]').trigger('click')
    await button(wrapper, '确认落子').trigger('click')
    await wrapper.get('.board-svg').trigger('keydown', { key: 'Enter' })
    expect(mocks.action).toHaveBeenCalledTimes(1)
    resolve(true)
    await flushPromises()
  })

  it('clears stale previews on a new turn but keeps them during unrelated snapshots', async () => {
    const data = snapshot()
    const wrapper = render(data)
    await wrapper.get('button[aria-label="M1，1 格"]').trigger('click')
    await wrapper.setProps({ snapshot: { ...data, revision: 2 } })
    expect(wrapper.findAll('.preview-tile')).toHaveLength(1)
    await wrapper.setProps({ snapshot: { ...data, game: { ...data.game, turnNumber: 2, currentPlayerId: 'p1', isMyTurn: false } } })
    expect(wrapper.findAll('.preview-tile')).toHaveLength(0)
    expect(button(wrapper, '等待你的回合').attributes('disabled')).toBeDefined()
  })

  it('never enables spectator moves even when the viewed player is current', async () => {
    const data = snapshot()
    data.viewer = { mode: 'spectator', id: 'watcher', name: '观众' }
    const wrapper = render(data)
    expect(wrapper.findAll('.piece-button').every(piece => piece.attributes('disabled') !== undefined)).toBe(true)
    await wrapper.get('.board-svg').trigger('keydown', { key: 'Enter' })
    expect(mocks.action).not.toHaveBeenCalled()
    expect(wrapper.find('[aria-label="落子操作"]').exists()).toBe(false)
  })

  it('clears an existing preview when switching to spectator mode', async () => {
    const data = snapshot()
    const wrapper = render(data)
    await wrapper.get('button[aria-label="M1，1 格"]').trigger('click')
    expect(wrapper.findAll('.preview-tile')).toHaveLength(1)
    await wrapper.setProps({ snapshot: { ...data, viewer: { mode: 'spectator', id: 'watcher', name: '观众' } } })
    expect(wrapper.findAll('.preview-tile')).toHaveLength(0)
    expect(wrapper.find('[aria-label="落子操作"]').exists()).toBe(false)
  })

  it('lets users inspect opponents but never use their pieces', async () => {
    const wrapper = render()
    await wrapper.get('[aria-label="查看玩家2的棋块，右上角"]').trigger('click')
    expect(wrapper.text()).toContain('玩家2的棋块')
    expect(wrapper.findAll('.piece-button').every(piece => piece.attributes('disabled') !== undefined)).toBe(true)
    await button(wrapper, '返回我的棋块').trigger('click')
    expect(wrapper.get('button[aria-label="M1，1 格"]').attributes('disabled')).toBeUndefined()
  })

  it('shows all four result points including zero, negative, and guest exclusion', () => {
    const data = snapshot()
    data.phase = 'finished'
    data.statsEligible = false
    const game = data.game as unknown as BlokusGame
    game.isMyTurn = false
    game.currentPlayerId = null
    game.players.forEach((player, index) => { player.rank = index + 1; player.points = [2, 1, 0, -1][index]! })
    const wrapper = render(data)
    expect(wrapper.findAll('.rank-points').map(item => item.text())).toEqual(['+2 分', '+1 分', '0 分', '-1 分'])
    expect(wrapper.text()).toContain('不记录账号战绩')
    expect(wrapper.find('[aria-label="落子操作"]').exists()).toBe(false)
  })
})
