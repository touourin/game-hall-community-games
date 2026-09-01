export type Direction = 'up' | 'left' | 'down' | 'right'
export type EndReason = 'wrong' | 'timeout' | 'completed' | null

export interface DirectionOption {
  direction: Direction
  equation: string
}

export interface MathRunnerSpeed {
  trackPeriodMs: number
  runCycleMs: number
  speedLines: number
}

export interface MathRunnerGameView {
  level?: number
  maxLevel?: number
  correctAnswers?: number
  totalQuestions?: number
  streakInLevel?: number
  questionsPerLevel?: number
  questionsToNextLevel?: number
  score?: number
  distanceMeters?: number
  questionId?: number | null
  timeLimitMs?: number
  remainingMs?: number
  options?: DirectionOption[]
  blockedDirections?: Direction[]
  lastDirection?: Direction | null
  lastPoints?: number
  levelUp?: boolean
  endReason?: EndReason
  correctDirection?: Direction | null
  elapsedMs?: number
  averageResponseMs?: number | null
  speed?: MathRunnerSpeed
  won?: boolean
  result?: string | null
}

export interface DirectionMeta {
  id: Direction
  label: string
  key: 'W' | 'A' | 'S' | 'D'
  symbol: '↑' | '←' | '↓' | '→'
}

export const DIRECTION_META: readonly DirectionMeta[] = [
  { id: 'up', label: '上', key: 'W', symbol: '↑' },
  { id: 'left', label: '左', key: 'A', symbol: '←' },
  { id: 'down', label: '下', key: 'S', symbol: '↓' },
  { id: 'right', label: '右', key: 'D', symbol: '→' },
]

export const KEY_TO_DIRECTION: Readonly<Record<string, Direction>> = {
  w: 'up',
  a: 'left',
  s: 'down',
  d: 'right',
}

export function directionLabel(direction: Direction | null | undefined): string {
  return DIRECTION_META.find((entry) => entry.id === direction)?.label ?? '未知'
}
