export type CommodityId = 'oil' | 'gold' | 'cotton' | 'copper'

export type CardView = {
  instanceId: string
  cardId: string
  name: string
  kind: 'personal' | 'public'
  category: string
  strength: string
  subtype: string
  targetLabel: string
  timing: string
  text: string
  durationText: string
  keywords: string[]
}

export type MarketView = {
  commodity: CommodityId
  name: string
  color: string
  spotIndex: number
  spotPrice: number
  openIndex: number
  openPrice: number
  currentIndex: number
  currentPrice: number
  closeIndex: number
  closePrice: number
  lowLimitIndex: number
  lowLimitPrice: number
  highLimitIndex: number
  highLimitPrice: number
  validTradeIndices: number[]
  validTradePrices: number[]
  seal: 'up' | 'down' | null
}

export type PositionView = {
  quantity: number
  basis: number
  margin: number
}

export type LedgerView = {
  playerId: string
  cash: number
  margin: number
  loanPrincipal: number
  loanInterest: number
  exchangeDebt: number
  estimatedEquity: number
  positions: Record<CommodityId, PositionView>
  handCount: number
  bankrupt: boolean
  forfeited: boolean
  forcedLiquidations: number
  marginBuffer: number
  finalScore: number | null
}

export type AuctionView = {
  initiatorId: string
  commodity: CommodityId
  side: 'buy' | 'sell'
  quoteIndex: number
  price: number
  leaderId: string
  passedIds: string[]
  cursorPlayerId: string | null
  initiationNumber: number
  initiationTotal: number
}

export type ActiveEffectView = {
  effectId: string
  cardId: string
  cardName: string
  scope: 'personal' | 'public'
  ownerId: string | null
  moves: Array<{ commodity: CommodityId; delta: number }>
  remainingTriggers: number
  direction: 'up' | 'down'
}

export type PlayableCard = {
  instanceId: string
  cardId: string
  commodities?: CommodityId[]
  effectIds?: string[]
}

export type LegalActions = {
  canResign?: boolean
  borrowAmounts?: number[]
  auctionStarts?: Array<{
    commodity: CommodityId
    side: 'buy' | 'sell'
    quoteIndices: number[]
  }>
  canSkipAuction?: boolean
  bidQuoteIndices?: number[]
  canPassBid?: boolean
  playableCards?: PlayableCard[]
  reduceOnlyCommodities?: CommodityId[]
  canPassCard?: boolean
  discardCount?: number
  liquidationCommodities?: CommodityId[]
}

export type GameEventView = {
  seq: number
  type: string
  message: string
  data: Record<string, unknown>
}

export type CrazyFuturesGame = {
  version: string
  round: number
  maxRounds: number
  stage: string
  stageLabel: string
  currentPlayerId: string | null
  starterPlayerId: string | null
  turnOrder: string[]
  markets: MarketView[]
  priceLadder: number[]
  priceZones: Record<string, [number, number]>
  ledgers: LedgerView[]
  auction: AuctionView | null
  initiationNumber: number
  initiationTotal: number
  publicEvents: CardView[]
  activeEffects: ActiveEffectView[]
  hand: CardView[]
  peekCards: CardView[]
  deckCounts: {
    personal: number
    personalDiscard: number
    public: number
    publicDiscard: number
  }
  pendingChoice: {
    kind: string
    playerId: string
    count: number | null
    reason: string | null
    isMine: boolean
  } | null
  legalActions: LegalActions
  events: GameEventView[]
  rankings: string[]
}
