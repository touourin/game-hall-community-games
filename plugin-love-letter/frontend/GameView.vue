<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  PluginButton,
  usePluginFullscreen,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import CharacterCard from './components/CharacterCard.vue'
import EffectLayer from './components/EffectLayer.vue'
import type {
  CardCatalogItem,
  LoveCard,
  LoveEvent,
  LoveLetterView,
  LovePlayerView,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const root = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported: fullscreenSupported, toggle: toggleFullscreen } = usePluginFullscreen(root)
const selectedCardId = ref<string | null>(null)
const selectedTargetId = ref<string | null>(null)
const selectedGuessTypeId = ref<string | null>(null)
const chancellorKeepId = ref<string | null>(null)
const reverseBottomOrder = ref(false)
const rulesOpen = ref(false)
const busy = ref(false)
const animationEvent = ref<LoveEvent | null>(null)
let animationTimer: ReturnType<typeof setTimeout> | null = null
let lastSeenEvent = 0
let lastEventSignature = ''
const eventQueue: LoveEvent[] = []

const game = computed(() => props.snapshot.game as unknown as LoveLetterView)
const selfId = computed(() => props.snapshot.self?.id ?? props.snapshot.viewer?.targetPlayerId ?? '')
const selfPlayer = computed(() => game.value.players.find(player => player.id === selfId.value) ?? null)
const hand = computed(() => selfPlayer.value?.visibleHand ?? [])
const sortedPlayers = computed(() => [...game.value.players].sort((a, b) => a.seat - b.seat))
const opponents = computed(() => {
  const players = sortedPlayers.value
  const selfIndex = players.findIndex(player => player.id === selfId.value)
  if (selfIndex < 0) return players.slice(1)
  return [...players.slice(selfIndex + 1), ...players.slice(0, selfIndex)]
})
const currentPlayer = computed(() => game.value.players.find(player => player.id === game.value.currentPlayerId) ?? null)
const selectedCard = computed(() => hand.value.find(card => card.id === selectedCardId.value) ?? null)
const pending = computed(() => game.value.pendingChoice)
const candidatePlayers = computed(() => (
  (pending.value?.candidatePlayerIds ?? [])
    .map(id => game.value.players.find(player => player.id === id))
    .filter((player): player is LovePlayerView => Boolean(player))
))
const guessCards = computed(() => (
  (pending.value?.candidateCardTypeIds ?? [])
    .map(id => game.value.cardCatalog.find(card => card.typeId === id))
    .filter((card): card is CardCatalogItem => Boolean(card))
))
const latestPlayedCard = computed<LoveCard | null>(() => {
  const all = game.value.players.flatMap(player => player.played.map(entry => ({ ...entry, seat: player.seat })))
  return all.sort((a, b) => a.turnNumber - b.turnNumber || a.seat - b.seat).at(-1)?.card ?? null
})
const publicHistory = computed(() => game.value.events.filter(event => !['draw_card', 'chancellor_draw'].includes(event.kind)).slice(-7).reverse())
const canDraw = computed(() => game.value.actions.includes('draw_card'))
const canPlay = computed(() => game.value.actions.includes('play_card'))
const canResolve = computed(() => Boolean(game.value.actions.includes('resolve_choice') && pending.value?.isActor))
const canNextRound = computed(() => game.value.actions.includes('next_round'))
const canSubmitChoice = computed(() => {
  if (!canResolve.value || !pending.value) return false
  if (pending.value.kind === 'target') return Boolean(selectedTargetId.value)
  if (pending.value.kind === 'guess') return Boolean(selectedTargetId.value && selectedGuessTypeId.value)
  return Boolean(chancellorKeepId.value)
})
const chancellorBottomCards = computed(() => {
  const cards = (pending.value?.privateCards ?? []).filter(card => card.id !== chancellorKeepId.value)
  return reverseBottomOrder.value ? [...cards].reverse() : cards
})
const stageText = computed(() => {
  if (props.snapshot.phase === 'finished' || game.value.stage === 'finished') return '整局完成'
  if (game.value.stage === 'round_summary') return '本轮密封结算完成'
  if (game.value.currentPlayerId !== selfId.value) return `等待 ${currentPlayer.value?.name ?? '玩家'} 行动`
  if (game.value.stage === 'draw') return '你的回合 · 从牌堆抽一张'
  if (game.value.stage === 'play') return '你的回合 · 打出一张合法角色牌'
  if (game.value.stage === 'choice') return pending.value?.promptZh ?? '完成角色牌效果'
  return '宫廷正在结算牌效'
})

watch(
  () => {
    const choice = game.value.pendingChoice
    return choice
      ? `${choice.choiceId}:${choice.sourceTypeId}:${choice.privateCards.map(card => card.id).join('|')}`
      : ''
  },
  () => {
    selectedTargetId.value = null
    selectedGuessTypeId.value = null
    chancellorKeepId.value = game.value.pendingChoice?.privateCards[0]?.id ?? null
    reverseBottomOrder.value = false
  },
  { immediate: true },
)

watch(
  () => {
    const event = game.value.events.at(-1)
    return event ? `${game.value.roundNumber}:${game.value.players.length}:${event.seq}:${event.kind}:${event.messageZh}` : ''
  },
  () => {
    const events = game.value.events
    if (!events.length) return
    const latest = events.at(-1)!
    const signature = `${game.value.roundNumber}:${game.value.players.length}:${latest.seq}:${latest.kind}:${latest.messageZh}`
    if (signature === lastEventSignature) return
    lastEventSignature = signature
    if (lastSeenEvent === 0 || latest.seq <= lastSeenEvent) {
      lastSeenEvent = latest.seq
      eventQueue.length = 0
      eventQueue.push(latest)
    } else {
      const incoming = events.filter(event => event.seq > lastSeenEvent)
      if (incoming.length) {
        lastSeenEvent = incoming.at(-1)!.seq
        if (incoming.length > 6) {
          eventQueue.length = 0
          if (animationTimer) clearTimeout(animationTimer)
          animationTimer = null
          animationEvent.value = null
          eventQueue.push(incoming.at(-1)!)
        } else {
          eventQueue.push(...incoming)
        }
      }
    }
    playNextAnimation()
  },
  { immediate: true },
)

watch(
  () => hand.value.map(card => card.id).join('|'),
  () => {
    if (selectedCardId.value && !hand.value.some(card => card.id === selectedCardId.value)) {
      selectedCardId.value = null
    }
  },
)

onUnmounted(() => {
  if (animationTimer) clearTimeout(animationTimer)
})

function playNextAnimation(): void {
  if (animationEvent.value || !eventQueue.length) return
  animationEvent.value = eventQueue.shift() ?? null
  animationTimer = setTimeout(() => {
    animationEvent.value = null
    animationTimer = null
    playNextAnimation()
  }, 1120)
}

function playerName(id: string | null | undefined): string {
  return game.value.players.find(player => player.id === id)?.name ?? '未知玩家'
}

function isChoiceCandidate(id: string): boolean {
  return canResolve.value && (pending.value?.candidatePlayerIds.includes(id) ?? false)
}

function selectHandCard(card: LoveCard): void {
  if (!canPlay.value || !game.value.legalCardIds.includes(card.id)) return
  selectedCardId.value = selectedCardId.value === card.id ? null : card.id
}

async function perform(action: string, payload: Record<string, unknown> = {}): Promise<void> {
  if (busy.value) return
  busy.value = true
  try {
    await actions.action(action, { ...payload, turnNumber: game.value.turnNumber })
  } finally {
    busy.value = false
  }
}

async function drawCard(): Promise<void> {
  await perform('draw_card')
}

async function playSelected(): Promise<void> {
  if (!selectedCard.value) return
  const cardId = selectedCard.value.id
  selectedCardId.value = null
  await perform('play_card', { cardId })
}

async function resolveChoice(): Promise<void> {
  if (!pending.value?.choiceId || !canSubmitChoice.value) return
  const payload: Record<string, unknown> = { choiceId: pending.value.choiceId }
  if (pending.value.kind === 'target') payload.targetPlayerId = selectedTargetId.value
  if (pending.value.kind === 'guess') {
    payload.targetPlayerId = selectedTargetId.value
    payload.cardTypeId = selectedGuessTypeId.value
  }
  if (pending.value.kind === 'chancellor') {
    payload.keepCardId = chancellorKeepId.value
    payload.bottomCardIds = chancellorBottomCards.value.map(card => card.id)
  }
  await perform('resolve_choice', payload)
}

async function nextRound(): Promise<void> {
  await perform('next_round', { roundNumber: game.value.roundNumber })
}
</script>

<template>
  <section
    ref="root"
    class="love-letter-game"
    :class="{ 'is-fullscreen': isFullscreen }"
    data-layout="browser-fill"
    :data-player-count="game.players.length"
    :data-scene-id="game.sceneId"
  >
    <div class="palace-shell">
      <div class="palace-light" aria-hidden="true" />
      <header class="court-hud">
        <div class="brand-lockup">
          <span class="brand-seal" aria-hidden="true">情</span>
          <span><small>THE SEALED COURT</small><h2>情书 <em>密封宫廷</em></h2></span>
        </div>
        <div class="turn-banner" :class="{ mine: game.currentPlayerId === selfId }">
          <small>ROUND {{ game.roundNumber }} · TURN {{ game.turnNumber }}</small>
          <strong>{{ stageText }}</strong>
        </div>
        <div class="hud-metrics">
          <span><small>规则</small><b>皇后 7½</b></span>
          <span :class="{ sealed: game.sealedCardCount === 1 }"><small>牌堆</small><b>{{ game.deckCount }} 张</b></span>
          <button type="button" class="hud-button" aria-label="打开规则说明" @click="rulesOpen = true">规则</button>
          <button v-if="fullscreenSupported" type="button" class="hud-button" :aria-label="isFullscreen ? '退出全屏' : '进入全屏'" @click="toggleFullscreen">{{ isFullscreen ? '退出' : '全屏' }}</button>
        </div>
      </header>

      <main class="court-board">
        <div class="balcony balcony-left" aria-hidden="true" /><div class="balcony balcony-right" aria-hidden="true" />
        <div class="marble-inlay" aria-hidden="true"><i /><i /><i /></div>

        <section class="opponent-ring" :class="`opponent-count-${opponents.length}`" aria-label="其他玩家座位">
          <article
            v-for="(player, index) in opponents"
            :key="player.id"
            class="player-seat opponent-seat"
            :class="{
              current: player.isCurrent,
              protected: player.protected,
              out: player.roundStatus !== 'active',
              candidate: isChoiceCandidate(player.id),
              selected: selectedTargetId === player.id,
            }"
            :data-player-id="player.id"
            :data-seat-index="index"
            @click="isChoiceCandidate(player.id) && (selectedTargetId = player.id)"
          >
            <button v-if="isChoiceCandidate(player.id)" type="button" class="seat-target" :aria-label="`选择 ${player.name}`" @click.stop="selectedTargetId = player.id" />
            <span class="portrait-token">{{ player.name.slice(0, 1) }}</span>
            <div class="seat-copy"><strong>{{ player.name }}</strong><small>{{ player.roundStatus === 'active' ? (player.isCurrent ? '正在行动' : `${player.handCount} 张隐藏手牌`) : (player.roundStatus === 'out' ? '本轮出局' : '已离席') }}</small></div>
            <span class="favor-track" :aria-label="`${player.favorTokens} 枚好感`"><i v-for="n in player.favorTarget" :key="n" :class="{ filled: n <= player.favorTokens }">♥</i></span>
            <span v-if="player.protected" class="protection-badge">◇ 侍女保护</span>
            <span class="opponent-hand" aria-hidden="true"><CharacterCard v-for="n in Math.min(player.handCount, 2)" :key="n" concealed mini /></span>
            <span class="played-ribbon" aria-label="公开出牌"><CharacterCard v-for="entry in player.played.slice(-4)" :key="`${entry.card.id}-${entry.reason}`" :card="entry.card" mini /></span>
          </article>
        </section>

        <section class="central-table" aria-label="中央宫廷牌桌">
          <div v-if="game.faceUpSetAside.length" class="set-aside-zone">
            <small>两人局 · 公开移除</small>
            <span><CharacterCard v-for="card in game.faceUpSetAside" :key="card.id" :card="card" compact /></span>
          </div>
          <div class="reserve-zone">
            <CharacterCard concealed compact :class="{ unavailable: !game.reserveAvailable }" />
            <small>暗置牌 · {{ game.reserveAvailable ? '可用于强制补牌' : '已用于补牌' }}</small>
          </div>
          <div class="draw-zone" :class="{ actionable: canDraw, sealed: game.sealedCardCount === 1 }">
            <div class="stack-shadow" aria-hidden="true" /><CharacterCard concealed />
            <b>{{ game.deckCount }}</b>
            <small v-if="game.sealedCardCount === 1">最后一张 · 永久封存</small><small v-else>角色牌堆</small>
            <button v-if="canDraw" type="button" :disabled="busy" aria-label="从角色牌堆抽一张" @click="drawCard" />
          </div>
          <div class="table-seal" aria-hidden="true"><i>✉</i><span>SECRETS<br>OF THE COURT</span></div>
          <div class="recent-zone">
            <small>最近公开角色</small>
            <CharacterCard v-if="latestPlayedCard" :card="latestPlayedCard" compact />
            <span v-else class="empty-letter">尚未出牌</span>
          </div>
        </section>

        <aside class="public-ledger" aria-label="公开宫廷记录">
          <header><small>PUBLIC LEDGER</small><strong>公开记录</strong></header>
          <ol><li v-for="event in publicHistory" :key="event.seq"><i>{{ event.seq }}</i><span>{{ event.messageZh }}</span></li></ol>
        </aside>

        <aside class="private-ledger" aria-label="仅你可见的线索">
          <header><small>PRIVATE CLUES</small><strong>私密线索</strong></header>
          <p v-if="!game.privateInfo.knownHands.length">尚未通过牧师或男爵取得线索。</p>
          <ol v-else>
            <li v-for="item in game.privateInfo.knownHands.slice(-4).reverse()" :key="`${item.subjectPlayerId}-${item.acquiredTurn}-${item.card.id}`" :class="{ stale: !item.current }">
              <CharacterCard :card="item.card" mini /><span><b>{{ playerName(item.subjectPlayerId) }}：{{ item.card.nameZh }} {{ item.card.value === 7.5 ? '7½' : item.card.value }}</b><small>第 {{ item.acquiredTurn }} 回合 · {{ item.current ? '当前仍有效' : '手牌已变化，仅作历史' }}</small></span>
            </li>
          </ol>
        </aside>

        <section v-if="selfPlayer" class="self-area" :class="{ current: selfPlayer.isCurrent, protected: selfPlayer.protected, out: selfPlayer.roundStatus !== 'active' }">
          <div class="self-seat player-seat" :data-player-id="selfPlayer.id">
            <span class="portrait-token">{{ selfPlayer.name.slice(0, 1) }}</span>
            <div class="seat-copy"><small>YOU · {{ selfPlayer.isCurrent ? '正在行动' : '宫廷密使' }}</small><strong>{{ selfPlayer.name }}</strong></div>
            <span class="favor-track"><i v-for="n in selfPlayer.favorTarget" :key="n" :class="{ filled: n <= selfPlayer.favorTokens }">♥</i></span>
            <span v-if="selfPlayer.protected" class="protection-badge">◇ 侍女保护</span>
          </div>
          <div class="self-hand" aria-label="你的手牌">
            <CharacterCard
              v-for="card in hand"
              :key="card.id"
              :card="card"
              selectable
              :selected="selectedCardId === card.id"
              :disabled="!canPlay || !game.legalCardIds.includes(card.id) || busy"
              @select="selectHandCard(card)"
            />
            <span v-if="!hand.length && selfPlayer.roundStatus !== 'active'" class="empty-hand">本轮身份已经公开</span>
          </div>
        </section>

        <div class="action-dock" aria-live="polite">
          <span><small>{{ game.sealedCardCount ? 'SEALED SHOWDOWN' : 'YOUR MOVE' }}</small><b>{{ stageText }}</b></span>
          <PluginButton v-if="canDraw" variant="primary" :disabled="busy" data-action="draw-card" @click="drawCard">抽一张牌</PluginButton>
          <PluginButton v-else-if="canPlay" variant="primary" :disabled="busy || !selectedCard" data-action="play-card" @click="playSelected">{{ selectedCard ? `打出${selectedCard.nameZh}` : '先选择一张手牌' }}</PluginButton>
          <span v-else class="waiting-mark">{{ game.stage === 'choice' ? '牌效选择中' : '静候密信' }}</span>
        </div>

        <Transition name="modal-fade">
          <section v-if="pending" class="choice-overlay" :class="`choice-${pending.kind}`" role="dialog" aria-modal="true" aria-label="牌效选择">
            <div class="choice-panel">
              <header><small>{{ pending.sourceTypeId.toUpperCase() }} EFFECT</small><h3>{{ pending.promptZh }}</h3><p v-if="!pending.isActor">等待 {{ playerName(pending.actorPlayerId) }} 完成私密选择。</p></header>
              <template v-if="pending.isActor && pending.kind !== 'chancellor'">
                <div class="target-grid" aria-label="合法目标">
                  <button v-for="player in candidatePlayers" :key="player.id" type="button" :class="{ selected: selectedTargetId === player.id }" @click="selectedTargetId = player.id"><span>{{ player.name.slice(0, 1) }}</span><b>{{ player.id === selfId ? '自己' : player.name }}</b><small>{{ player.protected ? '受保护' : '可选择' }}</small></button>
                </div>
                <div v-if="pending.kind === 'guess'" class="guess-grid" aria-label="猜测角色">
                  <CharacterCard v-for="card in guessCards" :key="card.typeId" :card="card" compact selectable :selected="selectedGuessTypeId === card.typeId" @select="selectedGuessTypeId = card.typeId" />
                </div>
              </template>
              <template v-else-if="pending.isActor">
                <div class="chancellor-layout">
                  <div><small>① 选择保留</small><div class="choice-cards"><CharacterCard v-for="card in pending.privateCards" :key="card.id" :card="card" selectable :selected="chancellorKeepId === card.id" @select="chancellorKeepId = card.id" /></div></div>
                  <div class="bottom-order"><small>② 牌底顺序 · 左侧最深</small><div><CharacterCard v-for="card in chancellorBottomCards" :key="card.id" :card="card" compact /></div><button type="button" :disabled="chancellorBottomCards.length < 2" @click="reverseBottomOrder = !reverseBottomOrder">交换牌底先后</button></div>
                </div>
              </template>
              <footer v-if="pending.isActor"><PluginButton variant="primary" :disabled="busy || !canSubmitChoice" data-action="resolve-choice" @click="resolveChoice">确认牌效</PluginButton></footer>
            </div>
          </section>
        </Transition>

        <Transition name="modal-fade">
          <section v-if="game.roundSummary && game.stage === 'round_summary'" class="result-overlay" role="dialog" aria-modal="true" aria-label="本轮结算">
            <div class="result-panel">
              <small>SEALED ROUND {{ game.roundSummary.roundNumber }}</small><h3>{{ game.roundSummary.endReason === 'one-card-left' ? '最后一张仍在信封里' : '本轮未使用牌保持密封' }}</h3><p>牌效已完整结算；最后一张牌没有翻开，也不会进入公开记录。</p>
              <div class="revealed-row"><article v-for="item in game.roundSummary.revealedHands" :key="item.playerId" :class="{ winner: game.roundSummary.roundWinnerIds.includes(item.playerId) }"><CharacterCard :card="item.card" compact /><b>{{ playerName(item.playerId) }}</b><small>{{ game.roundSummary.roundWinnerIds.includes(item.playerId) ? '本轮胜者 +1' : '本轮未胜' }}</small></article><article class="sealed-final"><CharacterCard concealed compact /><b>封存牌</b><small>身份永久保密</small></article></div>
              <p v-if="game.roundSummary.spyBonusPlayerId" class="spy-bonus">间谍奖励：{{ playerName(game.roundSummary.spyBonusPlayerId) }} 额外 +1 好感</p>
              <PluginButton variant="primary" :disabled="busy || !canNextRound" data-action="next-round" @click="nextRound">开始下一轮</PluginButton>
            </div>
          </section>
        </Transition>

        <section v-if="props.snapshot.phase === 'finished' || game.stage === 'finished'" class="result-overlay game-result" role="dialog" aria-modal="true" aria-label="整局结果">
          <div class="result-panel"><small>THE LETTER ARRIVED</small><h3>{{ game.gameWinnerIds.map(playerName).join('、') }} 赢得宫廷好感</h3><p>达到 {{ game.rules.favorTarget }} 枚好感标记。最后一张封存牌仍未公开。</p><div class="final-favors"><span v-for="player in game.players" :key="player.id" :class="{ winner: game.gameWinnerIds.includes(player.id) }"><b>{{ player.name }}</b><em>{{ player.favorTokens }} ♥</em></span></div><PluginButton variant="primary" @click="actions.restart()">再来一局</PluginButton></div>
        </section>

        <Transition name="drawer-slide"><aside v-if="rulesOpen" class="rules-drawer" role="dialog" aria-modal="true" aria-label="情书规则"><header><span><small>RULES · v{{ game.modelVersion }}</small><h3>密封宫廷规则</h3></span><button type="button" aria-label="关闭规则" @click="rulesOpen = false">×</button></header><div class="rule-callout"><b>最后一张永不翻开</b><p>当前牌效完整结算后，牌堆只剩 1 张就立即比点；王子、皇后防卫和大臣都不能取走它。</p></div><ol><li><b>抽一打一</b><span>回合开始抽一张，再从两张手牌中打出一张。</span></li><li><b>角色牌效</b><span>完整完成目标、猜测、交换或弃牌，再检查轮末。</span></li><li><b>轮胜</b><span>只剩一人，或封存牌时仍在局者手牌最高；同点共同获胜。</span></li><li><b>整局</b><span>2/3/4 人分别达到 6/5/4 枚好感即胜。</span></li></ol><div class="catalog-grid"><CharacterCard v-for="card in game.cardCatalog" :key="card.typeId" :card="card" compact :count="card.count" /></div></aside></Transition>

        <EffectLayer :key="animationEvent?.seq ?? 0" :event="animationEvent" />
      </main>
    </div>
  </section>
</template>

<style scoped>
.love-letter-game { --wine:#421726; --wine-deep:#180811; --velvet:#61273a; --paper:#fff6e3; --gold:#d9b65f; --gold-soft:#f2dc9d; --ink:#321720; position:relative; width:100%; height:calc(100dvh - 72px); min-height:600px; overflow:hidden; color:var(--paper); background:#160810; font-family:Inter,ui-sans-serif,system-ui,"Noto Sans SC",sans-serif; }
.love-letter-game.is-fullscreen { height:100dvh; min-height:100dvh; }
*,*::before,*::after{box-sizing:border-box}.palace-shell{position:relative;display:grid;grid-template-rows:64px 1fr;width:100%;height:100%;overflow:hidden;background:radial-gradient(ellipse at 50% 36%,rgba(177,89,99,.24),transparent 42%),linear-gradient(180deg,#32111f 0,#190a12 45%,#0f070c 100%)}
.palace-shell::before{content:"";position:absolute;inset:0;opacity:.16;background-image:linear-gradient(90deg,transparent 49.5%,#e2bf6c 50%,transparent 50.5%),repeating-linear-gradient(90deg,transparent 0 11.8%,rgba(222,190,116,.22) 12% 12.15%,transparent 12.35% 24%);pointer-events:none}.palace-light{position:absolute;left:50%;top:-25%;width:75%;height:76%;transform:translateX(-50%);background:conic-gradient(from 168deg at 50% 0,transparent 0 41%,rgba(255,231,164,.08) 45%,transparent 49% 52%,rgba(255,231,164,.055) 55%,transparent 60%);filter:blur(7px);pointer-events:none}
.court-hud{position:relative;z-index:50;display:grid;grid-template-columns:minmax(220px,1fr) minmax(300px,1.35fr) minmax(300px,1fr);align-items:center;gap:16px;padding:7px clamp(12px,2vw,30px);border-bottom:1px solid rgba(226,190,108,.42);background:linear-gradient(90deg,rgba(23,7,14,.96),rgba(66,20,36,.94),rgba(23,7,14,.96));box-shadow:0 8px 30px rgba(8,1,5,.45)}
.brand-lockup{display:flex;align-items:center;gap:10px;min-width:0}.brand-seal{display:grid;place-items:center;width:42px;aspect-ratio:1;border:2px double #f4d989;border-radius:50%;color:#ffe8a3;background:radial-gradient(circle at 35% 28%,#d54c68,#8c1738 68%);box-shadow:0 3px 12px #080206;font:900 21px/1 STSong,serif}.brand-lockup span:last-child{min-width:0}.brand-lockup small,.turn-banner small,.hud-metrics small{display:block;color:#d8b96c;font:700 8px/1.1 system-ui;letter-spacing:.2em}.brand-lockup h2{margin:2px 0 0;overflow:hidden;font:800 clamp(16px,1.5vw,23px)/1.05 "Noto Serif SC",STSong,serif;white-space:nowrap;text-overflow:ellipsis}.brand-lockup h2 em{color:#dcbf77;font:normal 500 12px/1 serif;letter-spacing:.1em}.turn-banner{min-width:0;padding:8px 17px;border:1px solid rgba(218,182,95,.28);border-radius:11px;text-align:center;background:rgba(16,5,10,.42)}.turn-banner.mine{border-color:#efd273;box-shadow:inset 0 0 18px rgba(236,200,106,.12)}.turn-banner strong{display:block;margin-top:3px;overflow:hidden;font-size:12px;white-space:nowrap;text-overflow:ellipsis}.hud-metrics{display:flex;align-items:center;justify-content:flex-end;gap:7px;min-width:0}.hud-metrics>span{min-width:70px;padding:6px 9px;border-left:1px solid rgba(219,184,101,.27)}.hud-metrics b{font-size:11px}.hud-metrics .sealed b{color:#ffe49a}.hud-button{min-height:36px;padding:0 10px;border:1px solid #9d7740;border-radius:8px;color:#fbe8b1;background:#3b1523;cursor:pointer}
.court-board{position:relative;min-height:0;overflow:hidden;isolation:isolate}.court-board::before{content:"";position:absolute;left:9%;right:9%;top:13%;bottom:3%;border:2px solid rgba(210,170,84,.44);border-radius:50% 50% 34% 34%;background:radial-gradient(ellipse at center,#6a3144 0,#4d2031 49%,#27101c 72%,#160912 100%);box-shadow:0 0 0 11px #170a10,0 0 0 13px rgba(222,186,101,.35),inset 0 0 90px rgba(13,3,8,.65);z-index:-2}.court-board::after{content:"";position:absolute;left:11%;right:11%;top:15%;bottom:5%;border-radius:50% 50% 34% 34%;opacity:.22;background:repeating-radial-gradient(ellipse at center,transparent 0 38px,rgba(255,244,212,.1) 39px 40px);z-index:-1}.balcony{position:absolute;top:7%;bottom:4%;width:6%;border:1px solid rgba(216,180,94,.35);background:linear-gradient(90deg,#13070c,#4c2130 60%,#1b0a12);box-shadow:inset 0 0 30px #080205;z-index:-1}.balcony::before{content:"";position:absolute;inset:5% 22%;background:repeating-linear-gradient(180deg,#d7b663 0 2px,transparent 2px 45px)}.balcony-left{left:1%;border-radius:0 80% 80% 0}.balcony-right{right:1%;border-radius:80% 0 0 80%;transform:scaleX(-1)}.marble-inlay{position:absolute;left:50%;top:46%;width:min(36vw,480px);aspect-ratio:2.4;transform:translate(-50%,-50%);border:1px solid rgba(238,208,133,.16);border-radius:50%;opacity:.3}.marble-inlay i{position:absolute;inset:18%;border:1px solid #d7b868;border-radius:50%}.marble-inlay i:nth-child(2){inset:35%;transform:rotate(45deg);border-radius:8px}.marble-inlay i:nth-child(3){inset:46%;background:#d7b868}
.opponent-ring{position:absolute;inset:0;z-index:12;pointer-events:none}.opponent-seat{position:absolute;width:clamp(188px,18vw,255px);min-height:82px}.opponent-seat>*{pointer-events:none}.opponent-seat .seat-target{position:absolute;inset:-5px;z-index:8;width:auto;height:auto;border:0;border-radius:19px;background:transparent;pointer-events:auto;cursor:pointer}.opponent-count-1 .opponent-seat{left:50%;top:3%;transform:translateX(-50%)}.opponent-count-2 .opponent-seat:nth-child(1){left:22%;top:5%;transform:translateX(-50%)}.opponent-count-2 .opponent-seat:nth-child(2){right:22%;top:5%;transform:translateX(50%)}.opponent-count-3 .opponent-seat:nth-child(1){left:2.2%;top:35%}.opponent-count-3 .opponent-seat:nth-child(2){left:50%;top:2.5%;transform:translateX(-50%)}.opponent-count-3 .opponent-seat:nth-child(3){right:2.2%;top:35%}
.player-seat{position:relative;display:grid;grid-template-columns:48px 1fr;align-items:center;gap:8px;padding:9px 12px;border:1px solid rgba(218,180,92,.45);border-radius:15px;background:linear-gradient(145deg,rgba(51,20,31,.96),rgba(24,8,15,.96));box-shadow:0 10px 26px rgba(10,2,6,.55),inset 0 1px rgba(255,245,216,.08)}.player-seat.opponent-seat{position:absolute}.player-seat.current{border-color:#f0cf74;box-shadow:0 0 0 3px rgba(238,198,97,.12),0 10px 28px #0d0308}.player-seat.protected{border-color:#6ee7d2}.player-seat.out{opacity:.56;filter:grayscale(.6)}.player-seat.candidate{pointer-events:auto;animation:candidate-pulse 1.1s ease-in-out infinite}.player-seat.selected{outline:3px solid #f7d674;outline-offset:3px}.portrait-token{grid-row:1/3;display:grid;place-items:center;width:46px;aspect-ratio:1;border:2px double #d6b35f;border-radius:50%;color:#f8dea0;background:radial-gradient(circle at 35% 30%,#8d4052,#381523 70%);font:900 20px/1 "Noto Serif SC",serif}.seat-copy{display:grid;min-width:0}.seat-copy strong{overflow:hidden;font:800 14px/1.2 "Noto Serif SC",serif;white-space:nowrap;text-overflow:ellipsis}.seat-copy small{margin-top:3px;color:#cbbcae;font-size:9px}.favor-track{grid-column:2;display:flex;gap:2px;color:#51313c;font-size:9px}.favor-track i{font-style:normal;text-shadow:0 1px #14060c}.favor-track i.filled{color:#ef6483}.protection-badge{position:absolute;right:8px;bottom:-10px;padding:4px 8px;border:1px solid #5eead4;border-radius:999px;color:#d8fff9;background:#103b38;font:800 8px/1 system-ui}.opponent-hand{position:absolute;left:4px;top:73%;display:flex;gap:2px;transform:rotate(-9deg)}.played-ribbon{position:absolute;right:4px;top:72%;display:flex;gap:1px;max-width:104px;overflow:hidden;transform:rotate(6deg)}
.central-table{position:absolute;left:19%;right:19%;top:23%;bottom:25%;z-index:8}.draw-zone,.reserve-zone,.recent-zone,.set-aside-zone{position:absolute;display:grid;justify-items:center;gap:4px}.draw-zone{left:50%;top:44%;transform:translate(-50%,-50%)}.draw-zone .character-card{width:clamp(100px,7.5vw,128px)}.draw-zone>b{position:absolute;right:-8px;top:-8px;display:grid;place-items:center;min-width:34px;height:34px;border:2px solid #f2d58a;border-radius:50%;color:#2a101a;background:#ffe3a0;font:900 14px/1 Georgia}.draw-zone small,.reserve-zone small,.recent-zone>small,.set-aside-zone>small{color:#e7d8c2;font:700 8px/1.2 system-ui;letter-spacing:.08em;text-align:center}.draw-zone>button{position:absolute;inset:-8px;z-index:5;border:0;border-radius:14px;background:transparent;cursor:pointer}.draw-zone.actionable{filter:drop-shadow(0 0 13px rgba(255,217,125,.62));animation:deck-breathe 1.25s ease-in-out infinite}.draw-zone.sealed{filter:drop-shadow(0 0 13px rgba(231,83,115,.55))}.stack-shadow{position:absolute;inset:3px -5px -5px 5px;border:1px solid #b78a40;border-radius:10px;background:#28101a}.reserve-zone{left:27%;top:47%;transform:translate(-50%,-50%)}.reserve-zone .character-card{opacity:.82}.reserve-zone .unavailable{opacity:.25}.recent-zone{right:24%;top:46%;transform:translate(50%,-50%)}.empty-letter{display:grid;place-items:center;width:76px;aspect-ratio:2/3;border:1px dashed rgba(232,208,155,.38);border-radius:8px;color:#bca88f;font-size:9px}.table-seal{position:absolute;left:50%;top:87%;display:flex;align-items:center;gap:8px;transform:translateX(-50%);color:rgba(231,199,123,.42)}.table-seal i{display:grid;place-items:center;width:32px;aspect-ratio:1;border:1px solid;border-radius:50%;font-style:normal}.table-seal span{font:700 7px/1.2 Georgia;letter-spacing:.18em}.set-aside-zone{left:2%;top:43%;transform:translateY(-50%)}.set-aside-zone>span{display:flex}.set-aside-zone .character-card{margin-left:-38px}.set-aside-zone .character-card:first-child{margin-left:0}
.public-ledger,.private-ledger{position:absolute;z-index:15;bottom:6%;width:clamp(190px,18vw,270px);height:164px;padding:12px;border:1px solid rgba(211,175,90,.33);border-radius:14px;color:#eadfcf;background:rgba(25,8,15,.88);box-shadow:0 10px 28px rgba(7,1,4,.42);backdrop-filter:blur(7px);overflow:hidden}.public-ledger{left:2%}.private-ledger{right:2%}.public-ledger header,.private-ledger header{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid rgba(221,186,104,.2);padding-bottom:7px}.public-ledger header small,.private-ledger header small{color:#b99955;font:700 7px/1 system-ui;letter-spacing:.18em}.public-ledger header strong,.private-ledger header strong{font:800 12px/1 "Noto Serif SC",serif}.public-ledger ol,.private-ledger ol{display:grid;gap:6px;margin:8px 0 0;padding:0;list-style:none}.public-ledger li{display:grid;grid-template-columns:19px 1fr;gap:6px;color:#cfc0b2;font-size:9px;line-height:1.35}.public-ledger li i{display:grid;place-items:center;width:18px;height:18px;border:1px solid #775061;border-radius:50%;color:#d9b968;font:normal 700 7px/1 system-ui}.private-ledger>p{color:#9f8e84;font-size:9px;line-height:1.5}.private-ledger li{display:flex;align-items:center;gap:7px}.private-ledger li.stale{opacity:.5}.private-ledger li span{display:grid;min-width:0}.private-ledger li b{overflow:hidden;font-size:9px;white-space:nowrap;text-overflow:ellipsis}.private-ledger li small{color:#bca99a;font-size:7px}
.self-area{position:absolute;left:50%;bottom:2%;z-index:24;display:flex;align-items:flex-end;gap:14px;transform:translateX(-50%)}.self-seat{width:clamp(205px,17vw,250px);margin-bottom:8px}.self-hand{display:flex;align-items:flex-end;justify-content:center;min-width:140px;min-height:150px}.self-hand .character-card+.character-card{margin-left:-34px}.empty-hand{padding:18px;border:1px dashed #856070;border-radius:10px;color:#bda8b0;font-size:10px}.action-dock{position:absolute;left:50%;bottom:1.2%;z-index:40;display:none;align-items:center;gap:14px;transform:translateX(-50%);padding:7px 10px 7px 15px;border:1px solid #ad8447;border-radius:999px;background:rgba(30,9,17,.96);box-shadow:0 10px 28px #0b0206}.action-dock>span:first-child{display:grid;max-width:220px}.action-dock small{color:#d9b45d;font:700 7px/1 system-ui;letter-spacing:.18em}.action-dock b{margin-top:3px;overflow:hidden;font-size:10px;white-space:nowrap;text-overflow:ellipsis}.waiting-mark{padding:8px 13px;color:#bcaa9c;font-size:10px}.self-area+.action-dock{bottom:1.2%}
.choice-overlay,.result-overlay{position:absolute;inset:0;z-index:70;display:grid;place-items:center;padding:28px;background:radial-gradient(circle,rgba(34,9,20,.45),rgba(8,2,5,.88));backdrop-filter:blur(5px)}.choice-panel,.result-panel{width:min(880px,88vw);max-height:84%;overflow:auto;padding:clamp(18px,2.6vw,34px);border:1px solid #d1a954;border-radius:21px;color:#34202a;background:radial-gradient(circle at 50% 0,#fffaf0,#f0ddba 72%,#ddbd7e);box-shadow:0 32px 90px rgba(5,0,3,.78),inset 0 0 0 4px #fff5dd,inset 0 0 0 6px rgba(117,64,55,.5)}.choice-panel>header,.result-panel{text-align:center}.choice-panel header small,.result-panel>small{color:#8e2542;font:800 9px/1 system-ui;letter-spacing:.24em}.choice-panel h3,.result-panel h3{margin:7px 0;color:#581c31;font:900 clamp(18px,2.2vw,30px)/1.2 "Noto Serif SC",serif}.choice-panel header p,.result-panel>p{color:#765e5a;font-size:11px}.target-grid{display:flex;justify-content:center;gap:10px;margin:20px 0}.target-grid button{display:grid;justify-items:center;gap:4px;min-width:108px;padding:12px;border:1px solid #b5935d;border-radius:12px;color:#4d2632;background:#fff8e8;cursor:pointer}.target-grid button.selected{outline:3px solid #a9244b;outline-offset:2px;background:#ffe5d8}.target-grid button>span{display:grid;place-items:center;width:36px;aspect-ratio:1;border-radius:50%;color:#fff;background:#7d2944;font:900 16px/1 serif}.target-grid button b{font-size:12px}.target-grid button small{color:#876e63;font-size:8px}.guess-grid,.choice-cards{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}.choice-panel>footer{display:flex;justify-content:center;margin-top:20px}.chancellor-layout{display:grid;grid-template-columns:1fr .65fr;gap:24px;align-items:center;margin-top:18px}.chancellor-layout>div>small{display:block;margin-bottom:10px;color:#7a4d46;font-weight:800}.bottom-order{padding:15px;border:1px solid #b8955b;border-radius:13px;background:rgba(255,249,233,.6)}.bottom-order>div{display:flex;justify-content:center}.bottom-order .character-card+.character-card{margin-left:-22px}.bottom-order button{margin-top:10px;padding:8px 12px;border:1px solid #9b7442;border-radius:8px;color:#5e2636;background:#fff7e6;cursor:pointer}.bottom-order button:disabled{opacity:.45}
.result-panel{width:min(760px,90vw)}.revealed-row{display:flex;align-items:end;justify-content:center;gap:12px;margin:20px 0}.revealed-row article{display:grid;justify-items:center;gap:4px;padding:9px;border:1px solid transparent;border-radius:12px}.revealed-row article.winner{border-color:#a61f49;background:rgba(186,36,75,.1)}.revealed-row article>b{font-size:10px}.revealed-row article>small{color:#83635c;font-size:8px}.sealed-final{opacity:.82}.spy-bonus{padding:8px;border-radius:8px;color:#fff!important;background:#555e6a}.final-favors{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:20px}.final-favors span{display:flex;justify-content:space-between;padding:10px 13px;border:1px solid #bc9960;border-radius:9px}.final-favors span.winner{color:#fff;background:#8d2343}.final-favors em{font-style:normal;font-weight:900}
.rules-drawer{position:absolute;right:0;top:0;bottom:0;z-index:100;width:min(480px,94vw);overflow:auto;padding:22px;color:#3b2028;background:#fff5df;box-shadow:-20px 0 60px rgba(7,1,4,.7)}.rules-drawer>header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #cfaa68;padding-bottom:12px}.rules-drawer h3{margin:3px 0;font:900 23px/1.2 "Noto Serif SC",serif}.rules-drawer header small{color:#9a2b4a;font-size:8px;letter-spacing:.18em}.rules-drawer header button{width:38px;aspect-ratio:1;border:1px solid #aa8050;border-radius:50%;color:#6f273c;background:#fffaf0;font-size:24px;cursor:pointer}.rule-callout{margin:16px 0;padding:14px;border-left:4px solid #a91d49;background:#f4dfc2}.rule-callout b{color:#8e1b3d}.rule-callout p{margin:4px 0 0;font-size:11px;line-height:1.5}.rules-drawer>ol{display:grid;gap:9px;padding-left:22px}.rules-drawer>ol li{padding-left:4px;font-size:11px}.rules-drawer>ol b{display:block}.rules-drawer>ol span{color:#755f5b}.catalog-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;align-items:start;margin-top:18px}.catalog-grid .character-card{width:100%}
.modal-fade-enter-active,.modal-fade-leave-active{transition:opacity .2s ease}.modal-fade-enter-from,.modal-fade-leave-to{opacity:0}.drawer-slide-enter-active,.drawer-slide-leave-active{transition:transform .25s ease}.drawer-slide-enter-from,.drawer-slide-leave-to{transform:translateX(100%)}
@keyframes candidate-pulse{50%{box-shadow:0 0 0 6px rgba(247,215,120,.23),0 10px 28px #0d0308}}@keyframes deck-breathe{50%{transform:translate(-50%,-53%) scale(1.025)}}
@media (min-width:1180px){.action-dock{display:flex}.self-area{bottom:14%}.central-table{top:19%;bottom:31%}.public-ledger,.private-ledger{bottom:5%}}
@media (max-width:1179px){.court-hud{grid-template-columns:1fr 1.3fr}.hud-metrics>span:first-child{display:none}.brand-lockup h2 em{display:none}.central-table{left:15%;right:15%;bottom:29%}.public-ledger,.private-ledger{height:132px;bottom:2%;width:190px}.self-area{bottom:12%}.self-seat{display:none}.action-dock{display:flex;bottom:1.2%;transform:translateX(-50%)}.opponent-count-3 .opponent-seat:nth-child(1){left:1%;top:29%}.opponent-count-3 .opponent-seat:nth-child(3){right:1%;top:29%}}
@media (max-width:760px){.love-letter-game{height:calc(100dvh - 72px);min-height:600px}.palace-shell{grid-template-rows:55px 1fr;min-height:0}.court-hud{grid-template-columns:1fr auto;padding:6px 9px}.turn-banner{position:absolute;left:8px;right:8px;top:61px;z-index:4;padding:6px}.hud-metrics>span{display:none}.brand-seal{width:36px}.brand-lockup h2{font-size:15px}.hud-button{min-height:32px;padding:0 7px}.court-board{overflow:hidden}.court-board::before{left:-16%;right:-16%;top:13%;bottom:4%}.opponent-ring{top:47px;height:105px;display:flex;gap:7px;justify-content:center;padding:0 7px;overflow-x:auto}.opponent-seat,.opponent-count-1 .opponent-seat,.opponent-count-2 .opponent-seat:nth-child(1),.opponent-count-2 .opponent-seat:nth-child(2),.opponent-count-3 .opponent-seat:nth-child(1),.opponent-count-3 .opponent-seat:nth-child(2),.opponent-count-3 .opponent-seat:nth-child(3){position:relative;left:auto;right:auto;top:auto;flex:0 0 145px;min-height:67px;transform:none}.player-seat{grid-template-columns:35px 1fr;padding:7px}.portrait-token{width:34px}.favor-track{font-size:7px}.opponent-hand,.played-ribbon{display:none}.central-table{left:1%;right:1%;top:28%;bottom:39%}.draw-zone{top:43%}.draw-zone .character-card{width:90px}.reserve-zone{left:22%;top:48%}.reserve-zone .character-card,.recent-zone .character-card{width:60px}.recent-zone{right:19%;top:47%}.set-aside-zone{left:1%;top:95%;transform:none}.set-aside-zone .character-card{width:47px;margin-left:-24px}.table-seal{display:none}.public-ledger,.private-ledger{display:none}.self-area{left:50%;bottom:82px;gap:0}.self-hand{min-height:130px}.self-hand .character-card+.character-card{margin-left:-38px}.self-area+.action-dock{bottom:6px}.action-dock{width:calc(100% - 20px);justify-content:space-between;transform:translateX(-50%)}.action-dock>span:first-child{max-width:55%}.choice-overlay,.result-overlay{padding:9px}.choice-panel,.result-panel{width:96vw;max-height:88%;padding:16px}.target-grid{gap:6px}.target-grid button{min-width:86px;padding:8px}.guess-grid{display:grid;grid-template-columns:repeat(5,1fr)}.guess-grid .character-card{width:100%}.chancellor-layout{grid-template-columns:1fr}.choice-cards{flex-wrap:nowrap}.revealed-row{gap:4px;overflow-x:auto;justify-content:flex-start}.catalog-grid{grid-template-columns:repeat(3,1fr)}}
@media (max-width:390px){.guess-grid{grid-template-columns:repeat(4,1fr)}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
</style>
