import catalog from '../pieces.json'

export type Cell = readonly [number, number]
export type Board = readonly (readonly number[])[]
export type Piece = { id: string; cells: Cell[]; size: number }
export type Placement = { pieceId: string; x: number; y: number; rotation: number; flipped: boolean }
export type PlayerColor = 'blue' | 'yellow' | 'red' | 'green'

export interface BlokusPlayer {
  id: string
  color: PlayerColor
  colorName: string
  start: Cell
  remainingPieces: string[]
  remainingSquares: number
  placedSquares: number
  openingPieceSize: number | null
  status: 'active' | 'blocked' | 'finished' | 'forfeited'
  rank: number | null
  points: number | null
}

export interface BlokusGame {
  mode: 'duo' | 'classic'
  boardSize: number
  board: number[][]
  players: BlokusPlayer[]
  currentPlayerId: string | null
  turnNumber: number
  isMyTurn: boolean
  moveCount: number
  lastMove: (Placement & { playerId: string; cells: Cell[]; turnNumber: number }) | null
  events: string[]
  rankings: string[]
  rankPoints: number[]
}

export const DUO_SIZE = 14
export const FOUR_SIZE = 20
export const DUO_STARTS: readonly Cell[] = [[4, 4], [9, 9]]
export const FOUR_STARTS: readonly Cell[] = [[0, 0], [19, 0], [19, 19], [0, 19]]
const EDGES: readonly Cell[] = [[1, 0], [-1, 0], [0, 1], [0, -1]]
const DIAGONALS: readonly Cell[] = [[1, 1], [1, -1], [-1, 1], [-1, -1]]

export const PIECES: Piece[] = catalog.map(({ id, rows }) => {
  const cells: Cell[] = []
  rows.forEach((row, y) => [...row].forEach((cell, x) => {
    if (cell === '#') cells.push([x, y])
  }))
  return { id, cells, size: cells.length }
})

export function transform(cells: readonly Cell[], rotation: number, flipped: boolean): Cell[] {
  let result: Cell[] = cells.map(([x, y]) => [flipped ? -x : x, y])
  for (let step = 0; step < rotation; step += 1) result = result.map(([x, y]) => [-y, x])
  const left = Math.min(...result.map(([x]) => x))
  const top = Math.min(...result.map(([, y]) => y))
  return result.map(([x, y]): Cell => [x - left, y - top]).sort((a, b) => a[1] - b[1] || a[0] - b[0])
}

export function inside(x: number, y: number, size: number): boolean {
  return x >= 0 && x < size && y >= 0 && y < size
}

export function placementError(
  board: Board,
  color: number,
  cells: readonly Cell[],
  first: boolean,
  start: Cell,
): string | null {
  const size = board.length
  if (!cells.length) return '请先选择棋块'
  if (cells.some(([x, y]) => !inside(x, y, size))) return '棋块超出棋盘，请调整位置'
  if (cells.some(([x, y]) => board[y]?.[x] !== -1)) return '这里已有棋块，不能重叠'
  if (first) {
    return cells.some(([x, y]) => x === start[0] && y === start[1])
      ? null : '首块必须覆盖自己的起始点'
  }
  if (cells.some(([x, y]) => EDGES.some(([dx, dy]) => board[y + dy]?.[x + dx] === color))) {
    return '同色只能角接，不能边接'
  }
  return cells.some(([x, y]) => DIAGONALS.some(([dx, dy]) => board[y + dy]?.[x + dx] === color))
    ? null : '需要与已有同色棋块角接'
}

export function legalAnchors(board: Board, color: number, first: boolean, start: Cell): Cell[] {
  if (first) return [start]
  const anchors: Cell[] = []
  for (let y = 0; y < board.length; y += 1) {
    for (let x = 0; x < (board[y]?.length ?? 0); x += 1) {
      if (board[y]?.[x] !== -1) continue
      if (EDGES.some(([dx, dy]) => board[y + dy]?.[x + dx] === color)) continue
      if (DIAGONALS.some(([dx, dy]) => board[y + dy]?.[x + dx] === color)) anchors.push([x, y])
    }
  }
  return anchors
}

export function findPlacement(
  board: Board,
  color: number,
  piece: Piece,
  first: boolean,
  start: Cell,
): Placement | null {
  const anchors = legalAnchors(board, color, first, start)
  const seen = new Set<string>()
  for (const flipped of [false, true]) {
    for (let rotation = 0; rotation < 4; rotation += 1) {
      const cells = transform(piece.cells, rotation, flipped)
      const key = JSON.stringify(cells)
      if (seen.has(key)) continue
      seen.add(key)
      for (const [ax, ay] of anchors) {
        for (const [sx, sy] of cells) {
          const x = ax - sx
          const y = ay - sy
          const placed: Cell[] = cells.map(([cx, cy]) => [x + cx, y + cy])
          if (!placementError(board, color, placed, first, start)) {
            return { pieceId: piece.id, x, y, rotation, flipped }
          }
        }
      }
    }
  }
  return null
}

export function signedPoints(points: number | null | undefined): string {
  return points == null ? '—' : `${points > 0 ? '+' : ''}${points}`
}
