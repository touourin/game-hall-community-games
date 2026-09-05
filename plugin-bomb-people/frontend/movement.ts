import type { BombGame, BombObject, BombPlayer } from './types'


export const DEFAULT_PLAYER_HITBOX_RADIUS = 0.3
export const DEFAULT_SOLID_HALF_EXTENT = 0.48
export const DEFAULT_BOMB_HITBOX_RADIUS = 0.34
const POSITION_EPSILON = 0.000_01

export interface ContinuousMoveResult {
  x: number
  y: number
  distance: number
  blocked: boolean
}

export function movementSpeed(game: BombGame, actor: BombPlayer) {
  if (actor.movementSpeed != null) return Math.max(0, actor.movementSpeed)
  const secondsPerCell = [0.2, 0.16, 0.13, 0.1][actor.equipment.speedLevel] ?? 0.2
  const interval = actor.moveIntervalTicks ?? Math.max(1, game.tickRate * secondsPerCell)
  return game.tickRate / interval
}

export function ruleCell(position: number, maximum: number) {
  return Math.min(maximum, Math.max(0, Math.floor(position + 0.5)))
}

function circleBlocksMotion(
  startX: number,
  startY: number,
  x: number,
  y: number,
  obstacleX: number,
  obstacleY: number,
  contact: number,
) {
  const candidateDistance = (x - obstacleX) ** 2 + (y - obstacleY) ** 2
  const contactSquared = contact ** 2
  if (candidateDistance >= contactSquared - POSITION_EPSILON) return false
  const startDistance = (startX - obstacleX) ** 2 + (startY - obstacleY) ** 2
  return startDistance >= contactSquared - POSITION_EPSILON
}

function bombDestinationOpen(
  game: BombGame,
  actor: BombPlayer,
  bomb: BombObject,
  dx: number,
  dy: number,
) {
  const targetX = bomb.x + dx
  const targetY = bomb.y + dy
  if (
    targetX < 0
    || targetY < 0
    || targetX >= game.boardSize
    || targetY >= game.boardSize
    || game.board[targetY]?.[targetX] !== 0
  ) return false
  if (game.bombs.some(other => (
    other.id !== bomb.id
    && !other.carriedBy
    && other.x === targetX
    && other.y === targetY
  ))) return false
  const contact = (game.playerHitboxRadius ?? DEFAULT_PLAYER_HITBOX_RADIUS)
    + (game.bombHitboxRadius ?? DEFAULT_BOMB_HITBOX_RADIUS)
  return !game.players.some(player => (
    player.alive
    && player.id !== actor.id
    && (player.x - targetX) ** 2 + (player.y - targetY) ** 2 < contact ** 2
  ))
}

function kickableContact(
  game: BombGame,
  actor: BombPlayer,
  startX: number,
  startY: number,
  x: number,
  y: number,
  dx: number,
  dy: number,
) {
  if (!actor.equipment.kick) return null
  const contact = (game.playerHitboxRadius ?? DEFAULT_PLAYER_HITBOX_RADIUS)
    + (game.bombHitboxRadius ?? DEFAULT_BOMB_HITBOX_RADIUS)
  return game.bombs.find(bomb => (
    !bomb.carriedBy
    && circleBlocksMotion(startX, startY, x, y, bomb.x, bomb.y, contact)
    && bombDestinationOpen(game, actor, bomb, dx, dy)
  )) ?? null
}

function positionOpen(
  game: BombGame,
  actor: BombPlayer,
  startX: number,
  startY: number,
  x: number,
  y: number,
  ignoredBombId: number | null,
) {
  const maximum = game.boardSize - 1
  if (x < 0 || y < 0 || x > maximum || y > maximum) return false

  const playerRadius = game.playerHitboxRadius ?? DEFAULT_PLAYER_HITBOX_RADIUS
  const solidHalfExtent = game.solidHalfExtent ?? DEFAULT_SOLID_HALF_EXTENT
  const baseX = Math.floor(x)
  const baseY = Math.floor(y)
  for (let cellY = Math.max(0, baseY - 1); cellY <= Math.min(maximum, baseY + 2); cellY += 1) {
    for (let cellX = Math.max(0, baseX - 1); cellX <= Math.min(maximum, baseX + 2); cellX += 1) {
      const cell = game.board[cellY]?.[cellX]
      if (cell == null || cell === 0 || (cell === 2 && actor.equipment.ghost)) continue
      const edgeX = Math.max(0, Math.abs(x - cellX) - solidHalfExtent)
      const edgeY = Math.max(0, Math.abs(y - cellY) - solidHalfExtent)
      if (edgeX ** 2 + edgeY ** 2 < playerRadius ** 2 - POSITION_EPSILON) return false
    }
  }

  // Mirror the authoritative ghost phase: terrain remains solid, but bombs
  // and players hidden inside a crate cluster cannot become invisible walls.
  if (actor.equipment.ghost) return true

  const bombContact = playerRadius + (game.bombHitboxRadius ?? DEFAULT_BOMB_HITBOX_RADIUS)
  for (const bomb of game.bombs) {
    if (bomb.carriedBy || bomb.id === ignoredBombId) continue
    if (circleBlocksMotion(startX, startY, x, y, bomb.x, bomb.y, bombContact)) return false
  }

  const playerContact = playerRadius * 2
  for (const player of game.players) {
    if (!player.alive || player.id === actor.id) continue
    if (circleBlocksMotion(startX, startY, x, y, player.x, player.y, playerContact)) return false
  }
  return true
}

function advanceAxis(
  game: BombGame,
  actor: BombPlayer,
  startX: number,
  startY: number,
  direction: number,
  distance: number,
  horizontal: boolean,
): ContinuousMoveResult {
  const dx = horizontal ? direction : 0
  const dy = horizontal ? 0 : direction
  const candidateX = startX + dx * distance
  const candidateY = startY + dy * distance
  const ignoredBomb = kickableContact(
    game,
    actor,
    startX,
    startY,
    candidateX,
    candidateY,
    dx,
    dy,
  )
  const isOpen = (travel: number) => positionOpen(
    game,
    actor,
    startX,
    startY,
    startX + dx * travel,
    startY + dy * travel,
    ignoredBomb?.id ?? null,
  )

  let allowed = distance
  if (!isOpen(distance)) {
    let low = 0
    let high = distance
    for (let iteration = 0; iteration < 14; iteration += 1) {
      const middle = (low + high) / 2
      if (isOpen(middle)) low = middle
      else high = middle
    }
    allowed = low
  }
  const moved = allowed > POSITION_EPSILON
  return {
    x: startX + dx * allowed,
    y: startY + dy * allowed,
    distance: moved ? allowed : 0,
    blocked: allowed + POSITION_EPSILON < distance,
  }
}

export function advanceContinuousPosition(
  game: BombGame,
  actor: BombPlayer,
  startX: number,
  startY: number,
  dx: number,
  dy: number,
  distance: number,
): ContinuousMoveResult {
  if (distance <= POSITION_EPSILON || (!dx && !dy)) {
    return { x: startX, y: startY, distance: 0, blocked: false }
  }

  const primary = advanceAxis(
    game,
    actor,
    startX,
    startY,
    dx || dy,
    distance,
    Boolean(dx),
  )
  if (primary.distance > POSITION_EPSILON) return primary

  // If a perpendicular turn catches a corner, slide toward the centre of the
  // current majority cell without snapping, then retry naturally next frame.
  const maximum = game.boardSize - 1
  const perpendicularOffset = dx
    ? startY - ruleCell(startY, maximum)
    : startX - ruleCell(startX, maximum)
  if (Math.abs(perpendicularOffset) <= POSITION_EPSILON) return primary
  const correction = Math.min(Math.abs(perpendicularOffset), distance)
  return advanceAxis(
    game,
    actor,
    startX,
    startY,
    perpendicularOffset > 0 ? -1 : 1,
    correction,
    Boolean(dy),
  )
}
