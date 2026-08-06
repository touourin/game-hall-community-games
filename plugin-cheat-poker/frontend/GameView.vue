<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Eye, Layers3, Trophy } from '@lucide/vue'
import {
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'

type RankOption = { rank: string; label: string }
type CheatCard = {
  id: string
  rank: string
  suit: string
  suitLabel: string
  label: string
  isJoker: boolean
}
type LastPlay = {
  playerId: string
  playerName: string
  claimedRank: string
  claimedLabel: string
  count: number
}
type HistoryEntry = {
  type: string
  message: string
  truthful?: boolean
  revealedCards?: CheatCard[]
}
type CheatPokerGame = {
  dealerPlayerId?: string | null
  currentPlayerId?: string | null
  stage?: 'play' | 'challenge'
  requiredRank?: string | null
  requiredRankLabel?: string | null
  rankOptions?: RankOption[]
  hand?: CheatCard[]
  cardCounts?: Record<string, number>
  activePlayerIds?: string[]
  forfeitedPlayerIds?: string[]
  pileCount?: number
  pileLimit?: number
  pileLocked?: boolean
  archivedCount?: number
  lastPlay?: LastPlay | null
  winnerTarget?: number
  rankings?: string[]
  scores?: Record<string, number>
  history?: HistoryEntry[]
  canPlay?: boolean
  canAccept?: boolean
  canChallenge?: boolean
  isOpening?: boolean
  myRank?: number | null
}

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const selectedCardIds = ref<string[]>([])
const selectedRank = ref('3')
const busy = ref(false)

const game = computed(() => props.snapshot.game as CheatPokerGame)
const hand = computed(() => game.value.hand ?? [])
const rankOptions = computed(() => game.value.rankOptions ?? [])
const declaredRank = computed(() => game.value.requiredRank ?? selectedRank.value)
const selectedCards = computed(() => (
  hand.value.filter((card) => selectedCardIds.value.includes(card.id))
))
const currentPlayer = computed(() => (
  props.snapshot.players.find((player) => player.id === game.value.currentPlayerId)
))
const rankedIds = computed(() => game.value.rankings ?? [])
const history = computed(() => [...(game.value.history ?? [])].reverse())
const canSubmit = computed(() => (
  props.snapshot.phase === 'playing'
  && game.value.canPlay === true
  && selectedCardIds.value.length >= 1
  && selectedCardIds.value.length <= 3
  && Boolean(declaredRank.value)
  && !busy.value
))
const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return '本局排名已确定'
  if (game.value.stage === 'challenge') {
    return game.value.canAccept ? '由你决定：相信还是质疑' : '上一手正在接受质疑'
  }
  return game.value.canPlay ? '轮到你暗扣手牌' : `等待 ${currentPlayer.value?.name ?? '下一位玩家'} 出牌`
})
const statusDetail = computed(() => {
  if (props.snapshot.phase === 'finished') {
    return `本局产生 ${game.value.winnerTarget ?? 0} 位获胜者`
  }
  if (game.value.stage === 'challenge' && game.value.lastPlay) {
    const claim = game.value.lastPlay
    return `${claim.playerName} 声称打出 ${claim.count} 张 ${claim.claimedLabel}`
  }
  if (game.value.canPlay) {
    return game.value.isOpening
      ? '新牌堆：可自由选择声明点数'
      : `本手必须声明 ${game.value.requiredRankLabel}`
  }
  return '留意质疑窗口，任何在局玩家都可以揭发'
})

watch(
  () => hand.value.map((card) => card.id).join('|'),
  () => {
    const available = new Set(hand.value.map((card) => card.id))
    selectedCardIds.value = selectedCardIds.value.filter((id) => available.has(id))
  },
)

watch(
  () => game.value.requiredRank,
  (rank) => {
    if (rank) selectedRank.value = rank
  },
  { immediate: true },
)

function toggleCard(cardId: string) {
  if (!game.value.canPlay || busy.value) return
  if (selectedCardIds.value.includes(cardId)) {
    selectedCardIds.value = selectedCardIds.value.filter((id) => id !== cardId)
    return
  }
  if (selectedCardIds.value.length < 3) {
    selectedCardIds.value = [...selectedCardIds.value, cardId]
  }
}

async function playCards() {
  if (!canSubmit.value) return
  busy.value = true
  try {
    await actions.action('play', {
      cardIds: [...selectedCardIds.value],
      claimedRank: declaredRank.value,
    })
    selectedCardIds.value = []
  }
  finally {
    busy.value = false
  }
}

async function challenge() {
  if (!game.value.canChallenge || busy.value) return
  busy.value = true
  try {
    await actions.action('challenge', {})
  }
  finally {
    busy.value = false
  }
}

async function accept() {
  if (!game.value.canAccept || busy.value) return
  busy.value = true
  try {
    await actions.action('accept', {})
  }
  finally {
    busy.value = false
  }
}

function playerRank(playerId: string): number | null {
  const index = rankedIds.value.indexOf(playerId)
  return index >= 0 ? index + 1 : null
}

function playerScore(playerId: string): number | null {
  const score = game.value.scores?.[playerId]
  return typeof score === 'number' ? score : null
}

function cardText(card: CheatCard): string {
  return card.isJoker ? card.label : `${card.suitLabel}${card.label}`
}

function isRed(card: CheatCard): boolean {
  return card.suit === 'hearts' || card.suit === 'diamonds' || card.isJoker
}
</script>

<template>
  <section class="cheat-poker surface">
    <header class="game-header">
      <div>
        <small>CHEAT POKER · 54 CARDS</small>
        <h2>欺诈者</h2>
        <p>牌面可以骗人，牌数不能。</p>
      </div>
      <div class="header-metrics" aria-label="牌局信息">
        <span><b>{{ game.pileCount ?? 0 }}</b> / {{ game.pileLimit ?? 15 }} 牌堆</span>
        <span><b>{{ game.archivedCount ?? 0 }}</b> 已封存</span>
      </div>
    </header>

    <div class="status-banner" :class="{ mine: game.canPlay || game.canAccept }" role="status">
      <Eye v-if="game.stage === 'challenge'" :size="21" />
      <Layers3 v-else :size="21" />
      <span><strong>{{ statusTitle }}</strong><small>{{ statusDetail }}</small></span>
    </div>

    <div class="game-grid">
      <aside class="players-panel" aria-label="玩家手牌数量与排名">
        <header><span>玩家</span><small>先出完仍需通过质疑</small></header>
        <ol>
          <li
            v-for="player in snapshot.players"
            :key="player.id"
            :class="{
              current: player.id === game.currentPlayerId,
              ranked: playerRank(player.id),
              out: game.forfeitedPlayerIds?.includes(player.id),
            }"
          >
            <span class="seat-mark">{{ playerRank(player.id) ? `#${playerRank(player.id)}` : player.name.slice(0, 1) }}</span>
            <span class="player-name">
              <b>{{ player.name }}</b>
              <small v-if="game.forfeitedPlayerIds?.includes(player.id)">已退出</small>
              <small v-else-if="playerRank(player.id)">已安全出完</small>
              <small v-else>{{ game.cardCounts?.[player.id] ?? 0 }} 张手牌</small>
              <small v-if="player.id === game.dealerPlayerId" class="dealer-label">庄家</small>
            </span>
            <strong v-if="playerScore(player.id) !== null" class="score" :class="{ gain: (playerScore(player.id) ?? 0) > 0 }">
              {{ (playerScore(player.id) ?? 0) > 0 ? '+' : '' }}{{ playerScore(player.id) }}
            </strong>
            <i v-else-if="player.id === game.currentPlayerId" aria-label="当前行动玩家"></i>
          </li>
        </ol>
      </aside>

      <main class="table-area">
        <div class="felt">
          <div class="pile" :class="{ locked: game.pileLocked }" aria-label="背面朝上的出牌堆">
            <span v-if="!(game.pileCount ?? 0)" class="empty-pile">新牌堆</span>
            <i
              v-for="index in Math.min(game.pileCount ?? 0, 5)"
              v-else
              :key="index"
              :style="{
                '--stack-x': `${(index - 1) * 3}px`,
                '--stack-y': `${(index - 1) * -3}px`,
                '--stack-angle': `${(index - 3) * 1.5}deg`,
              }"
            ><em>?</em></i>
          </div>
          <div class="claim-card">
            <template v-if="game.lastPlay">
              <small>上一手声明</small>
              <strong>{{ game.lastPlay.count }} × {{ game.lastPlay.claimedLabel }}</strong>
              <span>{{ game.lastPlay.playerName }} · 牌面未公开</span>
            </template>
            <template v-else>
              <small>{{ game.isOpening ? '自由开牌' : '下一点数' }}</small>
              <strong>{{ game.requiredRankLabel ?? '任意' }}</strong>
              <span>每次暗扣 1–3 张</span>
            </template>
          </div>
        </div>

        <div v-if="snapshot.phase === 'finished'" class="settlement">
          <Trophy :size="24" />
          <div><strong>获胜排名</strong><span>按人数与名次计分，未晋级玩家 −1</span></div>
          <ol>
            <li v-for="(playerId, index) in game.rankings ?? []" :key="playerId">
              <b>第 {{ index + 1 }} 名</b>
              <span>{{ snapshot.players.find((player) => player.id === playerId)?.name ?? '玩家' }}</span>
              <strong>+{{ game.scores?.[playerId] ?? 0 }}</strong>
            </li>
          </ol>
        </div>

        <div v-else-if="game.stage === 'challenge'" class="challenge-actions">
          <button
            type="button"
            class="challenge-button"
            :disabled="!game.canChallenge || busy"
            @click="challenge"
          >
            <Eye :size="19" /><span><b>立即质疑</b><small>翻开上一手，输家收走整堆</small></span>
          </button>
          <button
            v-if="game.canAccept"
            type="button"
            class="accept-button"
            :disabled="busy"
            @click="accept"
          >
            <Check :size="19" /><span><b>{{ game.pileLocked ? '相信并封存' : '相信并继续' }}</b><small>{{ game.pileLocked ? '整堆移出，本轮重新开牌' : `轮到你声明 ${game.requiredRankLabel}` }}</small></span>
          </button>
          <p v-else>任何在局玩家都可质疑；只有下一位玩家能选择相信。</p>
        </div>

        <div v-else class="play-controls" :class="{ disabled: !game.canPlay }">
          <div class="claim-picker">
            <span>声明点数</span>
            <div v-if="game.isOpening" class="rank-grid">
              <button
                v-for="option in rankOptions"
                :key="option.rank"
                type="button"
                :class="{ selected: selectedRank === option.rank }"
                :aria-pressed="selectedRank === option.rank"
                :disabled="!game.canPlay || busy"
                @click="selectedRank = option.rank"
              >{{ option.label }}</button>
            </div>
            <strong v-else>{{ game.requiredRankLabel ?? '等待开牌' }}</strong>
          </div>
          <button type="button" class="play-button" :disabled="!canSubmit" @click="playCards">
            <Layers3 :size="20" />
            <span v-if="selectedCards.length">背面打出 {{ selectedCards.length }} 张，声称 {{ selectedCards.length }} 张 {{ declaredRank }}</span>
            <span v-else>{{ game.canPlay ? '先从手牌中选择 1–3 张' : '等待你的回合' }}</span>
          </button>
        </div>
      </main>
    </div>

    <section class="hand-panel">
      <header>
        <span><b>你的手牌</b><small>点击选择，最多三张</small></span>
        <strong>{{ hand.length }} 张</strong>
      </header>
      <div class="hand-grid">
        <button
          v-for="card in hand"
          :key="card.id"
          type="button"
          class="hand-card"
          :class="{ selected: selectedCardIds.includes(card.id), red: isRed(card) }"
          :disabled="!game.canPlay || busy"
          :aria-pressed="selectedCardIds.includes(card.id)"
          @click="toggleCard(card.id)"
        >
          <b>{{ card.label }}</b><span>{{ card.isJoker ? '★' : card.suitLabel }}</span><small>{{ cardText(card) }}</small>
        </button>
        <span v-if="!hand.length" class="empty-hand">没有手牌；等待最后一次出牌通过质疑。</span>
      </div>
    </section>

    <div class="lower-grid">
      <section class="history-panel">
        <header><b>牌局记录</b><small>仅揭发时公开真实牌面</small></header>
        <ol v-if="history.length">
          <li v-for="(entry, index) in history" :key="`${entry.type}-${index}`" :class="{ reveal: entry.type === 'challenge' }">
            <span>{{ entry.message }}</span>
            <small v-if="entry.revealedCards?.length">翻开：{{ entry.revealedCards.map(cardText).join('、') }}</small>
          </li>
        </ol>
        <p v-else>等待第一手牌。</p>
      </section>
      <section class="rules-panel">
        <header><b>关键规则</b><small>{{ game.winnerTarget ?? 0 }} 个获胜名额</small></header>
        <ul>
          <li>新牌堆可任意开点；随后按 3 → … → K → A → 2 循环。</li>
          <li>大小王均为癞子；声明中的每一张牌都必须匹配才算实话。</li>
          <li>达到 15 张后不能续牌：质疑，或相信并封存。</li>
          <li>最后一手仍能被揭发，通过后才正式获得排名。</li>
          <li>4/5/6 人局分别取前 1/2/3 名；积分为 3、3/1、3/2/1，其余 −1。</li>
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.cheat-poker { width: min(100%, 1120px); min-width: 0; max-width: 100%; display: grid; gap: 16px; margin: 0 auto; padding: clamp(14px, 2.5vw, 26px); overflow: hidden; }
.game-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--line); padding-bottom: 15px; }.game-header small { color: var(--gold); font-size: 8px; font-weight: 900; letter-spacing: .17em; }.game-header h2 { margin: 3px 0 0; font-family: "Songti SC", "STSong", serif; font-size: clamp(30px, 5vw, 44px); line-height: 1; }.game-header p { margin: 7px 0 0; color: var(--muted); font-size: 10px; }.header-metrics { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px; }.header-metrics span { border: 1px solid var(--line); border-radius: 999px; padding: 7px 10px; color: var(--muted); background: var(--surface-inset); font-size: 9px; white-space: nowrap; }.header-metrics b { color: var(--gold); font-size: 13px; }
.status-banner { min-width: 0; min-height: 68px; display: flex; align-items: center; gap: 12px; border: 1px solid var(--line); border-radius: 15px; padding: 12px 14px; color: var(--muted); background: var(--surface-inset); }.status-banner.mine { border-color: color-mix(in srgb, var(--gold) 52%, var(--line)); color: var(--gold); background: color-mix(in srgb, var(--gold) 8%, var(--surface-inset)); }.status-banner > span { min-width: 0; display: grid; gap: 4px; }.status-banner strong { overflow: hidden; color: var(--text); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }.status-banner small { color: var(--muted); font-size: 9px; line-height: 1.45; }
.game-grid { min-width: 0; display: grid; grid-template-columns: minmax(190px, .52fr) minmax(0, 1.48fr); gap: 14px; }.players-panel,.table-area,.hand-panel,.history-panel,.rules-panel { min-width: 0; border: 1px solid var(--line); border-radius: 17px; background: color-mix(in srgb, var(--surface-elevated) 44%, transparent); }.players-panel { padding: 13px; }.players-panel > header,.hand-panel > header,.history-panel > header,.rules-panel > header { display: flex; align-items: center; justify-content: space-between; gap: 8px; border-bottom: 1px solid var(--line); padding-bottom: 10px; }.players-panel header > span,.hand-panel header > span { display: grid; gap: 3px; }.players-panel header span,.hand-panel header b,.history-panel header b,.rules-panel header b { color: var(--gold); font-size: 9px; font-weight: 900; letter-spacing: .09em; }.players-panel header small,.hand-panel header small,.history-panel header small,.rules-panel header small { color: var(--muted); font-size: 7px; }.players-panel ol { display: grid; gap: 7px; margin: 11px 0 0; padding: 0; list-style: none; }.players-panel li { min-width: 0; display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 8px; border: 1px solid transparent; border-radius: 11px; padding: 7px; }.players-panel li.current { border-color: color-mix(in srgb, var(--gold) 42%, var(--line)); background: color-mix(in srgb, var(--gold) 7%, var(--surface-inset)); }.players-panel li.ranked { background: color-mix(in srgb, var(--gold) 5%, var(--surface-inset)); }.players-panel li.out { opacity: .5; }.seat-mark { width: 34px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid var(--line); border-radius: 10px; color: var(--gold); background: var(--surface-inset); font-size: 10px; font-weight: 900; }.player-name { min-width: 0; display: grid; gap: 2px; }.player-name b,.player-name small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.player-name b { font-size: 10px; }.player-name small { color: var(--muted); font-size: 8px; }.player-name .dealer-label { color: var(--gold); font-size: 7px; font-weight: 900; letter-spacing: .08em; }.players-panel li > i { width: 7px; height: 7px; border-radius: 50%; background: var(--gold); box-shadow: 0 0 0 4px color-mix(in srgb, var(--gold) 12%, transparent); }.score { color: var(--muted); font-size: 12px; }.score.gain { color: var(--gold); }
.table-area { display: grid; gap: 13px; padding: 15px; }.felt { min-height: 245px; display: grid; grid-template-columns: minmax(130px, .8fr) minmax(150px, 1.2fr); place-items: center; gap: 18px; border: 1px solid color-mix(in srgb, var(--gold) 20%, var(--line)); border-radius: 18px; padding: 20px; background: radial-gradient(circle at 40% 45%, color-mix(in srgb, var(--gold) 8%, transparent), transparent 52%), var(--surface-inset); }.pile { position: relative; width: 110px; height: 145px; display: grid; place-items: center; border: 1px dashed color-mix(in srgb, var(--gold) 34%, var(--line)); border-radius: 13px; }.pile.locked { border-color: var(--gold); box-shadow: 0 0 0 4px color-mix(in srgb, var(--gold) 8%, transparent); }.empty-pile { color: var(--muted); font-size: 9px; }.pile i { position: absolute; width: 86px; height: 118px; display: grid; place-items: center; transform: translate(var(--stack-x), var(--stack-y)) rotate(var(--stack-angle)); border: 2px solid color-mix(in srgb, var(--gold) 46%, var(--line)); border-radius: 10px; color: color-mix(in srgb, var(--gold) 75%, var(--text)); background: repeating-linear-gradient(45deg, color-mix(in srgb, var(--gold) 12%, var(--surface-elevated)) 0 5px, var(--surface-elevated) 5px 10px); box-shadow: 0 8px 18px color-mix(in srgb, var(--bg) 38%, transparent); }.pile em { width: 42px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--gold) 50%, transparent); border-radius: 50%; font-size: 20px; font-style: normal; font-weight: 900; }.claim-card { width: 100%; min-width: 0; display: grid; gap: 7px; text-align: center; }.claim-card small { color: var(--muted); font-size: 8px; font-weight: 800; letter-spacing: .1em; }.claim-card strong { color: var(--gold); font-family: "Songti SC", "STSong", serif; font-size: clamp(30px, 5vw, 46px); }.claim-card span { overflow: hidden; color: var(--muted); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.challenge-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }.challenge-actions button,.play-button { min-width: 0; min-height: 62px; display: flex; align-items: center; justify-content: center; gap: 10px; border-radius: 13px; padding: 10px 12px; cursor: pointer; }.challenge-actions button > span { min-width: 0; display: grid; gap: 3px; text-align: left; }.challenge-actions b { font-size: 11px; }.challenge-actions small { overflow: hidden; color: var(--muted); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.challenge-button { border: 1px solid color-mix(in srgb, #d75b60 60%, var(--line)); color: #e26a70; background: color-mix(in srgb, #d75b60 8%, var(--surface-inset)); }.accept-button { border: 1px solid color-mix(in srgb, var(--gold) 46%, var(--line)); color: var(--gold); background: color-mix(in srgb, var(--gold) 7%, var(--surface-inset)); }.challenge-actions button:disabled,.play-button:disabled { opacity: .4; cursor: not-allowed; }.challenge-actions > p { grid-column: 1 / -1; margin: 0; color: var(--muted); font-size: 9px; text-align: center; }
.play-controls { min-width: 0; display: grid; gap: 10px; }.play-controls.disabled { opacity: .62; }.claim-picker { min-width: 0; display: grid; gap: 8px; }.claim-picker > span { color: var(--muted); font-size: 8px; font-weight: 900; letter-spacing: .1em; }.claim-picker > strong { min-height: 45px; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--gold) 36%, var(--line)); border-radius: 11px; color: var(--gold); background: color-mix(in srgb, var(--gold) 6%, var(--surface-inset)); font-size: 18px; }.rank-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }.rank-grid button { min-width: 0; min-height: 42px; border: 1px solid var(--line); border-radius: 8px; color: var(--muted); background: var(--surface-inset); font-size: 9px; font-weight: 900; cursor: pointer; }.rank-grid button.selected { border-color: var(--gold); color: var(--accent-contrast); background: var(--gold); }.play-button { width: 100%; border: 1px solid color-mix(in srgb, var(--gold) 50%, var(--line)); color: var(--accent-contrast); background: var(--gold); font-size: 10px; font-weight: 900; }
.hand-panel { padding: 14px; }.hand-panel header > strong { color: var(--gold); font-size: 13px; }.hand-grid { min-width: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(56px, 1fr)); gap: 7px; padding-top: 12px; }.hand-card { min-width: 0; min-height: 88px; display: grid; align-content: space-between; justify-items: start; border: 1px solid var(--line); border-radius: 10px; padding: 7px; color: var(--text); background: linear-gradient(145deg, color-mix(in srgb, white 5%, var(--surface-elevated)), var(--surface-inset)); box-shadow: 0 5px 12px color-mix(in srgb, var(--bg) 24%, transparent); cursor: pointer; transition: transform .14s ease, border-color .14s ease; }.hand-card b { font-size: 15px; }.hand-card > span { justify-self: center; font-size: 22px; }.hand-card small { width: 100%; overflow: hidden; color: var(--muted); font-size: 7px; text-align: right; text-overflow: ellipsis; white-space: nowrap; }.hand-card.red { color: #d75b60; }.hand-card.selected { transform: translateY(-7px); border-color: var(--gold); box-shadow: 0 8px 18px color-mix(in srgb, var(--gold) 18%, transparent); }.hand-card:disabled { cursor: default; }.empty-hand { grid-column: 1 / -1; padding: 22px 8px; color: var(--muted); font-size: 9px; text-align: center; }
.lower-grid { min-width: 0; display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(240px, .8fr); gap: 14px; }.history-panel,.rules-panel { padding: 13px; }.history-panel ol { max-height: 235px; display: grid; gap: 6px; margin: 10px 0 0; padding: 0; overflow: auto; list-style: none; }.history-panel li { display: grid; gap: 4px; border-left: 2px solid var(--line); padding: 6px 8px; color: var(--muted); font-size: 8px; line-height: 1.45; }.history-panel li.reveal { border-left-color: var(--gold); color: var(--text); background: color-mix(in srgb, var(--gold) 4%, transparent); }.history-panel li small { color: var(--gold); font-size: 8px; }.history-panel > p { margin: 18px 0 5px; color: var(--muted); font-size: 9px; text-align: center; }.rules-panel ul { display: grid; gap: 8px; margin: 10px 0 0; padding-left: 17px; color: var(--muted); font-size: 8px; line-height: 1.55; }
@media (hover: hover) { .hand-card:hover:not(:disabled) { border-color: color-mix(in srgb, var(--gold) 62%, var(--line)); transform: translateY(-4px); }.hand-card.selected:hover { transform: translateY(-7px); }.challenge-actions button:hover:not(:disabled),.play-button:hover:not(:disabled) { filter: brightness(1.08); } }
@media (max-width: 760px) { .game-grid,.lower-grid { grid-template-columns: 1fr; }.players-panel ol { grid-template-columns: repeat(2, minmax(0, 1fr)); }.table-area { grid-row: 1; }.players-panel { grid-row: 2; }.felt { min-height: 220px; }.rank-grid { grid-template-columns: repeat(7, minmax(34px, 1fr)); }.hand-grid { grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); } }
@media (max-width: 480px) { .cheat-poker { gap: 11px; padding: 13px 10px; }.game-header { align-items: flex-start; }.header-metrics { display: grid; justify-items: end; }.status-banner { min-height: 62px; padding: 10px; }.felt { min-height: 205px; grid-template-columns: 112px minmax(0, 1fr); gap: 8px; padding: 13px 8px; }.pile { width: 94px; height: 132px; }.pile i { width: 76px; height: 105px; }.claim-card strong { font-size: 29px; }.challenge-actions { grid-template-columns: 1fr; }.players-panel ol { grid-template-columns: 1fr; }.rank-grid { grid-template-columns: repeat(7, minmax(0, 1fr)); }.hand-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 5px; }.hand-card { min-height: 80px; padding: 5px; }.hand-card b { font-size: 12px; }.hand-card > span { font-size: 18px; }.lower-grid { gap: 11px; } }
@media (max-width: 350px) { .hand-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }.game-header p { display: none; }.header-metrics span { padding: 6px 8px; }.felt { grid-template-columns: 96px minmax(0, 1fr); }.pile { width: 84px; }.pile i { width: 68px; } }
</style>
