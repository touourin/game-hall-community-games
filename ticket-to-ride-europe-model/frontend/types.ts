export type TrainColor =
  | 'purple'
  | 'blue'
  | 'orange'
  | 'white'
  | 'green'
  | 'yellow'
  | 'black'
  | 'red'
  | 'gray'
  | 'locomotive'

export type PlayerColor = 'ruby' | 'sapphire' | 'jade' | 'amber' | 'violet'
export type RouteKind = 'standard' | 'tunnel' | 'ferry'

export interface CityModel {
  id: string
  boardLabel: string
  labelZhCN: string
  modernName: string
  position: { x: number; y: number }
}

export interface RouteModel {
  id: string
  fromCityId: string
  toCityId: string
  length: 1 | 2 | 3 | 4 | 6 | 8
  points: number
  color: TrainColor
  kind: RouteKind
  locomotivesRequired: number
  parallelGroupId: string | null
  trackIndex: number
}

export interface BoardModel {
  coordinateSystem: { width: number; height: number }
  cities: CityModel[]
  routes: RouteModel[]
}

export interface TrainCardModel {
  id: string
  typeId: string
  color: Exclude<TrainColor, 'gray'>
  label: string
  visual: {
    accent: string
    pattern: string
    accessibilityCode: string
  }
}

export interface DestinationTicketModel {
  id: string
  category: 'regular' | 'long'
  fromCityId: string
  toCityId: string
  fromLabel: string
  toLabel: string
  points: number
  completed: boolean
}

export interface EuropePlayerView {
  id: string
  name: string
  seat: number
  color: PlayerColor
  status: 'active' | 'forfeited'
  score: number
  trainsRemaining: number
  stationsRemaining: number
  trainHandCount: number
  destinationTicketCount: number
  initialTicketChoiceSubmitted: boolean
  finalStationAssignmentSubmitted: boolean
}

export interface RouteClaimView {
  routeId: string
  ownerPlayerId: string
}

export interface StationView {
  cityId: string
  ownerPlayerId: string
  borrowedRouteId: string | null
}

export interface EuropeEvent {
  sequence: number
  type: string
  playerId: string | null
  message: string
  routeId?: string
  cityId?: string
  source?: 'deck' | 'market'
  cardTypeId?: string | null
  marketRefreshed?: boolean
  routeKind?: RouteKind
  length?: number
  points?: number
  revealedCards?: TrainCardModel[]
  extraCost?: number
  count?: number
  keptCount?: number
  triggerPlayerId?: string
  remainingPlayerIds?: string[]
}

export interface PlayerScoreBreakdown {
  playerId: string
  status: string
  routePoints: number
  destinationPoints: number
  stationPoints: number
  longestPathPoints: number
  total: number
  completedTicketCount: number
  completedTicketIds: string[]
  failedTicketIds: string[]
  stationsUsed: number
  longestPathLength: number
  europeanExpress: boolean
  rank: number
}

export interface EuropeResult {
  reason: 'score' | 'last_player_remaining'
  winnerPlayerIds: string[]
  ranking: string[]
  europeanExpressPlayerIds: string[]
  longestPathLength: number
  players: PlayerScoreBreakdown[]
}

export interface EuropeGameView {
  schemaVersion: number
  gameKey: string
  sceneId: string
  phase: string
  rules: {
    playerCount: number
    startingTrains: number
    startingStations: number
    europeanExpressPoints: number
    unusedStationPoints: number
    doubleRoutesRestricted: boolean
  }
  turnOrder: string[]
  currentPlayerId: string | null
  turnNumber: number
  players: EuropePlayerView[]
  market: TrainCardModel[]
  trainDeckCount: number
  trainDiscardCount: number
  destinationDeckCount: number
  claimedRoutes: RouteClaimView[]
  stationPlacements: StationView[]
  hand: TrainCardModel[]
  destinationTickets: DestinationTicketModel[]
  initialTicketOptions: DestinationTicketModel[]
  pendingTicketChoice: {
    kind: string
    minKeep: number
    offeredTickets: DestinationTicketModel[]
  } | null
  pendingTunnel: {
    actorPlayerId: string
    routeId: string
    declaredColor: TrainColor
    revealedCards: TrainCardModel[]
    extraCost: number
    status: string
  } | null
  ownTunnelPayment: {
    routeId: string
    declaredColor: TrainColor
    initialCards: TrainCardModel[]
    extraCost: number
    paymentMode: 'declared-color' | 'locomotive-only'
  } | null
  legalClaimRouteIds: string[]
  stationEligibleCityIds: string[]
  finalRound: {
    triggerPlayerId: string
    remainingPlayerIds: string[]
  } | null
  actions: string[]
  latestEvent: EuropeEvent | null
  history: EuropeEvent[]
  result: EuropeResult | null
}
