<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import { usePluginGameActions } from '@game-hall/plugin-sdk'
import type {
  FundCardView,
  GameEventView,
  IndustryId,
  LedgerView,
  PonziGameView,
  TradeTarget,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const busy = ref(false)
const selectedIndustry = ref<IndustryId | null>(null)
const selectedTarget = ref<string | null>(null)
const selectedTradeIndustry = ref<IndustryId | null>(null)
const offer = ref(0)
const showRulebook = ref(false)
const rulebookDialog = ref<HTMLElement | null>(null)

type MotionKind = 'fund' | 'envelope' | 'transfer' | 'luxury' | 'market' | 'crash' | 'industry' | 'cash' | 'wheel' | 'bankruptcy' | 'marker'
type MotionCue = { seq: number, kind: MotionKind, message: string }

const motion = ref<MotionCue | null>(null)
const visualWheelPosition = ref(0)
const motionQueue: MotionCue[] = []
let lastSeenEvent: number | null = null
let motionTimer: ReturnType<typeof setTimeout> | undefined
let queueTimer: ReturnType<typeof setTimeout> | undefined

const game = computed(() => props.snapshot.game as unknown as PonziGameView)
const legal = computed(() => game.value.legalActions ?? {})
const selfId = computed(() => props.snapshot.self.id)
const myLedger = computed(() => ledgerFor(selfId.value))
const currentPlayer = computed(() => playerFor(game.value.currentPlayerId))
const starterPlayer = computed(() => playerFor(game.value.starterPlayerId))
const selectedFunding = computed(() => legal.value.fundingOptions?.find(
  option => option.industryId === selectedIndustry.value,
))
const selectedTradeTarget = computed(() => legal.value.tradeTargets?.find(
  item => item.targetId === selectedTarget.value,
))
const cashBills = computed(() => {
  let remaining = myLedger.value?.cash ?? 0
  return [20, 10, 5, 1].map((value) => {
    const count = Math.floor(remaining / value)
    remaining %= value
    return { value, count }
  }).filter(item => item.count > 0)
})
const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return props.snapshot.winReason ?? '骗局已经崩解'
  if (game.value.currentPlayerId === selfId.value) return `轮到你 · ${game.value.stageLabel}`
  return `${game.value.stageLabel} · 等待 ${currentPlayer.value?.name ?? '系统结算'}`
})
const statusDetail = computed(() => {
  if (props.snapshot.phase === 'finished') return '现金已揭示；产业分、奢侈品分与最高资金牌决胜顺序已完成审计'
  if (game.value.stage === 'funding') return '取得产业后，必须从对应排拿一张公开贷款牌'
  if (game.value.stage === 'trade') return '发出密封报价、购买奢侈品，或放弃本次暗盘行动'
  if (game.value.stage === 'trade_response') return '收下现金卖出产业，或补入等额现金反向收购'
  if (game.value.stage === 'market_prune') return '新起始玩家移除一张资金牌，随后检查熊市'
  if (game.value.stage === 'crash_discard') return '每人从数量最多的产业中退回一枚'
  return '轮盘推进后，所有到达箭头的利息必须全额支付'
})

const eventMotions: Partial<Record<string, MotionKind>> = {
  fund: 'fund',
  trade_offer: 'envelope',
  trade_accept: 'transfer',
  trade_counter: 'transfer',
  luxury: 'luxury',
  market_discard: 'market',
  market_crash: 'crash',
  crash_discard: 'industry',
  interest_paid: 'cash',
  wheel: 'wheel',
  bankruptcy: 'bankruptcy',
  marker_pass: 'marker',
}

function playerFor(playerId?: string | null) {
  return props.snapshot.players.find(player => player.id === playerId)
}

function ledgerFor(playerId?: string | null): LedgerView | undefined {
  return game.value.ledgers.find(ledger => ledger.playerId === playerId)
}

function industryName(industryId: IndustryId): string {
  return game.value.industryCatalog.find(item => item.id === industryId)?.shortName ?? industryId
}

function industryColor(industryId: IndustryId): string {
  return game.value.industryCatalog.find(item => item.id === industryId)?.color ?? '#8b765a'
}

function cardSelectable(card: FundCardView): boolean {
  if (legal.value.discardMarketCardIds?.includes(card.id)) return true
  return Boolean(selectedFunding.value?.cardIds.includes(card.id))
}

async function send(action: string, payload: Record<string, unknown> = {}) {
  if (busy.value) return
  busy.value = true
  try {
    await actions.action(action, payload)
  }
  finally {
    busy.value = false
  }
}

function actOnCard(card: FundCardView) {
  if (legal.value.discardMarketCardIds?.includes(card.id)) {
    void send('discard_market_card', { cardId: card.id })
    return
  }
  if (selectedIndustry.value && selectedFunding.value?.cardIds.includes(card.id)) {
    void send('fund', { industryId: selectedIndustry.value, cardId: card.id })
  }
}

function chooseTradeTarget(target: TradeTarget) {
  selectedTarget.value = target.targetId
  if (!target.industryIds.includes(selectedTradeIndustry.value as IndustryId)) {
    selectedTradeIndustry.value = target.industryIds[0] ?? null
  }
}

function submitOffer() {
  if (!selectedTarget.value || !selectedTradeIndustry.value) return
  const value = Math.max(0, Math.min(Math.floor(offer.value), legal.value.maxOffer ?? 0))
  void send('make_offer', {
    targetId: selectedTarget.value,
    industryId: selectedTradeIndustry.value,
    offer: value,
  })
}

function wheelCards(ledger: LedgerView | undefined, dueIn: number) {
  return ledger?.funds.filter(card => card.dueIn === dueIn) ?? []
}

function openRulebook() {
  showRulebook.value = true
  void nextTick(() => rulebookDialog.value?.focus())
}

function closeRulebook() {
  showRulebook.value = false
}

function queueMotion(event: GameEventView) {
  const kind = eventMotions[event.type]
  if (!kind) return
  motionQueue.push({ seq: event.seq, kind, message: event.message })
  playNextMotion()
}

function playNextMotion() {
  if (motion.value || motionQueue.length === 0) return
  motion.value = motionQueue.shift() ?? null
  motionTimer = setTimeout(() => {
    motion.value = null
    queueTimer = setTimeout(playNextMotion, 50)
  }, 1050)
}

watch(
  () => legal.value.fundingOptions?.map(option => option.industryId).join('|') ?? '',
  () => {
    const options = legal.value.fundingOptions ?? []
    if (!options.some(option => option.industryId === selectedIndustry.value)) {
      selectedIndustry.value = options[0]?.industryId ?? null
    }
  },
  { immediate: true },
)

watch(
  () => legal.value.tradeTargets?.map(target => `${target.targetId}:${target.industryIds.join(',')}`).join('|') ?? '',
  () => {
    const targets = legal.value.tradeTargets ?? []
    if (!targets.some(target => target.targetId === selectedTarget.value)) {
      selectedTarget.value = targets[0]?.targetId ?? null
    }
    const target = targets.find(item => item.targetId === selectedTarget.value)
    if (!target?.industryIds.includes(selectedTradeIndustry.value as IndustryId)) {
      selectedTradeIndustry.value = target?.industryIds[0] ?? null
    }
  },
  { immediate: true },
)

watch(
  () => legal.value.maxOffer ?? 0,
  max => { offer.value = Math.min(offer.value, max) },
)

watch(
  () => game.value.events.map(event => event.seq).join('|'),
  () => {
    const events = game.value.events
    const newest = events[events.length - 1]?.seq ?? 0
    if (lastSeenEvent === null) {
      lastSeenEvent = newest
      return
    }
    const previous = lastSeenEvent
    events.filter(event => event.seq > previous).forEach(queueMotion)
    lastSeenEvent = newest
  },
  { immediate: true },
)

watch(
  () => game.value.wheelPosition,
  (next, previous) => {
    if (previous === undefined) {
      visualWheelPosition.value = next
      return
    }
    visualWheelPosition.value += (next - previous + 5) % 5
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (motionTimer) clearTimeout(motionTimer)
  if (queueTimer) clearTimeout(queueTimer)
})
</script>

<template>
  <main class="ponzi-table" :class="{ 'is-crashing': motion?.kind === 'crash' }">
    <div v-if="motion" :key="motion.seq" class="motion-layer" :class="`cue-${motion.kind}`" aria-hidden="true">
      <div v-if="motion.kind === 'fund'" class="motion-card"><small>FUND</small><strong>$</strong></div>
      <div v-else-if="motion.kind === 'envelope' || motion.kind === 'transfer'" class="motion-envelope"><i /></div>
      <div v-else-if="motion.kind === 'luxury'" class="motion-luxury">◆</div>
      <div v-else-if="motion.kind === 'market'" class="motion-market-card">REMOVED</div>
      <div v-else-if="motion.kind === 'industry'" class="motion-industry">产</div>
      <div v-else-if="motion.kind === 'cash'" class="motion-cash">$</div>
      <div v-else-if="motion.kind === 'wheel'" class="motion-wheel">↻</div>
      <div v-else-if="motion.kind === 'marker'" class="motion-marker">起</div>
      <div v-else-if="motion.kind === 'crash'" class="motion-crash-label">MARKET CRASH</div>
      <div v-else class="motion-bankruptcy">BANKRUPT</div>
    </div>
    <p class="motion-announcer" aria-live="polite">{{ motion?.message }}</p>
    <header class="table-header">
      <div>
        <p class="eyebrow">THE LEDGER ROOM · 第 {{ game.round }} 轮</p>
        <h1>庞氏骗局</h1>
      </div>
      <div class="status-copy" role="status">
        <strong>{{ statusTitle }}</strong>
        <span>{{ statusDetail }}</span>
      </div>
      <div class="header-tools">
        <div class="starter-chip">
          <span>起始玩家</span>
          <b>{{ starterPlayer?.name ?? '—' }}</b>
        </div>
        <button
          type="button"
          class="rulebook-button"
          aria-haspopup="dialog"
          :aria-expanded="showRulebook"
          @click="openRulebook"
        >
          <span aria-hidden="true">▤</span>
          <b>说明书</b>
        </button>
      </div>
    </header>

    <div
      v-if="showRulebook"
      class="rulebook-overlay"
      @click.self="closeRulebook"
      @keydown.esc.stop="closeRulebook"
    >
      <section
        ref="rulebookDialog"
        class="rulebook-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ponzi-rulebook-title"
        tabindex="-1"
      >
        <header>
          <div>
            <span>PLAYER HANDBOOK · BRIGHT EYE STANDARD</span>
            <h2 id="ponzi-rulebook-title">庞氏骗局说明书</h2>
          </div>
          <button type="button" aria-label="关闭说明书" @click="closeRulebook">×</button>
        </header>
        <div class="rulebook-content">
          <div class="rulebook-facts" aria-label="游戏概要">
            <span><b>人数</b>3–5 人</span>
            <span><b>目标</b>撑到骗局崩解并取得最高资本分</span>
            <span><b>保密</b>现金与暗盘报价</span>
          </div>

          <div class="rulebook-columns">
            <ol class="rulebook-phases">
              <li>
                <b>募集资金</b>
                <p>选择一个产业并取得一枚产业牌。该产业的第 1／2／3 枚必须分别搭配市场第 1／2／3 排的资金牌；现金只到账一次，利息会循环到期。</p>
              </li>
              <li>
                <b>暗盘交易</b>
                <p>首轮跳过。之后可放弃、购买一件奢侈品，或向拥有共同产业的玩家秘密报价。收件人必须选择收钱卖出一枚，或支付同额现金反向买入一枚；报价可以是 0。</p>
              </li>
              <li>
                <b>传递标记</b>
                <p>起始玩家标记顺时针传递。新起始玩家移除一张市场资金牌，再把市场补回九张。</p>
              </li>
              <li>
                <b>检查熊市</b>
                <p>熊市牌达到玩家人数时崩盘：重洗熊市牌，每人退回自己数量最多产业中的一枚；并列时任选。本轮时间轮推进两格，否则推进一格。</p>
              </li>
              <li>
                <b>转轮付息</b>
                <p>合计所有到达或越过箭头的利息并一次付清。现金恰好付至 0 仍可存活；少一元也会立即破产并触发终局。</p>
              </li>
            </ol>

            <aside class="rulebook-scoring">
              <h3>终局计分</h3>
              <p>破产玩家不参与计分。存活玩家分别计算每种产业：</p>
              <div class="score-track"><span>数量</span><b>0</b><b>1</b><b>2</b><b>3</b><b>4</b><b>5</b></div>
              <div class="score-track"><span>分数</span><b>0</b><b>1</b><b>3</b><b>6</b><b>10</b><b>15</b></div>
              <p>产业分相加后，再加入奢侈品分。总分相同则比较各自金额最高的单张资金牌；仍相同则并列获胜。所有人同时破产时无人获胜。</p>
              <div class="rulebook-callout">
                <b>公开与保密</b>
                <span>产业、资金牌、周期和利息公开；游戏进行中，挡板后的现金只对本人可见，暗盘价格只对交易双方可见。</span>
              </div>
            </aside>
          </div>
        </div>
      </section>
    </div>

    <section class="scene-grid">
      <section class="funding-board" :class="{ 'market-shift': motion?.kind === 'market' || motion?.kind === 'fund' }" aria-label="资金市场">
        <div class="board-title">
          <div>
            <span>FUNDING DESK</span>
            <h2>募集市场</h2>
          </div>
          <div class="bear-meter" :class="{ danger: game.bearCount >= game.playerCount - 1 }">
            <span>熊市</span>
            <b>{{ game.bearCount }} / {{ game.playerCount }}</b>
          </div>
        </div>

        <div class="market-rows">
          <div v-for="(row, rowIndex) in game.marketRows" :key="rowIndex" class="market-row">
            <div class="row-key">
              <span>第 {{ rowIndex + 1 }} 排</span>
              <small>第 {{ rowIndex + 1 }} 枚产业</small>
            </div>
            <button
              v-for="card in row"
              :key="card.id"
              class="fund-card"
              :class="{ bear: card.isBear, starting: card.kind === 'starting', selectable: cardSelectable(card) }"
              :aria-disabled="!cardSelectable(card)"
              :disabled="busy"
              @click="actOnCard(card)"
            >
              <span class="card-code">{{ card.id }}</span>
              <span v-if="card.isBear" class="bear-mark">▼ 熊</span>
              <strong>{{ card.amount }}</strong>
              <span class="card-caption">到账现金</span>
              <span class="interest">利息 {{ card.interest }}</span>
              <span class="period">每 {{ card.period }} 轮</span>
              <small>均压 {{ card.averageBurden }} · {{ card.yieldPercent }}%</small>
            </button>
          </div>
        </div>

        <div class="board-footer">
          <span>抽牌 {{ game.deckCounts.draw }}</span>
          <span>弃牌 {{ game.deckCounts.discard }}</span>
          <span>移出起始牌 {{ game.deckCounts.removedStarting }}</span>
        </div>
      </section>

      <aside class="action-console">
        <div class="console-heading">
          <span>ACTION FOLDER</span>
          <h2>{{ game.stageLabel }}</h2>
        </div>

        <div v-if="legal.fundingOptions?.length" class="action-block funding-action">
          <p>先选择要扩张的产业</p>
          <div class="industry-options">
            <button
              v-for="option in legal.fundingOptions"
              :key="option.industryId"
              :class="{ selected: selectedIndustry === option.industryId }"
              :style="{ '--industry': industryColor(option.industryId) }"
              @click="selectedIndustry = option.industryId"
            >
              <i />
              <span>{{ option.industryName }}</span>
              <small>拿第 {{ option.row }} 排</small>
            </button>
          </div>
          <p class="hint">再点击市场中亮起的资金牌；现金到账一次，利息循环到期。</p>
          <button v-if="legal.canPassFunding" class="quiet-action" @click="send('pass_funding')">放弃募集</button>
        </div>

        <div v-else-if="legal.tradeTargets" class="action-block trade-builder">
          <div v-if="legal.tradeTargets.length">
            <p>选择信封收件人</p>
            <div class="target-list">
              <button
                v-for="target in legal.tradeTargets"
                :key="target.targetId"
                :class="{ selected: selectedTarget === target.targetId }"
                @click="chooseTradeTarget(target)"
              >{{ playerFor(target.targetId)?.name }}</button>
            </div>
            <div v-if="selectedTradeTarget" class="shared-industries">
              <button
                v-for="industryId in selectedTradeTarget.industryIds"
                :key="industryId"
                :class="{ selected: selectedTradeIndustry === industryId }"
                @click="selectedTradeIndustry = industryId"
              >{{ industryName(industryId) }}</button>
            </div>
            <label class="offer-input">
              <span>秘密报价</span>
              <input v-model.number="offer" type="number" min="0" :max="legal.maxOffer" step="1">
              <small>最多 {{ legal.maxOffer }}</small>
            </label>
            <button class="primary-action envelope-button" :disabled="busy" @click="submitOffer">封入现金并递交</button>
          </div>
          <p v-else class="hint">目前没有与你共享产业的玩家。</p>
          <div v-if="game.luxuriesEnabled && game.luxuryMarket.length" class="luxury-shortcut">
            <p>或以本次行动购入奢侈品</p>
            <button
              v-for="luxury in game.luxuryMarket.filter(item => legal.luxuryIds?.includes(item.id))"
              :key="luxury.id"
              @click="send('buy_luxury', { luxuryId: luxury.id })"
            >{{ luxury.name }} · {{ luxury.cost }}</button>
          </div>
          <button v-if="legal.canPassTrade" class="quiet-action" @click="send('pass_trade')">放弃暗盘行动</button>
        </div>

        <div v-else-if="game.pendingTrade" class="action-block sealed-offer">
          <div class="envelope-model"><i /><span>CONFIDENTIAL</span></div>
          <p>
            {{ playerFor(game.pendingTrade.proposerId)?.name }} 提议交易
            <b>{{ game.pendingTrade.industryName }}</b>
          </p>
          <strong v-if="game.pendingTrade.offerKnown" class="offer-value">{{ game.pendingTrade.offer }}</strong>
          <strong v-else class="offer-value hidden">报价保密</strong>
          <div v-if="legal.canAcceptOffer" class="response-grid">
            <button class="primary-action" @click="send('accept_offer')">收下现金 · 卖出 1 枚</button>
            <button :disabled="!legal.canCounterOffer" @click="send('counter_offer')">补入等额 · 反向买入</button>
          </div>
          <small v-if="legal.canAcceptOffer && !legal.canCounterOffer">你的现金不足以反向收购，但仍可选择卖出。</small>
        </div>

        <div v-else-if="legal.discardMarketCardIds?.length" class="action-block prune-action">
          <p>点击市场中的任意资金牌将它移除。</p>
          <div class="process-strip"><span>传标记</span><i>→</i><span>移除 1 张</span><i>→</i><span>检查熊市</span></div>
        </div>

        <div v-else-if="legal.discardIndustryIds?.length" class="action-block crash-action">
          <strong>市场崩盘</strong>
          <p>从数量最多的产业中退回一枚：</p>
          <button
            v-for="industryId in legal.discardIndustryIds"
            :key="industryId"
            @click="send('discard_industry', { industryId })"
          >弃置{{ industryName(industryId) }}</button>
        </div>

        <div v-else class="action-block waiting-action">
          <div class="stamp">WAIT</div>
          <p>{{ statusTitle }}</p>
          <small>所有公开资产仍可在桌面检查；挡板后的现金不会显示。</small>
        </div>
      </aside>
    </section>

    <section class="component-rail">
      <div class="industry-bank">
        <h2>产业牌库</h2>
        <article
          v-for="industry in game.industryCatalog"
          :key="industry.id"
          :style="{ '--industry': industry.color }"
        >
          <i class="tile-icon">{{ industry.shortName.slice(0, 1) }}</i>
          <span>{{ industry.name }}</span>
          <b>{{ industry.remaining }} / {{ industry.supply }}</b>
        </article>
      </div>
      <div class="luxury-bank">
        <h2>奢侈品陈列柜</h2>
        <div>
          <article v-for="luxury in game.luxuryMarket" :key="luxury.id">
            <i :class="`luxury-icon ${luxury.icon}`" />
            <span>{{ luxury.name }}</span>
            <b>{{ luxury.cost }} / {{ luxury.points }} 分</b>
          </article>
          <p v-if="!game.luxuryMarket.length">陈列柜已空</p>
        </div>
      </div>
    </section>

    <section class="private-desk">
      <div class="player-screen">
        <span>PRIVATE LEDGER</span>
        <strong>{{ props.snapshot.self.name }} 的挡板</strong>
        <small>现金与暗盘报价在游戏进行中保密</small>
      </div>
      <div class="cash-tray">
        <span class="tray-title">挡板后现金</span>
        <strong>{{ myLedger?.cash ?? '—' }}</strong>
        <div class="banknotes">
          <i
            v-for="bill in cashBills"
            :key="bill.value"
            class="banknote"
            :class="`note-${bill.value}`"
          ><b>{{ bill.value }}</b><small>×{{ bill.count }}</small></i>
          <em v-if="!cashBills.length">空</em>
        </div>
      </div>
      <div class="time-wheel-wrap">
        <div class="time-wheel" :class="{ double: game.wheelAdvance === 2 }" :style="{ '--wheel': visualWheelPosition }">
          <div class="wheel-center">
            <span>TIME</span>
            <b>轮</b>
            <small>{{ game.wheelAdvance === 2 ? '崩盘 +2' : '每轮 +1' }}</small>
          </div>
          <div v-for="slot in 5" :key="slot" class="wheel-slot" :class="`slot-${slot}`">
            <span>{{ slot }}</span>
            <b v-if="wheelCards(myLedger, slot).length">{{ wheelCards(myLedger, slot).length }} 张</b>
          </div>
        </div>
        <i class="due-arrow">到期</i>
      </div>
      <div class="my-liability">
        <span>下轮到期</span>
        <strong>{{ myLedger?.interestDueNext ?? 0 }}</strong>
        <small>循环总利息 {{ myLedger?.cycleInterest ?? 0 }}</small>
      </div>
    </section>

    <section v-if="game.settlement" class="settlement-panel" aria-label="终局结算">
      <header>
        <div><span>FINAL AUDIT</span><h2>终局结算</h2></div>
        <p>{{ game.settlement.reason }}</p>
      </header>
      <div class="settlement-grid">
        <article
          v-for="row in game.settlement.rows"
          :key="row.playerId"
          :class="{ winner: row.winner, bankrupt: row.bankrupt }"
        >
          <b class="result-rank">{{ row.bankrupt ? '破产' : `#${row.rank}` }}</b>
          <strong>{{ playerFor(row.playerId)?.name }}</strong>
          <template v-if="!row.bankrupt">
            <span>产业 {{ row.industryScore }}</span>
            <span v-if="row.luxuryScore !== null">奢侈品 {{ row.luxuryScore }}</span>
            <span v-else>财富 {{ row.wealthScore }}</span>
            <span>最高资金牌 {{ row.highestFund }}</span>
            <em>{{ row.total }} 分</em>
          </template>
          <span v-else>未参与胜负计分</span>
        </article>
      </div>
    </section>

    <section class="ledgers-section">
      <div class="section-title">
        <div><span>PUBLIC BOOKS</span><h2>玩家公开账簿</h2></div>
        <small>资金牌与产业公开 · 现金由挡板遮住</small>
      </div>
      <div class="ledger-scroll">
        <article
          v-for="ledger in game.ledgers"
          :key="ledger.playerId"
          class="player-ledger"
          :class="{ active: game.currentPlayerId === ledger.playerId, bankrupt: ledger.bankrupt }"
        >
          <header>
            <div>
              <span v-if="game.starterPlayerId === ledger.playerId" class="starter-dot">起</span>
              <strong>{{ playerFor(ledger.playerId)?.name }}</strong>
            </div>
            <b v-if="ledger.finalScore !== null">{{ ledger.finalScore }} 分</b>
            <span v-else-if="ledger.cashHidden" class="screen-mini">现金 ▧</span>
            <b v-else>现金 {{ ledger.cash }}</b>
          </header>
          <div class="tile-piles">
            <span
              v-for="(count, industryId) in ledger.industries"
              :key="industryId"
              :style="{ '--industry': industryColor(industryId as IndustryId) }"
              :title="industryName(industryId as IndustryId)"
            ><i />{{ industryName(industryId as IndustryId) }} {{ count }}</span>
          </div>
          <div class="fund-stack">
            <span v-if="!ledger.funds.length" class="empty-funds">尚无贷款</span>
            <i
              v-for="fund in ledger.funds.slice(0, 8)"
              :key="fund.id"
              :class="{ bear: fund.isBear, due: fund.dueIn === 1 }"
              :title="`贷款 ${fund.amount} / 利息 ${fund.interest} / ${fund.dueIn} 轮后到期`"
            >
              <span class="fund-amount">{{ fund.amount }}</span>
              <small class="fund-due-rounds" :aria-label="`${fund.dueIn} 轮后还款`">
                <b>{{ fund.dueIn }}</b><span>轮</span>
              </small>
            </i>
            <em v-if="ledger.funds.length > 8">+{{ ledger.funds.length - 8 }}</em>
          </div>
          <footer>
            <span>贷款 {{ ledger.fundCount }}</span>
            <span>下轮利息 {{ ledger.interestDueNext }}</span>
            <span>奢侈品 {{ ledger.luxuries.length }}</span>
          </footer>
          <div v-if="ledger.bankrupt" class="bankrupt-stamp">BANKRUPT</div>
        </article>
      </div>
    </section>

    <section class="event-tape" aria-label="公开事件记录">
      <div v-for="event in game.events.slice(-8).reverse()" :key="event.seq">
        <span>#{{ event.seq }}</span><p>{{ event.message }}</p>
      </div>
    </section>

    <button v-if="legal.canResign && props.snapshot.phase === 'playing'" class="resign" @click="send('resign')">宣告破产并退出</button>
  </main>
</template>

<style scoped>
.ponzi-table {
  --ink: #241f1a;
  --paper: #e9ddc2;
  --paper-deep: #c8b58e;
  --navy: #1f3440;
  --red: #8f3d36;
  --gold: #b68a43;
  width: 100%;
  min-height: calc(100dvh - 88px);
  box-sizing: border-box;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: clamp(14px, 2vw, 28px);
  color: var(--ink);
  background:
    radial-gradient(circle at 15% 10%, #445d56 0 1px, transparent 2px),
    radial-gradient(circle at 80% 75%, #203f39 0 1px, transparent 2px),
    linear-gradient(135deg, #17332e, #102824 58%, #0b201e);
  background-size: 31px 31px, 43px 43px, auto;
  font-family: Inter, "Noto Serif SC", "Microsoft YaHei", sans-serif;
}

.motion-announcer {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.motion-layer {
  position: absolute;
  z-index: 30;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.motion-layer > div { position: absolute; filter: drop-shadow(0 8px 10px #07100dcc); }
.motion-card, .motion-market-card {
  top: 17%; left: 42%; display: grid; place-items: center; width: 76px; height: 105px;
  color: #2a2922; background: linear-gradient(145deg, #f1ead8, #cdbf9d); border: 2px solid #69583c; border-radius: 5px;
}
.motion-card { animation: fund-flight 1.05s cubic-bezier(.25, .8, .25, 1) both; }
.motion-card small { font: 800 8px/1 ui-monospace, monospace; letter-spacing: .12em; }
.motion-card strong { font: 800 36px/1 Georgia, serif; }
.motion-market-card { animation: market-exit 1.05s ease-in both; font: 800 8px/1 ui-monospace, monospace; }
.motion-envelope {
  top: 25%; left: 73%; width: 112px; height: 70px; background: #d0b989; border: 2px solid #f2dfad;
  clip-path: polygon(0 10%, 50% 0, 100% 10%, 100% 100%, 0 100%);
  animation: envelope-flight 1.05s cubic-bezier(.32, .75, .23, 1) both;
}
.cue-transfer .motion-envelope { animation-direction: reverse; }
.motion-envelope i { position: absolute; left: 42px; top: 24px; width: 28px; height: 28px; background: #873b35; border: 5px double #d9a06f; border-radius: 50%; }
.motion-luxury { top: 32%; right: 20%; color: #f0cf7d; font: 900 86px/1 Georgia, serif; animation: luxury-glint 1.05s ease-out both; }
.motion-industry { top: 47%; left: 32%; display: grid; place-items: center; width: 62px; height: 62px; color: #f4ead2; background: #8d9b72; border: 5px double #e5d9b8; border-radius: 50%; animation: industry-drop 1.05s ease-in both; }
.motion-cash { top: 54%; left: 46%; display: grid; place-items: center; width: 92px; height: 48px; color: #26342f; background: #9bbd91; border: 2px solid #e4d9bd; font: 900 30px/1 Georgia, serif; animation: cash-payment 1.05s ease-in both; }
.motion-wheel { top: 52%; left: 67%; color: #e7c877; font: 900 92px/1 Georgia, serif; animation: wheel-cue 1.05s ease-out both; }
.motion-marker { top: 11%; left: 80%; display: grid; place-items: center; width: 54px; height: 54px; color: #f6ead0; background: #9b443a; border: 4px double #e2c99c; border-radius: 50%; font-weight: 900; animation: marker-pass 1.05s ease-in-out both; }
.motion-crash-label, .motion-bankruptcy {
  top: 20%; left: 50%; padding: 20px 30px; color: #9e3029; background: #e3d2b5e8; border: 8px double #9e3029;
  font: 900 clamp(28px, 5vw, 72px)/1 ui-monospace, monospace; letter-spacing: .05em; white-space: nowrap;
  animation: stamp-down 1.05s cubic-bezier(.2, .85, .25, 1.25) both;
}
.motion-bankruptcy { top: 55%; font-size: clamp(24px, 4vw, 56px); }
.is-crashing::after { content: ''; position: absolute; z-index: 29; inset: 0; background: #791e193d; pointer-events: none; animation: crash-flash 1.05s ease-out both; }
.market-shift .fund-card { animation: market-settle .42s ease-out both; }

button, input { font: inherit; }
button { color: inherit; }

.table-header, .funding-board, .action-console, .component-rail, .private-desk, .ledgers-section, .event-tape {
  box-shadow: 0 12px 28px #06120f66, inset 0 0 0 1px #fff4d31f;
}

.table-header {
  display: grid;
  grid-template-columns: minmax(180px, .8fr) minmax(260px, 1.5fr) auto;
  gap: 24px;
  align-items: center;
  padding: 18px 22px;
  color: #f5ead1;
  background: linear-gradient(110deg, #17252b, #263f45);
  border: 1px solid #bea66f66;
  border-radius: 4px;
}

.eyebrow, .console-heading > span, .section-title span, .player-screen > span {
  margin: 0 0 4px;
  color: #c9aa68;
  font-size: 10px;
  letter-spacing: .22em;
}

h1, h2, p { margin: 0; }
h1 { font: 700 clamp(26px, 3vw, 42px)/1.05 Georgia, "Noto Serif SC", serif; letter-spacing: .08em; }
h2 { font: 700 20px/1.2 Georgia, "Noto Serif SC", serif; }

.status-copy { display: flex; flex-direction: column; gap: 5px; padding-left: 20px; border-left: 1px solid #d9c59844; }
.status-copy strong { font-size: 16px; }
.status-copy span { color: #c8c8bc; font-size: 12px; }
.header-tools { display: flex; align-items: stretch; justify-content: flex-end; gap: 8px; }
.starter-chip { display: flex; flex-direction: column; min-width: 116px; padding: 10px 14px; text-align: center; background: #d6c393; color: #2c2a24; clip-path: polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%); }
.starter-chip span { font-size: 10px; letter-spacing: .12em; }
.starter-chip b { font-size: 14px; }
.rulebook-button { display: grid; grid-template-columns: auto auto; place-items: center; gap: 6px; min-width: 94px; padding: 8px 12px; color: #f2e6cb; background: #ffffff0a; border: 1px solid #c9aa6877; border-radius: 3px; cursor: pointer; }
.rulebook-button:hover, .rulebook-button:focus-visible { color: #1d2928; background: #d7c393; outline: 2px solid #f2dca7; outline-offset: 2px; }
.rulebook-button span { color: #d8b96e; font-size: 20px; line-height: 1; }
.rulebook-button:hover span, .rulebook-button:focus-visible span { color: #704c25; }
.rulebook-button b { font-size: 12px; letter-spacing: .08em; }

.rulebook-overlay { position: fixed; z-index: 80; inset: 0; display: grid; place-items: center; padding: clamp(12px, 3vw, 40px); background: #06110edb; backdrop-filter: blur(5px); }
.rulebook-dialog { width: min(920px, 96vw); max-height: min(900px, 92dvh); display: flex; flex-direction: column; overflow: hidden; color: #2b271f; background: #e5d8ba; border: 5px double #9d804a; border-radius: 4px; box-shadow: 0 26px 80px #000c; }
.rulebook-dialog:focus { outline: none; }
.rulebook-dialog > header { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 18px 22px; color: #f2e5c8; background: linear-gradient(110deg, #182b2c, #263f41); border-bottom: 1px solid #b99658; }
.rulebook-dialog > header span { color: #c9aa68; font: 700 9px/1.2 ui-monospace, monospace; letter-spacing: .15em; }
.rulebook-dialog > header h2 { margin-top: 5px; font-size: 25px; }
.rulebook-dialog > header button { flex: 0 0 auto; width: 38px; height: 38px; color: #eadbbd; background: #ffffff0a; border: 1px solid #c9aa6877; border-radius: 50%; cursor: pointer; font-size: 26px; line-height: 1; }
.rulebook-dialog > header button:hover, .rulebook-dialog > header button:focus-visible { color: #263635; background: #dbc99f; outline: 2px solid #f4dda6; }
.rulebook-content { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 18px 22px 24px; background: linear-gradient(#ebdfc5ee, #d4c19bee), repeating-linear-gradient(90deg, transparent 0 23px, #44331d0d 24px); }
.rulebook-facts { display: grid; grid-template-columns: .55fr 1.6fr 1fr; gap: 8px; margin-bottom: 17px; }
.rulebook-facts span { padding: 8px 10px; background: #263b3a; color: #eee3ca; font-size: 11px; }
.rulebook-facts b { display: block; margin-bottom: 2px; color: #cdb06d; font-size: 8px; letter-spacing: .14em; }
.rulebook-columns { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(250px, .8fr); gap: 18px; }
.rulebook-phases { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; counter-reset: rule-phase; }
.rulebook-phases li { position: relative; min-height: 66px; padding: 11px 12px 11px 48px; background: #f4ead6aa; border-left: 3px solid #876d3f; counter-increment: rule-phase; }
.rulebook-phases li::before { content: counter(rule-phase); position: absolute; left: 12px; top: 12px; display: grid; place-items: center; width: 25px; height: 25px; color: #f3e7cc; background: #243a39; border-radius: 50%; font: 800 11px/1 Georgia, serif; }
.rulebook-phases b { color: #3f382a; font-size: 13px; }
.rulebook-phases p, .rulebook-scoring p { margin-top: 4px; color: #5e5545; font-size: 11px; line-height: 1.55; }
.rulebook-scoring { align-self: start; padding: 15px; color: #ede2ca; background: #203233; border-top: 4px solid #b58b43; }
.rulebook-scoring h3 { margin: 0 0 8px; color: #e6cb8a; font: 700 18px/1.2 Georgia, "Noto Serif SC", serif; }
.rulebook-scoring p { color: #cbc5b6; }
.score-track { display: grid; grid-template-columns: 42px repeat(6, 1fr); gap: 2px; margin-top: 8px; text-align: center; }
.score-track span, .score-track b { display: grid; place-items: center; min-height: 25px; background: #ffffff0b; font-size: 9px; }
.score-track span { color: #cbb174; }
.rulebook-callout { display: grid; gap: 4px; margin-top: 13px; padding: 10px; color: #30291f; background: #d9c69b; border: 1px solid #f0ddb0; }
.rulebook-callout b { font-size: 11px; }
.rulebook-callout span { font-size: 10px; line-height: 1.5; }

.scene-grid { display: grid; grid-template-columns: minmax(0, 1fr) clamp(310px, 23vw, 380px); gap: 16px; margin-top: 16px; }
.funding-board { padding: 18px; background: linear-gradient(#e8dcc1f5, #cbbb9bf5), repeating-linear-gradient(90deg, transparent 0 23px, #44331d12 24px); border: 4px double #725e3d; border-radius: 6px; }
.board-title { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 12px; border-bottom: 2px solid #4d4230; }
.board-title span { font: 700 9px/1.2 ui-monospace, monospace; letter-spacing: .2em; }
.bear-meter { min-width: 88px; padding: 6px 10px; text-align: center; color: #f3e4c5; background: #293c3d; border-radius: 2px; }
.bear-meter span, .bear-meter b { display: block; }
.bear-meter.danger { background: var(--red); animation: warning 1.4s ease-in-out infinite; }

.market-rows { display: grid; gap: 10px; padding-top: 12px; }
.market-row { display: grid; grid-template-columns: 76px repeat(3, minmax(94px, 1fr)); gap: 9px; align-items: stretch; }
.row-key { display: flex; flex-direction: column; justify-content: center; color: #584c37; border-right: 1px solid #5b4b2a66; }
.row-key span { font-weight: 800; }
.row-key small { font-size: 10px; }
.fund-card { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 1px 8px; min-height: 118px; padding: 10px; overflow: hidden; color: var(--ink); text-align: left; background: linear-gradient(145deg, #f1ead8, #d8ceb4); border: 1px solid #4d483c; border-radius: 5px; box-shadow: 2px 3px 0 #5a4a3066; cursor: default; transition: transform .15s, box-shadow .15s; }
.fund-card::after { content: ''; position: absolute; inset: 4px; border: 1px solid #645c493d; pointer-events: none; }
.fund-card.starting { background: linear-gradient(145deg, #e4e9df, #c4cfc1); }
.fund-card.bear { color: #f3e7d2; background: linear-gradient(145deg, #603d39, #2d2929); }
.fund-card.selectable { cursor: pointer; outline: 3px solid #b7893d; outline-offset: 1px; }
.fund-card.selectable:hover { transform: translateY(-3px) rotate(-.3deg); box-shadow: 4px 7px 0 #5a4a3055; }
.card-code { z-index: 1; font: 700 9px/1 ui-monospace, monospace; opacity: .65; }
.bear-mark { z-index: 1; color: #edb46d; font-size: 10px; font-weight: 800; }
.fund-card > strong { z-index: 1; grid-column: 1 / -1; font: 700 34px/1 Georgia, serif; }
.card-caption { z-index: 1; grid-column: 1 / -1; font-size: 9px; letter-spacing: .16em; }
.interest, .period { z-index: 1; font-size: 12px; font-weight: 800; }
.period { text-align: right; }
.fund-card > small { z-index: 1; grid-column: 1 / -1; opacity: .7; font-size: 9px; }
.board-footer { display: flex; gap: 18px; margin-top: 12px; padding-top: 9px; border-top: 1px solid #4d423055; font: 600 10px/1 ui-monospace, monospace; }

.action-console { display: flex; flex-direction: column; min-height: 520px; color: #ede2c9; background: #202c2d; border: 1px solid #a98b5366; border-radius: 5px; }
.console-heading { padding: 18px; border-bottom: 1px solid #d0bd8b33; }
.action-block { display: flex; flex: 1; flex-direction: column; gap: 13px; padding: 18px; }
.action-block p { font-size: 13px; line-height: 1.5; }
.action-block .hint, .action-block small { color: #b8b7aa; font-size: 11px; line-height: 1.45; }
.industry-options { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.industry-options button, .target-list button, .shared-industries button, .luxury-shortcut button, .crash-action button, .response-grid button, .quiet-action, .primary-action {
  padding: 9px; color: #eee5d2; background: #ffffff0b; border: 1px solid #cfbd8f44; border-radius: 3px; cursor: pointer;
}
.industry-options button { display: grid; grid-template-columns: 8px 1fr; text-align: left; }
.industry-options i { grid-row: 1 / 3; width: 6px; height: 100%; background: var(--industry); }
.industry-options span { font-size: 12px; font-weight: 700; }
.industry-options small { font-size: 9px; }
.action-block button.selected { color: #1e2524; background: #d7c79f; border-color: #e7dcbf; }
.quiet-action { margin-top: auto; }
.primary-action { color: #182421 !important; background: #d0b573 !important; border-color: #e0cc98 !important; font-weight: 800; }
.target-list, .shared-industries { display: flex; flex-wrap: wrap; gap: 6px; }
.offer-input { display: grid; grid-template-columns: 1fr 92px; gap: 6px; align-items: center; }
.offer-input input { width: 100%; padding: 8px; color: #f4ead4; background: #101918; border: 1px solid #b99d64; border-radius: 3px; }
.offer-input small { grid-column: 2; }
.envelope-button { clip-path: polygon(0 7px, 50% 0, 100% 7px, 100% 100%, 0 100%); padding-top: 14px; }
.luxury-shortcut { display: grid; gap: 6px; padding-top: 10px; border-top: 1px dashed #d2bd8555; }
.luxury-shortcut button { text-align: left; font-size: 11px; }
.envelope-model { position: relative; height: 112px; color: #2b2420; background: #d0b989; border: 1px solid #f2dfad; box-shadow: 0 8px 16px #0005; }
.envelope-model::before, .envelope-model::after { content: ''; position: absolute; top: 0; width: 52%; height: 60%; background: #bea675; clip-path: polygon(0 0, 100% 0, 50% 100%); }
.envelope-model::before { left: 0; }
.envelope-model::after { right: 0; transform: scaleX(-1); }
.envelope-model i { position: absolute; z-index: 1; left: calc(50% - 20px); top: 34px; width: 40px; height: 40px; background: #873b35; border-radius: 50%; box-shadow: inset 0 0 0 6px #6a2927; }
.envelope-model span { position: absolute; bottom: 10px; left: 0; right: 0; text-align: center; font: 800 9px/1 ui-monospace; letter-spacing: .18em; }
.offer-value { font: 700 38px/1 Georgia, serif; text-align: center; }
.offer-value.hidden { font-size: 22px; letter-spacing: .12em; }
.response-grid { display: grid; gap: 8px; }
.response-grid button:disabled { opacity: .4; cursor: not-allowed; }
.process-strip { display: flex; align-items: center; justify-content: space-between; font-size: 10px; }
.crash-action > strong { color: #ef9b82; font: 800 25px/1 Georgia, serif; }
.stamp { align-self: center; margin-top: auto; padding: 16px; color: #c9aa68; border: 4px double #c9aa68; transform: rotate(-7deg); font: 800 26px/1 ui-monospace; opacity: .65; }

.component-rail { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; margin-top: 16px; padding: 16px 18px; background: #d7c7a7; border-radius: 4px; }
.component-rail h2 { margin-bottom: 10px; font-size: 16px; }
.industry-bank { min-width: 0; }
.industry-bank > article { display: inline-grid; grid-template-columns: 32px 1fr; min-width: 150px; margin: 0 6px 6px 0; padding: 7px; vertical-align: top; background: #f0e7d4; border-left: 5px solid var(--industry); }
.industry-bank article span, .industry-bank article b { font-size: 10px; }
.tile-icon { grid-row: 1 / 3; display: grid; place-items: center; width: 26px; height: 26px; color: white; background: var(--industry); border-radius: 50%; font-style: normal; }
.luxury-bank > div { display: flex; gap: 7px; overflow-x: auto; }
.luxury-bank article { display: grid; min-width: 104px; padding: 8px; background: #25393c; color: #f2e4c7; border-top: 3px solid var(--gold); }
.luxury-bank article span, .luxury-bank article b { font-size: 10px; }
.luxury-icon { width: 25px; height: 18px; margin-bottom: 5px; border: 2px solid #c5a563; border-radius: 50%; }
.luxury-icon.car { border-radius: 10px 10px 3px 3px; }
.luxury-icon.yacht { clip-path: polygon(0 40%, 100% 40%, 78% 100%, 18% 100%); background: #c5a563; border: 0; }
.luxury-icon.column { border-width: 0 6px; border-radius: 0; }

.private-desk { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(180px, .9fr) 230px 130px; align-items: center; gap: 18px; margin-top: 16px; padding: 18px; color: #e8ddc6; background: linear-gradient(100deg, #263b3b, #172c2b); border: 1px solid #b9985f55; border-radius: 5px; }
.player-screen { display: flex; flex-direction: column; min-height: 92px; justify-content: center; padding: 12px 20px; background: linear-gradient(135deg, #344c50, #1c3236); border: 2px solid #af975e; clip-path: polygon(6% 0, 94% 0, 100% 100%, 0 100%); text-align: center; }
.player-screen small { color: #b9beb4; font-size: 9px; }
.cash-tray { min-width: 0; }
.cash-tray > strong { display: block; font: 700 28px/1 Georgia, serif; }
.tray-title { color: #bdad88; font-size: 10px; }
.banknotes { display: flex; gap: 5px; margin-top: 8px; }
.banknote { display: grid; place-items: center; width: 48px; height: 25px; color: #20302d; background: #9bbd91; border: 1px solid #e1d7bd; box-shadow: 2px 2px 0 #0b191755; font-style: normal; }
.banknote b { font: 800 12px/1 Georgia, serif; }
.banknote small { font-size: 7px; }
.note-5 { background: #d0a45c; }.note-10 { background: #b76765; color: #fff1dc; }.note-20 { background: #6086a6; color: #fff1dc; }
.time-wheel-wrap { position: relative; width: 220px; height: 204px; margin: -8px auto; }
.time-wheel { position: relative; width: 190px; height: 190px; margin-left: 13px; border-radius: 50%; background: repeating-conic-gradient(#c7b47f 0 10deg, #d8c99f 10deg 72deg); border: 7px solid #9a7d48; box-shadow: inset 0 0 0 2px #f2e5bd, 0 7px 14px #0007; transform: rotate(calc(var(--wheel, 0) * 72deg)); transition: transform .72s cubic-bezier(.2, .8, .2, 1); }
.time-wheel.double { box-shadow: inset 0 0 0 2px #f2e5bd, 0 0 0 4px #a84b3f, 0 7px 14px #0007; }
.wheel-center { position: absolute; inset: 53px; display: grid; place-items: center; padding: 8px; color: #ead9b6; background: #26383a; border: 2px solid #9e8150; border-radius: 50%; text-align: center; }
.wheel-center span { font-size: 7px; letter-spacing: .12em; }.wheel-center b { font: 700 22px/1 Georgia, serif; }.wheel-center small { font-size: 7px; }
.wheel-slot { position: absolute; display: grid; place-items: center; width: 38px; height: 38px; color: #2b2a24; background: #ede2c5dd; border: 1px solid #745f3d; border-radius: 50%; font-style: normal; }
.wheel-slot span { font-weight: 900; font-size: 11px; }.wheel-slot b { font-size: 7px; }
.slot-1 { left: 76px; top: 8px; }.slot-2 { right: 15px; top: 50px; }.slot-3 { right: 32px; bottom: 15px; }.slot-4 { left: 32px; bottom: 15px; }.slot-5 { left: 15px; top: 50px; }
.due-arrow { position: absolute; z-index: 2; left: -2px; top: 88px; color: #efc879; font: 800 9px/1 sans-serif; font-style: normal; transform: rotate(-90deg); }
.my-liability { text-align: center; }
.my-liability span, .my-liability small { display: block; font-size: 10px; color: #bdb7a7; }
.my-liability strong { display: block; color: #e6bd73; font: 700 34px/1 Georgia, serif; }

.ledgers-section { margin-top: 16px; padding: 17px; background: #1d3030; border-radius: 5px; }
.section-title { display: flex; justify-content: space-between; align-items: end; color: #eee2c9; margin-bottom: 12px; }
.section-title small { color: #aeb4aa; font-size: 10px; }
.ledger-scroll { display: grid; grid-template-columns: repeat(auto-fit, minmax(215px, 1fr)); gap: 10px; }
.player-ledger { position: relative; min-width: 0; padding: 11px; overflow: hidden; color: #2b2923; background: #dfd1b6; border: 2px solid transparent; border-radius: 3px; }
.player-ledger.active { border-color: #d1a755; box-shadow: 0 0 18px #d1a75544; }
.player-ledger.bankrupt { filter: grayscale(.7); opacity: .78; }
.player-ledger header, .player-ledger footer { display: flex; justify-content: space-between; align-items: center; gap: 7px; }
.starter-dot { display: inline-grid; place-items: center; width: 22px; height: 22px; margin-right: 4px; color: white; background: #9b443a; border-radius: 50%; font-size: 9px; }
.screen-mini { padding: 4px 8px; color: #ddd2b7; background: #31474a; font-size: 9px; }
.tile-piles { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin: 10px 0; }
.tile-piles span { display: flex; align-items: center; gap: 4px; padding: 4px; background: #fff7e9aa; font-size: 9px; }
.tile-piles i { width: 5px; height: 14px; background: var(--industry); }
.fund-stack { display: flex; flex-wrap: wrap; min-height: 48px; align-items: end; align-content: end; gap: 4px; overflow: visible; }
.fund-stack > i { position: relative; display: flex; align-items: flex-start; justify-content: center; width: 34px; height: 46px; box-sizing: border-box; padding-top: 8px; color: #242620; background: #f0e8d7; border: 1px solid #77705f; border-radius: 2px; font: 700 13px/1 Georgia, serif; font-style: normal; }
.fund-stack > i.bear { color: #f0dfc1; background: #593a36; }.fund-stack > i.due { outline: 2px solid #b04135; }
.fund-due-rounds { position: absolute; right: 2px; bottom: 2px; display: flex; min-width: 24px; height: 19px; box-sizing: border-box; align-items: baseline; justify-content: center; gap: 1px; padding: 2px 3px; color: #f5e8cc; background: #263c3b; border: 1px solid #aa8c55; border-radius: 2px; box-shadow: 0 1px 2px #0005; }
.fund-due-rounds b { font: 900 14px/1 Georgia, serif; }
.fund-due-rounds span { font: 800 7px/1 "Microsoft YaHei", sans-serif; }
.fund-stack > i.bear .fund-due-rounds { color: #2b2720; background: #d2b66e; border-color: #f0d99c; }
.empty-funds { align-self: center; color: #7d7566; font-size: 9px; }
.player-ledger footer { margin-top: 9px; padding-top: 7px; border-top: 1px solid #6a5e4938; font-size: 8px; }
.bankrupt-stamp { position: absolute; inset: 38% 12%; display: grid; place-items: center; color: #9a362f; border: 4px double #9a362f; font: 900 18px/1 ui-monospace; transform: rotate(-12deg); background: #e2d5baaa; animation: ledger-stamp .5s cubic-bezier(.2, .9, .25, 1.3) both; }

.settlement-panel { margin-top: 16px; padding: 18px; color: #f1e5cd; background: linear-gradient(120deg, #17282a, #263c3d); border: 2px solid #b99455; box-shadow: 0 12px 28px #06120f88; }
.settlement-panel > header { display: grid; grid-template-columns: auto 1fr; gap: 24px; align-items: end; padding-bottom: 12px; border-bottom: 1px solid #d7bd8444; }
.settlement-panel > header span { color: #c9aa68; font-size: 9px; letter-spacing: .2em; }
.settlement-panel > header p { justify-self: end; color: #d0c7b4; font-size: 12px; text-align: right; }
.settlement-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; margin-top: 12px; }
.settlement-grid article { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 5px 12px; padding: 12px; color: #2e2a22; background: #d9ccb0; border: 2px solid transparent; }
.settlement-grid article.winner { background: linear-gradient(145deg, #f0dfb1, #c9ab65); border-color: #f2d58d; box-shadow: 0 0 20px #e4bd5b44; }
.settlement-grid article.bankrupt { color: #69564e; background: #b8aea1; filter: grayscale(.65); }
.settlement-grid strong { grid-column: 1 / -1; font-size: 16px; }
.settlement-grid span { font-size: 9px; }
.settlement-grid em { grid-row: 2 / span 3; grid-column: 2; align-self: center; font: 800 25px/1 Georgia, serif; font-style: normal; }
.result-rank { position: absolute; top: 8px; right: 9px; color: #8f3d36; font: 900 10px/1 ui-monospace, monospace; }

.event-tape { display: flex; gap: 6px; margin-top: 16px; padding: 10px; overflow-x: auto; background: #e4d8be; }
.event-tape > div { display: flex; min-width: 220px; gap: 8px; padding: 7px; border-right: 1px dashed #73675266; }
.event-tape span { font: 700 9px/1 ui-monospace; color: #8d3d35; }.event-tape p { font-size: 10px; }
.resign { display: block; margin: 14px 0 0 auto; padding: 7px 11px; color: #bdc4ba; background: transparent; border: 1px solid #bdc4ba55; border-radius: 3px; cursor: pointer; font-size: 10px; }

@keyframes warning { 50% { box-shadow: 0 0 18px #b34b3d99; } }
@keyframes fund-flight { from { transform: translate3d(0, 0, 0) rotate(0); } 55% { transform: translate3d(5vw, 25vh, 0) rotate(4deg); } to { transform: translate3d(-12vw, 48vh, 0) rotate(-9deg) scale(.55); opacity: 0; } }
@keyframes market-exit { to { transform: translate3d(-35vw, -14vh, 0) rotate(-20deg) scale(.65); opacity: 0; } }
@keyframes envelope-flight { from { transform: translate3d(0, 0, 0) rotate(4deg); } 55% { transform: translate3d(-30vw, 13vh, 0) rotate(-2deg); } to { transform: translate3d(-48vw, 29vh, 0) rotate(2deg); } }
@keyframes luxury-glint { from { transform: scale(.25) rotate(-30deg); opacity: 0; } 45% { transform: scale(1.2) rotate(5deg); opacity: 1; } to { transform: scale(.7) rotate(18deg); opacity: 0; } }
@keyframes industry-drop { from { transform: translateY(-25vh) rotate(-25deg); } to { transform: translateY(35vh) rotate(35deg); opacity: 0; } }
@keyframes cash-payment { from { transform: translateY(25vh) scale(.7); } 45% { transform: translateY(0) scale(1.05); } to { transform: translateY(-18vh) scale(.6); opacity: 0; } }
@keyframes wheel-cue { from { transform: rotate(0) scale(.5); opacity: 0; } 45% { opacity: 1; } to { transform: rotate(360deg) scale(1.15); opacity: 0; } }
@keyframes marker-pass { 50% { transform: translateX(-55vw) rotate(360deg); } to { transform: translateX(-70vw) rotate(430deg); opacity: 0; } }
@keyframes stamp-down { from { transform: translate(-50%, -50%) rotate(-18deg) scale(2.5); opacity: 0; } 55% { transform: translate(-50%, -50%) rotate(-7deg) scale(.92); opacity: 1; } to { transform: translate(-50%, -50%) rotate(-9deg) scale(1); opacity: 0; } }
@keyframes crash-flash { 45% { background: #9d2e2778; } to { background: transparent; } }
@keyframes market-settle { from { transform: translateY(-5px); opacity: .65; } to { transform: translateY(0); opacity: 1; } }
@keyframes ledger-stamp { from { transform: rotate(-12deg) scale(2); opacity: 0; } to { transform: rotate(-12deg) scale(1); opacity: 1; } }

@media (max-width: 980px) {
  .scene-grid { grid-template-columns: 1fr; }
  .action-console { min-height: 0; }
  .private-desk { grid-template-columns: 1fr 1fr; }
  .time-wheel-wrap { grid-row: span 2; }
}

@media (max-width: 680px) {
  .ponzi-table { padding: 8px; }
  .table-header { grid-template-columns: 1fr auto; gap: 12px; }
  .header-tools { gap: 5px; }
  .starter-chip { min-width: 92px; padding: 8px 9px; }
  .rulebook-button { min-width: 42px; grid-template-columns: 1fr; gap: 1px; padding: 5px 7px; }
  .rulebook-button span { font-size: 17px; }
  .rulebook-button b { font-size: 9px; }
  .status-copy { grid-column: 1 / -1; grid-row: 2; padding: 10px 0 0; border: 0; border-top: 1px solid #d9c59844; }
  .market-row { grid-template-columns: repeat(3, 1fr); }
  .row-key { grid-column: 1 / -1; border-right: 0; border-bottom: 1px solid #5b4b2a66; }
  .fund-card { min-width: 0; min-height: 108px; padding: 7px; }
  .fund-card > strong { font-size: 27px; }
  .component-rail, .private-desk { grid-template-columns: 1fr; }
  .time-wheel-wrap { grid-row: auto; }
  .section-title { align-items: flex-start; flex-direction: column; gap: 5px; }
  .settlement-panel > header { grid-template-columns: 1fr; gap: 7px; }
  .settlement-panel > header p { justify-self: start; text-align: left; }
  .motion-envelope { left: 64%; }
  .rulebook-overlay { padding: 6px; }
  .rulebook-dialog { width: 100%; max-height: 96dvh; }
  .rulebook-dialog > header { padding: 13px 14px; }
  .rulebook-dialog > header h2 { font-size: 21px; }
  .rulebook-content { padding: 12px; }
  .rulebook-facts, .rulebook-columns { grid-template-columns: 1fr; }
  .rulebook-facts { gap: 4px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
</style>
