export type BombStage = 'lobby' | 'countdown' | 'active' | 'collapse' | 'finished'

export interface BombMap {
  key: string
  name: string
  subtitle: string
  pace: string
  density: string
  spawnMode: string
  startingItems: string[]
}

export interface BombEquipment {
  bombCapacity: number
  blastRange: number
  speedLevel: number
  kick: boolean
  punch: boolean
  throw: boolean
  timer: boolean
  chain: boolean
  magnet: boolean
  ice: boolean
  shieldCharges: number
  ghostTicks: number
  invincibleTicks: number
  cursedTicks: number
}

export interface BombPlayer {
  id: string
  name: string
  seat: number
  color: string
  character: number
  x: number
  y: number
  facingX: number
  facingY: number
  moving: boolean
  moveIntervalTicks?: number
  alive: boolean
  eliminatedBy: string | null
  eliminationReason: string | null
  kills: number
  stats: {
    kills: number
    championships: number
    matches: number
    winRate: number
  }
  equipment: BombEquipment
}

export interface BombObject {
  id: number
  ownerId: string
  creditPlayerId: string
  x: number
  y: number
  fuseTicks: number
  maxFuseTicks: number
  moving: boolean
  motionX: number
  motionY: number
}

export interface BombItem {
  id: number
  kind: string
  x: number
  y: number
}

export interface BombFlame {
  x: number
  y: number
  remainingTicks: number
}

export interface BombIceTile {
  x: number
  y: number
  remainingTicks: number
}

export interface BombEvent {
  id: number
  tick: number
  kind: string
  actorId: string | null
  targetId: string | null
  item: string | null
  message: string
}

export type BombEffectKind =
  | 'bomb_placed'
  | 'bomb_exploded'
  | 'bomb_kicked'
  | 'bomb_punched'
  | 'bomb_thrown'

export interface BombEffect {
  id: number
  kind: BombEffectKind
  tick: number
  remainingTicks: number
  actorId: string | null
  bombId: number | null
  x: number
  y: number
  targetX: number | null
  targetY: number | null
  directionX: number
  directionY: number
}

export interface MapProposal {
  mapKey: string
  proposedBy: string
  approvedPlayerIds: string[]
  requiredPlayerIds: string[]
  approvalCount: number
  requiredCount: number
}

export interface BombGame {
  boardSize: number
  tick: number
  tickRate: number
  stage: BombStage
  stageTicksRemaining: number
  roundTicksRemaining: number
  collapsePlaced: number
  collapseTotal: number
  dangerCells: [number, number][]
  selectedMap: string
  mapRotation: 'random_no_repeat'
  currentMap: BombMap
  mapCatalog: BombMap[]
  mapProposal: MapProposal | null
  canProposeMap: boolean
  canVoteMap: boolean
  board: number[][]
  players: BombPlayer[]
  bombs: BombObject[]
  items: BombItem[]
  flames: BombFlame[]
  iceTiles: BombIceTile[]
  events: BombEvent[]
  effects: BombEffect[]
  winnerId: string | null
  clockLeaderId: string | null
  frozen: boolean
  selfInputSequence: number
  controls: Record<string, string>
  itemLabels: Record<string, string>
}
