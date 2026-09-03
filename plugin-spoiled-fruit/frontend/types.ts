export interface FruitCardView {
  instanceId: string
  catalogId: string
  cardCode: string
  sortIndex: number
  kind: 'normal' | 'old_maid'
  nameZh: string
  effectId: string
  effectLabelZh: string
  effectTextZh: string
  slug: string
}

export interface HandSlotView {
  slotId: string
  index: number
  card: FruitCardView | null
  protected: boolean
  selectable: boolean
}

export interface PlayerBoardView {
  playerId: string
  seatIndex: number
  handCount: number
  handSlots: HandSlotView[]
  safe: boolean
  pendingEmpty: boolean
  protectedSlotIndex: number | null
  harvestPairIds: string[]
  harvestCount: number
}

export interface EffectView {
  queueId: string
  batchId: string
  pairCatalogId: string
  effectId: string
  effectLabelZh: string
  ownerPlayerId: string
}

export interface FruitEvent {
  sequence: number
  type: string
  message: string
  pairCatalogId?: string
  effectId?: string
  playerId?: string
  sourcePlayerId?: string
  targetPlayerId?: string
  playerIds?: string[]
  [key: string]: unknown
}

export interface PrivateChoice {
  type: 'optional' | 'extra_draw' | 'half_select' | 'insert'
  queueId: string
  effectId: string
  effectLabelZh: string
  targetPlayerIds?: string[]
  availableCardIds?: string[]
  sourcePlayerId?: string
  selectionCount?: number
  handCount?: number
  otherPlayerId?: string
  transferType?: string
  incomingCards?: FruitCardView[]
  baseHandCount?: number
}

export interface PrivatePeek {
  effectOwnerId: string
  targetPlayerId: string
  orderedCards: FruitCardView[]
  protectedSlotIndex: number | null
  capturedAtEventSequence: number
}

export interface SpoiledFruitGameView {
  schemaVersion: number
  gameKey: string
  mode: 'standard'
  phase: string
  sceneId: string
  firstPlayerId: string | null
  currentPlayerId: string | null
  playerCount: number
  oldMaidCount: number
  totalCardCount: number
  removedPairCount: number
  initialRemovedPairCount: number
  normalDrawCount: number
  effectTransferCount: number
  players: PlayerBoardView[]
  drawSourcePlayerId: string | null
  effectQueue: EffectView[]
  activeEffect: EffectView | null
  skipCount: number
  pendingChoice: {
    type: string
    effectId: string
    requiredPlayerIds: string[]
    completedPlayerIds: string[]
  } | null
  privateChoice: PrivateChoice | null
  privatePeek: PrivatePeek | null
  legalActions: string[]
  events: FruitEvent[]
  eventSequence: number
  safeOrder: string[]
  finished: {
    winnerIds: string[]
    loserIds: string[]
    oldMaidHolders: Array<{ playerId: string; cards: FruitCardView[] }>
  } | null
  won: boolean
  result: string | null
}
