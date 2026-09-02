export type UnoColor = 'red' | 'yellow' | 'green' | 'blue'

export type UnoCardKind =
  | 'number'
  | 'skip'
  | 'reverse'
  | 'draw_two'
  | 'wild'
  | 'wild_draw_four'

export interface UnoCardModel {
  id: string
  color: UnoColor | null
  kind: UnoCardKind
  value: number | null
  label: string
}

export interface UnoColorOption {
  id: UnoColor
  label: string
}

export interface UnoEvent {
  sequence: number
  type: string
  playerId: string | null
  targetPlayerId: string | null
  card: UnoCardModel | null
  color: UnoColor | null
  count: number
  stackTotal: number
  stacked: boolean
  calledUno: boolean
  message: string
}

export interface UnoHistoryItem {
  type: string
  playerId?: string
  targetPlayerId?: string | null
  count?: number
  message: string
}

export interface UnoGameView {
  colors: UnoColorOption[]
  turnOrder: string[]
  currentPlayerId: string | null
  direction: 1 | -1
  activeColor: UnoColor | null
  stage: 'turn' | 'after_draw'
  topCard: UnoCardModel | null
  hand: UnoCardModel[]
  cardCounts: Record<string, number>
  drawPileCount: number
  discardPileCount: number
  drawnCardId: string | null
  playableCardIds: string[]
  pendingDrawTotal: number
  pendingDrawTargetPlayerId: string | null
  pendingDrawSourcePlayerId: string | null
  canTakePenalty: boolean
  canDraw: boolean
  canKeepDrawn: boolean
  canCatchUno: boolean
  unoVulnerablePlayerId: string | null
  forfeitedPlayerIds: string[]
  winnerPlayerIds: string[]
  latestEvent: UnoEvent | null
  history: UnoHistoryItem[]
}
