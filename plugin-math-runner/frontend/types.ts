export type RunnerAction = 'jump' | 'left' | 'slide' | 'right'
export type TrackLane = 'left' | 'center' | 'right'
export type ObstacleKind = 'ground' | 'overhead' | null
export type EndReason = 'wrong' | 'timeout' | 'completed' | null
export type RunnerFailureKind = 'wall' | 'cliff' | null

export interface RunnerOption {
  action: RunnerAction
  lane: TrackLane
  obstacle: ObstacleKind
  equation: string
}

export interface MathRunnerSpeed {
  trackPeriodMs: number
  runCycleMs: number
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
  options?: RunnerOption[]
  branchCount?: number
  blockedActions?: RunnerAction[]
  lastAction?: RunnerAction | null
  lastPoints?: number
  levelUp?: boolean
  endReason?: EndReason
  correctAction?: RunnerAction | null
  elapsedMs?: number
  averageResponseMs?: number | null
  speed?: MathRunnerSpeed
  won?: boolean
  result?: string | null
}

export interface RunnerActionMeta {
  id: RunnerAction
  label: string
  key: 'W' | 'A' | 'S' | 'D'
  symbol: '↑' | '←' | '↓' | '→'
  help: string
}

export const RUNNER_ACTION_META: readonly RunnerActionMeta[] = [
  { id: 'jump', label: '跳跃', key: 'W', symbol: '↑', help: '越过低墙' },
  { id: 'left', label: '左变道', key: 'A', symbol: '←', help: '进入左侧分叉' },
  { id: 'slide', label: '下蹲', key: 'S', symbol: '↓', help: '从高墙下方滑过' },
  { id: 'right', label: '右变道', key: 'D', symbol: '→', help: '进入右侧分叉' },
]

export const KEY_TO_ACTION: Readonly<Record<string, RunnerAction>> = {
  w: 'jump',
  arrowup: 'jump',
  ' ': 'jump',
  a: 'left',
  arrowleft: 'left',
  s: 'slide',
  arrowdown: 'slide',
  d: 'right',
  arrowright: 'right',
}

export function actionLabel(action: RunnerAction | null | undefined): string {
  return RUNNER_ACTION_META.find((entry) => entry.id === action)?.label ?? '未知动作'
}

export function laneLabel(lane: TrackLane): string {
  return {
    left: '左侧跑道',
    center: '中间跑道',
    right: '右侧跑道',
  }[lane]
}
