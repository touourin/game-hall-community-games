export type StandardColor = 'white' | 'blue' | 'green' | 'red' | 'black'
export type PieceColor = StandardColor | 'gold'
export type PieceVector = Record<PieceColor, number>
export type BonusVector = Record<StandardColor, number>

export const standardColors: StandardColor[] = ['white', 'blue', 'green', 'red', 'black']
export const pieceColors: PieceColor[] = [...standardColors, 'gold']

export const colorInfo: Record<PieceColor, { name: string, short: string, symbol: string, hex: string }> = {
  white: { name: '钻石', short: '白', symbol: '◇', hex: '#e8e3d8' },
  blue: { name: '蓝宝石', short: '蓝', symbol: '◆', hex: '#3a739a' },
  green: { name: '祖母绿', short: '绿', symbol: '⬟', hex: '#4e8068' },
  red: { name: '红宝石', short: '红', symbol: '⬢', hex: '#a8524b' },
  black: { name: '缟玛瑙', short: '黑', symbol: '●', hex: '#353a3d' },
  gold: { name: '黄金', short: '金', symbol: '★', hex: '#c79b43' },
}

export type PaymentPreview = {
  effectiveCost: BonusVector
  recommendedPayment: PieceVector
  minimumGold: number
  affordable: boolean
}

export type DevelopmentCardView = {
  id: string
  level: 1 | 2 | 3
  bonusColor: StandardColor
  prestige: number
  cost: BonusVector
  totalCost: number
  artVariant: number
  labelZh: string
  compactLabelZh: string
  payment?: PaymentPreview | null
  legal?: { buy: boolean, reserve: boolean }
}

export type NobleView = {
  id: string
  prestige: number
  requirement: BonusVector
  portraitVariant: number
  labelZh: string
  progress?: BonusVector
  eligible?: boolean
}

export type ReservationView = {
  reservationId: string
  level: number
  source: 'market' | 'deck'
  knownToAll: boolean
  card: DevelopmentCardView | null
}

export type PlayerView = {
  id: string
  name: string
  seat: number
  connected: boolean
  forfeited: boolean
  isActive: boolean
  isFirstPlayer: boolean
  pieces: PieceVector
  bonuses: BonusVector
  score: number
  cardPrestige: number
  noblePrestige: number
  purchasedCount: number
  purchasedCards: DevelopmentCardView[]
  nobles: NobleView[]
  reservations: ReservationView[]
}

export type TierView = {
  level: 1 | 2 | 3
  deckCount: number
  slots: Array<{ slot: number, card: DevelopmentCardView | null }>
}

export type ActionView = {
  canAct: boolean
  canTakeDifferent: boolean
  requiredDistinctCount: number
  differentColors: StandardColor[]
  sameColors: StandardColor[]
  canReserve: boolean
  blindReserveLevels: number[]
  canReturnTokens: boolean
  returnCount: number
  canChooseNoble: boolean
  eligibleNobleIds: string[]
  canResign: boolean
  disabledReasonZh: string | null
}

export type EventView = {
  seq: number
  type: string
  message: string
  data: Record<string, any>
}

export type ResultRowView = {
  player_id: string
  prestige: number
  card_prestige: number
  noble_prestige: number
  purchased_card_count: number
  rank: number
  winner: boolean
  forfeited: boolean
}

export type ResultView = {
  winnerIds: string[]
  outcome: 'win' | 'shared-win'
  reason: string
  rows: ResultRowView[]
  summaryZh: string
}

export type SplendorGameView = {
  schemaVersion: number
  modelVersion: string
  gameId: 'splendor'
  rulesProfile: 'base-2024-refresh'
  sceneId: string
  phase: 'turn_action' | 'return_tokens' | 'choose_noble' | 'finished'
  revision: number
  marketRevision: number
  roundNumber: number
  actionNumber: number
  turnOrder: string[]
  currentPlayerId: string | null
  firstPlayerId: string
  finalRound: null | {
    triggeredBy: string
    finalTurnPlayerId: string
    remainingPlayerIds: string[]
  }
  colors: Array<{ id: PieceColor, nameZh: string, symbol: string, semanticColor: string, pattern: string }>
  supply: PieceVector
  tiers: TierView[]
  availableNobles: NobleView[]
  players: PlayerView[]
  selfPlayerId: string | null
  actions: ActionView
  events: EventView[]
  result: ResultView | null
  rules: { targetPrestige: number, pieceLimit: number, reservationLimit: number, marketCardsPerLevel: number, noblePrestige: number }
}

export function emptyPieces(): PieceVector {
  return { white: 0, blue: 0, green: 0, red: 0, black: 0, gold: 0 }
}
