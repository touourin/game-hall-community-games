<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { usePluginGameActions } from '@game-hall/plugin-sdk'
import {
  Anchor,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Coins,
  Compass,
  Crown,
  Dice5,
  LockKeyhole,
  ShieldCheck,
  Skull,
  X,
} from '@lucide/vue'
import type {
  CommodityId,
  DestinationView,
  LaneId,
  ManilaGameView,
  ManilaPlayerView,
  PlacementTarget,
  PuntId,
  PuntView,
  SettlementEntry,
  ShareCardView,
  SpecialPositionView,
  WorkerView,
} from './types'
import './layout.css'
import './models.css'
import './responsive.css'
import './motion.css'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const busy = ref(false)
const localError = ref('')
const showRules = ref(false)
const bidAmount = ref(1)
const selectedCargo = ref<Record<PuntId, CommodityId>>({
  'punt-1': 'ginseng',
  'punt-2': 'nutmeg',
  'punt-3': 'silk',
})
const startPositions = ref<Record<PuntId, number>>({
  'punt-1': 2,
  'punt-2': 3,
  'punt-3': 4,
})
const startLanes = ref<Record<PuntId, LaneId>>({
  'punt-1': 'lane-1',
  'punt-2': 'lane-2',
  'punt-3': 'lane-3',
})
const moveOrder = ref<PuntId[]>([])
const pilotMoves = ref<Array<{ puntId: PuntId, delta: number }>>([])
const motion = ref<{ id: number, kind: string } | null>(null)
let lastAnimationId: number | null = null
let motionTimer: ReturnType<typeof setTimeout> | undefined

const game = computed(() => props.snapshot.game as unknown as ManilaGameView)
const legal = computed(() => game.value.legalActions ?? {})
const selfId = computed(() => props.snapshot.self.id)
const me = computed(() => game.value.players.find(player => player.id === selfId.value))
const currentPlayer = computed(() => playerFor(game.value.currentPlayerId))
const harborMaster = computed(() => playerFor(game.value.harborMasterId))
const startTotal = computed(() => Object.values(startPositions.value).reduce((sum, value) => sum + value, 0))
const cargoValid = computed(() => new Set(Object.values(selectedCargo.value)).size === 3)
const lanesValid = computed(() => new Set(Object.values(startLanes.value)).size === 3 && startTotal.value === 9)
const isMyTurn = computed(() => game.value.currentPlayerId === selfId.value)
const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return props.snapshot.winReason ?? '马尼拉航季结束'
  if (isMyTurn.value) return `轮到你 · ${game.value.stageLabel}`
  return `${game.value.stageLabel} · 等待 ${currentPlayer.value?.name ?? '系统结算'}`
})
const statusDetail = computed(() => {
  const copy: Record<string, string> = {
    auction: '逐次加价；一旦 Pass，本次拍卖不能返回。',
    harbor_share: '港务长可按当前市值（最低 5）购买至多一张份额。',
    harbor_load: '从四种货物选择三种，分别绑定三艘平底船。',
    harbor_launch: '三艘船使用不同航线，起点均为 0–5，合计必须为 9。',
    placement: '助手成本交给银行；Pass 后，本航行不再参与部署。',
    roll: '骰点由服务器生成，每艘仍在航行的船各掷一枚。',
    move_order: '港务长决定移动顺序；多船抵港时依次占据 A/B/C。',
    pirate_board: '基础规则：海盗只能登上恰停 13 且仍有空位的船。',
    pilot_small: '小引航员可将一艘未抵港船前后移动 1 格。',
    pilot_large: '大引航员可移动一艘最多 2 格，或两艘各 1 格。',
    pirate_route: '海盗船长逐艘决定被劫货船进入港口或船坞。',
    voyage_summary: '账目已原子结算，抵港货物的市值上升一格。',
    finished: '现金 + 全部份额市值 − 每张未赎抵押 15。',
  }
  return copy[game.value.stage] ?? '所有位置与账目均由服务器规则状态决定。'
})
const canSubmitPilot = computed(() => {
  const selected = pilotMoves.value
  if (!legal.value.pilot || selected.length === 0) return false
  if (!legal.value.pilot.large) return selected.length === 1 && Math.abs(selected[0].delta) === 1
  if (selected.length === 1) return [1, 2].includes(Math.abs(selected[0].delta))
  return selected.length === 2 && selected.every(move => Math.abs(move.delta) === 1)
})

const commodityIds: CommodityId[] = ['ginseng', 'nutmeg', 'silk', 'jade']
const puntIds: PuntId[] = ['punt-1', 'punt-2', 'punt-3']
const laneIds: LaneId[] = ['lane-1', 'lane-2', 'lane-3']

function playerFor(playerId?: string | null): ManilaPlayerView | undefined {
  return game.value.players.find(player => player.id === playerId)
}

function marketFor(commodityId?: CommodityId | null) {
  return game.value.market.find(item => item.id === commodityId)
}

function puntFor(puntId?: PuntId | null): PuntView | undefined {
  return game.value.punts.find(punt => punt.id === puntId)
}

function puntForLane(laneId: LaneId): PuntView | undefined {
  return game.value.punts.find(punt => punt.laneId === laneId)
}

function specialFor(specialId: string): SpecialPositionView | undefined {
  return game.value.specialPositions.find(item => item.id === specialId)
}

function destinationPunt(slot: DestinationView): PuntView | undefined {
  return puntFor(slot.puntId)
}

function legalTarget(targetId: string): PlacementTarget | undefined {
  return legal.value.placementTargets?.find(target => target.targetId === targetId)
}

function workerStyle(worker?: WorkerView | null) {
  return worker ? { '--worker-color': worker.color, '--worker-ink': worker.ink } : {}
}

function playerStyle(player: ManilaPlayerView) {
  return { '--player-color': player.color, '--player-ink': player.ink }
}

function puntStyle(punt: PuntView) {
  const position = Math.max(0, Math.min(13, punt.position))
  return {
    '--punt-position': `${10 + position / 13 * 80}%`,
    '--cargo-color': punt.cargo?.color ?? '#6f8583',
  }
}

function shareStyle(card: ShareCardView) {
  return { '--share-color': card.color }
}

function scheduleLabel(token: string, index: number): string {
  if (token === 'placement') return `部署 ${game.value.schedule.slice(0, index + 1).filter(item => item.token === 'placement').length}`
  if (token === 'movement') return `航行 ${game.value.schedule.slice(0, index + 1).filter(item => item.token === 'movement').length}`
  return '引航'
}

function cargoGlyph(commodityId?: CommodityId | null): string {
  return { ginseng: '参', nutmeg: '籽', silk: '绸', jade: '玉' }[commodityId ?? 'ginseng']
}

function destinationLabel(destination: string): string {
  return destination === 'port' ? '港口' : '船坞'
}

function settlementReason(reason: string): string {
  return {
    cargo_profit: '货船分成',
    pirate_profit: '海盗劫掠',
    port_bet: '港口收益',
    shipyard_bet: '船坞修理',
    shipyard_unclaimed: '无人认领修理',
    insured_repair: '保险修理',
    self_insurance: '保险自付自收',
    forced_mortgage: '强制抵押',
  }[reason] ?? reason
}

function partyName(id: string): string {
  if (id === 'bank') return '港口银行'
  return playerFor(id)?.name ?? id
}

function entryText(entry: SettlementEntry): string {
  if (entry.selfInsurance) return `${partyName(entry.toId)} 自付自收 ${entry.amount}`
  if (entry.reason === 'forced_mortgage') return `${partyName(entry.toId)} 抵押 +${entry.amount}`
  const coverage = entry.bankCoverage ? `（银行补 ${entry.bankCoverage}）` : ''
  return `${partyName(entry.fromId)} → ${partyName(entry.toId)} · ${entry.amount}${coverage}`
}

function isLegalPlacement(targetId: string): boolean {
  return Boolean(legalTarget(targetId)) && isMyTurn.value && !busy.value
}

async function send(action: string, payload: Record<string, unknown> = {}) {
  if (busy.value) return
  busy.value = true
  localError.value = ''
  try {
    await actions.action(action, { voyageNumber: game.value.voyageNumber, ...payload })
  }
  catch (error) {
    localError.value = error instanceof Error ? error.message : '操作未成功，请根据最新桌面重试。'
  }
  finally {
    busy.value = false
  }
}

function submitBid() {
  const minimum = legal.value.minimumBid ?? 1
  const maximum = legal.value.maximumBid ?? minimum
  bidAmount.value = Math.max(minimum, Math.min(maximum, Math.floor(bidAmount.value)))
  void send('bid', { amount: bidAmount.value })
}

function submitCargo() {
  if (!cargoValid.value) return
  void send('select_cargo', {
    assignments: puntIds.map(puntId => ({ puntId, commodityId: selectedCargo.value[puntId] })),
  })
}

function submitStarts() {
  if (!lanesValid.value) return
  void send('set_start_positions', {
    assignments: puntIds.map(puntId => ({
      puntId,
      laneId: startLanes.value[puntId],
      position: startPositions.value[puntId],
    })),
  })
}

function moveOrderItem(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= moveOrder.value.length) return
  const next = [...moveOrder.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  moveOrder.value = next
}

function togglePilotMove(puntId: PuntId, delta: number) {
  const large = legal.value.pilot?.large ?? false
  const existing = pilotMoves.value.findIndex(move => move.puntId === puntId)
  if (existing >= 0) {
    const next = [...pilotMoves.value]
    if (next[existing].delta === delta) next.splice(existing, 1)
    else next[existing] = { puntId, delta }
    pilotMoves.value = next
    return
  }
  if (!large || Math.abs(delta) === 2) {
    pilotMoves.value = [{ puntId, delta }]
    return
  }
  const oneStep = pilotMoves.value.filter(move => Math.abs(move.delta) === 1)
  pilotMoves.value = [...oneStep.slice(-1), { puntId, delta }]
}

function selectedPilotDelta(puntId: PuntId): number | null {
  return pilotMoves.value.find(move => move.puntId === puntId)?.delta ?? null
}

watch(
  () => legal.value.minimumBid,
  minimum => {
    if (minimum !== undefined) bidAmount.value = minimum
  },
  { immediate: true },
)

watch(
  () => legal.value.moveOrderPuntIds?.join('|') ?? '',
  () => { moveOrder.value = [...(legal.value.moveOrderPuntIds ?? [])] },
  { immediate: true },
)

watch(
  () => `${game.value.voyageNumber}:${game.value.stage}`,
  () => {
    pilotMoves.value = []
    localError.value = ''
    if (game.value.stage === 'harbor_load') {
      selectedCargo.value = {
        'punt-1': commodityIds[0],
        'punt-2': commodityIds[1],
        'punt-3': commodityIds[2],
      }
    }
  },
)

watch(
  () => game.value.animation?.id ?? 0,
  animationId => {
    if (lastAnimationId === null) {
      lastAnimationId = animationId
      return
    }
    if (!animationId || animationId === lastAnimationId) return
    lastAnimationId = animationId
    if (motionTimer) clearTimeout(motionTimer)
    motion.value = {
      id: animationId,
      kind: game.value.animation?.kind ?? 'event',
    }
    motionTimer = setTimeout(() => { motion.value = null }, 1250)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (motionTimer) clearTimeout(motionTimer)
})
</script>

<template>
  <main class="manila-table" :class="[`stage-${game.stage}`, motion ? `motion-${motion.kind}` : '']">
    <div class="ambient-water" aria-hidden="true"><i /><i /><i /></div>
    <div v-if="motion" :key="motion.id" class="motion-layer" :class="`cue-${motion.kind}`" aria-hidden="true">
      <div v-if="motion.kind === 'dice_roll'" class="motion-dice"><b>⚄</b><b>⚂</b><b>⚅</b></div>
      <div v-else-if="motion.kind === 'punt_move' || motion.kind === 'launch'" class="motion-punt"><i /><strong>MANILA</strong></div>
      <div v-else-if="motion.kind === 'worker_move'" class="motion-worker"><i /></div>
      <div v-else-if="motion.kind === 'pirate_board' || motion.kind === 'pirate_plunder'" class="motion-pirate"><Skull :size="34" /></div>
      <div v-else-if="motion.kind === 'pilot_move'" class="motion-compass"><Compass :size="42" /></div>
      <div v-else-if="motion.kind === 'share_deal' || motion.kind === 'mortgage' || motion.kind === 'redeem'" class="motion-share"><span>份额</span></div>
      <div v-else-if="motion.kind === 'settlement'" class="motion-coins"><i>₱</i><i>₱</i><i>₱</i></div>
      <div v-else class="motion-seal"><Anchor :size="38" /></div>
    </div>

    <header class="table-masthead">
      <div class="brand-lockup">
        <span class="eyebrow">GAME HALL · MANILA HARBOR</span>
        <div><Anchor :size="21" /><h1>马尼拉</h1><small>基础常规规则</small></div>
      </div>
      <div class="status-copy" role="status" aria-live="polite">
        <strong>{{ statusTitle }}</strong>
        <span>{{ statusDetail }}</span>
      </div>
      <div class="mast-actions">
        <span class="voyage-stamp">第 {{ game.voyageNumber }} 次航行</span>
        <button class="icon-button" type="button" aria-label="打开规则摘要" @click="showRules = true">
          <BookOpen :size="19" />
        </button>
      </div>
    </header>

    <section class="player-rail" aria-label="玩家财务轨">
      <article
        v-for="player in game.players"
        :key="player.id"
        class="player-ledger"
        :class="{ current: player.isCurrent, master: player.isHarborMaster, forfeited: player.forfeited }"
        :style="playerStyle(player)"
      >
        <span class="player-color" aria-hidden="true" />
        <div class="player-name">
          <strong>{{ player.name }}</strong>
          <span v-if="player.isHarborMaster"><Crown :size="13" /> 港务长</span>
          <span v-else-if="player.isCurrent">当前行动</span>
          <span v-else-if="player.forfeited">已退出</span>
          <span v-else>席位 {{ player.seat + 1 }}</span>
        </div>
        <div class="player-metrics">
          <span><Coins :size="13" /> {{ player.cash }}</span>
          <span><LockKeyhole :size="12" /> {{ player.shareCount }} / 抵 {{ player.mortgagedShareCount }}</span>
          <span class="worker-pips" :aria-label="`剩余助手 ${player.availableWorkerCount}`">
            <i v-for="index in player.workerCount" :key="index" :class="{ spent: index > player.availableWorkerCount }" />
          </span>
        </div>
        <b v-if="player.rank" class="rank-badge">#{{ player.rank }}</b>
      </article>
    </section>

    <nav v-if="game.schedule.length" class="voyage-schedule" aria-label="航行阶段进度">
      <span
        v-for="item in game.schedule"
        :key="item.index"
        :class="item.state"
      >{{ scheduleLabel(item.token, item.index) }}</span>
    </nav>

    <section class="scene-grid">
      <aside class="market-board board-panel" aria-label="黑市价值与份额供应">
        <header class="panel-heading">
          <div><span>BLACK MARKET</span><h2>黑市与份额</h2></div>
          <small>0 → 5 → 10 → 20 → 30</small>
        </header>
        <div class="market-list">
          <article
            v-for="commodity in game.market"
            :key="commodity.id"
            class="market-row"
            :class="[`commodity-${commodity.id}`, { terminal: commodity.value === 30 }]"
            :style="{ '--commodity-color': commodity.color }"
          >
            <div class="commodity-mark">
              <span>{{ cargoGlyph(commodity.id) }}</span>
              <div><b>{{ commodity.label }}</b><small>{{ commodity.code }} · {{ commodity.labelEn }}</small></div>
            </div>
            <div class="value-track" :aria-label="`${commodity.label}当前价值 ${commodity.value}`">
              <i
                v-for="value in game.marketTrack"
                :key="value"
                :class="{ reached: game.marketTrack.indexOf(value) <= commodity.trackIndex, current: value === commodity.value }"
              ><em>{{ value }}</em></i>
            </div>
            <div class="share-supply">
              <div class="mini-share-stack" aria-hidden="true"><i /><i /><i /></div>
              <span>供应 {{ commodity.supplyCount }}</span>
              <b>购入 {{ Math.max(5, commodity.value) }}</b>
            </div>
          </article>
        </div>
        <footer class="market-note">
          <ShieldCheck :size="15" />
          <span>份额种类仅持有者可见；现金、总数和抵押数公开。</span>
        </footer>
      </aside>

      <section class="route-board board-panel" aria-label="三条货船航线">
        <header class="panel-heading route-heading">
          <div><span>THE PASIG RUN</span><h2>三条航线 · 0—13</h2></div>
          <div class="hazard-key"><Skull :size="15" /> 恰停 13 检查海盗</div>
        </header>
        <div class="lanes-scroll">
          <div class="lanes-canvas">
            <article v-for="lane in game.lanes" :key="lane.id" class="shipping-lane">
              <div class="lane-label">
                <small>航线 {{ lane.number }}</small>
                <strong v-if="puntForLane(lane.id)?.cargo">{{ puntForLane(lane.id)?.cargo?.label }} · {{ puntForLane(lane.id)?.cargo?.code }}</strong>
                <strong v-else>等待港务长配置</strong>
              </div>
              <div class="track-wrap">
                <div class="route-line" />
                <div class="track-ticks">
                  <span v-for="mark in lane.marks" :key="mark" :class="{ hazard: mark === 13 }">
                    <i /><b>{{ mark }}</b><Skull v-if="mark === 13" :size="12" />
                  </span>
                </div>
                <div
                  v-if="puntForLane(lane.id) && puntForLane(lane.id)?.status === 'sailing'"
                  class="punt-model"
                  :class="{ selectable: legal.pirateBoardPuntIds?.includes(puntForLane(lane.id)!.id), plundered: puntForLane(lane.id)?.plundered }"
                  :style="puntStyle(puntForLane(lane.id)!)"
                  :aria-label="`${puntForLane(lane.id)?.cargo?.label}货船，位置 ${puntForLane(lane.id)?.position}，助手 ${puntForLane(lane.id)?.occupants.length}`"
                >
                  <button
                    v-if="legal.pirateBoardPuntIds?.includes(puntForLane(lane.id)!.id)"
                    class="punt-hit-area"
                    type="button"
                    :aria-label="`海盗登上${puntForLane(lane.id)?.cargo?.label}货船`"
                    :disabled="busy"
                    @click="send('pirate_board', { puntId: puntForLane(lane.id)!.id })"
                  />
                  <div class="punt-flag">{{ puntForLane(lane.id)?.cargo?.code }}</div>
                  <div class="punt-deck">
                    <span
                      v-for="slot in puntForLane(lane.id)?.cargoSlots"
                      :key="slot.index"
                      class="cargo-seat"
                      :class="{ occupied: slot.occupant }"
                    >
                      <i v-if="slot.occupant" class="worker-token" :style="workerStyle(slot.occupant)"><em /></i>
                      <b v-else>{{ slot.cost }}</b>
                    </span>
                  </div>
                  <div class="punt-hull"><i /><strong>{{ cargoGlyph(puntForLane(lane.id)?.cargoId) }}</strong></div>
                  <div v-if="puntForLane(lane.id)?.lastDie" class="punt-die">{{ puntForLane(lane.id)?.lastDie }}</div>
                  <button
                    v-if="isLegalPlacement(puntForLane(lane.id)!.id)"
                    class="place-on-punt"
                    type="button"
                    :aria-label="`部署到${puntForLane(lane.id)?.cargo?.label}货船，成本 ${legalTarget(puntForLane(lane.id)!.id)?.payable}`"
                    @click="send('place_accomplice', { targetId: puntForLane(lane.id)!.id })"
                  >+ {{ legalTarget(puntForLane(lane.id)!.id)?.payable }}</button>
                </div>
              </div>
            </article>
          </div>
        </div>

        <section class="special-islands" aria-label="特殊行动岛">
          <button
            v-for="special in game.specialPositions"
            :key="special.id"
            class="special-position"
            :class="[`special-${special.kind}`, special.id, { legal: isLegalPlacement(special.id), occupied: special.occupant }]"
            type="button"
            :disabled="!isLegalPlacement(special.id)"
            @click="send('place_accomplice', { targetId: special.id })"
          >
            <span class="special-icon">
              <Skull v-if="special.kind === 'pirate'" :size="19" />
              <Compass v-else-if="special.kind === 'pilot'" :size="19" />
              <ShieldCheck v-else :size="19" />
            </span>
            <span><b>{{ special.label }}</b><small>成本 {{ special.cost }}</small></span>
            <i v-if="special.occupant" class="worker-token" :style="workerStyle(special.occupant)"><em /></i>
            <em v-else-if="special.id === 'pilot-small'">±1</em>
            <em v-else-if="special.id === 'pilot-large'">Σ2</em>
            <em v-else-if="special.id === 'insurance'">+10</em>
          </button>
        </section>
      </section>

      <aside class="destination-board board-panel" aria-label="港口与船坞">
        <header class="panel-heading">
          <div><span>HARBOR LEDGER</span><h2>目的地区</h2></div>
          <small>投注层 / 船只层</small>
        </header>
        <section class="destination-group port-group">
          <h3><Anchor :size="16" /> 港口 <small>抵港收益</small></h3>
          <button
            v-for="slot in game.destinations.port"
            :key="slot.id"
            class="destination-slot"
            :class="{ legal: isLegalPlacement(slot.id), landed: slot.puntId }"
            type="button"
            :disabled="!isLegalPlacement(slot.id)"
            @click="send('place_accomplice', { targetId: slot.id })"
          >
            <span class="slot-letter">{{ slot.slot }}</span>
            <span class="slot-economy"><b>投 {{ slot.cost }}</b><strong>得 {{ slot.payout }}</strong></span>
            <i v-if="slot.bettor" class="worker-token bettor-token" :style="workerStyle(slot.bettor)"><em /></i>
            <span v-else class="empty-bet">助手位</span>
            <span v-if="destinationPunt(slot)" class="docked-punt" :style="{ '--cargo-color': destinationPunt(slot)?.cargo?.color }">
              <i /><b>{{ destinationPunt(slot)?.cargo?.code }}</b>
            </span>
          </button>
        </section>
        <section class="destination-group yard-group">
          <h3><span class="yard-glyph">⌂</span> 船坞 <small>保险修理责任</small></h3>
          <button
            v-for="slot in game.destinations.shipyard"
            :key="slot.id"
            class="destination-slot"
            :class="{ legal: isLegalPlacement(slot.id), landed: slot.puntId }"
            type="button"
            :disabled="!isLegalPlacement(slot.id)"
            @click="send('place_accomplice', { targetId: slot.id })"
          >
            <span class="slot-letter">{{ slot.slot }}</span>
            <span class="slot-economy"><b>投 {{ slot.cost }}</b><strong>得 {{ slot.payout }}</strong></span>
            <i v-if="slot.bettor" class="worker-token bettor-token" :style="workerStyle(slot.bettor)"><em /></i>
            <span v-else class="empty-bet">助手位</span>
            <span v-if="destinationPunt(slot)" class="docked-punt damaged" :style="{ '--cargo-color': destinationPunt(slot)?.cargo?.color }">
              <i /><b>{{ destinationPunt(slot)?.cargo?.code }}</b>
            </span>
          </button>
        </section>
        <div class="liability-card">
          <ShieldCheck :size="18" />
          <span><b>保险责任上限 29</b><small>A 6 + B 8 + C 15；无人投注也须向银行支付</small></span>
        </div>
      </aside>
    </section>

    <section class="private-console" aria-label="本人私密区与当前行动">
      <section class="private-hand">
        <header>
          <div><LockKeyhole :size="15" /><b>我的份额</b><small>仅你可见</small></div>
          <span><Coins :size="14" /> 现金 {{ game.own?.cash ?? 0 }}</span>
        </header>
        <div class="share-hand">
          <article
            v-for="card in game.own?.shareCards ?? []"
            :key="card.id"
            class="share-card"
            :class="[`share-${card.commodityId}`, { mortgaged: card.mortgaged }]"
            :style="shareStyle(card)"
            :aria-label="`${card.label}份额，当前价值 ${card.marketValue}${card.mortgaged ? '，已抵押' : ''}`"
          >
            <div class="share-face">
              <header><b>{{ card.code }}</b><small>货物份额</small></header>
              <svg v-if="card.commodityId === 'ginseng'" viewBox="0 0 64 52" aria-hidden="true"><path d="M32 5C19 14 22 29 12 41M32 5c13 9 10 24 22 36M32 16v29" /></svg>
              <svg v-else-if="card.commodityId === 'nutmeg'" viewBox="0 0 64 52" aria-hidden="true"><circle cx="20" cy="21" r="9"/><circle cx="39" cy="16" r="10"/><circle cx="45" cy="36" r="8"/><circle cx="23" cy="38" r="9"/></svg>
              <svg v-else-if="card.commodityId === 'silk'" viewBox="0 0 64 52" aria-hidden="true"><path d="M6 13c14-10 36 10 52 0M6 26c14-10 36 10 52 0M6 39c14-10 36 10 52 0" /></svg>
              <svg v-else viewBox="0 0 64 52" aria-hidden="true"><path d="m32 4 24 15-8 28H16L8 19Z M8 19l40 28M56 19 16 47M32 4v43" /></svg>
              <strong>{{ card.label }}</strong><small>{{ card.labelEn }}</small>
              <footer><span>市值</span><b>{{ card.marketValue }}</b></footer>
            </div>
            <div v-if="card.mortgaged" class="mortgage-band"><b>已抵押 12</b><span>赎回 15</span></div>
            <button
              v-if="legal.loanableShareIds?.includes(card.id)"
              type="button"
              :disabled="busy"
              @click="send('take_loan', { shareId: card.id })"
            >抵押 +12</button>
            <button
              v-else-if="legal.repayableShareIds?.includes(card.id)"
              type="button"
              :disabled="busy"
              @click="send('repay_loan', { shareId: card.id })"
            >赎回 −15</button>
          </article>
          <div v-if="!(game.own?.shareCards.length)" class="empty-hand">暂无份额</div>
        </div>
      </section>

      <section class="action-console" :class="{ active: isMyTurn, error: localError }">
        <header class="action-heading">
          <span>{{ game.sceneId }}</span>
          <div><strong>{{ game.stageLabel }}</strong><small>{{ isMyTurn ? '请完成当前决策' : `等待 ${currentPlayer?.name ?? '系统'}` }}</small></div>
          <span v-if="busy" class="busy-indicator">同步中</span>
        </header>
        <p v-if="localError" class="local-error" role="alert">{{ localError }}</p>

        <div v-if="game.stage === 'auction'" class="action-body auction-action">
          <div class="auction-meter">
            <small>当前报价</small><strong>{{ game.auction?.currentBid ?? 0 }}</strong>
            <span>领跑：{{ playerFor(game.auction?.leaderId)?.name ?? '尚无人报价' }}</span>
          </div>
          <template v-if="legal.canPassAuction">
            <label>你的报价<input v-model.number="bidAmount" type="number" :min="legal.minimumBid" :max="legal.maximumBid" /></label>
            <button class="primary-action" type="button" :disabled="!legal.canBid || busy" @click="submitBid">报价 {{ bidAmount }}</button>
            <button class="secondary-action" type="button" :disabled="busy" @click="send('pass_auction')">Pass</button>
          </template>
          <p v-else>仍在竞价：{{ game.auction?.activePlayerIds.map(id => playerFor(id)?.name).join('、') }}</p>
        </div>

        <div v-else-if="game.stage === 'harbor_share'" class="action-body share-action">
          <template v-if="legal.shareOptions">
            <button
              v-for="option in legal.shareOptions"
              :key="option.commodityId"
              type="button"
              class="commodity-buy"
              :style="{ '--commodity-color': marketFor(option.commodityId)?.color }"
              :disabled="!option.affordable || busy"
              @click="send('buy_share', { commodityId: option.commodityId })"
            ><b>{{ marketFor(option.commodityId)?.label }}</b><span>{{ option.price }} 比索 · 余 {{ option.remaining }}</span></button>
            <button class="secondary-action" type="button" :disabled="busy" @click="send('skip_share')">跳过购买</button>
          </template>
          <p v-else>港务长 {{ harborMaster?.name }} 正在决定是否购入份额。</p>
        </div>

        <div v-else-if="game.stage === 'harbor_load'" class="action-body setup-action">
          <template v-if="legal.canSelectCargo">
            <label v-for="puntId in puntIds" :key="puntId">船 {{ puntId.slice(-1) }}
              <select v-model="selectedCargo[puntId]">
                <option v-for="commodity in game.market" :key="commodity.id" :value="commodity.id">{{ commodity.label }} · 收益 {{ commodity.profit }}</option>
              </select>
            </label>
            <button class="primary-action" type="button" :disabled="!cargoValid || busy" @click="submitCargo">确认装船</button>
          </template>
          <p v-else>港务长正在从四种货物中选择三种。</p>
        </div>

        <div v-else-if="game.stage === 'harbor_launch'" class="action-body launch-action">
          <template v-if="legal.canSetStartPositions">
            <label v-for="puntId in puntIds" :key="puntId">船 {{ puntId.slice(-1) }}
              <select v-model="startLanes[puntId]"><option v-for="laneId in laneIds" :key="laneId" :value="laneId">航线 {{ laneId.slice(-1) }}</option></select>
              <input v-model.number="startPositions[puntId]" type="number" min="0" max="5" />
            </label>
            <span class="start-total" :class="{ valid: lanesValid }">起点合计 <b>{{ startTotal }}</b> / 9</span>
            <button class="primary-action" type="button" :disabled="!lanesValid || busy" @click="submitStarts">确认起航</button>
          </template>
          <p v-else>港务长正在配置三条航线和起点。</p>
        </div>

        <div v-else-if="game.stage === 'placement'" class="action-body placement-action">
          <template v-if="legal.placementTargets">
            <div class="target-strip">
              <button
                v-for="target in legal.placementTargets"
                :key="target.targetId"
                type="button"
                :class="{ blind: target.blindAllowed }"
                :disabled="busy"
                @click="send('place_accomplice', { targetId: target.targetId })"
              ><b>{{ target.label }}</b><span>{{ target.blindAllowed ? `免票 · 交 ${target.payable}` : `成本 ${target.cost}` }}</span></button>
            </div>
            <button class="secondary-action" type="button" :disabled="busy" @click="send('pass_placement')">Pass 本航行部署</button>
          </template>
          <p v-else>{{ currentPlayer?.name }} 正在选择助手位置。可用位置在版图上以金色描边标出。</p>
        </div>

        <div v-else-if="game.stage === 'roll'" class="action-body roll-action">
          <Dice5 :size="34" />
          <div><b>第 {{ game.movementRound }} 轮航行</b><span>服务器将为每艘未抵港船生成 1–6。</span></div>
          <button v-if="legal.canRollDice" class="primary-action" type="button" :disabled="busy" @click="send('roll_dice')">掷航行骰</button>
        </div>

        <div v-else-if="game.stage === 'move_order'" class="action-body move-order-action">
          <template v-if="legal.moveOrderPuntIds">
            <div class="order-list">
              <article v-for="(puntId, index) in moveOrder" :key="puntId">
                <b>{{ index + 1 }}</b><span>{{ puntFor(puntId)?.cargo?.label }} · 骰 {{ game.dice[puntId] }}</span>
                <button type="button" :disabled="index === 0" aria-label="上移" @click="moveOrderItem(index, -1)"><ChevronUp :size="16" /></button>
                <button type="button" :disabled="index === moveOrder.length - 1" aria-label="下移" @click="moveOrderItem(index, 1)"><ChevronDown :size="16" /></button>
              </article>
            </div>
            <button class="primary-action" type="button" :disabled="busy" @click="send('choose_move_order', { puntIds: moveOrder })">按此顺序移动</button>
          </template>
          <p v-else>港务长正在确定三艘船的处理顺序。</p>
        </div>

        <div v-else-if="game.stage === 'pirate_board'" class="action-body pirate-action">
          <Skull :size="32" />
          <template v-if="legal.canPirateStay">
            <div><b>海盗船长先行</b><span>可登上有空位的 13 格货船，或留守等待第三轮劫掠。</span></div>
            <button v-for="puntId in legal.pirateBoardPuntIds" :key="puntId" class="primary-action" type="button" :disabled="busy" @click="send('pirate_board', { puntId })">登上{{ puntFor(puntId)?.cargo?.label }}船</button>
            <button class="secondary-action" type="button" :disabled="busy" @click="send('pirate_stay')">留守海盗船</button>
          </template>
          <p v-else>当前海盗正在决定是否登船。</p>
        </div>

        <div v-else-if="game.stage === 'pilot_small' || game.stage === 'pilot_large'" class="action-body pilot-action">
          <Compass :size="32" />
          <template v-if="legal.pilot">
            <div class="pilot-options">
              <article v-for="puntId in legal.pilot.puntIds" :key="puntId" :class="{ selected: selectedPilotDelta(puntId) !== null }">
                <b>{{ puntFor(puntId)?.cargo?.label }} · {{ puntFor(puntId)?.position }}</b>
                <span>
                  <button v-for="delta in legal.pilot.large ? [-2, -1, 1, 2] : [-1, 1]" :key="delta" type="button" :class="{ selected: selectedPilotDelta(puntId) === delta }" :disabled="(puntFor(puntId)?.position ?? 0) + delta < 0" @click="togglePilotMove(puntId, delta)">{{ delta > 0 ? `+${delta}` : delta }}</button>
                </span>
              </article>
            </div>
            <button class="primary-action" type="button" :disabled="!canSubmitPilot || busy" @click="send('pilot_move', { moves: pilotMoves })">执行引航</button>
            <button class="secondary-action" type="button" :disabled="busy" @click="send('pilot_pass')">放弃引航</button>
          </template>
          <p v-else>对应引航员正在调整航线。</p>
        </div>

        <div v-else-if="game.stage === 'pirate_route'" class="action-body route-action">
          <Skull :size="31" />
          <template v-if="legal.pirateRoute">
            <div><b>{{ puntFor(legal.pirateRoute.puntId)?.cargo?.label }}船已被劫</b><span>货物收益归留守海盗；目的地区投注仍照常结算。</span></div>
            <button v-for="destination in legal.pirateRoute.destinations" :key="destination" class="primary-action" type="button" :disabled="busy" @click="send('route_plundered_punt', { puntId: legal.pirateRoute?.puntId, destination })">送往{{ destinationLabel(destination) }}</button>
          </template>
          <p v-else>海盗船长正在选择被劫货船去向。</p>
        </div>

        <div v-else-if="game.stage === 'voyage_summary'" class="action-body settlement-action">
          <div class="settlement-head">
            <b>第 {{ game.settlement?.voyageNumber }} 次航行账目</b>
            <span>抵港 {{ game.settlement?.deliveredCommodityIds.map(id => marketFor(id)?.label).join('、') || '无' }}</span>
          </div>
          <div class="settlement-entries">
            <article v-for="entry in game.settlement?.entries ?? []" :key="entry.entryId">
              <b>{{ settlementReason(entry.reason) }}</b><span>{{ entryText(entry) }}</span>
            </article>
            <p v-if="!game.settlement?.entries.length">本航行没有玩家收支。</p>
          </div>
          <button v-if="legal.canStartNextVoyage" class="primary-action" type="button" :disabled="busy" @click="send('next_voyage')">开始下一航行</button>
        </div>

        <div v-else-if="game.stage === 'finished'" class="action-body result-action">
          <Crown :size="34" />
          <div class="ranking-list">
            <article v-for="playerId in game.rankings" :key="playerId" :class="{ winner: game.winnerPlayerIds.includes(playerId) }">
              <b>#{{ playerFor(playerId)?.rank ?? '—' }} {{ playerFor(playerId)?.name }}</b>
              <span>最终财富 {{ playerFor(playerId)?.finalWealth ?? 0 }}</span>
            </article>
          </div>
          <p>财富 = 现金 + 全部份额市值 − 未赎抵押 × 15</p>
        </div>

        <div v-else class="action-body waiting-action"><span class="harbor-loader" /><p>{{ statusDetail }}</p></div>
      </section>
    </section>

    <div v-if="showRules" class="rules-overlay" role="dialog" aria-modal="true" aria-labelledby="rules-title">
      <section class="rules-sheet">
        <header><div><span>2005 BASE RULES</span><h2 id="rules-title">马尼拉 · 常规规则速查</h2></div><button type="button" aria-label="关闭规则" @click="showRules = false"><X :size="22" /></button></header>
        <div class="rules-grid">
          <article><b>1 · 港务长</b><p>严格加价或 Pass。赢家支付报价，可抵押份额补款；随后可买一张份额，三选四装船，并配置起点总和 9。</p></article>
          <article><b>2 · 助手部署</b><p>货船依次取最低成本位；港口/船坞 A/B/C 为 4/3/2，收益 6/8/15。部署 Pass 后本航行不能返回。</p></article>
          <article><b>3 · 航行</b><p>每轮每艘未抵港船掷 d6，港务长决定处理顺序。超过 13 立即抵港；恰停 13 留在航线上等待检查。</p></article>
          <article><b>4 · 海盗与引航</b><p>第二轮海盗可登有空位的 13 格船。第三轮前小引航 ±1、大引航总量 2。第三轮 13 格船由留守海盗劫掠。</p></article>
          <article><b>5 · 保险</b><p>保险位免费且立即 +10。保险代理承担每艘入坞船对应 6/8/15；先收本航行收益，再强制抵押，最后由银行补缺口。</p></article>
          <article><b>6 · 终局</b><p>抵港货物市值上升。任一货物达到 30 后终局：现金 + 所有份额市值 − 每张未赎抵押 15；最高者获胜，同分共胜。</p></article>
        </div>
        <footer class="rules-footer"><ShieldCheck :size="16" /><span>本实现使用基础常规海盗规则，不启用满船逐客增强变体。</span></footer>
      </section>
    </div>
  </main>
</template>
