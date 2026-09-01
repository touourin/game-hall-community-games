export type SkullPhase =
  | 'lobby'
  | 'round_setup'
  | 'placement'
  | 'bidding'
  | 'reveal'
  | 'penalty'
  | 'round_end'
  | 'finished'

export type DiscKind = 'unknown' | 'flower' | 'skull' | 'last_chance_flower'
export type ThemeSlug = 'ember' | 'tide' | 'moss' | 'orchid' | 'ochre' | 'slate'

export interface SkullDiscView {
  id: string
  kind: DiscKind
  origin: 'personal' | 'last_chance'
  faceUp: boolean
  knowledge: 'hidden' | 'self' | 'public'
}

export interface SkullThemeView {
  id: string
  slug: ThemeSlug
  label: string
  patternCode: string
}

export interface SkullPlayerView {
  id: string
  displayName: string
  seat: number
  status: 'active' | 'eliminated'
  challengeWins: number
  matSide: 'blank' | 'flower'
  lastChanceUsed: boolean
  passedBid: boolean
  handCount: number
  stack: SkullDiscView[]
  removedCount: number
  removed: SkullDiscView[]
  personalDiscCount: number
  theme: SkullThemeView
}

export interface SkullHistoryEntry {
  type: string
  message: string
  playerId?: string
  ownerId?: string
  chooserId?: string
  count?: number
  wins?: number
  kind?: DiscKind
  round?: number
}

export interface SkullGameView {
  schemaVersion: 1
  gameKey: 'skull'
  sceneId: string
  phase: SkullPhase
  rules: {
    targetWins: number
    lastChanceEnabled: boolean
  }
  players: SkullPlayerView[]
  activePlayerIds: string[]
  hand: SkullDiscView[]
  round: {
    number: number
    firstPlayerId: string
    currentPlayerId: string | null
    committedCount: number
    activePlayerCount: number
    hasCommitted: boolean
    firstPlayerCommitsLast: boolean
    totalPlaced: number
    currentBid: number
    highBidderId: string | null
    passedPlayerIds: string[]
    challengerId: string | null
    targetBid: number
    revealedCount: number
    failed: boolean
    skullOwnerId: string | null
    lastChanceHolderId: string | null
    lastChanceExpiresAfterRound: number | null
    penaltyMode: 'blind' | 'self_known' | null
    penaltyChooserId: string | null
    penaltySlots: string[]
    selfPenaltyCandidates: SkullDiscView[]
    nextFirstPlayerDecisionBy: string | null
    eligibleNextFirstPlayerIds: string[]
  }
  actions: string[]
  legalRevealOwnerIds: string[]
  minimumBid: number
  maximumBid: number
  lastPrivatePenalty?: {
    kind: 'flower' | 'skull'
    message: string
  } | null
  history: SkullHistoryEntry[]
  stats: {
    roundsPlayed: number
    activePlayers: number
    eliminatedPlayers: number
    challengeWins: Record<string, number>
  }
  result: {
    winnerIds: string[]
    reason: 'two_challenges' | 'last_player_remaining'
    summary: string
    statsEligible: boolean
  } | null
}
