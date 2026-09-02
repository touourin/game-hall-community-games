export type BullCardTier = 'single' | 'double' | 'triple' | 'quintuple' | 'royal'

export interface BullCard {
  id: string
  number: number
  bullheads: 1 | 2 | 3 | 5 | 7
  tier: BullCardTier
}

export interface BullPlayerView {
  id: string
  name: string
  seat: number
  status: 'active' | 'forfeited'
  handCount: number
  hasSelected: boolean
  roundPenalty: number
  totalPenalty: number
  capturedCount: number
  rank: number | null
}

export interface PublicPlay {
  playerId: string
  card: BullCard
}

export interface RowChoice {
  rowIndex: number
  cardCount: number
  bullheads: number
}

export type AnimationStepType = 'place' | 'take_full' | 'take_low'

export interface BullAnimationStep {
  id: string
  type: AnimationStepType
  playerId: string
  card: BullCard
  rowIndex: number
  takenCards: BullCard[]
  penalty: number
}

export interface BullAnimation {
  id: number
  kind: 'round_deal' | 'turn_resolution' | 'low_card_choice'
  roundNumber: number
  turnNumber: number
  revealed: PublicPlay[]
  steps: BullAnimationStep[]
  pendingChoice: PublicPlay | null
  complete: boolean
}

export interface BullRoundSummary {
  roundNumber: number
  penalties: Record<string, number>
  totals: Record<string, number>
  leaderIds: string[]
  thresholdReached: boolean
}

export interface BullHistoryEntry {
  type: string
  message: string
  playerId?: string
  rowIndex?: number
}

export interface BullheadGameView {
  schemaVersion: 1
  sceneId: string
  stage: 'setup' | 'select' | 'resolving' | 'choose_row' | 'round_summary' | 'finished'
  roundNumber: number
  turnNumber: number
  rules: {
    cardMinimum: number
    cardMaximum: number
    handSize: number
    rowCount: number
    rowLimit: number
    targetPenalty: number
  }
  players: BullPlayerView[]
  activePlayerIds: string[]
  rows: BullCard[][]
  hand: BullCard[]
  committedCard: BullCard | null
  committedPlayerIds: string[]
  waitingForPlayerIds: string[]
  revealed: PublicPlay[]
  pendingLowCard: PublicPlay | null
  rowChoices: RowChoice[]
  actions: string[]
  animation: BullAnimation | null
  roundSummary: BullRoundSummary | null
  history: BullHistoryEntry[]
  rankings: string[]
  canSelect: boolean
  canChooseRow: boolean
  canStartNextRound: boolean
}
