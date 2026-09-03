export type SuitId = 'anchor' | 'hook' | 'cannon' | 'key' | 'chest' | 'map' | 'oracle' | 'sword' | 'kraken' | 'mermaid'

export type CardView = {
  id: string
  suit: SuitId
  value: number
  nameZh: string
  nameEn: string
  symbol: string
  icon: string
  color: string
  summaryZh: string
}

export type SuitView = Omit<CardView, 'id' | 'suit' | 'value'> & {
  id: SuitId
}

export type TraitView = {
  id: string
  nameZh: string
  nameEn: string
  summaryZh: string
  appliesTo: string[]
}

export type BankStack = {
  suit: SuitId
  cardIds: string[]
  cards: CardView[]
  topValue: number | null
  count: number
  subtotal: number
}

export type PlayerView = {
  id: string
  seat: number
  displayName: string
  connected: boolean
  isActive: boolean
  forfeited: boolean
  traitId: string | null
  trait: TraitView | null
  selectingTrait: boolean
  lockerTargetId: string | null
  bank: BankStack[]
  liveScore: number
  bankCardCount: number
}

export type PlayEntryView = {
  entryId: string
  cardId: string
  card: CardView
  protected: boolean
  protectionLabelsZh: string[]
  sourceLabelZh: string
}

export type ChoiceOptionView = {
  optionId: string | null
  labelZh: string
  cardId: string | null
  card: CardView | null
  playerId: string | null
  suit: SuitId | null
  entryId: string | null
  causesImmediateBust: boolean
  actionable: boolean
}

export type PendingChoiceView = {
  choiceId: string | null
  kind: string
  actorId: string
  promptZh: string
  options: ChoiceOptionView[]
}

export type PublicEventView = {
  seq: number
  type: string
  textZh: string
  data: Record<string, any>
}

export type ScoreRowView = {
  playerId: string
  suitSubtotals: Record<SuitId, number>
  cardAdjustments: number
  variantAdjustment: number
  total: number
  eligible: boolean
  bankCardCount: number
  rank: number | null
  winner: boolean
}

export type ResultView = {
  winnerIds: string[]
  outcome: 'win' | 'shared-win' | 'shared-draw'
  reason: 'draw-pile-exhausted' | 'player-exit'
  scores: ScoreRowView[]
  summaryZh: string
}

export type DeadMansDrawView = {
  schemaVersion: number
  modelVersion: string
  gameId: string
  revision: number
  phase: 'waiting' | 'trait_selection' | 'turn' | 'effect_choice' | 'finished'
  rules: {
    profileId: string
    profileNameZh: string
    traitsEnabled: boolean
    globalVariantId: null
    globalVariantNameZh: null
  }
  suitCatalog: SuitView[]
  players: PlayerView[]
  currentPlayerId: string | null
  turnNumber: number
  drawCount: number
  discard: { count: number; cardIds: string[]; cards: CardView[] }
  playArea: PlayEntryView[]
  turn: null | {
    number: number
    actorId: string
    krakenDebt: number
    bustKey: 'suit'
    presentBustKeys: SuitId[]
    oraclePeekCardIds: string[]
    oraclePeekCards: CardView[]
    mapRevealCardIds: string[]
    mapRevealCards: CardView[]
    pendingChoice: PendingChoiceView | null
  }
  self: null | {
    playerId: string
    traitOffer: TraitView[]
    mustChooseLockerTarget: boolean
  }
  actions: {
    canChooseTrait: boolean
    canChooseLockerTarget: boolean
    canDraw: boolean
    canCollect: boolean
    canResolveEffect: boolean
    canResign: boolean
    disabledReasonZh: string | null
  }
  result: ResultView | null
  events: PublicEventView[]
}
