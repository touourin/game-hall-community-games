<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import {
  BookOpen, CheckCircle2, Clock3, Crown, Layers3,
  RotateCcw, Send, ShieldCheck, X,
} from '@lucide/vue'
import {
  PluginButton,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import NumberCard from './components/NumberCard.vue'
import type {
  BullAnimationStep,
  BullCard,
  BullPlayerView,
  BullheadGameView,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const selectedCardId = ref<string | null>(null)
const busy = ref(false)
const showRules = ref(false)
const gameRoot = ref<HTMLElement | null>(null)

interface TakeFlightMotion {
  id: string
  playerId: string
  x: number
  y: number
  middleX: number
  middleY: number
  destinationX: number
  destinationY: number
  delayMs: number
}

const takeFlightMotion = ref<TakeFlightMotion | null>(null)

interface CardFlightMotion {
  id: string
  card: BullCard
  x: number
  y: number
  width: number
  middleX: number
  middleY: number
  destinationX: number
  destinationY: number
  delayMs: number
}

const cardFlightMotions = ref<CardFlightMotion[]>([])

const game = computed(() => props.snapshot.game as unknown as BullheadGameView)
const players = computed(() => game.value.players ?? [])
const rows = computed(() => game.value.rows ?? [])
const hand = computed(() => game.value.hand ?? [])
const selectedCard = computed(() => (
  hand.value.find(card => card.id === selectedCardId.value) ?? null
))
const selfPlayer = computed(() => (
  players.value.find(player => player.id === props.snapshot.self?.id) ?? null
))
const revealPlays = computed(() => {
  const animated = game.value.animation?.revealed ?? []
  return animated.length ? animated : (game.value.revealed ?? [])
})
const animationSteps = computed(() => game.value.animation?.steps ?? [])
const latestTake = computed(() => (
  [...animationSteps.value].reverse().find(step => step.type !== 'place') ?? null
))
const canSubmit = computed(() => (
  game.value.canSelect
  && selectedCard.value !== null
  && !busy.value
  && props.snapshot.phase === 'playing'
))
const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const sortedRankings = computed(() => {
  if (game.value.rankings?.length) {
    return game.value.rankings
      .map(id => players.value.find(player => player.id === id))
      .filter((player): player is BullPlayerView => Boolean(player))
  }
  return [...players.value].sort((left, right) => (
    left.totalPenalty - right.totalPenalty || left.seat - right.seat
  ))
})
const winnerNames = computed(() => (
  (props.snapshot.winnerPlayerIds ?? [])
    .map(id => playerName(id))
    .join('、')
))

const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return '牛头王已经揭晓'
  if (game.value.stage === 'round_summary') return `第 ${game.value.roundNumber} 轮结算完成`
  if (game.value.stage === 'resolving') return '正按牌号从小到大结算'
  if (game.value.committedCard) return `已锁定 ${game.value.committedCard.number}`
  if (game.value.canSelect) return '从手牌中暗选一张'
  return '等待本手所有玩家锁定'
})

const statusDetail = computed(() => {
  if (props.snapshot.phase === 'finished') {
    return props.snapshot.winReason ?? '累计牛头分最低者获胜'
  }
  if (game.value.stage === 'round_summary') {
    return '比较本轮新增分和累计分，准备好后开始下一轮。'
  }
  if (game.value.stage === 'resolving') {
    return revealPlays.value.length
      ? `公开顺序：${revealPlays.value.map(play => play.card.number).join(' → ')}`
      : '服务端正在形成唯一落位结果。'
  }
  if (game.value.committedCard) {
    const waiting = game.value.waitingForPlayerIds?.length ?? 0
    return waiting ? `牌面仅你可见，还差 ${waiting} 人。` : '所有人已锁定，即将公开。'
  }
  return `第 ${game.value.roundNumber} 轮 · 第 ${game.value.turnNumber}/10 手 · 锁定后不能撤回。`
})

watch(
  () => hand.value.map(card => card.id).join('|'),
  () => {
    if (!hand.value.some(card => card.id === selectedCardId.value)) {
      selectedCardId.value = null
    }
  },
)

watch(
  () => `${game.value.roundNumber}:${game.value.turnNumber}`,
  () => { selectedCardId.value = null },
)

function playerName(playerId?: string | null): string {
  if (!playerId) return '当前玩家'
  return players.value.find(player => player.id === playerId)?.name ?? '当前玩家'
}

function cardLabel(card: BullCard): string {
  return `${card.number}，${card.bullheads} 牛头分`
}

function rowPenalty(row: BullCard[]): number {
  return row.reduce((sum, card) => sum + card.bullheads, 0)
}

function stepsForRow(index: number): BullAnimationStep[] {
  return animationSteps.value.filter(step => step.rowIndex === index)
}

function revealDurationMs(): number {
  return 420 + Math.max(0, revealPlays.value.length - 1) * 90
}

function stepStartMs(index: number): number {
  let cursor = revealDurationMs()
  for (let stepIndex = 0; stepIndex < index; stepIndex += 1) {
    cursor += animationSteps.value[stepIndex]?.type === 'place' ? 120 : 760
  }
  return cursor
}

function stepIndexForCard(cardId: string): number {
  return animationSteps.value.findIndex(step => step.card.id === cardId)
}

function cardMotionStyle(cardId: string): Record<string, string> | undefined {
  const index = stepIndexForCard(cardId)
  if (index < 0) return undefined
  const step = animationSteps.value[index]
  const settleOffset = step?.type === 'place' ? 0 : 520
  return { '--card-motion-delay': `${stepStartMs(index) + settleOffset}ms` }
}

function rowMotionStyle(rowIndex: number): Record<string, string> | undefined {
  const index = animationSteps.value.findIndex(step => (
    step.rowIndex === rowIndex && step.type !== 'place'
  ))
  return index < 0
    ? undefined
    : { '--row-motion-delay': `${stepStartMs(index)}ms` }
}

function dealMotionStyle(index: number, zone: 'row' | 'hand'): Record<string, string> {
  const base = zone === 'hand' ? 220 : 0
  return { '--deal-delay': `${base + index * 55}ms` }
}

function rowClasses(index: number) {
  const steps = stepsForRow(index)
  return {
    'row-line--active': steps.length > 0,
    'row-line--taken': steps.some(step => step.type !== 'place'),
  }
}

function revealDelay(index: number) {
  return { '--reveal-delay': `${index * 90}ms` }
}

function flightStyle(motion: TakeFlightMotion): Record<string, string> {
  return {
    '--flight-x': `${motion.x}px`,
    '--flight-y': `${motion.y}px`,
    '--flight-middle-x': `${motion.middleX}px`,
    '--flight-middle-y': `${motion.middleY}px`,
    '--flight-destination-x': `${motion.destinationX}px`,
    '--flight-destination-y': `${motion.destinationY}px`,
    '--flight-delay': `${motion.delayMs}ms`,
  }
}

function cardFlightStyle(motion: CardFlightMotion): Record<string, string> {
  return {
    '--play-flight-x': `${motion.x}px`,
    '--play-flight-y': `${motion.y}px`,
    '--play-flight-width': `${motion.width}px`,
    '--play-flight-middle-x': `${motion.middleX}px`,
    '--play-flight-middle-y': `${motion.middleY}px`,
    '--play-flight-destination-x': `${motion.destinationX}px`,
    '--play-flight-destination-y': `${motion.destinationY}px`,
    '--play-flight-delay': `${motion.delayMs}ms`,
  }
}

async function measureMotionPaths() {
  takeFlightMotion.value = null
  cardFlightMotions.value = []
  await nextTick()
  await new Promise<void>((resolve) => {
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(() => resolve())
      return
    }
    resolve()
  })
  const root = gameRoot.value
  const take = latestTake.value
  if (!root) return
  const takeRowCards = take
    ? root.querySelector<HTMLElement>(`[data-row-index="${take.rowIndex}"] .row-cards`)
    : null
  const playerChip = take
    ? [...root.querySelectorAll<HTMLElement>('[data-player-id]')]
        .find(element => element.dataset.playerId === take.playerId)
    : null
  const playerRail = root.querySelector<HTMLElement>('.player-rail')

  if (take && playerRail && playerChip) {
    const centered = playerChip.offsetLeft
      + playerChip.offsetWidth / 2
      - playerRail.clientWidth / 2
    playerRail.scrollLeft = Math.max(
      0,
      Math.min(centered, playerRail.scrollWidth - playerRail.clientWidth),
    )
  }
  await nextTick()
  const rootRect = root.getBoundingClientRect()
  if (rootRect.width <= 0) return

  cardFlightMotions.value = animationSteps.value.flatMap((step, index) => {
    if (step.type !== 'place') return []
    const source = root.querySelector<HTMLElement>(
      `[data-reveal-card-id="${step.card.id}"]`,
    )
    const target = root.querySelector<HTMLElement>(
      `[data-row-index="${step.rowIndex}"] .row-cards [data-card-id="${step.card.id}"]`,
    )
    const sourceLayoutRoot = source?.closest<HTMLElement>('.reveal-cards')
    const targetLayoutRoot = target?.closest<HTMLElement>('.row-line')
    if (!source || !target || !sourceLayoutRoot || !targetLayoutRoot) return []
    const sourceParentRect = sourceLayoutRoot.getBoundingClientRect()
    const targetParentRect = targetLayoutRoot.getBoundingClientRect()
    if (source.offsetWidth <= 0 || target.offsetWidth <= 0) return []
    const width = Math.min(62, Math.max(42, source.offsetWidth))
    const desiredSourceCenterX = sourceParentRect.left - rootRect.left
      + source.offsetLeft - sourceLayoutRoot.scrollLeft + source.offsetWidth * 0.5
    const sourceCenterX = Math.min(
      sourceParentRect.right - rootRect.left - width * 0.5,
      Math.max(
        sourceParentRect.left - rootRect.left + width * 0.5,
        desiredSourceCenterX,
      ),
    )
    const sourceCenterY = sourceParentRect.top - rootRect.top
      + source.offsetTop - sourceLayoutRoot.scrollTop + source.offsetHeight * 0.42
    const targetCenterX = targetParentRect.left - rootRect.left
      + target.offsetLeft + target.offsetWidth * 0.5
    const targetCenterY = targetParentRect.top - rootRect.top
      + target.offsetTop + target.offsetHeight * 0.5
    const destinationX = targetCenterX - sourceCenterX
    const destinationY = targetCenterY - sourceCenterY
    return [{
      id: step.id,
      card: step.card,
      x: sourceCenterX - width / 2,
      y: sourceCenterY - width * 96 / 68 / 2,
      width,
      middleX: destinationX * 0.52,
      middleY: destinationY * 0.46 - Math.min(46, Math.abs(destinationX) * 0.06 + 18),
      destinationX,
      destinationY,
      delayMs: stepStartMs(index),
    }]
  })

  if (!take || !takeRowCards || !playerChip) return
  const sourceRect = takeRowCards.getBoundingClientRect()
  const targetRect = playerChip.getBoundingClientRect()
  if (sourceRect.width <= 0 || targetRect.width <= 0) return

  const stackWidth = 82
  const stackHeight = 58
  const sourceCenterX = sourceRect.left - rootRect.left + sourceRect.width * 0.52
  const sourceCenterY = sourceRect.top - rootRect.top + sourceRect.height * 0.5
  const targetCenterX = targetRect.left - rootRect.left + targetRect.width * 0.5
  const targetCenterY = targetRect.top - rootRect.top + targetRect.height * 0.5
  const x = sourceCenterX - stackWidth / 2
  const y = sourceCenterY - stackHeight / 2
  const destinationX = targetCenterX - sourceCenterX
  const destinationY = targetCenterY - sourceCenterY
  const stepIndex = animationSteps.value.findIndex(step => step.id === take.id)
  takeFlightMotion.value = {
    id: take.id,
    playerId: take.playerId,
    x,
    y,
    middleX: destinationX * 0.48,
    middleY: destinationY * 0.52 - Math.min(72, Math.abs(destinationX) * 0.08 + 26),
    destinationX,
    destinationY,
    delayMs: stepStartMs(Math.max(0, stepIndex)),
  }
}

watch(
  () => `${game.value.animation?.id ?? 0}:${latestTake.value?.id ?? ''}`,
  measureMotionPaths,
  { immediate: true, flush: 'post' },
)

function selectCard(cardId: string) {
  if (!game.value.canSelect || busy.value) return
  selectedCardId.value = selectedCardId.value === cardId ? null : cardId
}

async function commitCard() {
  if (!canSubmit.value || !selectedCardId.value) return
  busy.value = true
  try {
    await actions.action('select_card', {
      cardId: selectedCardId.value,
      turnNumber: game.value.turnNumber,
    })
    selectedCardId.value = null
  }
  finally {
    busy.value = false
  }
}

async function nextRound() {
  if (!game.value.canStartNextRound || busy.value) return
  busy.value = true
  try {
    await actions.action('next_round', { roundNumber: game.value.roundNumber })
  }
  finally {
    busy.value = false
  }
}
</script>

<template>
  <section
    ref="gameRoot"
    class="bullhead-game"
    data-game="bullhead-king"
    data-layout="browser-fill"
    :data-scene="game.sceneId"
    :data-animation-id="game.animation?.id ?? 0"
  >
    <header class="hero-bar">
      <div class="brand-lockup">
        <span class="horn-emblem" aria-hidden="true"><i /><b /><i /></span>
        <div>
          <small>NUMBER ROWS · LOW SCORE WINS</small>
          <h2>谁是牛头王</h2>
          <p>别成为一行里的第六张。</p>
        </div>
      </div>
      <div class="hero-metrics" aria-label="牌局指标">
        <span><small>轮次</small><b>{{ game.roundNumber || 1 }}</b></span>
        <span><small>手数</small><b>{{ game.turnNumber || 1 }}/10</b></span>
        <span><small>终局线</small><b>{{ game.rules?.targetPenalty ?? 66 }}</b></span>
      </div>
      <button class="rules-button" type="button" @click="showRules = true">
        <BookOpen :size="17" /> 规则
      </button>
    </header>

    <div class="status-banner" :class="{ done: snapshot.phase === 'finished' }" role="status" aria-live="polite">
      <Crown v-if="snapshot.phase === 'finished'" :size="21" />
      <Clock3 v-else-if="game.committedCard" :size="21" />
      <Layers3 v-else :size="21" />
      <span><strong>{{ statusTitle }}</strong><small>{{ statusDetail }}</small></span>
    </div>

    <section class="player-rail" aria-label="玩家牛头分与提交状态">
      <article
        v-for="player in players"
        :key="`${player.id}-${latestTake?.playerId === player.id ? game.animation?.id ?? 0 : 0}`"
        class="player-chip"
        :class="{
          self: player.id === snapshot.self?.id,
          committed: player.hasSelected,
          forfeited: player.status === 'forfeited',
          winner: snapshot.winnerPlayerIds?.includes(player.id),
          'score-hit': latestTake?.playerId === player.id,
        }"
        :style="latestTake?.playerId === player.id && takeFlightMotion
          ? { '--score-hit-delay': `${takeFlightMotion.delayMs + 620}ms` }
          : undefined"
        :data-player-id="player.id"
      >
        <span class="seat-index">{{ player.rank ? `#${player.rank}` : player.seat + 1 }}</span>
        <span class="player-copy">
          <b>{{ player.name }}</b>
          <small v-if="player.status === 'forfeited'">已退出</small>
          <small v-else-if="player.hasSelected"><CheckCircle2 :size="11" /> 已锁定</small>
          <small v-else>{{ player.handCount }} 张手牌</small>
        </span>
        <span class="score-copy">
          <b>{{ player.totalPenalty }}</b>
          <small>+{{ player.roundPenalty }} 本轮</small>
        </span>
      </article>
    </section>

    <main class="table-shell">
      <div class="felt-glow" aria-hidden="true" />

      <section v-if="revealPlays.length" class="reveal-rail" aria-label="本手公开牌，按升序排列">
        <header>
          <span>{{ game.stage === 'select' ? '上一手公开' : '同时揭示 · 升序结算' }}</span>
          <small>{{ revealPlays.map(play => play.card.number).join(' → ') }}</small>
        </header>
        <div class="reveal-cards" :key="game.animation?.id ?? 0">
          <div
            v-for="(play, index) in revealPlays"
            :key="`${game.animation?.id ?? 0}-${play.playerId}-${play.card.id}`"
            class="reveal-entry"
            :style="revealDelay(index)"
            :data-reveal-card-id="play.card.id"
          >
            <NumberCard :card="play.card" compact />
            <small>{{ playerName(play.playerId) }}</small>
          </div>
        </div>
      </section>

      <section class="row-board" aria-label="四条数字行">
        <article
          v-for="(row, rowIndex) in rows"
          :key="`${rowIndex}-${stepsForRow(rowIndex).some(step => step.type !== 'place') ? game.animation?.id ?? 0 : 0}`"
          class="row-line"
          :class="rowClasses(rowIndex)"
          :style="rowMotionStyle(rowIndex)"
          :data-row-index="rowIndex"
        >
          <header class="row-meta">
            <span><b>0{{ rowIndex + 1 }}</b> 行</span>
            <small>{{ row.length }}/5 张</small>
            <strong>{{ rowPenalty(row) }} <i aria-hidden="true" /> </strong>
          </header>
          <div class="row-cards">
            <NumberCard
              v-for="(card, cardIndex) in row"
              :key="card.id"
              :card="card"
              :class="{
                'motion-card': stepIndexForCard(card.id) >= 0,
                'deal-card': game.animation?.kind === 'round_deal',
              }"
              :style="game.animation?.kind === 'round_deal'
                ? dealMotionStyle(rowIndex * 5 + cardIndex, 'row')
                : cardMotionStyle(card.id)"
            />
            <span
              v-for="slot in Math.max(0, 5 - row.length)"
              :key="`slot-${slot}`"
              class="empty-slot"
              aria-hidden="true"
            />
          </div>
        </article>
      </section>

      <p v-if="latestTake" class="take-announcement" aria-live="polite">
        {{ playerName(latestTake.playerId) }} 收走第 {{ latestTake.rowIndex + 1 }} 行，增加 {{ latestTake.penalty }} 牛头分。
      </p>
    </main>

    <section v-if="game.committedCard" class="committed-panel" aria-label="你已锁定的牌">
      <div>
        <ShieldCheck :size="18" />
        <span><b>你的牌已锁定</b><small>其他玩家只能看到你已提交</small></span>
      </div>
      <NumberCard :card="game.committedCard" compact />
    </section>

    <section v-if="game.stage === 'round_summary' && game.roundSummary" class="round-summary">
      <header>
        <span><Crown :size="20" /> 第 {{ game.roundSummary.roundNumber }} 轮结束</span>
        <small>达到 66 分只在一轮结束后检查</small>
      </header>
      <div class="summary-grid">
        <article v-for="player in sortedRankings" :key="player.id">
          <span>{{ player.name }}</span>
          <b>+{{ game.roundSummary.penalties[player.id] ?? 0 }}</b>
          <strong>{{ game.roundSummary.totals[player.id] ?? player.totalPenalty }} 总分</strong>
        </article>
      </div>
      <PluginButton variant="primary" :disabled="busy || !game.canStartNextRound" @click="nextRound">
        <RotateCcw :size="17" /> 开始下一轮
      </PluginButton>
    </section>

    <section v-if="snapshot.phase === 'finished'" class="final-panel">
      <Crown :size="31" />
      <small>最低牛头分</small>
      <h3>{{ winnerNames || '牌局结束' }}</h3>
      <p>{{ snapshot.winReason }}</p>
      <ol>
        <li v-for="player in sortedRankings" :key="player.id">
          <span>#{{ player.rank ?? sortedRankings.indexOf(player) + 1 }} {{ player.name }}</span>
          <b>{{ player.totalPenalty }} 分</b>
        </li>
      </ol>
      <PluginButton variant="primary" @click="actions.restart()">
        <RotateCcw :size="17" /> 再来一局
      </PluginButton>
    </section>

    <section v-else-if="!isSpectator" class="hand-panel" aria-label="你的手牌">
      <header>
        <span><b>你的手牌</b><small>{{ hand.length }} 张可选</small></span>
        <small v-if="selectedCard">已选：{{ cardLabel(selectedCard) }}</small>
        <small v-else-if="game.committedCard">等待其他玩家，不可撤回</small>
        <small v-else>牌面仅你可见</small>
      </header>
      <div v-if="hand.length" class="hand-scroll">
        <NumberCard
          v-for="(card, cardIndex) in hand"
          :key="card.id"
          :card="card"
          interactive
          :selected="selectedCardId === card.id"
          :disabled="!game.canSelect || busy"
          :class="{
            'commit-lift': busy && selectedCardId === card.id,
            'deal-card': game.animation?.kind === 'round_deal',
          }"
          :style="game.animation?.kind === 'round_deal'
            ? dealMotionStyle(cardIndex, 'hand')
            : undefined"
          @select="selectCard(card.id)"
        />
      </div>
      <div v-else class="empty-hand">
        <CheckCircle2 :size="19" /> 本轮手牌已全部打出
      </div>
      <PluginButton
        v-if="game.canSelect"
        class="commit-button"
        variant="primary"
        :disabled="!canSubmit"
        @click="commitCard"
      >
        <Send :size="17" /> 锁定这张牌
      </PluginButton>
    </section>

    <section v-else class="spectator-note">
      <ShieldCheck :size="18" /> 本游戏未开放观战；防御视图不展示任何玩家手牌。
    </section>

    <details class="history-panel">
      <summary>牌局记录 <small>最近 {{ game.history?.length ?? 0 }} 条</small></summary>
      <ol>
        <li v-for="(entry, index) in [...(game.history ?? [])].reverse()" :key="`${index}-${entry.message}`">
          {{ entry.message }}
        </li>
      </ol>
    </details>

    <div
      v-for="motion in cardFlightMotions"
      :key="`${game.animation?.id ?? 0}-${motion.id}`"
      class="play-flight"
      :style="cardFlightStyle(motion)"
      :data-motion-step="motion.id"
      aria-hidden="true"
    >
      <NumberCard :card="motion.card" compact class="play-flight-card" />
    </div>

    <div
      v-if="latestTake && takeFlightMotion"
      :key="`${game.animation?.id ?? 0}-${takeFlightMotion.id}`"
      class="take-flight"
      :style="flightStyle(takeFlightMotion)"
      :data-source-row="latestTake.rowIndex"
      :data-target-player="takeFlightMotion.playerId"
      aria-hidden="true"
    >
      <div class="flight-stack">
        <NumberCard
          v-for="(card, cardIndex) in latestTake.takenCards.slice(0, 5)"
          :key="card.id"
          :card="card"
          compact
          class="flight-card"
          :style="{ '--stack-index': cardIndex }"
        />
      </div>
      <b>+{{ latestTake.penalty }}</b>
      <em>{{ playerName(latestTake.playerId) }}</em>
    </div>

    <div v-if="showRules" class="rules-overlay" role="dialog" aria-modal="true" aria-label="谁是牛头王规则摘要" @click.self="showRules = false">
      <article class="rules-sheet">
        <header><span><BookOpen :size="20" /> 玩法速查</span><button type="button" aria-label="关闭规则" @click="showRules = false"><X :size="20" /></button></header>
        <section>
          <b>1 · 同时暗选</b>
          <p>每人从 10 张手牌锁定一张；全员完成后一起公开。</p>
        </section>
        <section>
          <b>2 · 由小到大</b>
          <p>公开牌按数字升序处理；四行按第一张牌升序，牌进入对应的行首区间。</p>
        </section>
        <section>
          <b>3 · 避开第六张</b>
          <p>你的牌若成为第六张，收走原五张；自己的牌成为新行首。</p>
        </section>
        <section>
          <b>4 · 自动收行</b>
          <p>低于所有行首时自动收第一行；落入一行已有牌之间时自动收该行，再用出牌重开。</p>
        </section>
        <section>
          <b>5 · 最低分获胜</b>
          <p>每轮 10 手。有人在轮末累计达到 66 分时结束，总分最低者获胜。</p>
        </section>
        <footer><span>5 尾数 = 2 分 · 整十 = 3 分 · 对子数 = 5 分 · 55 = 7 分</span></footer>
      </article>
    </div>
  </section>
</template>

<style scoped>
.bullhead-game {
  --bull-gold: #d6a447;
  --bull-gold-soft: #f0d39b;
  --bull-teal: #0b3437;
  --bull-deep: #061c1f;
  --bull-coral: #df7354;
  position: relative;
  isolation: isolate;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  min-height: max(760px, calc(100dvh - 112px));
  display: grid;
  align-content: start;
  gap: clamp(10px, 1.5vw, 16px);
  padding: clamp(12px, 2vw, 22px);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
  border-radius: clamp(18px, 2.4vw, 32px);
  color: var(--text, #f5f0e5);
  background:
    radial-gradient(circle at 50% -20%, rgb(214 164 71 / .14), transparent 34%),
    linear-gradient(155deg, color-mix(in srgb, var(--surface, #102427) 84%, #0b3437), var(--surface, #11191b));
}
.hero-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.brand-lockup { display: flex; align-items: center; gap: 12px; min-width: 0; }
.brand-lockup > div { min-width: 0; }
.brand-lockup small { color: var(--bull-gold); font-size: 8px; font-weight: 900; letter-spacing: .18em; }
.brand-lockup h2 { margin: 3px 0 1px; font-family: 'Songti SC', 'STSong', Georgia, serif; font-size: clamp(26px, 4vw, 42px); line-height: 1; }
.brand-lockup p { margin: 0; color: var(--muted); font-size: 10px; }
.horn-emblem { position: relative; width: 52px; height: 42px; display: flex; flex: 0 0 auto; align-items: center; justify-content: center; }
.horn-emblem b { width: 19px; height: 22px; border-radius: 55% 55% 45% 45%; background: linear-gradient(#f0d39b, #a6732c); box-shadow: inset 0 -4px 5px rgb(73 39 8 / .4); }
.horn-emblem i { width: 23px; height: 18px; border-top: 6px solid var(--bull-gold); }
.horn-emblem i:first-child { margin-right: -5px; border-left: 5px solid var(--bull-gold); border-radius: 22px 0 0; transform: rotate(10deg); }
.horn-emblem i:last-child { margin-left: -5px; border-right: 5px solid var(--bull-gold); border-radius: 0 22px 0 0; transform: rotate(-10deg); }
.hero-metrics { display: flex; gap: 6px; }
.hero-metrics span { min-width: 62px; display: grid; justify-items: center; gap: 1px; border: 1px solid var(--line); border-radius: 11px; padding: 7px 9px; background: var(--surface-inset); }
.hero-metrics small { color: var(--muted); font-size: 7px; letter-spacing: .1em; }
.hero-metrics b { font-size: 15px; }
.rules-button { min-height: 42px; display: inline-flex; align-items: center; gap: 7px; border: 1px solid color-mix(in srgb, var(--bull-gold) 45%, var(--line)); border-radius: 11px; padding: 0 14px; color: var(--bull-gold-soft); background: color-mix(in srgb, var(--bull-gold) 8%, var(--surface-inset)); cursor: pointer; }
.status-banner { min-height: 52px; display: flex; align-items: center; gap: 11px; border: 1px solid color-mix(in srgb, var(--bull-gold) 35%, var(--line)); border-radius: 14px; padding: 9px 14px; background: linear-gradient(90deg, rgb(214 164 71 / .1), transparent 56%), var(--surface-inset); }
.status-banner > svg { flex: 0 0 auto; color: var(--bull-gold); }
.status-banner > span { min-width: 0; display: grid; gap: 2px; }
.status-banner strong { font-size: 13px; }
.status-banner small { overflow: hidden; color: var(--muted); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.status-banner.done { border-color: color-mix(in srgb, #75c89f 58%, var(--line)); }
.player-rail { display: flex; gap: 8px; min-width: 0; overflow-x: auto; padding: 2px 1px 7px; scrollbar-width: thin; }
.player-chip { min-width: 150px; display: grid; grid-template-columns: 32px minmax(58px, 1fr) auto; align-items: center; gap: 7px; border: 1px solid var(--line); border-radius: 13px; padding: 8px; background: var(--surface-inset); }
.player-chip.self { border-color: color-mix(in srgb, var(--bull-gold) 60%, var(--line)); }
.player-chip.committed { box-shadow: inset 0 3px 0 #65bd91; }
.player-chip.forfeited { opacity: .5; filter: grayscale(.7); }
.player-chip.winner { border-color: var(--bull-gold); box-shadow: inset 0 0 18px rgb(214 164 71 / .14); }
.player-chip.score-hit { animation: score-hit 420ms ease-out both; animation-delay: var(--score-hit-delay, 0ms); }
.seat-index { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 9px; color: var(--bull-deep); background: var(--bull-gold); font-size: 10px; font-weight: 950; }
.player-copy, .score-copy { min-width: 0; display: grid; gap: 2px; }
.player-copy b { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.player-copy small { display: flex; align-items: center; gap: 3px; color: var(--muted); font-size: 8px; }
.player-chip.committed .player-copy small { color: #72cca0; }
.score-copy { justify-items: end; }
.score-copy b { font-family: Georgia, serif; color: var(--bull-gold-soft); font-size: 18px; }
.score-copy small { color: var(--muted); font-size: 7px; }
.table-shell { position: relative; min-width: 0; min-height: clamp(430px, 55dvh, 620px); display: grid; align-content: center; overflow: hidden; border: 1px solid color-mix(in srgb, var(--bull-gold) 38%, #183c3d); border-radius: clamp(18px, 3vw, 30px); padding: clamp(12px, 2.4vw, 26px); background: linear-gradient(145deg, rgb(255 255 255 / .025), transparent 34%), repeating-linear-gradient(20deg, transparent 0 16px, rgb(255 255 255 / .012) 16px 17px), var(--bull-teal); box-shadow: inset 0 0 70px rgb(0 0 0 / .28), 0 18px 34px rgb(0 0 0 / .18); }
.table-shell::before { content: ''; position: absolute; inset: 7px; border: 1px solid rgb(214 164 71 / .24); border-radius: inherit; pointer-events: none; }
.felt-glow { position: absolute; width: 55%; height: 60%; left: 22%; top: 18%; border-radius: 50%; background: rgb(214 164 71 / .05); filter: blur(40px); pointer-events: none; }
.reveal-rail { position: relative; z-index: 2; display: grid; grid-template-columns: 130px minmax(0, 1fr); align-items: center; gap: 10px; margin: 0 auto 13px; border: 1px solid rgb(214 164 71 / .28); border-radius: 14px; padding: 8px 10px; background: rgb(4 24 26 / .64); }
.reveal-rail > header { display: grid; gap: 3px; }
.reveal-rail > header span { color: var(--bull-gold-soft); font-size: 9px; font-weight: 900; letter-spacing: .08em; }
.reveal-rail > header small { color: #91aaa5; font: 700 9px Georgia, serif; }
.reveal-cards { min-width: 0; display: flex; align-items: end; gap: 7px; overflow-x: auto; padding: 4px 2px 6px; }
.reveal-entry { display: grid; justify-items: center; gap: 3px; animation: reveal-flip 420ms cubic-bezier(.2, .7, .2, 1) both; animation-delay: var(--reveal-delay); }
.reveal-entry > small { max-width: 58px; overflow: hidden; color: #bcd0cc; font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }
.row-board { position: relative; z-index: 1; display: grid; gap: 9px; }
.row-line { position: relative; display: grid; grid-template-columns: 80px minmax(0, 1fr); align-items: center; gap: 11px; min-width: 0; border: 1px solid rgb(143 181 171 / .18); border-radius: 15px; padding: 8px 10px; background: rgb(2 20 22 / .28); transition: border-color 180ms ease, background 180ms ease; }
.row-line--active { border-color: rgb(214 164 71 / .6); background: rgb(214 164 71 / .07); }
.row-line--taken { animation: row-warning 760ms ease-out both; animation-delay: var(--row-motion-delay, 0ms); }
.row-meta { display: grid; gap: 2px; border-right: 1px solid rgb(255 255 255 / .09); padding-right: 10px; }
.row-meta > span { color: #c9ded8; font-size: 9px; }
.row-meta > span b { color: var(--bull-gold); font: 800 15px Georgia, serif; }
.row-meta small { color: #77938e; font-size: 7px; }
.row-meta strong { display: inline-flex; align-items: center; gap: 4px; color: var(--bull-gold-soft); font-size: 10px; }
.row-meta strong i { position: relative; width: 7px; height: 7px; border-radius: 50%; background: var(--bull-gold); }
.row-cards { min-width: 0; display: flex; align-items: center; gap: clamp(4px, .7vw, 9px); }
.row-cards :deep(.number-card.motion-card) { animation: card-settle 360ms cubic-bezier(.2, .8, .25, 1) both; animation-delay: var(--card-motion-delay, 0ms); }
.bullhead-game :deep(.number-card.deal-card) { animation: card-deal 520ms cubic-bezier(.18, .78, .22, 1) both; animation-delay: var(--deal-delay, 0ms); }
.bullhead-game :deep(.number-card.commit-lift) { animation: commit-lift 180ms ease-out both; }
.empty-slot { width: clamp(54px, 6.3vw, 82px); aspect-ratio: 68 / 96; flex: 0 0 auto; border: 1px dashed rgb(164 199 190 / .2); border-radius: 9px; background: rgb(255 255 255 / .012); }
.play-flight { position: absolute; z-index: 23; left: var(--play-flight-x); top: var(--play-flight-y); width: var(--play-flight-width); pointer-events: none; will-change: transform, opacity; animation: play-flight 360ms cubic-bezier(.2, .78, .24, 1) both; animation-delay: var(--play-flight-delay, 0ms); filter: drop-shadow(0 10px 10px rgb(0 0 0 / .34)); }
.play-flight :deep(.play-flight-card) { width: var(--play-flight-width); }
.take-flight { position: absolute; z-index: 24; left: var(--flight-x); top: var(--flight-y); width: 82px; height: 58px; pointer-events: none; will-change: transform, opacity; animation: take-flight 760ms cubic-bezier(.2, .72, .24, 1) both; animation-delay: var(--flight-delay, 0ms); filter: drop-shadow(0 12px 12px rgb(0 0 0 / .38)); }
.flight-stack { position: absolute; inset: 0; }
.take-flight :deep(.flight-card) { position: absolute; left: calc(var(--stack-index) * 7px); top: calc(var(--stack-index) * -2px + 5px); width: 34px; border-radius: 5px; transform: rotate(calc((var(--stack-index) - 2) * 3deg)); box-shadow: 0 5px 9px rgb(0 0 0 / .34); }
.take-flight b { position: absolute; z-index: 8; right: 0; top: -4px; min-width: 32px; height: 32px; display: grid; place-items: center; border-radius: 50%; color: #fff; background: var(--bull-coral); box-shadow: 0 0 0 5px rgb(223 115 84 / .18); font-size: 11px; }
.take-flight em { position: absolute; z-index: 8; right: -2px; bottom: -2px; max-width: 66px; overflow: hidden; border: 1px solid rgb(255 255 255 / .16); border-radius: 999px; padding: 3px 7px; color: #fff4dc; background: rgb(5 25 27 / .9); font-size: 7px; font-style: normal; text-overflow: ellipsis; white-space: nowrap; }
.take-announcement { position: relative; z-index: 2; margin: 10px 0 0; color: #f2c0ae; font-size: 9px; text-align: center; }
.committed-panel { display: flex; align-items: center; justify-content: center; gap: 16px; border: 1px solid color-mix(in srgb, #65bd91 45%, var(--line)); border-radius: 16px; padding: 10px 16px; background: color-mix(in srgb, #65bd91 7%, var(--surface-inset)); }
.committed-panel > div { display: flex; align-items: center; gap: 9px; }
.committed-panel svg { color: #65bd91; }
.committed-panel span { display: grid; gap: 2px; }
.committed-panel b { font-size: 11px; }
.committed-panel small { color: var(--muted); font-size: 8px; }
.hand-panel, .round-summary, .final-panel, .spectator-note, .history-panel { border: 1px solid var(--line); border-radius: 17px; background: var(--surface-inset); }
.hand-panel { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px 14px; padding: 12px; }
.hand-panel > header { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hand-panel > header > span { display: flex; align-items: baseline; gap: 8px; }
.hand-panel > header b { font-size: 11px; }
.hand-panel > header small { color: var(--muted); font-size: 8px; }
.hand-scroll { min-width: 0; display: flex; align-items: end; gap: 8px; overflow-x: auto; overflow-y: hidden; padding: 15px 5px 8px; scrollbar-width: thin; }
.commit-button { align-self: center; min-width: 142px; }
.empty-hand { min-height: 74px; display: flex; align-items: center; justify-content: center; gap: 7px; color: var(--muted); font-size: 10px; }
.round-summary { display: grid; gap: 12px; padding: 16px; }
.round-summary > header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.round-summary > header span { display: flex; align-items: center; gap: 7px; color: var(--bull-gold-soft); font-size: 13px; font-weight: 800; }
.round-summary > header small { color: var(--muted); font-size: 8px; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 7px; }
.summary-grid article { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 3px 8px; border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; }
.summary-grid span { overflow: hidden; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.summary-grid b { color: var(--bull-coral); font-size: 11px; }
.summary-grid strong { grid-column: 1 / -1; color: var(--muted); font-size: 8px; }
.round-summary > button { justify-self: center; }
.final-panel { display: grid; justify-items: center; gap: 6px; padding: 20px; text-align: center; }
.final-panel > svg { color: var(--bull-gold); }
.final-panel > small { color: var(--bull-gold); font-size: 8px; font-weight: 900; letter-spacing: .14em; }
.final-panel h3 { margin: 0; font-family: 'Songti SC', 'STSong', serif; font-size: 27px; }
.final-panel p { margin: 0; color: var(--muted); font-size: 9px; }
.final-panel ol { width: min(100%, 480px); display: grid; gap: 5px; margin: 8px 0; padding: 0; list-style: none; }
.final-panel li { display: flex; justify-content: space-between; border-bottom: 1px solid var(--line); padding: 6px; font-size: 10px; }
.spectator-note { display: flex; align-items: center; justify-content: center; gap: 7px; padding: 13px; color: var(--muted); font-size: 9px; }
.spectator-note svg { color: #65bd91; }
.history-panel { padding: 0 13px; }
.history-panel summary { display: flex; justify-content: space-between; padding: 11px 0; cursor: pointer; font-size: 9px; font-weight: 800; }
.history-panel summary small { color: var(--muted); font-size: 8px; }
.history-panel ol { display: grid; gap: 5px; max-height: 170px; overflow-y: auto; margin: 0 0 12px; padding: 0 0 0 18px; color: var(--muted); font-size: 8px; line-height: 1.5; }
.rules-overlay { position: absolute; z-index: 30; inset: 0; display: grid; place-items: center; padding: 16px; background: rgb(2 12 14 / .82); backdrop-filter: blur(7px); }
.rules-sheet { width: min(100%, 610px); max-height: min(720px, 90vh); overflow-y: auto; border: 1px solid rgb(214 164 71 / .55); border-radius: 20px; padding: 18px; background: var(--surface, #142224); box-shadow: 0 28px 70px rgb(0 0 0 / .45); }
.rules-sheet > header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.rules-sheet > header span { display: flex; align-items: center; gap: 8px; color: var(--bull-gold-soft); font-size: 15px; font-weight: 850; }
.rules-sheet > header button { width: 38px; height: 38px; display: grid; place-items: center; border: 1px solid var(--line); border-radius: 10px; color: var(--text); background: var(--surface-inset); cursor: pointer; }
.rules-sheet section { border-top: 1px solid var(--line); padding: 10px 2px; }
.rules-sheet section b { color: var(--bull-gold); font-size: 10px; }
.rules-sheet section p { margin: 4px 0 0; color: var(--muted); font-size: 9px; line-height: 1.65; }
.rules-sheet footer { border-radius: 10px; padding: 10px; color: #f0d39b; background: rgb(214 164 71 / .1); font-size: 8px; text-align: center; }
@keyframes reveal-flip { 0% { opacity: 0; transform: rotateY(90deg) translateY(-8px); } 55% { opacity: 1; transform: rotateY(-8deg) translateY(-3px); } 100% { opacity: 1; transform: rotateY(0) translateY(0); } }
@keyframes card-settle { 0% { opacity: 0; transform: translateY(-16px) scale(.9) rotate(3deg); } 72% { opacity: .45; transform: translateY(3px) scale(1.03) rotate(-1deg); } 100% { opacity: 1; transform: none; } }
@keyframes card-deal { 0% { opacity: 0; transform: translateY(-24px) scale(.74) rotate(-5deg); } 66% { opacity: 1; transform: translateY(2px) scale(1.03) rotate(1deg); } 100% { opacity: 1; transform: none; } }
@keyframes commit-lift { 0% { opacity: 1; transform: translateY(-12px) rotate(-1deg); } 55% { opacity: .92; transform: translateY(-18px) scale(.94); } 100% { opacity: .55; transform: translateY(-8px) scale(.86); } }
@keyframes row-warning { 0%, 100% { box-shadow: none; } 28% { box-shadow: inset 0 0 0 2px rgb(223 115 84 / .8), 0 0 24px rgb(223 115 84 / .22); } }
@keyframes play-flight { 0% { opacity: 0; transform: translate3d(0, 0, 0) scale(.96) rotate(-4deg); } 14% { opacity: 1; } 62% { opacity: 1; transform: translate3d(var(--play-flight-middle-x), var(--play-flight-middle-y), 0) scale(1.02) rotate(2deg); } 100% { opacity: 0; transform: translate3d(var(--play-flight-destination-x), var(--play-flight-destination-y), 0) scale(.96) rotate(0); } }
@keyframes take-flight { 0% { opacity: 0; transform: translate3d(0, 0, 0) scale(1.08) rotate(-7deg); } 14% { opacity: 1; } 58% { opacity: 1; transform: translate3d(var(--flight-middle-x), var(--flight-middle-y), 0) scale(.88) rotate(4deg); } 88% { opacity: 1; } 100% { opacity: 0; transform: translate3d(var(--flight-destination-x), var(--flight-destination-y), 0) scale(.48) rotate(9deg); } }
@keyframes score-hit { 0% { transform: scale(1); } 48% { transform: scale(1.055); border-color: var(--bull-coral); box-shadow: 0 0 0 6px rgb(223 115 84 / .13), inset 0 0 18px rgb(223 115 84 / .12); } 100% { transform: scale(1); } }
@media (min-width: 621px) and (max-height: 820px) {
  .bullhead-game { min-height: max(640px, calc(100dvh - 96px)); gap: 9px; padding-top: 12px; padding-bottom: 12px; }
  .table-shell { min-height: 420px; padding-top: 12px; padding-bottom: 12px; }
  .empty-slot { width: clamp(48px, 5.4vw, 68px); }
}
@media (max-width: 860px) {
  .hero-bar { grid-template-columns: minmax(0, 1fr) auto; }
  .hero-metrics { grid-column: 1 / -1; grid-row: 2; }
  .hero-metrics span { flex: 1; }
  .rules-button { grid-column: 2; grid-row: 1; }
  .row-line { grid-template-columns: 64px minmax(0, 1fr); }
  .empty-slot { width: clamp(38px, 8.2vw, 58px); }
}
@media (max-width: 620px) {
  .bullhead-game { min-height: max(760px, calc(100dvh - 64px)); padding: 10px; border-radius: 18px; }
  .horn-emblem { width: 42px; transform: scale(.84); }
  .brand-lockup small { display: none; }
  .brand-lockup h2 { font-size: 28px; }
  .hero-metrics span { min-width: 0; }
  .status-banner small { white-space: normal; }
  .reveal-rail { grid-template-columns: 1fr; }
  .reveal-rail > header { grid-template-columns: auto 1fr; align-items: center; }
  .reveal-rail > header small { text-align: right; }
  .table-shell { padding: 12px 8px; }
  .row-line { grid-template-columns: 1fr; gap: 6px; padding: 7px; }
  .row-meta { grid-template-columns: auto auto 1fr; align-items: center; border-right: 0; border-bottom: 1px solid rgb(255 255 255 / .08); padding: 0 2px 5px; }
  .row-meta strong { justify-self: end; }
  .row-cards { justify-content: center; gap: 4px; }
  .empty-slot { width: clamp(43px, 13vw, 58px); }
  .hand-panel { grid-template-columns: 1fr; }
  .hand-panel > header { align-items: flex-start; }
  .commit-button { width: 100%; }
  .round-summary > header { align-items: flex-start; flex-direction: column; }
}
@media (max-width: 390px) {
  .brand-lockup p { display: none; }
  .rules-button { min-height: 38px; padding: 0 10px; }
  .hero-metrics span { padding: 6px 4px; }
  .player-chip { min-width: 137px; }
  .row-cards { gap: 3px; }
  .empty-slot { width: clamp(44px, 13vw, 58px); }
}
@media (prefers-reduced-motion: reduce) {
  .reveal-entry, .row-line--taken, .row-cards :deep(.number-card.motion-card), .bullhead-game :deep(.number-card.deal-card), .bullhead-game :deep(.number-card.commit-lift), .player-chip.score-hit, .play-flight, .take-flight { animation: none !important; }
  .row-line { transition: opacity 120ms linear; }
}
</style>
