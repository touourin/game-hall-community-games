<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { BookOpen, History, Maximize2, Minimize2, Trophy } from '@lucide/vue'
import {
  PluginButton, PluginIconButton, PluginModal, usePluginFullscreen, usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import EuropeMap from './components/EuropeMap.vue'
import TrainCard from './components/TrainCard.vue'
import DestinationTicket from './components/DestinationTicket.vue'
import EffectOverlay from './components/EffectOverlay.vue'
import boardSource from '../model/board-map.json'
import type {
  BoardModel, DestinationTicketModel, EuropeGameView, EuropePlayerView, RouteModel,
  TrainCardModel, TrainColor,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported: fullscreenSupported, toggle: toggleFullscreen } = usePluginFullscreen(gameRoot)
const board = boardSource as unknown as BoardModel
const routeById = new Map(board.routes.map(route => [route.id, route]))
const cityById = new Map(board.cities.map(city => [city.id, city]))

const game = computed(() => props.snapshot.game as unknown as EuropeGameView)
const selfId = computed(() => props.snapshot.self.id)
const spectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const me = computed(() => game.value.players?.find(player => player.id === selfId.value))
const currentPlayer = computed(() => game.value.players?.find(player => player.id === game.value.currentPlayerId))
const finished = computed(() => props.snapshot.phase === 'finished' || game.value.phase === 'finished')
const canInteract = computed(() => !spectator.value && !finished.value && Boolean(props.snapshot.actions.canAct))
const available = computed(() => new Set(game.value.actions ?? []))
const holdEffects = computed(() => Boolean((props.snapshot.options as Record<string, unknown> | undefined)?.qaHoldAnimations))

const showRules = ref(false)
const showHistory = ref(false)
const mode = ref<'route' | 'station' | null>(null)
const selectedRouteId = ref<string | null>(null)
const selectedCityId = ref<string | null>(null)
const selectedCardIds = ref<string[]>([])
const selectedTicketIds = ref<string[]>([])
const declaredColor = ref<Exclude<TrainColor, 'gray'> | null>(null)
const pending = ref(false)
const error = ref('')
const stationAssignments = reactive<Record<string, string>>({})

const selectedRoute = computed(() => selectedRouteId.value ? routeById.get(selectedRouteId.value) ?? null : null)
const ownStations = computed(() => (game.value.stationPlacements ?? []).filter(station => station.ownerPlayerId === selfId.value))
const stationCost = computed(() => 4 - (me.value?.stationsRemaining ?? 3))
const focusedTickets = computed(() => game.value.destinationTickets ?? [])
const ticketOffer = computed<DestinationTicketModel[]>(() => game.value.phase === 'setup_ticket_selection'
  ? game.value.initialTicketOptions ?? []
  : game.value.pendingTicketChoice?.offeredTickets ?? [])
const ticketMinimum = computed(() => game.value.phase === 'setup_ticket_selection'
  ? 2
  : game.value.pendingTicketChoice?.minKeep ?? 1)
const tunnelAllowedCards = computed(() => {
  const tunnel = game.value.ownTunnelPayment
  if (!tunnel) return []
  return (game.value.hand ?? []).filter(card => tunnel.paymentMode === 'locomotive-only'
    ? card.color === 'locomotive'
    : card.color === 'locomotive' || card.color === tunnel.declaredColor)
})
const selectedCards = computed(() => (game.value.hand ?? []).filter(card => selectedCardIds.value.includes(card.id)))
const routeColor = computed(() => {
  const route = selectedRoute.value
  if (!route) return null
  if (route.color !== 'gray') return route.color as Exclude<TrainColor, 'gray'>
  return selectedCards.value.find(card => card.color !== 'locomotive')?.color ?? declaredColor.value
})
const routePaymentReady = computed(() => {
  const route = selectedRoute.value
  const color = routeColor.value
  if (!route || !color || selectedCards.value.length !== route.length) return false
  if (selectedCards.value.some(card => card.color !== 'locomotive' && card.color !== color)) return false
  return route.kind !== 'ferry'
    || selectedCards.value.filter(card => card.color === 'locomotive').length >= route.locomotivesRequired
})
const stationPaymentReady = computed(() => {
  if (!selectedCityId.value || selectedCards.value.length !== stationCost.value) return false
  return new Set(selectedCards.value.filter(card => card.color !== 'locomotive').map(card => card.color)).size <= 1
})
const tunnelPaymentReady = computed(() => {
  const tunnel = game.value.ownTunnelPayment
  if (!tunnel || selectedCards.value.length !== tunnel.extraCost) return false
  const allowed = new Set(tunnelAllowedCards.value.map(card => card.id))
  return selectedCardIds.value.every(id => allowed.has(id))
})
const phaseLabel = computed(() => {
  if (finished.value) return '终局结算完成'
  if (spectator.value) return `观战 · ${currentPlayer.value?.name ?? '玩家'} 的回合`
  if (game.value.phase === 'setup_ticket_selection') return '选择初始任务 · 至少保留 2 张'
  if (game.value.phase === 'tunnel_payment') return game.value.ownTunnelPayment
    ? `隧道追加费用 · ${game.value.ownTunnelPayment.extraCost} 张` : '等待隧道工程决定'
  if (game.value.phase === 'ticket_choice') return game.value.pendingTicketChoice ? '选择新任务 · 至少保留 1 张' : '等待任务选择'
  if (game.value.phase === 'final_station_assignment') return '终局火车站借线确认'
  if (game.value.phase === 'train_draw_second') return game.value.currentPlayerId === selfId.value
    ? '再抽 1 张（公共彩虹除外）' : '等待第二次抽牌'
  if (game.value.finalRound) return `最后一轮 · ${game.value.finalRound.remainingPlayerIds.length} 位尚未行动`
  return game.value.currentPlayerId === selfId.value ? '你的回合 · 选择一项行动' : `等待 ${currentPlayer.value?.name ?? '玩家'} 行动`
})

const playerColors: Record<string, string> = {
  ruby: '#dd625c', sapphire: '#4f9add', jade: '#58ad7b', amber: '#e5b94e', violet: '#a078cb',
}
const colorLabels: Record<string, string> = {
  purple: '紫色', blue: '蓝色', orange: '橙色', white: '白色', green: '绿色', yellow: '黄色',
  black: '黑色', red: '红色', locomotive: '彩虹', gray: '灰色',
}

function resetSelection(): void {
  mode.value = null
  selectedRouteId.value = null
  selectedCityId.value = null
  selectedCardIds.value = []
  declaredColor.value = null
  error.value = ''
}
watch([() => game.value.turnNumber, () => game.value.phase, () => selfId.value], resetSelection)
watch(
  () => ticketOffer.value.map(ticket => ticket.id).join('|'),
  () => { selectedTicketIds.value = ticketOffer.value.slice(0, ticketMinimum.value).map(ticket => ticket.id) },
  { immediate: true },
)
watch(
  () => ownStations.value.map(station => `${station.cityId}:${station.borrowedRouteId ?? ''}`).join('|'),
  () => { for (const station of ownStations.value) stationAssignments[station.cityId] = station.borrowedRouteId ?? '' },
  { immediate: true },
)

async function act(name: string, payload?: Record<string, unknown>): Promise<boolean> {
  if (pending.value || spectator.value) return false
  error.value = ''
  pending.value = true
  try {
    const ok = await actions.action(name, payload)
    if (ok === false) error.value = '操作未被服务器接受，请检查当前选择。'
    return ok !== false
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '操作失败，请重试。'
    return false
  } finally {
    pending.value = false
  }
}
function beginMode(next: 'route' | 'station'): void { resetSelection(); mode.value = next }
function selectRoute(routeId: string): void {
  if (mode.value !== 'route') return
  selectedRouteId.value = routeId
  selectedCardIds.value = []
  const route = routeById.get(routeId)
  declaredColor.value = route?.color !== 'gray' ? route?.color as Exclude<TrainColor, 'gray'> : null
}
function selectCity(cityId: string): void {
  if (mode.value !== 'station') return
  selectedCityId.value = cityId
  selectedCardIds.value = []
}
function toggleCard(card: TrainCardModel): void {
  if (pending.value || (!game.value.ownTunnelPayment && !mode.value)) return
  const index = selectedCardIds.value.indexOf(card.id)
  if (index >= 0) selectedCardIds.value.splice(index, 1)
  else selectedCardIds.value.push(card.id)
  if (mode.value === 'route' && selectedRoute.value?.color === 'gray' && card.color !== 'locomotive') declaredColor.value = card.color
}
function toggleTicket(ticketId: string): void {
  const index = selectedTicketIds.value.indexOf(ticketId)
  if (index >= 0) selectedTicketIds.value.splice(index, 1)
  else selectedTicketIds.value.push(ticketId)
}
async function drawDeck(): Promise<void> { await act('draw_train_card', { source: 'deck' }) }
async function drawMarket(card: TrainCardModel): Promise<void> { await act('draw_train_card', { source: 'market', cardId: card.id }) }
async function claimRoute(): Promise<void> {
  if (!selectedRoute.value || !routePaymentReady.value) return
  const ok = await act('claim_route', { routeId: selectedRoute.value.id, cardIds: [...selectedCardIds.value], declaredColor: routeColor.value })
  if (ok) resetSelection()
}
async function buildStation(): Promise<void> {
  if (!stationPaymentReady.value || !selectedCityId.value) return
  const ok = await act('build_station', { cityId: selectedCityId.value, cardIds: [...selectedCardIds.value] })
  if (ok) resetSelection()
}
async function submitTickets(): Promise<void> {
  if (selectedTicketIds.value.length < ticketMinimum.value) return
  await act(game.value.phase === 'setup_ticket_selection' ? 'keep_initial_tickets' : 'keep_destination_tickets', { ticketIds: [...selectedTicketIds.value] })
}
async function payTunnel(): Promise<void> {
  if (tunnelPaymentReady.value) await act('pay_tunnel_extra', { cardIds: [...selectedCardIds.value] })
}
async function submitStationAssignments(): Promise<void> {
  const assignments = Object.fromEntries(ownStations.value.map(station => [station.cityId, stationAssignments[station.cityId] || null]))
  await act('assign_station_routes', { assignments })
}
function adjacentBorrowableRoutes(cityId: string): RouteModel[] {
  const claims = new Map((game.value.claimedRoutes ?? []).map(claim => [claim.routeId, claim.ownerPlayerId]))
  return board.routes.filter(route => {
    const owner = claims.get(route.id)
    return Boolean(owner && owner !== selfId.value && (route.fromCityId === cityId || route.toCityId === cityId))
  })
}
function routeName(route: RouteModel): string {
  return `${cityById.get(route.fromCityId)?.labelZhCN}—${cityById.get(route.toCityId)?.labelZhCN}（${route.length}格）`
}
function playerName(playerId: string | null | undefined): string {
  return game.value.players?.find(player => player.id === playerId)?.name ?? '玩家'
}
function resultFor(player: EuropePlayerView) { return game.value.result?.players.find(item => item.playerId === player.id) }
</script>

<template>
  <section ref="gameRoot" class="europe-game" :class="{ 'is-finished': finished }" data-testid="europe-game">
    <header class="topbar">
      <div class="brand" aria-label="欧洲车票之旅"><span class="brand-mark" aria-hidden="true"><i /><i /><b>EU</b></span><div><small>CONTINENTAL RAILWAYS</small><h1>欧洲车票之旅</h1></div></div>
      <div class="turn-banner" :class="{ urgent: Boolean(game.finalRound) }" data-testid="turn-status"><span class="signal" /><div><small>第 {{ game.turnNumber || 0 }} 回合</small><strong>{{ phaseLabel }}</strong></div></div>
      <div class="header-actions">
        <PluginIconButton label="查看历史记录" @click="showHistory = !showHistory"><History :size="18" /></PluginIconButton>
        <PluginIconButton label="查看完整规则" @click="showRules = true"><BookOpen :size="18" /></PluginIconButton>
        <PluginIconButton v-if="fullscreenSupported" :label="isFullscreen ? '退出游戏全屏' : '进入游戏全屏'" @click="toggleFullscreen()"><Minimize2 v-if="isFullscreen" :size="18" /><Maximize2 v-else :size="18" /></PluginIconButton>
      </div>
    </header>

    <main class="table-layout">
      <div class="board-zone">
        <EuropeMap :board="board" :players="game.players ?? []" :claimed-routes="game.claimedRoutes ?? []" :stations="game.stationPlacements ?? []" :legal-route-ids="mode === 'route' ? game.legalClaimRouteIds ?? [] : []" :station-city-ids="mode === 'station' ? game.stationEligibleCityIds ?? [] : []" :selected-route-id="selectedRouteId" :selected-city-id="selectedCityId" :focused-tickets="focusedTickets" :latest-event="game.latestEvent" :interactive="canInteract && Boolean(mode)" @select-route="selectRoute" @select-city="selectCity" />
        <div class="player-strip" data-testid="player-strip">
          <article v-for="player in game.players" :key="player.id" class="player-token" :class="{ current: player.id === game.currentPlayerId, self: player.id === selfId, forfeited: player.status === 'forfeited' }" :style="{ '--player': playerColors[player.color] }">
            <span class="pawn"><i /></span><div><strong>{{ player.name }}</strong><small>{{ player.score }} 分</small></div><div class="player-stock"><span title="剩余车厢">▰ {{ player.trainsRemaining }}</span><span title="剩余车站">⌂ {{ player.stationsRemaining }}</span></div>
          </article>
        </div>
        <div v-if="!finished" class="action-dock" data-testid="action-dock">
          <button type="button" class="dock-action" :class="{ active: available.has('draw_train_card') }" :disabled="!canInteract || !available.has('draw_train_card')" @click="drawDeck"><span>▤</span><b>盲抽车票</b><small>{{ game.trainDeckCount }} 张</small></button>
          <button type="button" class="dock-action" :class="{ active: mode === 'route' }" :disabled="!canInteract || !available.has('claim_route')" @click="beginMode('route')"><span>═</span><b>占用轨道</b><small>选轨道与支付牌</small></button>
          <button type="button" class="dock-action" :disabled="!canInteract || !available.has('draw_destination_tickets')" @click="act('draw_destination_tickets')"><span>⌁</span><b>抽任务牌</b><small>{{ game.destinationDeckCount }} 张</small></button>
          <button type="button" class="dock-action" :class="{ active: mode === 'station' }" :disabled="!canInteract || !available.has('build_station')" @click="beginMode('station')"><span>⌂</span><b>建火车站</b><small>当前费用 {{ stationCost }} 张</small></button>
        </div>
        <Transition name="panel-rise"><div v-if="mode" class="construction-panel" data-testid="construction-panel">
          <button class="panel-close" type="button" aria-label="取消当前操作" @click="resetSelection">×</button>
          <template v-if="mode === 'route'"><small>ROUTE CONSTRUCTION</small><strong>{{ selectedRoute ? routeName(selectedRoute) : '请点击版图上发光的可用轨道' }}</strong><p v-if="selectedRoute">{{ selectedRoute.kind === 'tunnel' ? '隧道将翻开 3 张风险牌' : selectedRoute.kind === 'ferry' ? `渡轮至少需要 ${selectedRoute.locomotivesRequired} 张彩虹牌` : `${colorLabels[selectedRoute.color]}线路` }} · 支付 {{ selectedRoute.length }} 张</p><label v-if="selectedRoute?.color === 'gray'">支付颜色 <select v-model="declaredColor"><option :value="null" disabled>选择颜色</option><option v-for="color in ['purple','blue','orange','white','green','yellow','black','red']" :key="color" :value="color">{{ colorLabels[color] }}</option></select></label><PluginButton compact :disabled="!routePaymentReady || pending" @click="claimRoute">{{ pending ? '正在铺轨…' : '确认占用轨道' }}</PluginButton></template>
          <template v-else><small>STATION CONSTRUCTION</small><strong>{{ selectedCityId ? `在${cityById.get(selectedCityId)?.labelZhCN}建站` : '请点击版图上发光的城市' }}</strong><p>第 {{ stationCost }} 座车站需支付 {{ stationCost }} 张同色牌；彩虹牌可替代。</p><PluginButton compact :disabled="!stationPaymentReady || pending" @click="buildStation">{{ pending ? '正在施工…' : '确认建造车站' }}</PluginButton></template>
        </div></Transition>
        <EffectOverlay :event="game.latestEvent" :hold="holdEffects" />
      </div>

      <aside class="market-rail" aria-label="公共牌市场">
        <div class="rail-heading"><div><small>PUBLIC MARKET</small><h2>公共车票市场</h2></div><span>{{ game.trainDiscardCount }} 弃牌</span></div>
        <div class="market-cards" data-testid="market-cards"><TrainCard v-for="card in game.market" :key="card.id" :card="card" compact :interactive="canInteract && available.has('draw_train_card') && !(game.phase === 'train_draw_second' && card.color === 'locomotive')" @select="drawMarket(card)" /></div>
        <button class="deck-stack" type="button" :disabled="!canInteract || !available.has('draw_train_card')" aria-label="从车票牌库盲抽一张" @click="drawDeck"><span class="deck-card" aria-hidden="true"><i /><i /><b>EUR</b><small>RAIL PASS</small></span><span class="deck-count">{{ game.trainDeckCount }}</span></button>
        <div class="legend"><span><i class="normal" />普通轨道</span><span><i class="tunnel" />隧道</span><span><i class="ferry" />渡轮</span></div>
        <Transition name="slide-left"><div v-if="showHistory" class="history-sheet" data-testid="history-panel"><div class="history-title"><strong>行车日志</strong><button type="button" @click="showHistory = false">×</button></div><ol><li v-for="event in [...(game.history ?? [])].reverse()" :key="event.sequence"><small>#{{ event.sequence }}</small><span>{{ event.message }}</span></li></ol></div></Transition>
      </aside>
    </main>

    <footer v-if="!spectator && !finished" class="hand-tray" data-testid="hand-tray">
      <div class="hand-label"><small>PRIVATE HAND</small><strong>我的车票牌</strong><span>{{ game.hand?.length ?? 0 }} 张</span></div>
      <div class="hand-cards"><TrainCard v-for="card in game.hand" :key="card.id" :card="card" :selected="selectedCardIds.includes(card.id)" :interactive="Boolean(mode || game.ownTunnelPayment)" :disabled="Boolean(game.ownTunnelPayment) && !tunnelAllowedCards.some(item => item.id === card.id)" @select="toggleCard(card)" /></div>
      <div class="ticket-peek"><small>任务进度</small><strong>{{ game.destinationTickets?.filter(ticket => ticket.completed).length ?? 0 }} / {{ game.destinationTickets?.length ?? 0 }}</strong><span>版图已高亮任务端点</span></div>
    </footer>

    <div v-if="spectator" class="spectator-ribbon">观战模式 · 私密手牌和任务已隐藏</div><p v-if="error" class="error-toast" role="alert">{{ error }}</p>
    <div v-if="finished && game.result" class="result-overlay" data-testid="result-overlay"><div class="result-card"><Trophy :size="34" /><small>EUROPEAN EXPRESS · FINAL</small><h2>{{ game.result.winnerPlayerIds.length > 1 ? '并列冠军' : '欧洲铁路之星' }}</h2><p>{{ game.result.winnerPlayerIds.map(playerName).join('、') }} 赢得本局</p><div class="ranking-table"><div v-for="player in [...game.players].sort((a,b) => (resultFor(a)?.rank ?? 9) - (resultFor(b)?.rank ?? 9))" :key="player.id" :class="{ winner: game.result.winnerPlayerIds.includes(player.id) }"><b>#{{ resultFor(player)?.rank }}</b><span>{{ player.name }}</span><strong>{{ resultFor(player)?.total }} 分</strong><small>线路 {{ resultFor(player)?.routePoints }} · 任务 {{ resultFor(player)?.destinationPoints }} · 车站 {{ resultFor(player)?.stationPoints }}<em v-if="resultFor(player)?.europeanExpress"> · 欧洲快车 +10</em></small></div></div><p class="tie-note">平分依次比较：完成任务数、较少使用车站、最长连续路线；完全相同则共同获胜。</p></div></div>

    <PluginModal v-if="ticketOffer.length" title="选择任务牌" description="任务一旦保留便不能丢弃，终局按是否连通加分或扣分。" size="large" :close-on-backdrop="false" aria-label="任务牌选择" mobile-sheet><div class="ticket-choice" data-testid="ticket-choice"><DestinationTicket v-for="ticket in ticketOffer" :key="ticket.id" :ticket="ticket" :selected="selectedTicketIds.includes(ticket.id)" interactive @select="toggleTicket(ticket.id)" /></div><div class="modal-footer"><span>已选 {{ selectedTicketIds.length }} 张 · 至少 {{ ticketMinimum }} 张</span><PluginButton :disabled="selectedTicketIds.length < ticketMinimum || pending" @click="submitTickets">确认保留</PluginButton></div></PluginModal>
    <PluginModal v-if="game.ownTunnelPayment" title="隧道勘探结果" :description="`翻牌产生 ${game.ownTunnelPayment.extraCost} 张追加费用；也可以撤回工程并结束回合。`" size="large" :close-on-backdrop="false" aria-label="隧道追加支付" mobile-sheet><div class="tunnel-modal" data-testid="tunnel-payment"><div class="reveal-row"><TrainCard v-for="card in game.pendingTunnel?.revealedCards" :key="card.id" :card="card" /></div><p>从下列手牌中补付 {{ game.ownTunnelPayment.extraCost }} 张{{ game.ownTunnelPayment.paymentMode === 'locomotive-only' ? '彩虹牌' : `${colorLabels[game.ownTunnelPayment.declaredColor]}或彩虹牌` }}。</p><div class="tunnel-hand" aria-label="可用于隧道补付的手牌"><TrainCard v-for="card in tunnelAllowedCards" :key="card.id" :card="card" compact interactive :selected="selectedCardIds.includes(card.id)" @select="toggleCard(card)" /></div><div class="tunnel-actions"><PluginButton variant="secondary" :disabled="pending" @click="act('decline_tunnel')">放弃并收回初始牌</PluginButton><PluginButton :disabled="!tunnelPaymentReady || pending" @click="payTunnel">补付并通车</PluginButton></div></div></PluginModal>
    <PluginModal v-if="game.phase === 'final_station_assignment' && available.has('assign_station_routes')" title="终局火车站借线" description="每座火车站可临时借用一条相邻的对手轨道，仅用于任务连通判定。" size="large" :close-on-backdrop="false" aria-label="火车站借线选择" mobile-sheet><div class="assignment-list" data-testid="station-assignments"><label v-for="station in ownStations" :key="station.cityId"><strong>{{ cityById.get(station.cityId)?.labelZhCN }}</strong><select v-model="stationAssignments[station.cityId]"><option value="">不借用</option><option v-for="route in adjacentBorrowableRoutes(station.cityId)" :key="route.id" :value="route.id">{{ routeName(route) }} · {{ playerName(game.claimedRoutes.find(item => item.routeId === route.id)?.ownerPlayerId) }}</option></select></label><p v-if="!ownStations.length">你没有已建车站，直接确认即可。</p></div><div class="modal-footer"><span>借线不会计入最长连续路线。</span><PluginButton :disabled="pending" @click="submitStationAssignments">确认并进入结算</PluginButton></div></PluginModal>
    <PluginModal v-if="showRules" title="欧洲车票之旅 · 常规规则" description="2–5 人基础欧洲地图规则" size="large" aria-label="欧洲车票之旅完整规则" mobile-sheet @close="showRules = false"><div class="rulebook"><section><h3>目标与回合</h3><p>修筑铁路并完成秘密任务。每回合四选一：抽车票牌、占用一条轨道、抽 3 张任务牌并至少留 1 张、或建造一座火车站。抽车票时可抽两张；拿公共彩虹牌会立刻结束抽牌，第二张不能拿公共彩虹牌。</p></section><section><h3>线路、渡轮与隧道</h3><p>支付等于线路长度的同色车票，彩虹牌可替代；灰线可声明任一颜色。渡轮还必须达到图示彩虹牌数量。隧道先支付，再翻 3 张牌：每张与支付颜色相同或彩虹的牌都使费用 +1；付不起或不愿补付可撤回，但回合结束。</p></section><section><h3>双线与火车站</h3><p>2–3 人时，同一城市对之间的双线只能占一条；4–5 人可由不同玩家各占一条，同一玩家仍不能独占两条。三座车站依次花费 1、2、3 张同色牌；终局每站可借一条相邻对手线路完成任务，未建车站每座 +4 分。</p></section><section><h3>终局与胜负</h3><p>任一玩家回合结束时剩余车厢不超过 2，触发最后一轮，每位玩家（含触发者）再行动一次。线路即时计分；完成任务加分、失败扣分；最长连续路线的所有并列者各 +10。总分并列依次比较完成任务数、较少使用车站、最长路线；仍相同则共同获胜。</p></section></div></PluginModal>
  </section>
</template>

<style scoped>
.europe-game{--gold:#e7bd68;position:relative;display:grid;grid-template-rows:64px minmax(0,1fr) 158px;width:100%;height:calc(100dvh - 8px);min-height:660px;overflow:hidden;color:#edf2ed;background:radial-gradient(circle at 44% 28%,#173845,#091820 62%,#060e14);font-family:Inter,"Microsoft YaHei",sans-serif}.europe-game::before{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(115deg,transparent 0 18px,#fff .6px 19px,transparent 20px);opacity:.018}.topbar{position:relative;z-index:30;display:grid;grid-template-columns:minmax(245px,1fr) minmax(300px,1.4fr) minmax(170px,1fr);align-items:center;gap:16px;padding:8px 14px;border-bottom:1px solid #d6b56832;background:#071219e8;box-shadow:0 7px 22px #0006}.brand{display:flex;align-items:center;gap:10px;min-width:0}.brand-mark{position:relative;display:grid;place-items:center;width:46px;height:46px;border:2px solid var(--gold);border-radius:12px;color:#f3d896;background:#18323d;box-shadow:inset 0 0 0 3px #07131a,0 0 22px #e0b55225}.brand-mark i{position:absolute;width:33px;height:3px;background:#e2b85f;transform:rotate(37deg)}.brand-mark i:nth-child(2){transform:rotate(-37deg)}.brand-mark b{z-index:1;padding:2px;color:#f5db9a;background:#18323d;font-size:10px}.brand small,.rail-heading small,.hand-label small,.construction-panel>small,.result-card>small{display:block;color:#8fb0b4;font-size:7px;font-weight:900;letter-spacing:.22em}.brand h1{margin:1px 0 0;overflow:hidden;font-family:Georgia,"Microsoft YaHei",serif;font-size:20px;line-height:1.1;letter-spacing:.08em;white-space:nowrap;text-overflow:ellipsis}.turn-banner{justify-self:center;display:flex;align-items:center;gap:10px;min-width:300px;padding:7px 18px;border:1px solid #8ca6a63a;border-radius:13px;background:#11252de6;box-shadow:inset 0 0 20px #0004;text-align:left}.turn-banner .signal{width:10px;height:10px;border-radius:50%;background:#65c589;box-shadow:0 0 14px #65c589;animation:signal 1.6s ease-in-out infinite}.turn-banner.urgent{border-color:#df665a66;background:#341b20e8}.turn-banner.urgent .signal{background:#e96159;box-shadow:0 0 15px #e96159}.turn-banner small{display:block;color:#8fa9aa;font-size:8px;font-weight:800;letter-spacing:.1em}.turn-banner strong{display:block;max-width:430px;overflow:hidden;font-size:12px;white-space:nowrap;text-overflow:ellipsis}.header-actions{justify-self:end;display:flex;gap:6px}.table-layout{position:relative;z-index:2;display:grid;grid-template-columns:minmax(0,1fr) 278px;gap:10px;min-height:0;padding:10px 10px 6px}.board-zone{position:relative;min-width:0;min-height:0}.player-strip{position:absolute;z-index:16;top:10px;left:50%;display:flex;gap:6px;max-width:calc(100% - 335px);transform:translateX(-32%)}.player-token{--player:#d95b58;display:grid;grid-template-columns:28px auto;column-gap:6px;align-items:center;min-width:110px;padding:5px 8px;border:1px solid #ffffff1b;border-radius:10px;background:#0a171ed9;box-shadow:0 6px 16px #0008;opacity:.8;backdrop-filter:blur(5px)}.player-token.current{border-color:var(--player);box-shadow:0 0 0 2px color-mix(in srgb,var(--player),transparent 68%),0 7px 19px #0009;opacity:1}.player-token.self{background:#142630ed}.player-token.forfeited{filter:grayscale(1);opacity:.45}.pawn{grid-row:span 2;position:relative;width:25px;height:25px;border:3px solid #ede2c2;border-radius:50%;background:var(--player);box-shadow:0 3px 8px #0007}.pawn i{position:absolute;left:5px;right:5px;bottom:-5px;height:7px;border-radius:2px;background:var(--player)}.player-token strong{display:block;max-width:82px;overflow:hidden;font-size:9px;white-space:nowrap;text-overflow:ellipsis}.player-token small{display:block;color:#aebfc0;font-size:8px}.player-stock{grid-column:2;display:flex;gap:7px;color:#d9c68e;font-size:7px}.action-dock{position:absolute;z-index:18;left:50%;bottom:9px;display:flex;gap:5px;padding:5px;border:1px solid #e4bd6845;border-radius:14px;background:#07141bef;box-shadow:0 13px 30px #000b;transform:translateX(-50%);backdrop-filter:blur(8px)}.dock-action{display:grid;grid-template-columns:25px auto;grid-template-rows:1fr 1fr;column-gap:6px;min-width:122px;padding:7px 10px;border:1px solid transparent;border-radius:9px;color:#9db0b1;background:#14252d;cursor:pointer;text-align:left;transition:.18s}.dock-action span{grid-row:span 2;align-self:center;color:#e5bd69;font-size:22px}.dock-action b{align-self:end;color:#e9efec;font-size:10px}.dock-action small{font-size:7px}.dock-action:hover:not(:disabled),.dock-action.active{border-color:#e5bd69;background:#263b41;transform:translateY(-2px)}.dock-action:disabled{cursor:not-allowed;filter:saturate(.25);opacity:.38}.construction-panel{position:absolute;z-index:22;left:12px;bottom:12px;width:min(340px,45%);padding:13px 16px;border:1px solid #e4bd6866;border-radius:15px;background:#0a1820f2;box-shadow:0 18px 38px #000c}.construction-panel strong{display:block;margin:4px 26px 2px 0;font-size:13px}.construction-panel p{margin:4px 0 9px;color:#adc0c1;font-size:9px}.construction-panel label{display:flex;align-items:center;gap:8px;margin-bottom:9px;color:#b9c9c7;font-size:9px}.construction-panel select,.assignment-list select{min-width:0;border:1px solid #647b7d;border-radius:7px;padding:5px 8px;color:#edf2eb;background:#162a31}.panel-close{position:absolute;right:8px;top:7px;border:0;color:#a9bcbc;background:none;font-size:19px;cursor:pointer}.market-rail{position:relative;display:flex;flex-direction:column;min-height:0;overflow:hidden;border:1px solid #ffffff13;border-radius:18px;background:linear-gradient(180deg,#132831,#0b1820);box-shadow:0 17px 35px #0007}.rail-heading{display:flex;align-items:center;justify-content:space-between;padding:12px 13px 7px}.rail-heading h2{margin:2px 0 0;font-family:Georgia,"Microsoft YaHei",serif;font-size:14px}.rail-heading>span{padding:4px 7px;border-radius:8px;color:#9fb4b5;background:#08151c;font-size:8px}.market-cards{display:grid;grid-template-columns:repeat(3,1fr);justify-items:center;gap:7px;padding:6px 10px}.market-cards :deep(.train-card:nth-child(4)),.market-cards :deep(.train-card:nth-child(5)){transform:translateX(34px)}.market-cards :deep(.train-card:nth-child(4):hover),.market-cards :deep(.train-card:nth-child(5):hover){transform:translate(34px,-7px)}.deck-stack{position:relative;align-self:center;margin:8px 0 5px;border:0;padding:0;background:none;cursor:pointer}.deck-stack::before,.deck-stack::after{content:"";position:absolute;inset:2px;border:1px solid #bc9457;border-radius:8px;background:#20333d;transform:translate(-7px,5px);z-index:-1}.deck-stack::after{transform:translate(7px,3px)}.deck-stack>span{position:absolute;right:-13px;bottom:-4px;display:grid;place-items:center;min-width:26px;height:22px;padding:0 4px;border:2px solid #e6c06f;border-radius:12px;color:#16232a;background:#efd48d;font-size:9px;font-weight:900}.deck-stack.disabled{cursor:not-allowed;filter:grayscale(1);opacity:.55}.legend{display:grid;gap:6px;margin:auto 12px 12px;padding-top:8px;border-top:1px solid #ffffff12;color:#8fa5a7;font-size:8px}.legend span{display:flex;align-items:center;gap:7px}.legend i{width:38px;border-top:4px solid #889195}.legend .tunnel{border-top-style:dashed}.legend .ferry{border-top-style:dotted}.history-sheet{position:absolute;z-index:20;inset:0;display:flex;flex-direction:column;background:#091820f5;backdrop-filter:blur(9px)}.history-title{display:flex;justify-content:space-between;padding:14px;border-bottom:1px solid #ffffff17}.history-title button{border:0;color:#d7e1de;background:none;font-size:20px;cursor:pointer}.history-sheet ol{margin:0;padding:8px 14px 18px 35px;overflow:auto}.history-sheet li{padding:7px 2px;border-bottom:1px solid #ffffff0d;color:#bdcbca;font-size:9px}.history-sheet li small{margin-right:7px;color:#deb767}.hand-tray{position:relative;z-index:26;display:grid;grid-template-columns:128px minmax(0,1fr) 118px;align-items:center;gap:10px;min-width:0;padding:7px 15px 10px;border-top:1px solid #e1bd6b30;background:linear-gradient(180deg,#0d1b22,#071218);box-shadow:0 -15px 35px #0008}.hand-label strong{display:block;margin:4px 0;font-family:Georgia,"Microsoft YaHei",serif;font-size:14px}.hand-label span{color:#e6c577;font-size:9px}.hand-cards{display:flex;align-items:flex-end;gap:5px;min-width:0;height:137px;overflow-x:auto;overflow-y:hidden;padding:12px 5px 2px;scrollbar-color:#6d5e42 transparent}.hand-cards :deep(.train-card){margin-right:-18px}.hand-cards :deep(.train-card:last-child){margin-right:0}.ticket-peek{display:grid;gap:4px;padding:10px;border:1px solid #ffffff17;border-radius:12px;background:#12252c}.ticket-peek small,.ticket-peek span{color:#91a6a7;font-size:7px}.ticket-peek strong{color:#edcb7b;font-size:20px}.spectator-ribbon{position:absolute;z-index:35;left:50%;bottom:13px;transform:translateX(-50%);padding:8px 15px;border:1px solid #e4bd6866;border-radius:20px;color:#ead59e;background:#09171ee8;font-size:9px}.error-toast{position:absolute;z-index:100;right:20px;bottom:175px;max-width:420px;margin:0;padding:10px 14px;border:1px solid #e36f66;border-radius:10px;color:#ffe7df;background:#4a1d1de8;box-shadow:0 10px 25px #0008;font-size:10px}.result-overlay{position:absolute;z-index:60;inset:64px 0 0;display:grid;place-items:center;padding:20px;background:radial-gradient(circle,#102b35aa,#061016e8);backdrop-filter:blur(4px)}.result-card{width:min(770px,92%);max-height:92%;overflow:auto;padding:23px;border:1px solid #e4bd6877;border-radius:25px;color:#edf1e8;background:linear-gradient(145deg,#17333bef,#09171fee);box-shadow:0 30px 90px #000d,0 0 70px #dbae4c22;text-align:center}.result-card>svg{color:#edc46d}.result-card h2{margin:4px 0 0;font-family:Georgia,"Microsoft YaHei",serif;font-size:30px}.result-card>p{margin:5px;color:#b9cac8;font-size:11px}.ranking-table{display:grid;gap:6px;margin:18px 0}.ranking-table>div{display:grid;grid-template-columns:35px 1fr 80px;align-items:center;padding:8px 12px;border:1px solid #ffffff15;border-radius:10px;background:#0b1b22;text-align:left}.ranking-table>div.winner{border-color:#e7bf6d;background:#2a2a23}.ranking-table b{color:#e6bd67}.ranking-table strong{text-align:right}.ranking-table small{grid-column:2/4;color:#8fa5a6;font-size:8px}.ranking-table em{color:#e8bd65;font-style:normal}.result-card .tie-note{font-size:8px}.ticket-choice{display:flex;flex-wrap:wrap;justify-content:center;gap:17px;padding:16px 0 22px}.modal-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:12px;border-top:1px solid #ffffff18;color:#a8bbbb;font-size:10px}.tunnel-modal{text-align:center}.reveal-row{display:flex;justify-content:center;gap:12px;margin:12px}.tunnel-modal p{color:#bdcbca}.tunnel-hand{display:flex;justify-content:center;gap:8px;min-height:112px;margin:8px 0 16px;padding:10px;border:1px solid #ffffff17;border-radius:12px;background:#081820}.tunnel-actions{display:flex;justify-content:center;gap:10px}.assignment-list{display:grid;gap:11px;padding:8px 0 17px}.assignment-list label{display:grid;grid-template-columns:110px 1fr;align-items:center;gap:8px}.assignment-list p{color:#a8b9b9}.rulebook{display:grid;grid-template-columns:1fr 1fr;gap:12px}.rulebook section{padding:12px 14px;border:1px solid #ffffff15;border-radius:12px;background:#0b1a21}.rulebook h3{margin:0 0 6px;color:#edc570;font-size:13px}.rulebook p{margin:0;color:#bdcac8;font-size:10px;line-height:1.7}.panel-rise-enter-active,.panel-rise-leave-active,.slide-left-enter-active,.slide-left-leave-active{transition:.2s ease}.panel-rise-enter-from,.panel-rise-leave-to{opacity:0;transform:translateY(15px)}.slide-left-enter-from,.slide-left-leave-to{opacity:0;transform:translateX(50px)}@keyframes signal{50%{opacity:.35;transform:scale(.72)}}
@media(max-width:1050px){.europe-game{grid-template-rows:58px minmax(0,1fr) 146px}.topbar{grid-template-columns:1fr 1.35fr auto}.brand small{display:none}.table-layout{grid-template-columns:minmax(0,1fr) 222px}.market-cards{gap:5px;padding-inline:5px}.market-cards :deep(.train-card){--card-width:52px}.market-cards :deep(.train-card:nth-child(4)),.market-cards :deep(.train-card:nth-child(5)){transform:translateX(28px)}.action-dock{max-width:94%}.dock-action{min-width:100px;padding-inline:7px}.dock-action small{display:none}.player-strip{top:8px;max-width:65%;transform:translateX(-40%)}.player-token{min-width:83px;grid-template-columns:20px auto;padding:4px}.pawn{width:18px;height:18px}.player-stock{display:none}.hand-cards :deep(.train-card){--card-width:76px}.result-overlay{inset:58px 0 0}}
@media(max-width:760px){.europe-game{grid-template-rows:54px minmax(0,1fr) 132px;min-height:580px}.topbar{grid-template-columns:1fr auto;padding:5px 8px}.brand-mark{width:38px;height:38px}.brand h1{font-size:14px}.turn-banner{position:absolute;left:50%;bottom:-35px;z-index:10;min-width:0;width:min(72%,360px);padding:5px 10px;transform:translateX(-50%)}.turn-banner small{display:none}.turn-banner strong{font-size:9px}.table-layout{grid-template-columns:1fr;padding:5px}.market-rail{position:absolute;z-index:28;top:49px;right:8px;width:66px;height:auto;overflow:visible;border:0;background:transparent;box-shadow:none}.rail-heading,.legend,.deck-stack{display:none}.market-cards{display:flex;flex-direction:column;padding:0}.market-cards :deep(.train-card){--card-width:44px}.market-cards :deep(.train-card:nth-child(n)){transform:none}.player-strip{left:7px;top:46px;display:grid;max-width:125px;transform:none}.player-token{min-width:76px}.player-token:not(.current):not(.self){display:none}.action-dock{bottom:6px;gap:2px}.dock-action{display:grid;place-items:center;min-width:62px;padding:5px}.dock-action span{grid-row:auto;font-size:18px}.dock-action b{font-size:8px}.construction-panel{left:7px;bottom:62px;width:calc(100% - 85px)}.hand-tray{grid-template-columns:74px 1fr;padding-inline:8px}.hand-label small,.ticket-peek{display:none}.hand-label strong{font-size:10px}.hand-cards{height:116px}.hand-cards :deep(.train-card){--card-width:65px;margin-right:-25px}.rulebook{grid-template-columns:1fr}.ticket-choice{flex-wrap:nowrap;justify-content:flex-start;overflow:auto}.ticket-choice :deep(.destination-ticket){width:175px}.result-overlay{inset:54px 0 0;padding:8px}.ranking-table>div{grid-template-columns:28px 1fr 55px}.ranking-table small{font-size:7px}.header-actions :deep(button:first-child){display:none}}
@media(prefers-reduced-motion:reduce){.turn-banner .signal,.dock-action,.panel-rise-enter-active,.panel-rise-leave-active,.slide-left-enter-active,.slide-left-leave-active{animation:none!important;transition:none!important}}
.deck-stack>.deck-card{position:relative;right:auto;bottom:auto;display:grid;place-content:center;width:62px;height:auto;aspect-ratio:11/17;padding:0;border:2px solid #bd9558;border-radius:8px;color:#e6c78c;background:repeating-linear-gradient(45deg,#22313a 0 7px,#2b414c 7px 14px);box-shadow:0 10px 18px #0007;font-weight:900;letter-spacing:.12em}
.deck-card i{position:absolute;left:12%;right:12%;top:48%;height:3px;background:#c89e5b;transform:rotate(35deg)}.deck-card i:nth-child(2){transform:rotate(-35deg)}.deck-card b{z-index:1;padding:2px;background:#293e48;font-size:12px}.deck-card small{z-index:1;font-size:5px}.deck-stack>.deck-count{position:absolute;right:-13px;bottom:-4px}.deck-stack:disabled{cursor:not-allowed;filter:grayscale(1);opacity:.55}
</style>
