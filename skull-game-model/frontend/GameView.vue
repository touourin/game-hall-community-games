<script setup lang="ts">
import { computed, nextTick, ref, watch, type CSSProperties } from 'vue'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Flower2,
  Gavel,
  History,
  LockKeyhole,
  ShieldCheck,
  Skull,
  Sparkles,
  Trophy,
  Users,
} from '@lucide/vue'
import {
  PluginButton,
  PluginModal,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import { cardAsset, discLabel, privateCardAsset } from './cardAssets'
import type {
  SkullDiscView,
  SkullGameView,
  SkullPlayerView,
  SkullPublicReveal,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()

const selectedDiscId = ref<string | null>(null)
const selectedPenaltyDiscId = ref<string | null>(null)
const bidValue = ref(1)
const busy = ref(false)
const rulesOpen = ref(false)
const historyOpen = ref(false)

const game = computed(() => props.snapshot.game as unknown as SkullGameView)
const perspectiveId = computed(() => (
  props.snapshot.viewer?.targetPlayerId ?? props.snapshot.self.id
))
const selfPlayer = computed(() => (
  game.value.players?.find((player) => player.id === perspectiveId.value)
))
const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const canUseAction = (name: string) => (
  !isSpectator.value
  && props.snapshot.actions.canAct
  && (game.value.actions ?? []).includes(name)
)
const playerById = (playerId: string | null | undefined) => (
  game.value.players?.find((player) => player.id === playerId)
)
const currentPlayer = computed(() => playerById(game.value.round?.currentPlayerId))
const highBidder = computed(() => playerById(game.value.round?.highBidderId))
const challenger = computed(() => playerById(game.value.round?.challengerId))
const winner = computed(() => playerById(game.value.result?.winnerIds?.[0]))

const seatPlayers = computed(() => {
  const players = game.value.players ?? []
  const ownIndex = players.findIndex((player) => player.id === perspectiveId.value)
  if (ownIndex < 0) return players
  return [...players.slice(ownIndex), ...players.slice(0, ownIndex)]
})

const phaseCopy = computed(() => {
  if (props.snapshot.phase === 'lobby') {
    return { eyebrow: '等待开局', title: '围桌入座', detail: '凑齐 3–6 位玩家后由房主开始牌局' }
  }
  if (props.snapshot.phase === 'finished' || game.value.phase === 'finished') {
    return { eyebrow: '对局结算', title: winner.value?.displayName ?? '胜者诞生', detail: game.value.result?.summary ?? props.snapshot.winReason ?? '' }
  }
  const phase = game.value.phase
  if (phase === 'round_setup') {
    if (game.value.round.hasCommitted) {
      return { eyebrow: '秘密暗置', title: '你的选择已锁定', detail: '等待其他玩家完成暗置，牌面仍保持秘密' }
    }
    if (canUseAction('commit_initial')) {
      return { eyebrow: '秘密暗置', title: '选择本轮第一枚牌', detail: '只有你能看到牌面；锁定后不能更改' }
    }
    return { eyebrow: '秘密暗置', title: '等待其他玩家锁定', detail: '首家最后提交，避免从提交顺序获得额外信息' }
  }
  if (phase === 'placement') {
    return game.value.round.currentPlayerId === perspectiveId.value
      ? { eyebrow: '叠牌或开叫', title: '轮到你掌控节奏', detail: '继续埋下一枚牌，或宣布你敢翻开的数量' }
      : { eyebrow: '叠牌或开叫', title: '观察桌面', detail: '等待 ' + (currentPlayer.value?.displayName ?? '当前玩家') + ' 作出选择' }
  }
  if (phase === 'bidding') {
    return game.value.round.currentPlayerId === perspectiveId.value
      ? { eyebrow: '公开竞标', title: '加价，还是暂不跟价？', detail: '暂不跟价只对当前叫价有效；若有人加价，你会重新获得行动机会' }
      : { eyebrow: '公开竞标', title: (highBidder.value?.displayName ?? '玩家') + ' 暂时领先', detail: '当前叫价 ' + game.value.round.currentBid + ' / 桌面 ' + game.value.round.totalPlaced }
  }
  if (phase === 'reveal') {
    return game.value.round.challengerId === perspectiveId.value
      ? { eyebrow: '挑战翻牌', title: '选择高亮的牌堆', detail: '必须先从自己的顶部翻起；翻到骷髅立即失败' }
      : { eyebrow: '挑战翻牌', title: (challenger.value?.displayName ?? '挑战者') + ' 正在翻牌', detail: '已安全翻开 ' + game.value.round.revealedCount + ' / ' + game.value.round.targetBid }
  }
  if (phase === 'penalty') {
    if (canUseAction('choose_penalty')) {
      return { eyebrow: '盲选处罚', title: '从不透明槽位中选一枚', detail: '所有槽位已由服务端随机打乱，不会泄露牌面' }
    }
    if (canUseAction('choose_self_penalty')) {
      return { eyebrow: '秘密处罚', title: '选择永久失去的一枚牌', detail: '只有你会知道最终移除的是花还是骷髅' }
    }
    return { eyebrow: '挑战失败', title: '等待秘密处罚完成', detail: (playerById(game.value.round.penaltyChooserId)?.displayName ?? '相关玩家') + ' 正在作出选择' }
  }
  return canUseAction('choose_next_first')
    ? { eyebrow: '下一轮', title: '指定一名仍在场的首家', detail: '这是你被淘汰前的最后一个决定' }
    : { eyebrow: '轮次结算', title: '等待下一轮首家', detail: '牌面已收回，新的秘密暗置即将开始' }
})

const bidProgress = computed(() => {
  const maximum = Math.max(1, game.value.round?.totalPlaced ?? 1)
  const value = game.value.phase === 'reveal'
    ? game.value.round.revealedCount
    : game.value.round.currentBid
  return Math.min(1, Math.max(0, value / maximum))
})

const latestHistory = computed(() => [...(game.value.history ?? [])].reverse())
const publicReveals = computed(() => game.value.publicReveals ?? [])
const latestPublicRevealId = computed(() => publicReveals.value.at(-1)?.eventId)
const revealListElement = ref<HTMLOListElement | null>(null)
const selectedDisc = computed(() => (
  game.value.hand?.find((disc) => disc.id === selectedDiscId.value)
))
const penaltyCandidates = computed(() => game.value.round?.selfPenaltyCandidates ?? [])
const canSubmitCard = computed(() => (
  Boolean(selectedDisc.value)
  && !busy.value
  && (canUseAction('commit_initial') || canUseAction('place_disc'))
))
const canSubmitBid = computed(() => {
  const action = game.value.phase === 'bidding' ? 'raise_bid' : 'open_bid'
  return (
    canUseAction(action)
    && !busy.value
    && Number.isInteger(bidValue.value)
    && bidValue.value >= game.value.minimumBid
    && bidValue.value <= game.value.maximumBid
  )
})

watch(
  () => (game.value.hand ?? []).map((disc) => disc.id).join('|'),
  () => {
    if (!game.value.hand?.some((disc) => disc.id === selectedDiscId.value)) {
      selectedDiscId.value = null
    }
  },
)

watch(
  () => [game.value.phase, game.value.minimumBid, game.value.maximumBid] as const,
  () => {
    const minimum = Math.max(1, game.value.minimumBid ?? 1)
    const maximum = Math.max(minimum, game.value.maximumBid ?? minimum)
    bidValue.value = Math.min(maximum, minimum)
    selectedPenaltyDiscId.value = null
  },
  { immediate: true },
)

watch(latestPublicRevealId, async () => {
  await nextTick()
  if (revealListElement.value) {
    revealListElement.value.scrollLeft = revealListElement.value.scrollWidth
  }
}, { immediate: true })

function seatStyle(index: number, count: number): CSSProperties {
  const layouts: Record<number, Array<[number, number]>> = {
    3: [[50, 83], [18, 27], [82, 27]],
    4: [[50, 84], [13, 48], [50, 17], [87, 48]],
    5: [[50, 85], [13, 62], [25, 18], [75, 18], [87, 62]],
    6: [[50, 86], [12, 66], [16, 23], [50, 17], [84, 23], [88, 66]],
  }
  const point = (layouts[count] ?? layouts[6])?.[index] ?? [50, 50]
  return {
    left: point[0] + '%',
    top: point[1] + '%',
    '--seat-order': String(index),
  }
}

function stackDiscStyle(index: number, count: number): CSSProperties {
  return {
    '--disc-rise': `${index * 7}px`,
    '--disc-rotation': `${(index - (count - 1) / 2) * 2}deg`,
    zIndex: index + 1,
  }
}

function isLegalReveal(playerId: string): boolean {
  return canUseAction('reveal_disc') && game.value.legalRevealOwnerIds.includes(playerId)
}

function tableCardAsset(player: SkullPlayerView, disc: SkullDiscView): string {
  return cardAsset(player.theme.slug, disc.kind, disc.faceUp)
}

function publicRevealLabel(reveal: SkullPublicReveal): string {
  if (reveal.kind === 'skull') return '骷髅牌'
  if (reveal.kind === 'last_chance_flower') return '花牌 · 最后机会'
  return '花牌'
}

function playerInitial(player: SkullPlayerView): string {
  return player.displayName.trim().slice(0, 1) || '玩'
}

function playerConnection(playerId: string): string {
  const player = props.snapshot.players.find((candidate) => candidate.id === playerId)
  if (player?.leftRoom) return '已离开'
  if (player?.disconnectForfeited) return '已判负'
  if (player && !player.connected) return '重连中'
  return ''
}

function selectHandDisc(disc: SkullDiscView) {
  if (busy.value || game.value.round.hasCommitted) return
  selectedDiscId.value = selectedDiscId.value === disc.id ? null : disc.id
}

async function sendAction(action: string, payload: Record<string, unknown> = {}) {
  if (busy.value) return
  busy.value = true
  try {
    await actions.action(action, payload)
  }
  finally {
    busy.value = false
  }
}

async function submitSelectedCard() {
  if (!selectedDisc.value || !canSubmitCard.value) return
  const action = canUseAction('commit_initial') ? 'commit_initial' : 'place_disc'
  await sendAction(action, { discId: selectedDisc.value.id })
  selectedDiscId.value = null
}

async function submitBid() {
  if (!canSubmitBid.value) return
  const action = game.value.phase === 'bidding' ? 'raise_bid' : 'open_bid'
  await sendAction(action, { count: bidValue.value })
}

async function revealStack(playerId: string) {
  if (!isLegalReveal(playerId)) return
  await sendAction('reveal_disc', { ownerId: playerId })
}

async function chooseBlindPenalty(slotId: string) {
  if (!canUseAction('choose_penalty')) return
  await sendAction('choose_penalty', { slotId })
}

async function confirmSelfPenalty() {
  if (!selectedPenaltyDiscId.value || !canUseAction('choose_self_penalty')) return
  await sendAction('choose_self_penalty', { discId: selectedPenaltyDiscId.value })
  selectedPenaltyDiscId.value = null
}

function adjustBid(delta: number) {
  const minimum = game.value.minimumBid
  const maximum = game.value.maximumBid
  bidValue.value = Math.min(maximum, Math.max(minimum, bidValue.value + delta))
}
</script>

<template>
  <section
    class="skull-game"
    :class="['phase-' + game.phase, { 'many-players': seatPlayers.length >= 5 }]"
    data-game="skull"
    data-layout="browser-fill"
  >
    <div class="scene-noise" aria-hidden="true"></div>
    <div class="scene-orbit orbit-one" aria-hidden="true"></div>
    <div class="scene-orbit orbit-two" aria-hidden="true"></div>

    <header class="skull-header">
      <div class="brand-lockup">
        <span class="brand-mark"><Skull :size="22" stroke-width="1.6" /></span>
        <div>
          <small>SKULL · BLUFF & BID</small>
          <h2>骷髅牌</h2>
        </div>
      </div>

      <div class="match-metrics" aria-label="本局信息">
        <span><b>{{ game.round?.number ?? 0 }}</b><small>轮次</small></span>
        <span><b>{{ game.stats?.activePlayers ?? snapshot.players.length }}</b><small>在场</small></span>
        <span><b>{{ selfPlayer?.challengeWins ?? 0 }}/{{ game.rules?.targetWins ?? 2 }}</b><small>我的挑战</small></span>
        <span :class="{ ranked: snapshot.statsEligible !== false }">
          <ShieldCheck :size="15" />
          <small>{{ snapshot.statsEligible === false ? '休闲局' : '计入战绩' }}</small>
        </span>
      </div>

      <div class="header-actions">
        <button type="button" class="header-button" aria-label="查看完整规则" @click="rulesOpen = true">
          <BookOpen :size="18" /><span>规则</span>
        </button>
        <button type="button" class="header-button" aria-label="查看对局记录" @click="historyOpen = !historyOpen">
          <History :size="18" /><span>记录</span>
        </button>
      </div>
    </header>

    <main class="scene-stage" aria-label="骷髅牌沉浸式牌桌">
      <div class="table-shadow" aria-hidden="true"></div>
      <div class="ritual-table" aria-hidden="true">
        <span class="table-ring ring-a"></span>
        <span class="table-ring ring-b"></span>
        <span class="table-sigil">S</span>
      </div>

      <article
        v-for="(player, index) in seatPlayers"
        :key="player.id"
        class="player-seat"
        :class="{
          self: player.id === perspectiveId,
          current: player.id === game.round?.currentPlayerId,
          challenger: player.id === game.round?.challengerId,
          high: player.id === game.round?.highBidderId,
          passed: player.passedBid,
          eliminated: player.status === 'eliminated',
          legal: isLegalReveal(player.id),
        }"
        :style="seatStyle(index, seatPlayers.length)"
        :data-player-id="player.id"
      >
        <div class="seat-nameplate">
          <span class="player-avatar">{{ playerInitial(player) }}</span>
          <span class="player-copy">
            <b>{{ player.displayName }}</b>
            <small>{{ player.theme.label }} · {{ player.theme.patternCode }}</small>
          </span>
          <span class="win-track" :aria-label="player.challengeWins + ' 次挑战成功'">
            <i :class="{ earned: player.challengeWins >= 1 }"><Flower2 :size="11" /></i>
            <i :class="{ earned: player.challengeWins >= 2 }"><Flower2 :size="11" /></i>
          </span>
        </div>

        <div class="seat-flags">
          <span v-if="player.id === game.round?.firstPlayerId">首家</span>
          <span v-if="player.id === game.round?.currentPlayerId">行动</span>
          <span v-if="player.id === game.round?.highBidderId">高叫 {{ game.round.currentBid }}</span>
          <span v-if="player.passedBid">本价不跟</span>
          <span v-if="player.id === game.round?.lastChanceHolderId">最后机会</span>
          <span v-if="playerConnection(player.id)" class="warning">{{ playerConnection(player.id) }}</span>
        </div>

        <button
          type="button"
          class="stack-zone"
          :class="{ clickable: isLegalReveal(player.id), empty: !player.stack.length }"
          :disabled="!isLegalReveal(player.id)"
          :aria-label="isLegalReveal(player.id) ? '翻开' + player.displayName + '牌堆顶部' : player.displayName + '的牌堆'"
          @click="revealStack(player.id)"
        >
          <span v-if="!player.stack.length" class="empty-stack">空牌垫</span>
          <span
            v-for="(disc, discIndex) in player.stack"
            :key="disc.id"
            class="table-disc"
            :class="{
              revealed: disc.faceUp,
              flower: disc.faceUp && disc.kind !== 'skull',
              skull: disc.faceUp && disc.kind === 'skull',
              lastChance: disc.kind === 'last_chance_flower',
            }"
            :style="stackDiscStyle(discIndex, player.stack.length)"
          >
            <span v-if="disc.kind === 'last_chance_flower'" class="last-chance-face">
              <Sparkles :size="22" /><small>{{ disc.faceUp ? '安全花牌' : '公开花' }}</small>
            </span>
            <img v-else :src="tableCardAsset(player, disc)" :alt="disc.faceUp ? discLabel(disc.kind) : player.theme.label + '牌背'">
            <span v-if="!disc.faceUp && disc.knowledge === 'self'" class="memory-mark" :class="disc.kind">
              <Flower2 v-if="disc.kind === 'flower'" :size="11" />
              <Skull v-else :size="11" />
            </span>
          </span>
        </button>

        <footer
          class="seat-counters"
          :aria-label="player.displayName + '剩余 ' + player.personalDiscCount + ' 张个人牌'"
        >
          <strong class="seat-card-total">剩余 {{ player.personalDiscCount }} 张</strong>
          <span class="seat-card-detail">
            手持 {{ player.handCount }} · 已叠 {{ player.stack.length }} · 失去 {{ player.removedCount }}
          </span>
        </footer>
        <div v-if="player.status === 'eliminated'" class="eliminated-stamp">已淘汰</div>
      </article>

      <section class="bid-core" :style="{ '--bid-progress': String(bidProgress) }" aria-live="polite">
        <div class="bid-orbit" aria-hidden="true"></div>
        <small>{{ phaseCopy.eyebrow }}</small>
        <template v-if="game.phase === 'bidding'">
          <strong>{{ game.round.currentBid }}</strong>
          <span>最高叫价 · 共 {{ game.round.totalPlaced }} 枚</span>
        </template>
        <template v-else-if="game.phase === 'reveal'">
          <strong>{{ game.round.revealedCount }}<em>/{{ game.round.targetBid }}</em></strong>
          <span>安全翻牌进度</span>
        </template>
        <template v-else>
          <strong>{{ game.round?.totalPlaced ?? 0 }}</strong>
          <span>桌面暗牌</span>
        </template>
      </section>

      <section
        v-if="publicReveals.length"
        class="reveal-broadcast"
        aria-label="全员可见的翻牌过程"
        aria-live="polite"
      >
        <header>
          <span><History :size="13" /><b>第 {{ publicReveals.at(-1)?.round }} 轮翻牌公示</b></span>
          <small>全员可见 · 按翻开顺序</small>
        </header>
        <ol ref="revealListElement">
          <li
            v-for="reveal in publicReveals"
            :key="reveal.eventId"
            :class="[
              reveal.kind === 'skull' ? 'skull' : 'flower',
              { latest: reveal.eventId === latestPublicRevealId },
            ]"
          >
            <span class="reveal-order">{{ reveal.index }}</span>
            <span class="reveal-symbol">
              <Skull v-if="reveal.kind === 'skull'" :size="18" />
              <Flower2 v-else :size="18" />
            </span>
            <span class="reveal-copy">
              <b>{{ publicRevealLabel(reveal) }}</b>
              <small>{{ playerById(reveal.ownerId)?.displayName ?? '玩家' }} 的牌</small>
            </span>
          </li>
        </ol>
      </section>

      <section class="phase-banner" role="status">
        <span class="phase-icon">
          <LockKeyhole v-if="game.phase === 'round_setup'" :size="20" />
          <Gavel v-else-if="game.phase === 'placement' || game.phase === 'bidding'" :size="20" />
          <Flower2 v-else-if="game.phase === 'reveal'" :size="20" />
          <Skull v-else-if="game.phase === 'penalty'" :size="20" />
          <Trophy v-else :size="20" />
        </span>
        <span><small>{{ phaseCopy.eyebrow }}</small><b>{{ phaseCopy.title }}</b><em>{{ phaseCopy.detail }}</em></span>
      </section>

      <aside class="history-drawer" :class="{ open: historyOpen }" aria-label="本局公开记录">
        <button type="button" class="drawer-toggle" @click="historyOpen = !historyOpen">
          <History :size="16" /><b>本局记录</b>
          <ChevronDown v-if="historyOpen" :size="16" />
          <ChevronUp v-else :size="16" />
        </button>
        <ol v-if="historyOpen">
          <li v-for="(entry, index) in latestHistory" :key="entry.type + '-' + index">
            <span :class="['event-dot', entry.type]"></span>
            <p>{{ entry.message }}</p>
          </li>
        </ol>
      </aside>
    </main>

    <section v-if="snapshot.phase !== 'finished'" class="action-dock">
      <div class="private-hand">
        <header>
          <span><LockKeyhole :size="15" /><b>你的私密手牌</b></span>
          <small v-if="isSpectator">固定玩家视角 · 只读观战</small>
          <small v-else>牌面仅当前视角可见</small>
        </header>
        <p v-if="game.lastPrivatePenalty" class="private-penalty-note" role="status">
          <Skull v-if="game.lastPrivatePenalty.kind === 'skull'" :size="14" />
          <Flower2 v-else :size="14" />
          <span><b>最近一次秘密处罚</b><small>{{ game.lastPrivatePenalty.message }}</small></span>
        </p>
        <div class="hand-row" :class="{ locked: game.round?.hasCommitted }">
          <button
            v-for="disc in game.hand ?? []"
            :key="disc.id"
            type="button"
            class="hand-disc"
            :class="{
              selected: selectedDiscId === disc.id,
              skull: disc.kind === 'skull',
              lastChance: disc.kind === 'last_chance_flower',
            }"
            :aria-pressed="selectedDiscId === disc.id"
            :disabled="busy || game.round?.hasCommitted || isSpectator"
            :data-disc-id="disc.id"
            @click="selectHandDisc(disc)"
          >
            <span v-if="disc.kind === 'last_chance_flower'" class="private-last-chance">
              <Sparkles :size="31" /><b>最后机会</b><small>公开安全花</small>
            </span>
            <img v-else :src="privateCardAsset(selfPlayer?.theme.slug ?? 'ember', disc.kind)" :alt="discLabel(disc.kind)">
            <span class="hand-label">
              <Skull v-if="disc.kind === 'skull'" :size="12" />
              <Flower2 v-else :size="12" />
              {{ discLabel(disc.kind) }}
            </span>
          </button>
          <span v-if="!(game.hand?.length)" class="empty-hand-message">没有可用手牌</span>
        </div>
      </div>

      <div class="action-console">
        <div class="console-heading">
          <span><small>{{ phaseCopy.eyebrow }}</small><b>{{ phaseCopy.title }}</b></span>
          <em>第 {{ game.round?.number ?? 0 }} 轮</em>
        </div>

        <template v-if="game.phase === 'lobby'">
          <div class="waiting-state">
            <Users :size="24" /><span><b>等待房主开局</b><small>当前 {{ snapshot.players.length }} 人，支持 3–6 人同时游玩</small></span>
          </div>
        </template>

        <template v-else-if="game.phase === 'round_setup'">
          <div v-if="game.round.hasCommitted" class="waiting-state">
            <LockKeyhole :size="24" /><span><b>暗置已锁定</b><small>{{ game.round.committedCount }}/{{ game.round.activePlayerCount }} 位已完成</small></span>
          </div>
          <div v-else-if="canUseAction('commit_initial')" class="card-submit-row">
            <p>{{ selectedDisc ? '已选择' + discLabel(selectedDisc.kind) : '先从左侧选择一枚牌' }}</p>
            <PluginButton variant="primary" :disabled="!canSubmitCard" @click="submitSelectedCard">
              锁定本轮暗置
            </PluginButton>
          </div>
          <div v-else class="waiting-state">
            <Users :size="24" /><span><b>等待其他玩家</b><small>{{ game.round.committedCount }}/{{ Math.max(0, game.round.activePlayerCount - 1) }} 位非首家已锁定</small></span>
          </div>
        </template>

        <template v-else-if="game.phase === 'placement'">
          <template v-if="game.round.currentPlayerId === perspectiveId && !isSpectator">
            <div class="split-actions">
              <div class="place-action">
                <small>继续叠牌</small>
                <PluginButton :disabled="!canSubmitCard" @click="submitSelectedCard">
                  {{ selectedDisc ? '叠放' + discLabel(selectedDisc.kind) : '先选择手牌' }}
                </PluginButton>
              </div>
              <span class="or-divider">或</span>
              <div class="bid-action">
                <small>开启竞标</small>
                <div class="bid-stepper">
                  <button type="button" aria-label="叫价减一" :disabled="bidValue <= game.minimumBid" @click="adjustBid(-1)">−</button>
                  <strong>{{ bidValue }}</strong>
                  <button type="button" aria-label="叫价加一" :disabled="bidValue >= game.maximumBid" @click="adjustBid(1)">＋</button>
                </div>
                <PluginButton variant="primary" compact :disabled="!canSubmitBid" @click="submitBid">开叫</PluginButton>
              </div>
            </div>
          </template>
          <div v-else class="waiting-state">
            <Gavel :size="24" /><span><b>轮到 {{ currentPlayer?.displayName ?? '其他玩家' }}</b><small>对方可叠牌或开启竞标</small></span>
          </div>
        </template>

        <template v-else-if="game.phase === 'bidding'">
          <div v-if="game.round.currentPlayerId === perspectiveId && !isSpectator" class="bid-console">
            <div class="bid-stepper large">
              <button type="button" aria-label="叫价减一" :disabled="bidValue <= game.minimumBid" @click="adjustBid(-1)">−</button>
              <span><small>你的新叫价</small><strong>{{ bidValue }}</strong><em>/ {{ game.maximumBid }}</em></span>
              <button type="button" aria-label="叫价加一" :disabled="bidValue >= game.maximumBid" @click="adjustBid(1)">＋</button>
            </div>
            <PluginButton variant="primary" :disabled="!canSubmitBid" @click="submitBid">提高叫价</PluginButton>
            <PluginButton :disabled="!canUseAction('pass_bid') || busy" @click="sendAction('pass_bid')">暂不加价</PluginButton>
          </div>
          <div v-else class="waiting-state">
            <Gavel :size="24" /><span><b>{{ highBidder?.displayName ?? '玩家' }} 以 {{ game.round.currentBid }} 枚领先</b><small>等待 {{ currentPlayer?.displayName ?? '其他玩家' }} 加价或暂不跟价</small></span>
          </div>
        </template>

        <template v-else-if="game.phase === 'reveal'">
          <div class="reveal-console" :class="{ active: canUseAction('reveal_disc') }">
            <span class="reveal-score"><b>{{ game.round.revealedCount }}</b><em>/</em><strong>{{ game.round.targetBid }}</strong></span>
            <span>
              <b>{{ canUseAction('reveal_disc') ? '点击桌面上发光的牌堆' : challenger?.displayName + ' 正在挑战' }}</b>
              <small>{{ canUseAction('reveal_disc') ? '服务端只接收玩家区域，不接收隐藏牌 ID' : '每次只能翻开牌堆最上方的一枚暗牌' }}</small>
            </span>
          </div>
        </template>

        <template v-else-if="game.phase === 'penalty'">
          <div v-if="canUseAction('choose_penalty')" class="penalty-slots">
            <p>选择任意槽位；每个槽位背后都是挑战者的一枚随机牌。</p>
            <div>
              <button
                v-for="(slot, index) in game.round.penaltySlots"
                :key="slot"
                type="button"
                :disabled="busy"
                :data-slot-id="slot"
                @click="chooseBlindPenalty(slot)"
              ><span>?</span><small>槽位 {{ index + 1 }}</small></button>
            </div>
          </div>
          <div v-else-if="canUseAction('choose_self_penalty')" class="self-penalty">
            <div class="penalty-cards">
              <button
                v-for="disc in penaltyCandidates"
                :key="disc.id"
                type="button"
                :class="{ selected: selectedPenaltyDiscId === disc.id }"
                :aria-pressed="selectedPenaltyDiscId === disc.id"
                :data-penalty-disc-id="disc.id"
                @click="selectedPenaltyDiscId = disc.id"
              >
                <img :src="privateCardAsset(selfPlayer?.theme.slug ?? 'ember', disc.kind)" :alt="discLabel(disc.kind)">
              </button>
            </div>
            <PluginButton variant="danger" :disabled="!selectedPenaltyDiscId || busy" @click="confirmSelfPenalty">永久移除所选牌</PluginButton>
          </div>
          <div v-else class="waiting-state danger">
            <Skull :size="25" /><span><b>处罚正在秘密完成</b><small>其他玩家只能看到数量变化，看不到被移除的牌面</small></span>
          </div>
        </template>

        <template v-else-if="game.phase === 'round_end'">
          <div v-if="canUseAction('choose_next_first')" class="next-first-picker">
            <p>选择下一轮首家</p>
            <div>
              <button
                v-for="playerId in game.round.eligibleNextFirstPlayerIds"
                :key="playerId"
                type="button"
                :disabled="busy"
                :data-next-player-id="playerId"
                @click="sendAction('choose_next_first', { playerId })"
              >{{ playerById(playerId)?.displayName }}</button>
            </div>
          </div>
          <div v-else class="waiting-state"><Users :size="24" /><span><b>等待首家决定</b><small>完成后所有仍在场玩家重新秘密暗置</small></span></div>
        </template>
      </div>
    </section>

    <section v-else class="result-dock" role="status">
      <span class="result-emblem"><Trophy :size="34" /></span>
      <div class="result-copy">
        <small>{{ game.result?.reason === 'two_challenges' ? 'DOUBLE CHALLENGE' : 'LAST PLAYER STANDING' }}</small>
        <h3>{{ winner?.displayName ?? '本局胜者' }} 赢得牌局</h3>
        <p>{{ game.result?.summary ?? snapshot.winReason }}</p>
      </div>
      <div class="result-record">
        <ShieldCheck :size="22" />
        <span><b>{{ snapshot.statsEligible === false ? '休闲局不计战绩' : '胜场与胜率已保存' }}</b><small>{{ game.stats.roundsPlayed }} 轮 · {{ game.stats.eliminatedPlayers }} 人淘汰</small></span>
      </div>
      <PluginButton variant="primary" :disabled="!snapshot.actions.canRestart || busy" @click="actions.restart()">再来一局</PluginButton>
    </section>

    <PluginModal
      v-if="rulesOpen"
      title="骷髅牌规则"
      description="3–6 人 · 竞标、胆量与隐藏信息"
      aria-label="骷髅牌完整规则"
      size="large"
      mobile-sheet
      @close="rulesOpen = false"
    >
      <article class="rules-content">
        <section><span>01</span><div><h3>随机开局与秘密暗置</h3><p>开局第一轮随机抽取首家；后续轮次继续按挑战结果决定首家。每人暗置一枚牌，首家最后锁定，随后由首家先叠牌或开叫。</p></div></section>
        <section><span>02</span><div><h3>叠牌或开叫</h3><p>轮到你时，继续把一枚牌面朝下叠在自己牌堆顶部，或宣布你敢翻开的数量。一旦开叫，只能加价或暂不跟价；有人加价后，所有人重新获得回应机会。</p></div></section>
        <section><span>03</span><div><h3>公开挑战翻牌</h3><p>最高叫价者先从自己的牌堆顶部逐枚翻起。每次翻牌的顺序、所属玩家以及花/骷髅结果都向全员公示。</p></div></section>
        <section><span>04</span><div><h3>失败处罚</h3><p>翻到自己的骷髅时秘密自选一枚牌移除；翻到别人骷髅时，由骷髅所有者从服务端打乱的槽位中盲选。</p></div></section>
        <section><span>05</span><div><h3>赢得整局</h3><p>率先成功挑战两次者获胜；若其他玩家都失去最后一枚个人牌，唯一仍在场的玩家立即获胜。</p></div></section>
        <section v-if="game.rules.lastChanceEnabled"><span>+</span><div><h3>最后机会</h3><p>首次因失败而只剩一枚个人牌时，下一轮临时获得一枚公开安全花牌；若该轮作为挑战者失败，则直接淘汰。</p></div></section>
        <footer>所有牌面、翻牌、处罚和胜负均由服务端裁定；客户端不会收到他人的隐藏牌 ID 或种类。</footer>
      </article>
    </PluginModal>
  </section>
</template>

<style scoped>
.skull-game {
  --skull-ink: #f4eee3;
  --skull-muted: #a9a39a;
  --skull-gold: #c9a664;
  --skull-gold-soft: rgba(201, 166, 100, .16);
  --skull-danger: #c26662;
  --skull-safe: #7eaa83;
  position: relative;
  isolation: isolate;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  min-height: max(760px, calc(100dvh - 112px));
  display: grid;
  grid-template-rows: auto minmax(520px, 1fr) auto;
  overflow: hidden;
  color: var(--skull-ink);
  border: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
  border-radius: clamp(18px, 2.4vw, 32px);
  background:
    radial-gradient(circle at 50% 36%, rgba(137, 118, 82, .12), transparent 29%),
    radial-gradient(circle at 12% 10%, rgba(88, 115, 103, .09), transparent 30%),
    linear-gradient(145deg, #121615 0%, #1b201d 47%, #111413 100%);
  box-shadow: inset 0 1px rgba(255,255,255,.04), 0 30px 80px rgba(0,0,0,.26);
}
.scene-noise { position: absolute; inset: 0; z-index: -1; opacity: .19; pointer-events: none; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E"); mix-blend-mode: soft-light; }
.scene-orbit { position: absolute; z-index: -1; border: 1px solid rgba(201,166,100,.08); border-radius: 50%; pointer-events: none; }.orbit-one { width: 74vw; aspect-ratio: 1; top: -43vw; right: -26vw; }.orbit-two { width: 54vw; aspect-ratio: 1; bottom: -39vw; left: -18vw; }
.skull-header { position: relative; z-index: 20; min-width: 0; display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: clamp(14px, 2vw, 30px); min-height: 78px; padding: 13px clamp(15px, 2.4vw, 34px); border-bottom: 1px solid rgba(255,255,255,.07); background: linear-gradient(180deg, rgba(8,10,9,.7), rgba(8,10,9,.18)); backdrop-filter: blur(18px); }
.brand-lockup { display: flex; align-items: center; gap: 11px; }.brand-mark { width: 42px; aspect-ratio: 1; display: grid; place-items: center; color: var(--skull-gold); border: 1px solid rgba(201,166,100,.32); border-radius: 50%; background: rgba(201,166,100,.08); box-shadow: inset 0 0 0 4px rgba(0,0,0,.14); }.brand-lockup small { display: block; color: var(--skull-gold); font-size: 8px; font-weight: 800; letter-spacing: .2em; }.brand-lockup h2 { margin: 3px 0 0; font-family: Georgia, "Songti SC", serif; font-size: clamp(22px, 2.2vw, 31px); line-height: 1; letter-spacing: .06em; }
.match-metrics { min-width: 0; display: flex; justify-content: center; gap: clamp(5px, .8vw, 10px); }.match-metrics > span { min-width: 70px; min-height: 44px; display: grid; grid-template-columns: auto auto; place-content: center; align-items: center; gap: 2px 6px; padding: 6px 10px; border: 1px solid rgba(255,255,255,.07); border-radius: 12px; background: rgba(0,0,0,.18); }.match-metrics b { color: var(--skull-ink); font-size: 14px; line-height: 1; }.match-metrics small { grid-column: 1 / -1; color: var(--skull-muted); font-size: 8px; white-space: nowrap; }.match-metrics > span.ranked { color: var(--skull-safe); border-color: rgba(126,170,131,.22); }.match-metrics > span.ranked small { color: #9abf9e; }
.header-actions { display: flex; align-items: center; gap: 6px; }.header-button { min-width: 51px; display: grid; grid-template-columns: auto; place-items: center; gap: 3px; border: 1px solid transparent; border-radius: 11px; padding: 7px 9px; color: var(--skull-muted); background: transparent; cursor: pointer; transition: .2s ease; }.header-button span { font-size: 8px; }.header-button:hover { color: var(--skull-gold); border-color: rgba(201,166,100,.25); background: rgba(201,166,100,.07); }
.scene-stage { position: relative; min-width: 0; min-height: 520px; overflow: hidden; }.table-shadow,.ritual-table { position: absolute; left: 50%; top: 48%; transform: translate(-50%,-50%); width: min(72%, 1040px); height: min(71%, 580px); border-radius: 50%; }.table-shadow { transform: translate(-50%,calc(-50% + 26px)); background: rgba(0,0,0,.55); filter: blur(28px); }.ritual-table { overflow: hidden; border: 2px solid rgba(183,158,112,.26); background: radial-gradient(ellipse at center, rgba(70,86,70,.9) 0%, rgba(42,58,48,.96) 48%, rgba(26,36,31,.99) 72%), repeating-radial-gradient(ellipse at center, transparent 0 44px, rgba(255,255,255,.018) 45px 46px); box-shadow: inset 0 0 0 12px rgba(11,14,12,.48), inset 0 0 0 14px rgba(201,166,100,.15), inset 0 0 90px rgba(0,0,0,.58); }.table-ring { position: absolute; inset: 18%; border: 1px solid rgba(201,166,100,.12); border-radius: 50%; }.ring-b { inset: 33%; border-style: dashed; transform: rotate(12deg); }.table-sigil { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); color: rgba(201,166,100,.05); font-family: Georgia,serif; font-size: 170px; }
.player-seat { position: absolute; z-index: 6; width: clamp(148px, 15vw, 214px); transform: translate(-50%,-50%); transition: opacity .25s, filter .25s; }.player-seat.self { z-index: 8; }.player-seat.passed { opacity: .58; filter: saturate(.72); }.player-seat.eliminated { opacity: .32; filter: grayscale(.7); }.seat-nameplate { position: relative; z-index: 8; display: grid; grid-template-columns: 34px minmax(0,1fr) auto; align-items: center; gap: 7px; min-width: 0; padding: 7px 9px; border: 1px solid rgba(255,255,255,.1); border-radius: 13px; background: rgba(13,17,15,.88); box-shadow: 0 8px 22px rgba(0,0,0,.28); backdrop-filter: blur(12px); }.player-seat.current .seat-nameplate,.player-seat.high .seat-nameplate { border-color: rgba(201,166,100,.56); box-shadow: 0 0 0 3px rgba(201,166,100,.08),0 8px 22px rgba(0,0,0,.3); }.player-seat.challenger .seat-nameplate { border-color: rgba(126,170,131,.58); }.player-avatar { width: 34px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 10px; color: var(--skull-gold); background: rgba(201,166,100,.11); font-size: 13px; font-weight: 900; }.player-copy { min-width: 0; display: grid; gap: 2px; }.player-copy b,.player-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.player-copy b { font-size: 10px; }.player-copy small { color: var(--skull-muted); font-size: 7px; }.win-track { display: flex; gap: 3px; }.win-track i { width: 19px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid rgba(255,255,255,.09); border-radius: 50%; color: rgba(255,255,255,.22); }.win-track i.earned { color: #b5d5ad; border-color: rgba(126,170,131,.42); background: rgba(126,170,131,.13); }
.seat-flags { position: relative; z-index: 7; min-height: 18px; display: flex; justify-content: center; flex-wrap: wrap; gap: 3px; padding-top: 4px; }.seat-flags span { border: 1px solid rgba(201,166,100,.18); border-radius: 999px; padding: 2px 6px; color: #d5bd8f; background: rgba(15,18,16,.85); font-size: 6px; font-weight: 800; letter-spacing: .04em; }.seat-flags span.warning { color: #dda39f; border-color: rgba(194,102,98,.25); }
.stack-zone { position: relative; width: 106px; height: 92px; display: block; margin: -1px auto 0; border: 1px solid rgba(255,255,255,.07); border-radius: 50%; color: var(--skull-muted); background: radial-gradient(circle, rgba(0,0,0,.32), rgba(0,0,0,.05) 64%, transparent 66%); cursor: default; }.stack-zone.clickable { border-color: rgba(201,166,100,.72); cursor: pointer; animation: legal-pulse 1.7s ease-in-out infinite; }.stack-zone:disabled { opacity: 1; }.empty-stack { position: absolute; inset: 0; display: grid; place-items: center; font-size: 7px; letter-spacing: .08em; }.table-disc { position: absolute; left: 50%; top: 60%; width: clamp(54px, 5.2vw, 76px); aspect-ratio: 1; transform: translate(-50%, calc(-50% - var(--disc-index) * 7px)) rotate(calc((var(--disc-index) - var(--disc-count) / 2) * 2deg)); border-radius: 50%; filter: drop-shadow(0 6px 7px rgba(0,0,0,.38)); transition: transform .35s ease, filter .35s ease; }.stack-zone.clickable .table-disc:last-child { transform: translate(-50%, calc(-56% - var(--disc-index) * 7px)) scale(1.07); filter: drop-shadow(0 0 12px rgba(201,166,100,.42)); }.table-disc img { width: 100%; height: 100%; display: block; border-radius: 50%; }.table-disc.revealed { transform: translate(-50%, calc(-50% - var(--disc-index) * 7px)) rotateY(0); }.last-chance-face { width: 100%; height: 100%; display: grid; place-items: center; align-content: center; gap: 1px; border: 2px solid #d3b771; border-radius: 50%; color: #f5df9c; background: radial-gradient(circle,#4d4935,#242b25); }.last-chance-face small { font-size: 6px; }.memory-mark { position: absolute; right: -1px; bottom: -1px; width: 20px; aspect-ratio: 1; display: grid; place-items: center; border: 2px solid #161a18; border-radius: 50%; color: #c9d8c5; background: #526f58; }.memory-mark.skull { color: #f2d8d5; background: #844945; }.seat-counters { display:grid; justify-items:center; gap:2px; margin-top:0; }.seat-card-total { border:1px solid rgba(201,166,100,.28); border-radius:999px; padding:2px 7px; color:#e2c98e; background:rgba(13,17,15,.88); font-size:7px; line-height:1.1; white-space:nowrap; box-shadow:0 3px 10px rgba(0,0,0,.22); }.seat-card-detail { color:var(--skull-muted); font-size:6px; white-space:nowrap; }.eliminated-stamp { position: absolute; z-index: 12; left: 50%; top: 58%; transform: translate(-50%,-50%) rotate(-9deg); border: 2px solid #bd6c67; padding: 3px 9px; color: #e8a29e; background: rgba(32,16,15,.8); font-size: 10px; font-weight: 900; letter-spacing: .12em; }
.table-disc { transform: translate(-50%, calc(-50% - var(--disc-rise))) rotate(var(--disc-rotation)); }
.stack-zone.clickable .table-disc:last-child { transform: translate(-50%, calc(-56% - var(--disc-rise))) scale(1.07); }
.table-disc.revealed { transform: translate(-50%, calc(-50% - var(--disc-rise))) rotateY(0); backface-visibility:hidden; animation:stack-reveal .46s ease-out; }
.bid-core { --progress-angle: calc(var(--bid-progress) * 360deg); position: absolute; z-index: 7; left: 50%; top: 48%; width: clamp(112px, 11vw, 154px); aspect-ratio: 1; display: grid; place-items: center; align-content: center; transform: translate(-50%,-50%); border: 1px solid rgba(201,166,100,.34); border-radius: 50%; background: radial-gradient(circle,#252c27 0 52%,#171c19 53% 65%,transparent 66%), conic-gradient(var(--skull-gold) var(--progress-angle),rgba(255,255,255,.08) 0); box-shadow: 0 16px 40px rgba(0,0,0,.4),inset 0 0 20px rgba(0,0,0,.5); }.bid-orbit { position: absolute; inset: -12px; border: 1px dashed rgba(201,166,100,.18); border-radius: 50%; animation: spin 28s linear infinite; }.bid-core small { color: var(--skull-gold); font-size: 7px; font-weight: 900; letter-spacing: .13em; }.bid-core strong { margin: 2px 0; font-family: Georgia,serif; font-size: clamp(34px,4vw,52px); line-height: .95; }.bid-core strong em { color: var(--skull-muted); font-size: .42em; font-style: normal; }.bid-core > span { color: var(--skull-muted); font-size: 7px; }
.reveal-broadcast { position:absolute; z-index:15; left:50%; top:calc(48% + clamp(80px,8vw,116px)); width:min(560px,52%); transform:translateX(-50%); border:1px solid rgba(255,255,255,.1); border-radius:13px; padding:7px 8px 8px; background:rgba(10,14,12,.9); box-shadow:0 12px 32px rgba(0,0,0,.32); backdrop-filter:blur(14px); }
.reveal-broadcast header { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px; padding:0 2px; }.reveal-broadcast header > span { display:flex; align-items:center; gap:5px; color:var(--skull-gold); }.reveal-broadcast header b { font-size:7px; letter-spacing:.06em; }.reveal-broadcast header small { color:var(--skull-muted); font-size:6px; white-space:nowrap; }
.reveal-broadcast ol { display:flex; gap:5px; margin:0; padding:0 0 2px; overflow-x:auto; list-style:none; scroll-behavior:smooth; }.reveal-broadcast li { flex:0 0 auto; min-width:104px; display:grid; grid-template-columns:16px 24px minmax(54px,1fr); align-items:center; gap:4px; border:1px solid rgba(126,170,131,.25); border-radius:9px; padding:5px 6px; color:#b7d8bb; background:rgba(126,170,131,.09); animation:public-reveal .48s ease-out; }.reveal-broadcast li.skull { color:#efb4b0; border-color:rgba(194,102,98,.36); background:rgba(194,102,98,.12); }.reveal-broadcast li.latest { box-shadow:inset 0 0 0 1px currentColor,0 0 14px color-mix(in srgb,currentColor 24%,transparent); }.reveal-order { display:grid; place-items:center; width:16px; aspect-ratio:1; border-radius:50%; color:var(--skull-ink); background:rgba(255,255,255,.1); font:700 7px/1 ui-monospace,monospace; }.reveal-symbol { display:grid; place-items:center; }.reveal-copy { min-width:0; display:grid; gap:1px; }.reveal-copy b,.reveal-copy small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.reveal-copy b { font-size:7px; }.reveal-copy small { color:var(--skull-muted); font-size:6px; }
.phase-banner { position: absolute; z-index: 12; left: clamp(13px,2vw,28px); top: clamp(13px,2vw,25px); width: min(310px,31%); display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid rgba(255,255,255,.08); border-radius: 14px; background: rgba(11,14,12,.78); backdrop-filter: blur(14px); }.phase-icon { flex: 0 0 auto; width: 38px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid rgba(201,166,100,.22); border-radius: 11px; color: var(--skull-gold); background: rgba(201,166,100,.08); }.phase-banner > span:last-child { min-width: 0; display: grid; gap: 2px; }.phase-banner small { color: var(--skull-gold); font-size: 7px; font-weight: 900; letter-spacing: .12em; }.phase-banner b,.phase-banner em { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.phase-banner b { font-size: 11px; }.phase-banner em { color: var(--skull-muted); font-size: 7px; font-style: normal; }
.history-drawer { position: absolute; z-index: 18; right: clamp(12px,1.8vw,26px); top: clamp(12px,1.8vw,24px); width: min(360px,36%); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; background: rgba(11,14,12,.82); backdrop-filter: blur(16px); overflow: hidden; }.drawer-toggle { width: 100%; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; border: 0; padding: 13px 14px; color: var(--skull-muted); background: transparent; cursor: pointer; text-align: left; }.drawer-toggle b { color: var(--skull-ink); font-size: 13px; }.history-drawer ol { max-height: min(360px,52vh); display: grid; gap: 0; margin: 0; padding: 0 14px 12px; overflow: auto; list-style: none; }.history-drawer li { display: grid; grid-template-columns: 10px 1fr; gap: 10px; padding: 10px 0; border-top: 1px solid rgba(255,255,255,.07); }.history-drawer p { margin: 0; color: #c3beb5; font-size: 12px; line-height: 1.6; }.event-dot { width: 7px; aspect-ratio: 1; margin-top: 6px; border-radius: 50%; background: #797d78; }.event-dot.reveal,.event-dot.challenge_success { background: var(--skull-safe); }.event-dot.penalty_pending,.event-dot.eliminated,.event-dot.last_chance_elimination { background: var(--skull-danger); }
.action-dock,.result-dock { position: relative; z-index: 24; margin: 0 clamp(12px,2vw,28px) clamp(12px,2vw,26px); border: 1px solid rgba(255,255,255,.09); border-radius: 21px; background: linear-gradient(135deg,rgba(25,30,27,.96),rgba(12,15,13,.97)); box-shadow: 0 20px 50px rgba(0,0,0,.38); backdrop-filter: blur(20px); }.action-dock { min-width: 0; display: grid; grid-template-columns: minmax(0,1.45fr) minmax(330px,.8fr); gap: 0; }.private-hand { min-width: 0; padding: 13px 16px 14px; border-right: 1px solid rgba(255,255,255,.07); }.private-hand header { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }.private-hand header > span { display: flex; align-items: center; gap: 6px; color: var(--skull-gold); }.private-hand header b { font-size: 8px; letter-spacing: .08em; }.private-hand header small { color: var(--skull-muted); font-size: 7px; }.private-penalty-note { display:flex;align-items:center;gap:7px;margin:0 0 8px;border:1px solid rgba(194,102,98,.2);border-radius:9px;padding:6px 8px;color:#dda39f;background:rgba(194,102,98,.07); }.private-penalty-note > span { display:grid;gap:1px; }.private-penalty-note b { font-size:7px;letter-spacing:.04em; }.private-penalty-note small { color:#c6aaa7;font-size:7px; }.hand-row { min-width: 0; display: flex; align-items: flex-end; gap: clamp(7px,1vw,12px); overflow-x: auto; padding: 3px 3px 2px; }.hand-row.locked { opacity: .58; }.hand-disc { position: relative; flex: 0 0 clamp(78px,8vw,106px); aspect-ratio: 1; border: 1px solid transparent; border-radius: 50%; padding: 0; background: transparent; cursor: pointer; transition: transform .2s ease,filter .2s ease; }.hand-disc:hover:not(:disabled) { transform: translateY(-5px); }.hand-disc.selected { transform: translateY(-8px); filter: drop-shadow(0 0 10px rgba(201,166,100,.35)); }.hand-disc.selected::after { content:""; position:absolute; inset:-4px; border:2px solid var(--skull-gold); border-radius:50%; }.hand-disc img { width: 100%; display: block; border-radius: 50%; filter: drop-shadow(0 7px 8px rgba(0,0,0,.35)); }.hand-disc:disabled { cursor: default; }.hand-label { position: absolute; left: 50%; bottom: -1px; display: flex; align-items: center; gap: 3px; transform: translateX(-50%); border: 1px solid rgba(255,255,255,.11); border-radius: 999px; padding: 3px 7px; color: #d9ddd7; background: rgba(9,11,10,.91); font-size: 6px; font-weight: 800; white-space: nowrap; }.hand-disc.skull .hand-label { color: #efc1bd; border-color: rgba(194,102,98,.25); }.private-last-chance { width: 100%; height: 100%; display: grid; place-items: center; align-content: center; gap: 2px; border: 3px solid #c6aa62; border-radius: 50%; color: #f3db98; background: radial-gradient(circle,#56503a,#232b25 68%); box-shadow: inset 0 0 0 6px rgba(0,0,0,.25); }.private-last-chance b { font-size: 8px; }.private-last-chance small { font-size: 6px; }.empty-hand-message { min-height: 92px; display: grid; place-items: center; color: var(--skull-muted); font-size: 9px; }
.action-console { min-width: 0; display: grid; align-content: center; gap: 10px; padding: 14px 16px; }.console-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }.console-heading > span { display: grid; gap: 2px; }.console-heading small { color: var(--skull-gold); font-size: 7px; font-weight: 900; letter-spacing: .1em; }.console-heading b { font-size: 12px; }.console-heading em { border: 1px solid rgba(255,255,255,.08); border-radius: 999px; padding: 4px 8px; color: var(--skull-muted); font-size: 7px; font-style: normal; }.waiting-state { min-height: 70px; display: flex; align-items: center; gap: 12px; color: var(--skull-gold); }.waiting-state > span { display: grid; gap: 4px; }.waiting-state b { color: var(--skull-ink); font-size: 11px; }.waiting-state small { color: var(--skull-muted); font-size: 8px; }.waiting-state.danger { color: var(--skull-danger); }.card-submit-row { display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 12px; }.card-submit-row p { margin: 0; color: var(--skull-muted); font-size: 8px; }
.split-actions { display: grid; grid-template-columns: minmax(0,.8fr) auto minmax(0,1.25fr); align-items: end; gap: 11px; }.place-action,.bid-action { display: grid; gap: 6px; }.place-action > small,.bid-action > small { color: var(--skull-muted); font-size: 7px; }.bid-action { grid-template-columns: minmax(105px,1fr) auto; }.bid-action > small { grid-column:1/-1; }.or-divider { align-self:center; color:rgba(255,255,255,.25); font-size:8px; }.bid-stepper { min-height: 34px; display: grid; grid-template-columns: 31px 1fr 31px; align-items: center; border: 1px solid rgba(255,255,255,.1); border-radius: 10px; overflow: hidden; }.bid-stepper button { height: 100%; border: 0; color: var(--skull-gold); background: rgba(255,255,255,.035); cursor:pointer; }.bid-stepper button:disabled { color:rgba(255,255,255,.18); cursor:default; }.bid-stepper strong { text-align:center; font-family:Georgia,serif; font-size:19px; }.bid-console { display:grid; grid-template-columns:minmax(155px,1fr) auto auto; align-items:center; gap:8px; }.bid-stepper.large { min-height:50px; grid-template-columns:38px 1fr 38px; }.bid-stepper.large > span { display:flex; align-items:baseline; justify-content:center; gap:5px; }.bid-stepper.large small { color:var(--skull-muted); font-size:7px; }.bid-stepper.large strong { color:var(--skull-gold); font-size:25px; }.bid-stepper.large em { color:var(--skull-muted); font-size:8px; font-style:normal; }
.reveal-console { min-height:70px; display:grid; grid-template-columns:auto 1fr; align-items:center; gap:14px; }.reveal-console.active { color:var(--skull-gold); }.reveal-score { min-width:76px; display:flex; align-items:baseline; justify-content:center; gap:4px; border-right:1px solid rgba(255,255,255,.08); }.reveal-score b { font-family:Georgia,serif; font-size:35px; }.reveal-score em { color:var(--skull-muted); font-style:normal; }.reveal-score strong { color:var(--skull-muted); font-size:18px; }.reveal-console > span:last-child { display:grid; gap:4px; }.reveal-console > span:last-child b { color:var(--skull-ink); font-size:11px; }.reveal-console small { color:var(--skull-muted); font-size:8px; }
.penalty-slots { display:grid; gap:8px; }.penalty-slots p,.next-first-picker p { margin:0; color:var(--skull-muted); font-size:8px; }.penalty-slots > div { display:flex; flex-wrap:wrap; gap:6px; }.penalty-slots button { min-width:58px; display:grid; place-items:center; gap:1px; border:1px solid rgba(194,102,98,.25); border-radius:10px; padding:7px; color:#e6b6b2; background:rgba(194,102,98,.08); cursor:pointer; }.penalty-slots button span { font-family:Georgia,serif; font-size:17px; }.penalty-slots button small { font-size:6px; }.self-penalty { display:grid; grid-template-columns:1fr auto; align-items:center; gap:10px; }.penalty-cards { display:flex; gap:6px; overflow-x:auto; }.penalty-cards button { flex:0 0 52px; border:2px solid transparent; border-radius:50%; padding:0; background:transparent; cursor:pointer; }.penalty-cards button.selected { border-color:var(--skull-danger); transform:translateY(-3px); }.penalty-cards img { width:100%; display:block; border-radius:50%; }.next-first-picker { display:grid; gap:8px; }.next-first-picker > div { display:flex; flex-wrap:wrap; gap:6px; }.next-first-picker button { border:1px solid rgba(201,166,100,.26); border-radius:9px; padding:8px 11px; color:var(--skull-ink); background:rgba(201,166,100,.08); cursor:pointer; }
.result-dock { display:grid; grid-template-columns:auto minmax(0,1fr) auto auto; align-items:center; gap:16px; padding:16px 18px; border-color:rgba(201,166,100,.28); }.result-emblem { width:58px; aspect-ratio:1; display:grid; place-items:center; border:1px solid rgba(201,166,100,.34); border-radius:50%; color:var(--skull-gold); background:rgba(201,166,100,.1); }.result-copy { min-width:0; }.result-copy small { color:var(--skull-gold); font-size:7px; font-weight:900; letter-spacing:.14em; }.result-copy h3 { margin:3px 0; font-size:18px; }.result-copy p { margin:0; overflow:hidden; color:var(--skull-muted); font-size:8px; text-overflow:ellipsis; white-space:nowrap; }.result-record { display:flex; align-items:center; gap:8px; color:var(--skull-safe); }.result-record > span { display:grid; gap:2px; }.result-record b { color:var(--skull-ink); font-size:9px; }.result-record small { color:var(--skull-muted); font-size:7px; }
.rules-content { display:grid; gap:3px; }.rules-content section { display:grid; grid-template-columns:42px 1fr; gap:16px; padding:16px 0; border-bottom:1px solid var(--line); }.rules-content section > span { width:38px; aspect-ratio:1; display:grid; place-items:center; border:1px solid color-mix(in srgb,var(--gold) 35%,var(--line)); border-radius:50%; color:var(--gold); font-family:Georgia,serif; font-size:14px; }.rules-content h3 { margin:0 0 6px; font-size:16px; }.rules-content p { margin:0; color:var(--muted); font-size:13px; line-height:1.72; }.rules-content footer { margin-top:12px; border-radius:10px; padding:13px; color:var(--muted); background:var(--surface-inset); font-size:11px; line-height:1.65; }
@keyframes legal-pulse { 0%,100%{box-shadow:0 0 0 3px rgba(201,166,100,.05),0 0 13px rgba(201,166,100,.12)} 50%{box-shadow:0 0 0 6px rgba(201,166,100,.11),0 0 22px rgba(201,166,100,.3)} }
@keyframes stack-reveal { from { opacity:.3; transform:translate(-50%,calc(-50% - var(--disc-rise))) rotateY(88deg) scale(.9); } to { opacity:1; transform:translate(-50%,calc(-50% - var(--disc-rise))) rotateY(0); } }
@keyframes public-reveal { from { opacity:0; transform:translateY(8px) scale(.92); } to { opacity:1; transform:none; } }
@keyframes spin { to { transform:rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .bid-orbit,.stack-zone.clickable,.table-disc.revealed,.reveal-broadcast li { animation:none; }.table-disc,.player-seat,.hand-disc { transition:none; } }
@media (min-width: 701px) {
  .skull-game.many-players .phase-banner { top:auto;bottom:16px;width:min(280px,28%); }
  .skull-game.many-players .history-drawer { top:auto;bottom:16px; }
}
@media (min-width: 701px) and (max-height: 820px) {
  .skull-game { min-height:max(600px,calc(100dvh - 112px));grid-template-rows:auto minmax(420px,1fr) auto; }
  .skull-header { min-height:64px;padding-top:8px;padding-bottom:8px; }
  .scene-stage { min-height:420px; }
  .ritual-table,.table-shadow { height:74%; }
  .action-dock,.result-dock { margin-bottom:10px; }
  .result-dock { padding-top:11px;padding-bottom:11px; }
}
@media (max-width: 980px) {
  .skull-game { min-height:max(780px,calc(100dvh - 80px)); grid-template-rows:auto minmax(500px,1fr) auto; }
  .skull-header { grid-template-columns:auto 1fr auto; }.match-metrics > span:nth-child(2) { display:none; }.match-metrics > span { min-width:58px; }.header-button span { display:none; }.header-button { min-width:38px; }
  .ritual-table,.table-shadow { width:78%; height:66%; }.player-seat { width:clamp(130px,18vw,172px); }.seat-nameplate { grid-template-columns:30px minmax(0,1fr); }.player-avatar { width:30px; }.win-track { position:absolute; right:6px; bottom:-11px; }.phase-banner { width:min(260px,38%); }.history-drawer { width:min(320px,44%); }
  .reveal-broadcast { width:min(500px,58%); }
  .action-dock { grid-template-columns:minmax(0,1.2fr) minmax(300px,.8fr); }.private-hand { padding-left:12px;padding-right:12px; }.hand-disc { flex-basis:82px; }.bid-console { grid-template-columns:1fr 1fr; }.bid-console .bid-stepper { grid-column:1/-1; }
}
@media (max-width: 700px) {
  .skull-game { min-height:100dvh; grid-template-rows:auto 535px auto; border-radius:18px; overflow:clip; }
  .skull-header { min-height:64px; grid-template-columns:1fr auto; padding:10px 12px; }.brand-mark { width:36px; }.brand-lockup h2 { font-size:21px; }.match-metrics { grid-column:1/-1; grid-row:2; justify-content:stretch; order:3; }.match-metrics > span { flex:1; min-width:0; min-height:36px; }.header-actions { position:absolute; right:9px; top:10px; }.brand-lockup { padding-right:130px; }
  .scene-stage { min-height:535px; }.ritual-table,.table-shadow { top:49%; width:94%; height:59%; }.player-seat { width:120px; }.seat-nameplate { grid-template-columns:27px minmax(0,1fr); gap:5px; padding:5px 6px; border-radius:10px; }.player-avatar { width:27px; border-radius:8px;font-size:10px; }.player-copy b { font-size:8px; }.player-copy small,.seat-counters,.seat-flags { font-size:5px; }.win-track i { width:16px; }.stack-zone { width:82px;height:72px; }.table-disc { width:52px; }.bid-core { top:49%; width:104px; }.bid-core strong { font-size:32px; }.phase-banner { left:8px;top:8px;width:calc(100% - 16px);max-width:none;min-height:49px;padding:7px 9px; }.phase-icon { width:32px; }.phase-banner em { max-width:76vw; }.history-drawer { right:8px;top:64px;width:min(340px,calc(100% - 16px)); }.history-drawer:not(.open) { width:126px; }.drawer-toggle { padding:11px 12px; }.drawer-toggle b { font-size:12px; }.history-drawer p { font-size:11px; }.rules-content section { grid-template-columns:36px 1fr; gap:11px; padding:14px 0; }.rules-content section > span { width:34px; font-size:12px; }.rules-content h3 { font-size:15px; }.rules-content p { font-size:12px; }
  .reveal-broadcast { top:calc(49% + 70px); width:min(430px,68%); }.reveal-broadcast header small { display:none; }
  .action-dock { grid-template-columns:1fr; margin:0 8px 8px; border-radius:16px; }.private-hand { border-right:0;border-bottom:1px solid rgba(255,255,255,.07); }.private-hand header small { display:none; }.hand-row { padding-bottom:7px; }.hand-disc { flex-basis:76px; }.action-console { padding:12px; }.split-actions { grid-template-columns:1fr; }.or-divider { display:none; }.bid-action { grid-template-columns:1fr auto; }.bid-console { grid-template-columns:1fr 1fr; }.result-dock { grid-template-columns:auto 1fr; margin:0 8px 8px; }.result-record { grid-column:1/-1; }.result-dock > .plugin-button { grid-column:1/-1; }.result-copy p { white-space:normal; }
}
@media (max-width: 430px) {
  .skull-game { grid-template-rows:auto 505px auto; }.scene-stage { min-height:505px; }.player-seat { width:106px; }.seat-nameplate { grid-template-columns:24px minmax(0,1fr); }.player-avatar { width:24px; }.win-track { display:none; }.stack-zone { width:70px;height:63px; }.table-disc { width:46px; }.bid-core { width:91px; }.bid-core strong { font-size:29px; }.bid-core > span { font-size:6px; }.phase-banner { display:none; }.history-drawer { top:8px; }.hand-disc { flex-basis:70px; }.console-heading b { font-size:10px; }.bid-console { grid-template-columns:1fr; }.bid-console .plugin-button { width:100%; }.self-penalty { grid-template-columns:1fr; }
}
</style>
