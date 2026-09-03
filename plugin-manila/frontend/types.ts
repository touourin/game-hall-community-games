export type CommodityId = 'ginseng' | 'nutmeg' | 'silk' | 'jade'
export type PuntId = 'punt-1' | 'punt-2' | 'punt-3'
export type LaneId = 'lane-1' | 'lane-2' | 'lane-3'

export interface WorkerView {
  workerId: string
  playerId: string
  role: string
  slotIndex: number | null
  colorId: string
  color: string
  ink: string
}

export interface CommodityView {
  id: CommodityId
  label: string
  labelEn: string
  code: string
  profit: number
  costs: number[]
  color: string
  pattern: string
  value: number
  trackIndex: number
  supplyCount: number
}

export interface ShareCardView {
  id: string
  commodityId: CommodityId
  label: string
  labelEn: string
  code: string
  color: string
  pattern: string
  marketValue: number
  mortgaged: boolean
}

export interface ManilaPlayerView {
  id: string
  name: string
  seat: number
  avatarUrl?: string | null
  connected: boolean
  forfeited: boolean
  cash: number
  colorId: string
  color: string
  ink: string
  workerCount: number
  availableWorkerCount: number
  shareCount: number
  mortgagedShareCount: number
  passedPlacement: boolean
  isHarborMaster: boolean
  isCurrent: boolean
  finalWealth: number | null
  rank: number | null
  shareCards?: ShareCardView[]
}

export interface CargoSlotView {
  index: number
  cost: number
  occupant: WorkerView | null
}

export interface PuntView {
  id: PuntId
  number: number
  cargoId: CommodityId | null
  cargo: Omit<CommodityView, 'value' | 'trackIndex' | 'supplyCount'> | null
  laneId: LaneId | null
  position: number
  status: 'waiting' | 'sailing' | 'port' | 'shipyard' | 'plundered_waiting'
  lastDie: number | null
  destinationSlot: string | null
  plundered: boolean
  displacedPlayerIds: string[]
  occupants: WorkerView[]
  cargoSlots: CargoSlotView[]
}

export interface DestinationView {
  id: string
  slot: 'A' | 'B' | 'C'
  kind: 'port' | 'shipyard'
  cost: number
  payout: number
  bettor: WorkerView | null
  puntId: PuntId | null
}

export interface SpecialPositionView {
  id: string
  kind: 'pirate' | 'pilot' | 'insurance'
  label: string
  cost: number
  occupant: WorkerView | null
}

export interface PlacementTarget {
  targetId: string
  kind: string
  label: string
  cost: number
  slotIndex?: number
  payout?: number
  affordable: boolean
  blindAllowed: boolean
  payable: number
}

export interface LegalActions {
  canResign?: boolean
  loanableShareIds?: string[]
  repayableShareIds?: string[]
  canBid?: boolean
  minimumBid?: number
  maximumBid?: number
  canPassAuction?: boolean
  shareOptions?: Array<{
    commodityId: CommodityId
    price: number
    remaining: number
    affordable: boolean
  }>
  canSkipShare?: boolean
  canSelectCargo?: boolean
  canSetStartPositions?: boolean
  placementTargets?: PlacementTarget[]
  canPassPlacement?: boolean
  canRollDice?: boolean
  moveOrderPuntIds?: PuntId[]
  pirateBoardPuntIds?: PuntId[]
  canPirateStay?: boolean
  pilot?: { large: boolean, puntIds: PuntId[], canPass: boolean }
  pirateRoute?: { puntId: PuntId, destinations: Array<'port' | 'shipyard'> }
  canStartNextVoyage?: boolean
}

export interface SettlementEntry {
  entryId: string
  fromId: string
  toId: string
  amount: number
  reason: string
  puntId: PuntId | null
  slotId: string | null
  bankCoverage: number
  payerAmount: number
  selfInsurance: boolean
}

export interface SettlementView {
  voyageNumber: number
  entries: SettlementEntry[]
  cashBefore: Record<string, number>
  cashAfter: Record<string, number>
  marketBefore: Record<CommodityId, number>
  marketAfter: Record<CommodityId, number>
  deliveredCommodityIds: CommodityId[]
  damagedPuntIds: PuntId[]
  plunderedPuntIds: PuntId[]
}

export interface GameEventView {
  id: number
  type: string
  message: string
  details: Record<string, unknown>
}

export interface AnimationView {
  id: number
  kind: string
  [key: string]: unknown
}

export interface ManilaGameView {
  schemaVersion: number
  modelVersion: string
  ruleset: string
  rulesVariant: 'base'
  enhancedPirates: false
  sceneId: string
  stage: string
  stageLabel: string
  voyageNumber: number
  roomPhase: string
  currentPlayerId: string | null
  harborMasterId: string | null
  turnOrder: string[]
  players: ManilaPlayerView[]
  market: CommodityView[]
  marketTrack: number[]
  lanes: Array<{ id: LaneId, number: number, marks: number[], puntId: PuntId | null }>
  punts: PuntView[]
  destinations: { port: DestinationView[], shipyard: DestinationView[] }
  specialPositions: SpecialPositionView[]
  auction: {
    openerId: string
    currentPlayerId: string | null
    activePlayerIds: string[]
    passedPlayerIds: string[]
    leaderId: string | null
    currentBid: number
  } | null
  schedule: Array<{ index: number, token: string, state: 'done' | 'current' | 'upcoming' }>
  placementRound: number
  movementRound: number
  dice: Partial<Record<PuntId, number>>
  lastMoveOrder: PuntId[]
  pirateBoardQueue: string[]
  pirateRouteQueue: PuntId[]
  legalActions: LegalActions
  animation: AnimationView | null
  events: GameEventView[]
  settlement: SettlementView | null
  rankings: string[]
  winnerPlayerIds: string[]
  winReason: string | null
  own: {
    playerId: string
    cash: number
    availableWorkerIds: string[]
    shareCards: ShareCardView[]
  } | null
  rules: Record<string, unknown>
}

