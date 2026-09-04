export type FruitId = 'banana' | 'strawberry' | 'lime' | 'plum'
export type PlayerStatus = 'eligible' | 'eliminated' | 'resigned'
export type DisplayStatus = PlayerStatus | 'current_turn' | 'last_chance'
export type AnimationCue =
  | 'round_deal'
  | 'card_flip'
  | 'bell_press_local'
  | 'bell_confirmed'
  | 'collect_piles'
  | 'penalty_transfer'
  | 'player_eliminated'
  | 'final_duel_armed'
  | 'result_enter'

export type Palette = {
  base: string
  dark: string
  light: string
}

export type FruitCardView = {
  faceId: string
  fruitId: FruitId
  fruitCount: number
  copies?: number
  labelZh: string
  altZh: string
  shape: string
  pattern: string
  palette: Palette
}

export type FruitLegendItem = {
  fruitId: FruitId
  nameZh: string
  shape: string
  palette: Palette
}

export type HalliGalliPlayerView = {
  id: string
  name: string
  seat: number
  relativeSeat: number
  isSelf: boolean
  isCurrent: boolean
  connected: boolean
  status: PlayerStatus
  displayStatus: DisplayStatus
  eliminationReason: string | null
  drawCount: number
  discardCount: number
  ownedCount: number
  topCard: FruitCardView | null
}

export type BellPenalty = {
  toPlayerId: string
  count: number
}

export type BellResolutionView = {
  kind: 'correct' | 'wrong' | 'wrong_final'
  boardEpoch: number
  resultBoardEpoch: number
  actorPlayerId: string
  winnerPlayerId: string | null
  validFruitIds: FruitId[]
  capturedCount: number
  sourceCounts: Record<string, number>
  penalties: BellPenalty[]
  eliminatedPlayerIds: string[]
  inputMethod: string
  preFinalDuel: boolean
}

export type HalliGalliEvent = {
  seq: number
  type: string
  cue: AnimationCue
  actorPlayerId: string | null
  targetPlayerIds: string[]
  messageZh: string
  boardEpoch: number
  data: Record<string, unknown> & {
    card?: FruitCardView
    sourceCounts?: Record<string, number>
    penalties?: BellPenalty[]
    winnerPlayerId?: string | null
    capturedCount?: number
  }
}

export type ResultRow = {
  playerId: string
  name: string
  seat: number
  status: PlayerStatus
  drawCount: number
  discardCount: number
  totalCount: number
  rank: number
  won: boolean
}

export type HalliGalliResult = {
  reasonCode: string
  reasonZh: string
  winnerPlayerIds: string[]
  sharedWin: boolean
  rows: ResultRow[]
}

export type HalliGalliView = {
  schemaVersion: number
  modelVersion: string
  profileId: 'official_last_bell'
  sceneId: string
  stage: 'playing' | 'finished'
  revision: number
  turnNumber: number
  boardEpoch: number
  startingPlayerId: string | null
  currentPlayerId: string | null
  selfPlayerId: string
  finalDuelArmed: boolean
  earliestNextFlipAtMs: number
  noProgressDeadlineMs: number | null
  players: HalliGalliPlayerView[]
  rules: {
    playerMin: number
    playerMax: number
    deckSize: number
    bellTarget: number
    profileId: string
    minimumFlipDelayMs: number
    noProgressTimeoutMs: number
    faithfulCounting: boolean
  }
  actions: {
    canFlip: boolean
    canFlipWhenReady: boolean
    canRing: boolean
    canSettleNoProgress: boolean
    flipDisabledReason: string | null
    ringDisabledReason: string | null
  }
  bell: {
    boardEpoch: number
    enabled: boolean
    lastResolution: BellResolutionView | null
  }
  cardCatalog: FruitCardView[]
  fruitLegend: FruitLegendItem[]
  events: HalliGalliEvent[]
  latestEvent: HalliGalliEvent | null
  result: HalliGalliResult | null
}

export const fruitNames: Record<FruitId, string> = {
  banana: '香蕉',
  strawberry: '草莓',
  lime: '青柠',
  plum: '李子',
}
