<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  BookOpen,
  Crown,
  Expand,
  RotateCcw,
  Sparkles,
  X,
} from '@lucide/vue'
import {
  usePluginFullscreen,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import DevelopmentCard from './components/DevelopmentCard.vue'
import GemToken from './components/GemToken.vue'
import NobleTile from './components/NobleTile.vue'
import PaymentComposer from './components/PaymentComposer.vue'
import PlayerTableau from './components/PlayerTableau.vue'
import type {
  DevelopmentCardView,
  EventView,
  NobleView,
  PieceColor,
  PieceVector,
  PlayerView,
  SplendorGameView,
  StandardColor,
} from './types'
import { colorInfo, emptyPieces, pieceColors, standardColors } from './types'
import './layout.css'
import './models.css'
import './motion.css'
import './responsive.css'

type Intent = 'idle' | 'take-different' | 'take-same' | 'blind-reserve'
type CardTarget = {
  card: DevelopmentCardView
  source: 'market' | 'reservation'
  reservationId?: string
}

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const gameActions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported, toggle: toggleFullscreen } = usePluginFullscreen(gameRoot)

const busy = ref(false)
const localError = ref('')
const showRules = ref(false)
const intent = ref<Intent>('idle')
const selectedColors = ref<StandardColor[]>([])
const selectedSame = ref<StandardColor | null>(null)
const selectedBlindLevel = ref<number | null>(null)
const selectedCard = ref<CardTarget | null>(null)
const paymentTarget = ref<CardTarget | null>(null)
const payment = ref<PieceVector>(emptyPieces())
const returnPieces = ref<PieceVector>(emptyPieces())
const selectedNobleId = ref<string | null>(null)

const motionQueue = ref<EventView[]>([])
const currentMotion = ref<EventView | null>(null)
let motionTimer: ReturnType<typeof setTimeout> | undefined
let motionInitialized = false
let lastMotionSeq = 0

const game = computed(() => props.snapshot.game as unknown as SplendorGameView)
const me = computed(() => game.value.players.find(player => player.id === game.value.selfPlayerId) ?? null)
const currentPlayer = computed(() => game.value.players.find(player => player.id === game.value.currentPlayerId) ?? null)
const opponents = computed(() => {
  if (!me.value) return game.value.players
  const index = game.value.turnOrder.indexOf(me.value.id)
  return game.value.turnOrder
    .slice(index + 1)
    .concat(game.value.turnOrder.slice(0, index))
    .map(id => game.value.players.find(player => player.id === id))
    .filter((player): player is PlayerView => Boolean(player))
})
const latestEvents = computed(() => game.value.events.slice(-5).reverse())
const canUseTable = computed(() => game.value.actions.canAct && !busy.value)
const selectedCardPayment = computed(() => selectedCard.value?.card.payment ?? null)
const returnTotal = computed(() => Object.values(returnPieces.value).reduce((sum, value) => sum + value, 0))
const statusTitle = computed(() => {
  if (game.value.phase === 'finished') return '本局已经结算'
  if (game.value.phase === 'return_tokens') return '强制归还棋子'
  if (game.value.phase === 'choose_noble') return '选择一位贵族'
  if (game.value.currentPlayerId === game.value.selfPlayerId) return '轮到你行动'
  return `等待 ${currentPlayer.value?.name ?? '当前玩家'}`
})
const motionClass = computed(() => currentMotion.value ? `motion-${currentMotion.value.type.replaceAll('_', '-')}` : '')
const purchasedByColor = computed(() => {
  const result: Record<StandardColor, DevelopmentCardView[]> = {
    white: [], blue: [], green: [], red: [], black: [],
  }
  for (const card of me.value?.purchasedCards ?? []) result[card.bonusColor].push(card)
  return result
})

const motionDuration: Record<string, number> = {
  pieces_taken: 380,
  pieces_returned: 320,
  card_reserved_public: 420,
  card_reserved_blind: 360,
  card_purchased: 520,
  market_refilled: 280,
  noble_acquired: 560,
  final_round_triggered: 420,
  turn_advanced: 220,
  game_finished: 650,
}

watch(() => game.value.events, (events) => {
  const latest = events.at(-1)?.seq ?? 0
  if (!motionInitialized || latest < lastMotionSeq) {
    motionInitialized = true
    lastMotionSeq = latest
    return
  }
  const additions = events.filter(event => event.seq > lastMotionSeq && motionDuration[event.type])
  if (additions.length) {
    motionQueue.value.push(...additions)
    lastMotionSeq = latest
    playNextMotion()
  }
}, { deep: true, immediate: true })

watch(() => game.value.revision, () => {
  if (game.value.phase !== 'turn_action') {
    intent.value = 'idle'
    selectedColors.value = []
    selectedSame.value = null
    selectedBlindLevel.value = null
    selectedCard.value = null
    paymentTarget.value = null
  }
  if (game.value.phase !== 'return_tokens') returnPieces.value = emptyPieces()
  if (game.value.phase !== 'choose_noble') selectedNobleId.value = null
})

onBeforeUnmount(() => {
  if (motionTimer) clearTimeout(motionTimer)
})

function playNextMotion() {
  if (currentMotion.value || motionQueue.value.length === 0) return
  currentMotion.value = motionQueue.value.shift() ?? null
  if (!currentMotion.value) return
  const duration = motionDuration[currentMotion.value.type] ?? 420
  motionTimer = setTimeout(() => {
    currentMotion.value = null
    playNextMotion()
  }, duration + 90)
}

async function submit(action: string, payload: Record<string, unknown> = {}) {
  if (busy.value) return false
  busy.value = true
  localError.value = ''
  try {
    await gameActions.action(action, { revision: game.value.revision, ...payload })
    return true
  } catch (reason) {
    localError.value = reason instanceof Error ? reason.message : String(reason)
    return false
  } finally {
    busy.value = false
  }
}

function beginIntent(next: Intent) {
  if (!canUseTable.value) return
  intent.value = next
  selectedColors.value = []
  selectedSame.value = null
  selectedBlindLevel.value = null
  selectedCard.value = null
  localError.value = ''
}

function cancelDraft() {
  intent.value = 'idle'
  selectedColors.value = []
  selectedSame.value = null
  selectedBlindLevel.value = null
  selectedCard.value = null
  paymentTarget.value = null
  localError.value = ''
}

function selectSupply(color: PieceColor) {
  if (!canUseTable.value || color === 'gold') return
  if (intent.value === 'take-different') {
    if (!game.value.actions.differentColors.includes(color)) return
    if (selectedColors.value.includes(color)) {
      selectedColors.value = selectedColors.value.filter(item => item !== color)
    } else if (selectedColors.value.length < game.value.actions.requiredDistinctCount) {
      selectedColors.value.push(color)
    }
  } else if (intent.value === 'take-same' && game.value.actions.sameColors.includes(color)) {
    selectedSame.value = color
  }
}

async function confirmTokenAction() {
  if (intent.value === 'take-different') {
    if (selectedColors.value.length !== game.value.actions.requiredDistinctCount) return
    if (await submit('take_different', { colors: [...selectedColors.value] })) cancelDraft()
  } else if (intent.value === 'take-same' && selectedSame.value) {
    if (await submit('take_same', { color: selectedSame.value })) cancelDraft()
  } else if (intent.value === 'blind-reserve' && selectedBlindLevel.value) {
    if (await submit('reserve_blind', { level: selectedBlindLevel.value, marketRevision: game.value.marketRevision })) cancelDraft()
  }
}

function openMarketCard(card: DevelopmentCardView) {
  selectedCard.value = { card, source: 'market' }
  intent.value = 'idle'
}

function openReservedCard(card: DevelopmentCardView, reservationId: string) {
  selectedCard.value = { card, source: 'reservation', reservationId }
  intent.value = 'idle'
}

function chooseBlindLevel(level: number) {
  if (!canUseTable.value || !game.value.actions.blindReserveLevels.includes(level)) return
  intent.value = 'blind-reserve'
  selectedBlindLevel.value = level
  selectedCard.value = null
}

function beginPayment(target: CardTarget) {
  if (!target.card.payment?.affordable || !me.value) return
  paymentTarget.value = target
  payment.value = { ...target.card.payment.recommendedPayment }
  selectedCard.value = null
}

async function confirmPurchase() {
  const target = paymentTarget.value
  if (!target) return
  const ok = target.source === 'market'
    ? await submit('purchase_face_up', { cardId: target.card.id, payment: { ...payment.value }, marketRevision: game.value.marketRevision })
    : await submit('purchase_reserved', { reservationId: target.reservationId, payment: { ...payment.value } })
  if (ok) paymentTarget.value = null
}

async function reserveSelectedCard() {
  const target = selectedCard.value
  if (!target || target.source !== 'market') return
  if (await submit('reserve_face_up', { cardId: target.card.id, marketRevision: game.value.marketRevision })) selectedCard.value = null
}

function adjustReturn(color: PieceColor, delta: number) {
  if (!me.value || busy.value) return
  const next = returnPieces.value[color] + delta
  const nextTotal = returnTotal.value + delta
  if (next < 0 || next > me.value.pieces[color] || nextTotal > game.value.actions.returnCount) return
  returnPieces.value = { ...returnPieces.value, [color]: next }
}

async function confirmReturn() {
  if (returnTotal.value !== game.value.actions.returnCount) return
  if (await submit('return_tokens', { pieces: { ...returnPieces.value } })) returnPieces.value = emptyPieces()
}

async function confirmNoble() {
  if (!selectedNobleId.value) return
  if (await submit('choose_noble', { nobleId: selectedNobleId.value })) selectedNobleId.value = null
}

function playerName(playerId: string | null | undefined) {
  return game.value.players.find(player => player.id === playerId)?.name ?? playerId ?? '—'
}

function selectedNoble(): NobleView | null {
  return game.value.availableNobles.find(item => item.id === selectedNobleId.value) ?? null
}
</script>

<template>
  <section
    ref="gameRoot"
    class="splendor-game"
    :class="[`scene-${game.sceneId}`, `phase-${game.phase}`, { busy, fullscreen: isFullscreen }]"
    data-model-version="1.0.0"
  >
    <div class="table-grain" aria-hidden="true" />
    <header id="status_bar" class="table-masthead">
      <div class="brand-lockup"><small>GAME HALL · JEWELERS' GUILD</small><h2>璀璨宝石</h2></div>
      <div class="status-copy" :class="{ final: game.finalRound }">
        <span>第 {{ game.roundNumber }} 轮 · 行动 {{ game.actionNumber + 1 }}</span>
        <strong>{{ statusTitle }}</strong>
        <small v-if="game.finalRound">最终轮 · {{ playerName(game.finalRound.triggeredBy) }} 已触发 · 尚可行动 {{ game.finalRound.remainingPlayerIds.map(playerName).join('、') || '无' }}</small>
        <small v-else>首家 {{ playerName(game.firstPlayerId) }} · 15 分触发最终轮</small>
      </div>
      <div class="mast-actions">
        <button type="button" aria-label="打开规则摘要" @click="showRules = true"><BookOpen :size="17" /><span>规则</span></button>
        <button v-if="isSupported" type="button" :aria-label="isFullscreen ? '退出全屏' : '进入全屏'" @click="toggleFullscreen"><Expand :size="17" /><span>{{ isFullscreen ? '退出' : '全屏' }}</span></button>
      </div>
    </header>

    <section id="opponent_rail" class="opponent-rail" aria-label="对手公开区域">
      <PlayerTableau v-for="opponent in opponents" :key="opponent.id" :player="opponent" compact />
    </section>

    <div class="scene-grid">
      <main class="market-board">
        <section id="noble_row" class="noble-row" aria-labelledby="noble-title">
          <header><div><small>PATRONS</small><h3 id="noble-title">贵族长廊</h3></div><span>仅计算永久奖励 · 每回合最多 1 位</span></header>
          <div class="noble-list">
            <NobleTile v-for="noble in game.availableNobles" :key="noble.id" :noble="noble" />
            <span v-if="game.availableNobles.length === 0" class="empty-zone">贵族均已拜访</span>
          </div>
        </section>

        <section
          v-for="tier in game.tiers"
          :id="`tier_${tier.level}_market`"
          :key="tier.level"
          class="market-tier"
          :class="`tier-${tier.level}`"
          :aria-labelledby="`tier-title-${tier.level}`"
        >
          <header><small>LEVEL</small><strong :id="`tier-title-${tier.level}`">{{ tier.level }} 级市场</strong></header>
          <div class="deck-stack" :class="{ legal: game.actions.blindReserveLevels.includes(tier.level) }">
            <DevelopmentCard
              :card="null"
              :face-down-level="tier.level"
              :interactive="game.actions.blindReserveLevels.includes(tier.level)"
              :selected="selectedBlindLevel === tier.level"
              @select="chooseBlindLevel(tier.level)"
            />
            <b>{{ tier.deckCount }}</b><small>剩余</small>
          </div>
          <div class="market-slots">
            <div v-for="entry in tier.slots" :key="entry.slot" class="market-slot" :class="{ empty: !entry.card }">
              <DevelopmentCard v-if="entry.card" :card="entry.card" interactive :selected="selectedCard?.card.id === entry.card.id" @select="openMarketCard(entry.card)" />
              <span v-else>牌堆已空</span>
            </div>
          </div>
        </section>
      </main>

      <aside class="table-sidebar">
        <section id="gem_supply" class="gem-supply" aria-labelledby="supply-title">
          <header><div><small>PUBLIC SUPPLY</small><h3 id="supply-title">公共供应</h3></div><span>棋子信息全部公开</span></header>
          <div class="supply-grid">
            <GemToken
              v-for="color in pieceColors"
              :key="color"
              :color="color"
              :count="game.supply[color]"
              :interactive="color !== 'gold' && (intent === 'take-different' || intent === 'take-same')"
              :selected="color !== 'gold' && (selectedColors.includes(color) || selectedSame === color)"
              :sequence="color !== 'gold' ? selectedColors.indexOf(color) + 1 || null : null"
              :disabled="color === 'gold' || (intent === 'take-different' ? !game.actions.differentColors.includes(color as StandardColor) : intent === 'take-same' ? !game.actions.sameColors.includes(color as StandardColor) : true)"
              :subtitle="intent === 'take-same' && color !== 'gold' ? (game.supply[color] >= 4 ? `${game.supply[color]} → ${game.supply[color] - 2}` : '至少需 4') : ''"
              @select="selectSupply(color)"
            />
          </div>
        </section>

        <section id="event_strip" class="event-strip" aria-labelledby="event-title">
          <header><small>LEDGER</small><h3 id="event-title">最近事件</h3></header>
          <ol><li v-for="event in latestEvents" :key="event.seq"><b>{{ String(event.seq).padStart(2, '0') }}</b><span>{{ event.message }}</span></li></ol>
        </section>
      </aside>
    </div>

    <section class="private-console">
      <div id="self_tableau" class="self-engine">
        <PlayerTableau v-if="me" :player="me" self />
        <div v-if="me" class="engine-columns" aria-label="本人已购买发展卡">
          <div v-for="color in standardColors" :key="color" :class="`engine-column engine-${color}`">
            <header><i>{{ colorInfo[color].symbol }}</i><b>{{ me.bonuses[color] }}</b><span>{{ colorInfo[color].name }}</span></header>
            <div class="engine-card-stack">
              <DevelopmentCard v-for="card in purchasedByColor[color].slice(-4)" :key="card.id" :card="card" compact />
              <small v-if="purchasedByColor[color].length === 0">尚无</small>
            </div>
          </div>
        </div>
      </div>

      <section id="reserved_drawer" class="reserved-drawer" aria-labelledby="reserved-title">
        <header><div><small>PRIVATE DRAWER</small><h3 id="reserved-title">保留牌</h3></div><b>{{ me?.reservations.length ?? 0 }}/3</b></header>
        <div class="reserved-list">
          <template v-for="reservation in me?.reservations ?? []" :key="reservation.reservationId">
            <DevelopmentCard v-if="reservation.card" :card="reservation.card" interactive compact :selected="selectedCard?.reservationId === reservation.reservationId" @select="openReservedCard(reservation.card, reservation.reservationId)" />
            <DevelopmentCard v-else :card="null" :face-down-level="reservation.level" compact />
          </template>
          <span v-if="!me?.reservations.length" class="empty-zone">尚未保留</span>
        </div>
      </section>
    </section>

    <section id="action_dock" class="action-dock" :class="{ active: canUseTable, error: localError }" aria-labelledby="action-title">
      <header><span>TURN ACTION</span><div><strong id="action-title">{{ intent === 'idle' ? statusTitle : intent === 'take-different' ? `选择 ${game.actions.requiredDistinctCount} 种不同颜色` : intent === 'take-same' ? '选择一种供应至少 4 枚的颜色' : '选择盲保留等级' }}</strong><small>{{ localError || game.actions.disabledReasonZh || '一个回合只能执行一项主要行动' }}</small></div><em v-if="busy">结算中…</em></header>
      <div v-if="intent === 'idle'" class="dock-actions">
        <button type="button" class="primary-action" :disabled="!game.actions.canTakeDifferent || busy" @click="beginIntent('take-different')">取 {{ game.actions.requiredDistinctCount }} 种不同色</button>
        <button type="button" class="secondary-action" :disabled="!game.actions.sameColors.length || busy" @click="beginIntent('take-same')">取同色 2 枚</button>
        <button type="button" class="secondary-action" :disabled="!game.actions.blindReserveLevels.length || busy" @click="beginIntent('blind-reserve')">盲保留牌堆顶</button>
        <span>也可直接点市场牌查看购买／保留</span>
      </div>
      <div v-else class="dock-actions draft-actions">
        <div v-if="intent === 'take-different'" class="draft-summary">已选 {{ selectedColors.length }}/{{ game.actions.requiredDistinctCount }}：{{ selectedColors.map(color => colorInfo[color].name).join('、') || '请点供应棋子' }}</div>
        <div v-else-if="intent === 'take-same'" class="draft-summary">{{ selectedSame ? `拿取 2 枚${colorInfo[selectedSame].name}` : '请点可用的供应棋子' }}</div>
        <div v-else class="blind-levels"><button v-for="level in game.actions.blindReserveLevels" :key="level" type="button" :class="{ selected: selectedBlindLevel === level }" @click="selectedBlindLevel = level">{{ level }} 级 · {{ game.tiers.find(tier => tier.level === level)?.deckCount }} 张</button></div>
        <button type="button" class="ghost-action" :disabled="busy" @click="cancelDraft">取消</button>
        <button type="button" class="primary-action" :disabled="busy || (intent === 'take-different' ? selectedColors.length !== game.actions.requiredDistinctCount : intent === 'take-same' ? !selectedSame : !selectedBlindLevel)" @click="confirmTokenAction">确认行动</button>
      </div>
    </section>

    <aside v-if="selectedCard" class="card-detail-sheet" role="dialog" aria-modal="true" aria-labelledby="card-detail-title">
      <header><div><small>{{ selectedCard.source === 'market' ? 'MARKET CARD' : 'RESERVED CARD' }}</small><h3 id="card-detail-title">{{ selectedCard.card.level }} 级 · {{ colorInfo[selectedCard.card.bonusColor].name }}奖励</h3></div><button type="button" aria-label="关闭卡牌详情" @click="selectedCard = null"><X :size="18" /></button></header>
      <div class="card-detail-body">
        <DevelopmentCard :card="selectedCard.card" />
        <div class="cost-analysis">
          <h4>费用分析</h4>
          <div v-for="color in standardColors" :key="color" :class="{ zero: selectedCard.card.cost[color] === 0 }"><span>{{ colorInfo[color].symbol }} {{ colorInfo[color].name }}</span><b>{{ selectedCard.card.cost[color] }}</b><i>− {{ me?.bonuses[color] ?? 0 }}</i><strong>= {{ selectedCardPayment?.effectiveCost[color] ?? 0 }}</strong></div>
          <p v-if="selectedCardPayment?.affordable">可以买下 · 最少使用 {{ selectedCardPayment.minimumGold }} 枚黄金</p><p v-else>当前棋子不足</p>
        </div>
      </div>
      <footer>
        <button v-if="selectedCard.source === 'market'" type="button" class="secondary-action" :disabled="!selectedCard.card.legal?.reserve || busy" @click="reserveSelectedCard">保留此牌</button>
        <button type="button" class="primary-action" :disabled="!selectedCard.card.legal?.buy || busy" @click="beginPayment(selectedCard)">编辑支付并购买</button>
      </footer>
    </aside>

    <div v-if="paymentTarget && me" class="modal-scrim payment-scrim"><PaymentComposer :card="paymentTarget.card" :player="me" :payment="payment" :busy="busy" @change="payment = $event" @confirm="confirmPurchase" @cancel="paymentTarget = null" /></div>

    <div v-if="game.phase === 'return_tokens' && me" class="modal-scrim resolution-scrim">
      <section id="resolution_sheet" class="resolution-sheet return-sheet" role="dialog" aria-modal="true" aria-labelledby="return-title">
        <header><Sparkles :size="22" /><div><small>强制后处理</small><h3 id="return-title">必须归还 {{ game.actions.returnCount }} 枚棋子</h3></div></header>
        <p>当前 {{ Object.values(me.pieces).reduce((sum, value) => sum + value, 0) }} 枚 / 上限 10。可归还刚拿到或原有的任意棋子，包括黄金。</p>
        <div class="return-grid">
          <article v-for="color in pieceColors" :key="color" :class="`return-${color}`"><i>{{ colorInfo[color].symbol }}</i><strong>{{ colorInfo[color].name }}</strong><small>持有 {{ me.pieces[color] }}</small><div><button type="button" :disabled="returnPieces[color] <= 0 || busy" @click="adjustReturn(color, -1)">−</button><b>{{ returnPieces[color] }}</b><button type="button" :disabled="returnPieces[color] >= me.pieces[color] || returnTotal >= game.actions.returnCount || busy" @click="adjustReturn(color, 1)">+</button></div></article>
        </div>
        <footer><span>已选 {{ returnTotal }}/{{ game.actions.returnCount }}</span><button type="button" class="primary-action" :disabled="returnTotal !== game.actions.returnCount || busy" @click="confirmReturn">确认归还</button></footer>
      </section>
    </div>

    <div v-if="game.phase === 'choose_noble'" class="modal-scrim resolution-scrim">
      <section id="resolution_sheet" class="resolution-sheet noble-choice-sheet" role="dialog" aria-modal="true" aria-labelledby="choice-title">
        <header><Crown :size="24" /><div><small>贵族拜访</small><h3 id="choice-title">选择其中一位贵族</h3></div></header>
        <p>你同时满足多位贵族；本回合必须选择 1 位并获得 3 点威望。</p>
        <div class="noble-choice-list"><NobleTile v-for="noble in game.availableNobles.filter(item => game.actions.eligibleNobleIds.includes(item.id))" :key="noble.id" :noble="noble" interactive :selected="selectedNobleId === noble.id" @select="selectedNobleId = noble.id" /></div>
        <footer><span>{{ selectedNoble() ? '已选择一位贵族' : '请选择' }}</span><button type="button" class="primary-action" :disabled="!selectedNobleId || busy" @click="confirmNoble">确认拜访</button></footer>
      </section>
    </div>

    <div v-if="game.phase === 'finished' && game.result" class="modal-scrim resolution-scrim result-scrim">
      <section id="resolution_sheet" class="resolution-sheet result-sheet" role="dialog" aria-modal="true" aria-labelledby="result-title">
        <header><Crown :size="25" /><div><small>{{ game.result.outcome === 'shared-win' ? 'SHARED VICTORY' : 'VICTORY' }}</small><h3 id="result-title">{{ game.result.summaryZh }}</h3></div></header>
        <div class="ranking-table"><article v-for="row in game.result.rows" :key="row.player_id" :class="{ winner: row.winner, forfeited: row.forfeited }"><b>#{{ row.rank }}</b><strong>{{ playerName(row.player_id) }}</strong><span>卡牌 {{ row.card_prestige }} + 贵族 {{ row.noble_prestige }}</span><em>{{ row.prestige }} 分</em><small>{{ row.purchased_card_count }} 张发展卡</small></article></div>
        <p v-if="game.result.outcome === 'shared-win'">最高威望与购买卡数均相同，因此按常规规则共同获胜。</p>
        <footer><span>同分先比较已购买发展卡数量，越少越优</span><button type="button" class="primary-action" :disabled="!snapshot.actions.canRestart" @click="gameActions.restart"><RotateCcw :size="16" /> 再来一局</button></footer>
      </section>
    </div>

    <div v-if="showRules" class="modal-scrim rules-scrim" @click.self="showRules = false">
      <section class="rules-sheet" role="dialog" aria-modal="true" aria-labelledby="rules-title">
        <header><div><small>2024 BASE RULES</small><h3 id="rules-title">常规规则速查</h3></div><button type="button" aria-label="关闭规则摘要" @click="showRules = false"><X :size="19" /></button></header>
        <div class="rules-grid">
          <article><b>01 · 每回合四选一</b><p>取 3 种不同色；供应至少 4 枚时取同色 2 枚；保留一张并尽可能拿黄金；购买市场或自己的保留牌。</p></article>
          <article><b>02 · 永久奖励</b><p>已购买发展卡的颜色奖励永久降低同色费用。黄金可精确替代任意仍需支付的宝石。</p></article>
          <article><b>03 · 两项上限</b><p>回合结束最多持有 10 枚棋子；同时最多保留 3 张发展卡。超出棋子上限必须立即归还。</p></article>
          <article><b>04 · 贵族</b><p>只用永久奖励检查要求；同时满足多位时选 1 位，每回合最多获得 1 位。</p></article>
          <article><b>05 · 最终轮</b><p>回合末达到 15 分后完成当前轮，直到首家右手边玩家行动完毕。</p></article>
          <article><b>06 · 胜负</b><p>最高威望获胜；同分时已购买发展卡更少者获胜，仍相同则共同获胜。</p></article>
        </div>
      </section>
    </div>

    <div v-if="currentMotion" class="motion-layer" :class="motionClass" aria-hidden="true">
      <div v-if="currentMotion.type.startsWith('pieces_')" class="motion-gem-trail"><i v-for="index in 3" :key="index">{{ currentMotion.type === 'pieces_returned' ? '◇' : '◆' }}</i></div>
      <div v-else-if="currentMotion.type.startsWith('card_') || currentMotion.type === 'market_refilled'" class="motion-card-model"><span>{{ currentMotion.data.card?.level ?? currentMotion.data.level ?? 1 }}</span><i>{{ currentMotion.type === 'card_reserved_blind' ? '?' : '◇' }}</i></div>
      <div v-else-if="currentMotion.type === 'noble_acquired'" class="motion-noble-model"><Crown :size="28" /><b>+3</b></div>
      <div v-else-if="currentMotion.type === 'final_round_triggered'" class="motion-final-banner">FINAL ROUND</div>
      <div v-else-if="currentMotion.type === 'game_finished'" class="motion-victory-seal"><Crown :size="34" /><span>VICTORY</span></div>
      <div v-else class="motion-turn-ring" />
    </div>

    <p class="sr-live" aria-live="polite">{{ game.events.at(-1)?.message }}</p>
  </section>
</template>
