export type IndustryId = 'transportation' | 'grain' | 'media' | 'real_estate'

export type FundKind = 'starting' | 'regular' | 'bear'

export type FundCardView = {
  id: string
  amount: number
  period: number
  interest: number
  averageBurden: number
  yieldPercent: number
  kind: FundKind
  isBear: boolean
  dueIn?: number
}

export type IndustryView = {
  id: IndustryId
  name: string
  shortName: string
  supply: number
  remaining: number
  color: string
  icon: string
}

export type LuxuryView = {
  id: string
  name: string
  cost: number
  points: number
  icon: string
}

export type LedgerView = {
  playerId: string
  cash: number | null
  cashHidden: boolean
  industries: Record<IndustryId, number>
  industryTotal: number
  funds: FundCardView[]
  fundCount: number
  luxuries: LuxuryView[]
  interestDueNext: number
  cycleInterest: number
  bankrupt: boolean
  forfeited: boolean
  finalScore: number | null
}

export type SettlementRow = {
  playerId: string
  rank: number | null
  winner: boolean
  bankrupt: boolean
  industryScore: number
  luxuryScore: number | null
  wealthScore: number | null
  highestFund: number
  total: number
}

export type SettlementView = {
  mode: 'industry_and_luxury' | 'industry_and_wealth'
  winnerPlayerIds: string[]
  bankruptPlayerIds: string[]
  reason: string | null
  rows: SettlementRow[]
}

export type FundingOption = {
  industryId: IndustryId
  industryName: string
  row: number
  cardIds: string[]
}

export type TradeTarget = {
  targetId: string
  industryIds: IndustryId[]
}

export type LegalActions = {
  canResign?: boolean
  fundingOptions?: FundingOption[]
  canPassFunding?: boolean
  tradeTargets?: TradeTarget[]
  maxOffer?: number
  canPassTrade?: boolean
  luxuryIds?: string[]
  canAcceptOffer?: boolean
  canCounterOffer?: boolean
  discardMarketCardIds?: string[]
  discardIndustryIds?: IndustryId[]
}

export type GameEventView = {
  seq: number
  type: string
  message: string
  data: Record<string, unknown>
}

export type PonziGameView = {
  version: string
  ruleset: 'bright-eye-standard'
  round: number
  stage: string
  stageLabel: string
  currentPlayerId: string | null
  starterPlayerId: string | null
  turnOrder: string[]
  marketRows: FundCardView[][]
  bearCount: number
  playerCount: number
  deckCounts: { draw: number, discard: number, removedStarting: number }
  industryCatalog: IndustryView[]
  luxuryMarket: LuxuryView[]
  luxuriesEnabled: boolean
  scoringMode: 'industry_and_luxury' | 'industry_and_wealth'
  wheelPosition: number
  wheelAdvance: 1 | 2
  ledgers: LedgerView[]
  pendingTrade: {
    proposerId: string
    targetId: string
    industryId: IndustryId
    industryName: string
    offer: number | null
    offerKnown: boolean
  } | null
  legalActions: LegalActions
  events: GameEventView[]
  bankruptPlayerIds: string[]
  rankings: string[]
  settlement: SettlementView | null
  privacy: {
    cash: string
    tradeOffer: string
    fundsAndIndustries: string
  }
}
