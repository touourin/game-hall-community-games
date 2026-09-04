export type LoveStage = 'setup' | 'draw' | 'play' | 'choice' | 'resolving' | 'round_summary' | 'finished'

export interface LoveCard {
  id: string
  typeId: string
  value: number
  nameZh: string
  nameEn: string
  symbol: string
  color: string
  motif: string
  effectZh: string
}

export interface CardCatalogItem extends Omit<LoveCard, 'id'> {
  count: number
}

export interface PlayedCardView {
  card: LoveCard
  turnNumber: number
  reason: 'played' | 'prince' | 'guard-hit' | 'eliminated' | 'round-reveal' | string
}

export interface LovePlayerView {
  id: string
  name: string
  seat: number
  favorTokens: number
  favorTarget: number
  roundStatus: 'active' | 'out' | 'forfeited'
  protected: boolean
  handCount: number
  visibleHand: LoveCard[]
  played: PlayedCardView[]
  isCurrent: boolean
}

export interface PendingChoiceView {
  kind: 'guess' | 'target' | 'chancellor'
  sourceTypeId: string
  actorPlayerId: string
  isActor: boolean
  choiceId: string | null
  promptZh: string
  candidatePlayerIds: string[]
  candidateCardTypeIds: string[]
  privateCards: LoveCard[]
}

export interface KnowledgeView {
  subjectPlayerId: string
  card: LoveCard
  source: 'priest' | 'baron'
  acquiredTurn: number
  current: boolean
}

export interface LoveEvent {
  seq: number
  kind: string
  actorPlayerId: string | null
  targetPlayerIds: string[]
  messageZh: string
  data: Record<string, unknown>
}

export interface RevealedHand {
  playerId: string
  card: LoveCard
}

export interface RoundSummary {
  roundNumber: number
  endReason: 'last-player' | 'one-card-left' | 'forfeit'
  roundWinnerIds: string[]
  revealedHands: RevealedHand[]
  spyBonusPlayerId: string | null
  rewardDeltas: Record<string, number>
  deckCountAtEnd: number
  sealedCardCount: number
  sealedCardRevealed: false
  reserveRevealed: false
}

export interface LoveLetterView {
  schemaVersion: 1
  modelVersion: string
  profileId: 'queen_22'
  sceneId: string
  stage: LoveStage
  roundNumber: number
  turnNumber: number
  currentPlayerId: string | null
  startPlayerId: string | null
  deckCount: number
  sealedCardCount: number
  reserveAvailable: boolean
  faceUpSetAside: LoveCard[]
  players: LovePlayerView[]
  cardCatalog: CardCatalogItem[]
  rules: {
    playerMin: 2
    playerMax: 4
    deckSize: 22
    favorTarget: number
    finalCardSealed: true
    roundEndsAtDeckCount: 1
    queenValue: 7.5
  }
  actions: string[]
  legalCardIds: string[]
  pendingChoice: PendingChoiceView | null
  privateInfo: { knownHands: KnowledgeView[] }
  events: LoveEvent[]
  latestEvent: LoveEvent | null
  roundSummary: RoundSummary | null
  gameWinnerIds: string[]
}
