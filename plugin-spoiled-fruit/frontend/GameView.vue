<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  BookOpen,
  Check,
  ChevronLeft,
  ChevronRight,
  Eye,
  History,
  Maximize2,
  Minimize2,
  ShieldCheck,
  Sparkles,
  X,
} from '@lucide/vue'
import {
  usePluginFullscreen,
  usePluginGameActions,
  usePluginTheme,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import FruitCard from './components/FruitCard.vue'
import { cardArt, cardBackArt, effectAccent, effectDescription, runtimeTableArt } from './catalog'
import type {
  FruitCardView,
  FruitEvent,
  HandSlotView,
  PlayerBoardView,
  SpoiledFruitGameView,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const busy = ref(false)
const showRules = ref(false)
const showHistory = ref(false)
const selectedTargetId = ref<string | null>(null)
const selectedOwnCardIds = ref<string[]>([])
const selectedReturnSlot = ref<number | null>(null)
const moveToIndex = ref(0)
const incomingOrder = ref<string[]>([])
const insertionIndexes = ref<number[]>([])
const animationEvent = ref<FruitEvent | null>(null)
const animationQueue: FruitEvent[] = []
let animationTimer: number | null = null

const game = computed(() => props.snapshot.game as unknown as SpoiledFruitGameView)
const selfId = computed(() => props.snapshot.self?.id ?? '')
const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const { materials } = usePluginTheme()
const {
  isFullscreen,
  isSupported: isFullscreenSupported,
  toggle: toggleFullscreen,
} = usePluginFullscreen(gameRoot)

const rootStyle = computed<Record<string, string>>(() => ({
  '--market-art': `url("${runtimeTableArt}")`,
  '--host-copy': materials.value.copy.primary,
  '--host-line': materials.value.stage.edge,
}))
const selfBoard = computed(() => game.value.players?.find((item) => item.playerId === selfId.value) ?? null)
const opponents = computed(() => (game.value.players ?? []).filter((item) => item.playerId !== selfId.value))
const sourceBoard = computed(() => {
  const sourceId = game.value.privateChoice?.type === 'extra_draw'
    ? game.value.privateChoice.sourcePlayerId
    : game.value.drawSourcePlayerId
  return game.value.players?.find((item) => item.playerId === sourceId) ?? null
})
const targetBoard = computed(() => (
  game.value.players?.find((item) => item.playerId === selectedTargetId.value) ?? null
))
const incomingCards = computed(() => game.value.privateChoice?.incomingCards ?? [])
const incomingById = computed(() => Object.fromEntries(
  incomingCards.value.map((card) => [card.instanceId, card]),
))
const currentPlayerName = computed(() => playerName(game.value.currentPlayerId))
const drawSourceName = computed(() => playerName(sourceBoard.value?.playerId ?? null))
const canDraw = computed(() => (
  game.value.legalActions?.includes('draw_card') && !busy.value && !isSpectator.value
))
const choice = computed(() => game.value.privateChoice)
const effectColor = computed(() => effectAccent[choice.value?.effectId ?? game.value.activeEffect?.effectId ?? 'harvest'])
const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return '坏果已经揭晓'
  if (choice.value) return `等待你处理 · ${choice.value.effectLabelZh}`
  if (game.value.pendingChoice) return `等待果客完成 · ${game.value.activeEffect?.effectLabelZh ?? '果效'}`
  if (game.value.currentPlayerId === selfId.value) return `轮到你从${drawSourceName.value}摘果`
  return `等待${currentPlayerName.value}摘果`
})
const statusDetail = computed(() => {
  if (props.snapshot.phase === 'finished') return '全部 30 对水果及最后一条效果链都已结算。'
  if (choice.value) return effectDescription[choice.value.effectId] ?? '完成当前私密选择后继续结算。'
  if (game.value.activeEffect) return `${game.value.activeEffect.effectLabelZh}正在 FIFO 队首结算。`
  return '牌背从左到右的位置固定；正常抽到的新牌只会落到自己最右侧。'
})
const canSubmitOptional = computed(() => {
  const value = choice.value
  if (!value || value.type !== 'optional') return false
  if (value.effectId === 'peek_hand') return Boolean(selectedTargetId.value)
  if (value.effectId === 'shell_guard') return selectedOwnCardIds.value.length === 1
  if (value.effectId === 'careful_stocking') return selectedOwnCardIds.value.length === 1
  if (value.effectId === 'sweet_share') {
    return Boolean(selectedTargetId.value)
      && selectedOwnCardIds.value.length === 1
      && selectedReturnSlot.value !== null
  }
  return false
})
const canSubmitHalf = computed(() => (
  choice.value?.type === 'half_select'
  && selectedOwnCardIds.value.length === choice.value.selectionCount
))
const resultHolders = computed(() => game.value.finished?.oldMaidHolders ?? [])

function playerName(playerId: string | null | undefined): string {
  if (!playerId) return '无人'
  return props.snapshot.players.find((player) => player.id === playerId)?.name ?? playerId
}

function seatStyle(playerId: string): Record<string, string> {
  const players = game.value.players ?? []
  const count = Math.max(1, players.length)
  const selfIndex = Math.max(0, players.findIndex((item) => item.playerId === selfId.value))
  const index = players.findIndex((item) => item.playerId === playerId)
  const relative = (index - selfIndex + count) % count
  const angle = (90 + relative * 360 / count) * Math.PI / 180
  return {
    '--seat-x': `${50 + 43 * Math.cos(angle)}%`,
    '--seat-y': `${44 + 35 * Math.sin(angle)}%`,
  }
}

function miniCardCount(board: PlayerBoardView): number {
  return Math.min(board.handCount, 11)
}

function isSelectableOwn(cardId: string): boolean {
  const available = choice.value?.availableCardIds
  return !available || available.includes(cardId)
}

function toggleOwnCard(cardId: string) {
  if (!isSelectableOwn(cardId)) return
  const value = choice.value
  const limit = value?.type === 'half_select' ? value.selectionCount ?? 0 : 1
  const next = selectedOwnCardIds.value.filter((id) => id !== cardId)
  if (next.length === selectedOwnCardIds.value.length) {
    if (limit === 1) selectedOwnCardIds.value = [cardId]
    else if (selectedOwnCardIds.value.length < limit) selectedOwnCardIds.value = [...selectedOwnCardIds.value, cardId]
  } else {
    selectedOwnCardIds.value = next
  }
}

function selectTarget(playerId: string) {
  selectedTargetId.value = playerId
  selectedReturnSlot.value = null
}

async function send(action: string, payload: Record<string, unknown>) {
  if (busy.value || isSpectator.value) return
  busy.value = true
  try {
    await actions.action(action, payload)
  } finally {
    busy.value = false
  }
}

async function drawSlot(slot: HandSlotView) {
  if (!slot.selectable || busy.value) return
  const action = choice.value?.type === 'extra_draw' ? 'draw_extra' : 'draw_card'
  await send(action, { slotIndex: slot.index })
}

async function declineOptional() {
  await send('resolve_optional', { use: false })
}

async function submitOptional() {
  const value = choice.value
  if (!value || !canSubmitOptional.value) return
  const payload: Record<string, unknown> = { use: true }
  if (value.effectId === 'peek_hand') payload.targetPlayerId = selectedTargetId.value
  if (value.effectId === 'shell_guard') payload.cardId = selectedOwnCardIds.value[0]
  if (value.effectId === 'careful_stocking') {
    payload.cardId = selectedOwnCardIds.value[0]
    payload.toIndex = moveToIndex.value
  }
  if (value.effectId === 'sweet_share') {
    payload.targetPlayerId = selectedTargetId.value
    payload.outgoingCardId = selectedOwnCardIds.value[0]
    payload.returnSlotIndex = selectedReturnSlot.value
  }
  await send('resolve_optional', payload)
}

async function submitHalfSelection() {
  if (!canSubmitHalf.value) return
  await send('select_exchange_cards', { cardIds: selectedOwnCardIds.value })
}

function moveIncoming(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= incomingOrder.value.length) return
  const next = [...incomingOrder.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  incomingOrder.value = next
}

function placementOptionCount(index: number | string): number {
  return (choice.value?.baseHandCount ?? 0) + Number(index) + 1
}

async function submitPlacement() {
  if (!choice.value || choice.value.type !== 'insert') return
  await send('place_received', {
    orderedCardIds: incomingOrder.value,
    insertionIndexes: insertionIndexes.value,
  })
}

function resetChoice() {
  selectedTargetId.value = choice.value?.targetPlayerIds?.[0] ?? null
  selectedOwnCardIds.value = []
  selectedReturnSlot.value = null
  moveToIndex.value = Math.max(0, (selfBoard.value?.handCount ?? 1) - 1)
  incomingOrder.value = incomingCards.value.map((card) => card.instanceId)
  const base = choice.value?.baseHandCount ?? selfBoard.value?.handCount ?? 0
  insertionIndexes.value = incomingCards.value.map((_, index) => base + index)
}

function animationKind(event: FruitEvent): string | null {
  if (event.type === 'deal') return 'deal'
  if (event.type === 'initial_sweep' || event.type === 'pair') return 'pair'
  if (event.type === 'draw' || event.type === 'extra_draw') return 'draw'
  if (event.type === 'shuffle') return 'shuffle'
  if (event.type === 'skip') return 'skip'
  if (event.type === 'peek') return 'peek'
  if (event.type === 'sweet_share' || event.type === 'half_exchange') return 'exchange'
  if (event.type === 'protect') return 'protect'
  if (event.type === 'move') return 'move'
  if (event.type === 'conveyor_start' || event.type === 'market_conveyor') return 'conveyor'
  if (event.type === 'safe') return 'safe'
  if (event.type === 'finish') return 'finish'
  return null
}

function playNextAnimation() {
  if (animationEvent.value || !animationQueue.length) return
  animationEvent.value = animationQueue.shift() ?? null
  if (!animationEvent.value) return
  animationTimer = window.setTimeout(() => {
    animationEvent.value = null
    animationTimer = null
    playNextAnimation()
  }, animationEvent.value.type === 'finish' ? 1250 : 760)
}

let lastSeenSequence = game.value.eventSequence ?? 0
watch(
  () => `${choice.value?.queueId ?? ''}:${choice.value?.type ?? ''}`,
  resetChoice,
  { immediate: true },
)
watch(
  () => game.value.eventSequence,
  () => {
    const fresh = (game.value.events ?? []).filter((event) => event.sequence > lastSeenSequence)
    if (fresh.length) lastSeenSequence = Math.max(...fresh.map((event) => event.sequence))
    animationQueue.push(...fresh.filter((event) => animationKind(event)))
    playNextAnimation()
  },
)
onBeforeUnmount(() => {
  if (animationTimer !== null) window.clearTimeout(animationTimer)
})
</script>

<template>
  <section
    ref="gameRoot"
    class="spoiled-fruit"
    :class="{ fullscreen: isFullscreen }"
    :style="rootStyle"
  >
    <div class="market-wash" aria-hidden="true" />

    <header class="top-bar">
      <div class="brand">
        <small>暮市 · 标准版</small>
        <h2>坏果别留手！</h2>
      </div>
      <div class="metrics" aria-label="牌局进度">
        <span><b>{{ game.playerCount }}</b> 位果客</span>
        <span><b>{{ game.oldMaidCount }}</b> 张老鳖</span>
        <span><b>{{ game.removedPairCount }}</b> / 30 对</span>
        <span v-if="game.skipCount"><b>{{ game.skipCount }}</b> 次待跳过</span>
      </div>
      <nav class="table-tools" aria-label="牌桌工具">
        <button type="button" aria-label="查看牌局记录" @click="showHistory = true"><History :size="18" /></button>
        <button type="button" aria-label="查看完整规则" @click="showRules = true"><BookOpen :size="18" /></button>
        <button
          v-if="isFullscreenSupported"
          type="button"
          :aria-label="isFullscreen ? '退出沉浸牌桌' : '进入沉浸牌桌'"
          class="fullscreen-button"
          @click="toggleFullscreen"
        >
          <Minimize2 v-if="isFullscreen" :size="19" />
          <Maximize2 v-else :size="19" />
          <span>{{ isFullscreen ? '退出' : '沉浸' }}</span>
        </button>
      </nav>
    </header>

    <main class="table-stage">
      <article
        v-for="board in opponents"
        :key="board.playerId"
        class="seat"
        :class="{
          current: board.playerId === game.currentPlayerId,
          source: board.playerId === sourceBoard?.playerId,
          safe: board.safe,
          waiting: game.pendingChoice?.requiredPlayerIds.includes(board.playerId),
        }"
        :style="seatStyle(board.playerId)"
        :data-player-id="board.playerId"
      >
        <header>
          <span class="seat-number">{{ board.seatIndex + 1 }}</span>
          <span><b>{{ playerName(board.playerId) }}</b><small>{{ board.safe ? '安全离场' : `${board.handCount} 张 · 收获 ${board.harvestCount} 对` }}</small></span>
          <ShieldCheck v-if="board.protectedSlotIndex !== null" :size="15" aria-label="有一张硬壳保护牌" />
        </header>
        <div v-if="!board.safe" class="mini-hand" aria-hidden="true">
          <i
            v-for="index in miniCardCount(board)"
            :key="index"
            :class="{ protected: index - 1 === board.protectedSlotIndex }"
            :style="{ '--mini-index': index - 1 }"
          />
          <em v-if="board.handCount > 11">+{{ board.handCount - 11 }}</em>
        </div>
        <Sparkles v-else class="safe-spark" :size="23" aria-hidden="true" />
      </article>

      <aside class="effect-ribbon" aria-label="果效队列">
        <span class="ribbon-label">FIFO 果效队列</span>
        <ol v-if="game.effectQueue?.length">
          <li
            v-for="(effect, index) in game.effectQueue.slice(0, 5)"
            :key="effect.queueId"
            :class="{ active: index === 0 }"
            :style="{ '--effect': effectAccent[effect.effectId] }"
          >
            <b>{{ index + 1 }}</b>
            <span>{{ effect.effectLabelZh }}<small>{{ playerName(effect.ownerPlayerId) }}</small></span>
          </li>
        </ol>
        <p v-else>队列已清空</p>
      </aside>

      <section class="market-core" :style="{ '--effect': effectColor }">
        <div class="status-card" aria-live="polite">
          <span class="status-orb"><Sparkles :size="18" /></span>
          <span><strong>{{ statusTitle }}</strong><small>{{ statusDetail }}</small></span>
        </div>

        <div v-if="sourceBoard && (canDraw || choice?.type === 'extra_draw')" class="draw-tray">
          <header><b>{{ drawSourceName }}的固定牌序</b><small>选择一个未受保护的位置；抽到后自动落到你的最右侧</small></header>
          <div class="draw-sequence">
            <FruitCard
              v-for="slot in sourceBoard.handSlots"
              :key="slot.slotId"
              hidden
              compact
              :protected="slot.protected"
              :disabled="!slot.selectable || busy"
              :label="`第 ${slot.index + 1} 个位置${slot.protected ? '，受保护' : '，可暗抽'}`"
              @activate="drawSlot(slot)"
            />
          </div>
        </div>

        <section v-if="choice" class="choice-panel" :style="{ '--effect': effectColor }">
          <header>
            <span><small>私密果效选择</small><b>{{ choice.effectLabelZh }}</b></span>
            <em>{{ effectDescription[choice.effectId] }}</em>
          </header>

          <template v-if="choice.type === 'optional'">
            <div v-if="choice.targetPlayerIds?.length" class="choice-block">
              <label>选择目标</label>
              <div class="chip-row">
                <button
                  v-for="playerId in choice.targetPlayerIds"
                  :key="playerId"
                  type="button"
                  :class="{ selected: selectedTargetId === playerId }"
                  @click="selectTarget(playerId)"
                >{{ playerName(playerId) }}</button>
              </div>
            </div>

            <div v-if="['sweet_share', 'shell_guard', 'careful_stocking'].includes(choice.effectId)" class="choice-block">
              <label>{{ choice.effectId === 'sweet_share' ? '选择送出的牌' : '选择自己的牌' }}</label>
              <div class="choice-cards">
                <FruitCard
                  v-for="slot in selfBoard?.handSlots ?? []"
                  :key="slot.slotId"
                  :card="slot.card"
                  compact
                  :protected="slot.protected"
                  :selected="Boolean(slot.card && selectedOwnCardIds.includes(slot.card.instanceId))"
                  :disabled="!slot.card || !isSelectableOwn(slot.card.instanceId)"
                  @activate="slot.card && toggleOwnCard(slot.card.instanceId)"
                />
              </div>
            </div>

            <div v-if="choice.effectId === 'sweet_share' && targetBoard" class="choice-block">
              <label>从目标原有可用牌中盲选回礼</label>
              <div class="return-slots">
                <button
                  v-for="slot in targetBoard.handSlots"
                  :key="slot.slotId"
                  type="button"
                  :disabled="slot.protected"
                  :class="{ selected: selectedReturnSlot === slot.index, protected: slot.protected }"
                  @click="selectedReturnSlot = slot.index"
                >{{ slot.index + 1 }}</button>
              </div>
            </div>

            <div v-if="choice.effectId === 'careful_stocking'" class="choice-block position-picker">
              <label for="stock-position">移动到新位置</label>
              <input id="stock-position" v-model.number="moveToIndex" type="range" min="0" :max="Math.max(0, (selfBoard?.handCount ?? 1) - 1)">
              <b>第 {{ moveToIndex + 1 }} 位</b>
            </div>

            <footer>
              <button type="button" class="ghost" :disabled="busy" @click="declineOptional"><X :size="16" />放弃</button>
              <button type="button" class="primary" :disabled="!canSubmitOptional || busy" @click="submitOptional"><Check :size="16" />发动果效</button>
            </footer>
          </template>

          <template v-else-if="choice.type === 'half_select'">
            <p class="choice-note">随机目标：{{ playerName(choice.otherPlayerId) }}。秘密选 {{ choice.selectionCount }} / {{ choice.handCount }} 张；双方都锁定前不会交换。</p>
            <div class="choice-cards wide">
              <FruitCard
                v-for="slot in selfBoard?.handSlots ?? []"
                :key="slot.slotId"
                :card="slot.card"
                :protected="slot.protected"
                :selected="Boolean(slot.card && selectedOwnCardIds.includes(slot.card.instanceId))"
                :disabled="!slot.card || !isSelectableOwn(slot.card.instanceId)"
                @activate="slot.card && toggleOwnCard(slot.card.instanceId)"
              />
            </div>
            <footer><span /><button type="button" class="primary" :disabled="!canSubmitHalf || busy" @click="submitHalfSelection"><Check :size="16" />锁定 {{ choice.selectionCount }} 张</button></footer>
          </template>

          <template v-else-if="choice.type === 'insert'">
            <p class="choice-note">收到的牌可自行排序并插入任意位置；提交前不会与对方的选择一起生效。</p>
            <div class="incoming-list">
              <article v-for="(cardId, index) in incomingOrder" :key="cardId">
                <FruitCard :card="incomingById[cardId]" compact disabled />
                <span class="order-tools">
                  <button type="button" :disabled="index === 0" aria-label="向左调整收到牌顺序" @click="moveIncoming(index, -1)"><ChevronLeft :size="15" /></button>
                  <button type="button" :disabled="index === incomingOrder.length - 1" aria-label="向右调整收到牌顺序" @click="moveIncoming(index, 1)"><ChevronRight :size="15" /></button>
                </span>
                <label>插入槽
                  <select v-model.number="insertionIndexes[index]">
                    <option v-for="position in placementOptionCount(index)" :key="position - 1" :value="position - 1">{{ position - 1 }}</option>
                  </select>
                </label>
              </article>
            </div>
            <footer><span /><button type="button" class="primary" :disabled="busy" @click="submitPlacement"><Check :size="16" />确认全部位置</button></footer>
          </template>
        </section>

        <section v-if="game.privatePeek" class="peek-panel">
          <header><span><Eye :size="17" /><b>{{ playerName(game.privatePeek.targetPlayerId) }}的完整固定牌序</b></span><small>查看不会打乱这些牌</small></header>
          <div class="peek-cards">
            <FruitCard
              v-for="(card, index) in game.privatePeek.orderedCards"
              :key="card.instanceId"
              :card="card"
              compact
              :protected="index === game.privatePeek.protectedSlotIndex"
              disabled
            />
          </div>
        </section>
      </section>

      <div class="self-marker" :class="{ current: game.currentPlayerId === selfId }">
        <b>{{ playerName(selfId) }}</b><small>你的果篮 · 固定左 → 右</small>
      </div>

      <section class="self-hand" aria-label="你的固定顺序手牌">
        <div v-if="selfBoard?.handSlots.length" class="hand-scroll">
          <div
            v-for="slot in selfBoard.handSlots"
            :key="slot.slotId"
            class="hand-slot"
            :data-index="slot.index"
          >
            <span class="position-number">{{ slot.index + 1 }}</span>
            <FruitCard :card="slot.card" :protected="slot.protected" disabled />
          </div>
          <span class="right-edge"><b>最右侧</b><small>正常新牌落点</small></span>
        </div>
        <div v-else class="empty-basket"><Sparkles :size="24" /><b>果篮已空，等待效果队列确认安全</b></div>
      </section>

      <div
        v-if="animationEvent"
        :key="animationEvent.sequence"
        class="animation-layer"
        :class="`animation-${animationKind(animationEvent)}`"
        style="pointer-events: none"
        aria-hidden="true"
      >
        <div class="animation-caption">{{ animationEvent.message }}</div>
        <template v-if="animationKind(animationEvent) === 'pair'">
          <div class="pair-card left"><img v-if="animationEvent.pairCatalogId" :src="cardArt[animationEvent.pairCatalogId]" alt=""></div>
          <div class="pair-card right"><img v-if="animationEvent.pairCatalogId" :src="cardArt[animationEvent.pairCatalogId]" alt=""></div>
          <Sparkles class="pair-spark" :size="44" />
        </template>
        <template v-else-if="animationKind(animationEvent) === 'shuffle'">
          <img v-for="index in 5" :key="index" class="shuffle-card" :style="{ '--i': index }" :src="cardBackArt" alt="">
        </template>
        <template v-else-if="['draw', 'deal', 'exchange', 'conveyor', 'move'].includes(animationKind(animationEvent) ?? '')">
          <img v-for="index in animationKind(animationEvent) === 'conveyor' ? 6 : 2" :key="index" class="flying-card" :style="{ '--i': index }" :src="cardBackArt" alt="">
        </template>
        <template v-else-if="animationKind(animationEvent) === 'protect'">
          <ShieldCheck class="shield-animation" :size="86" />
        </template>
        <template v-else-if="animationKind(animationEvent) === 'peek'">
          <Eye class="peek-animation" :size="86" />
        </template>
        <template v-else-if="animationKind(animationEvent) === 'skip'">
          <div class="skip-animation">+{{ game.skipCount || 1 }}</div>
        </template>
        <template v-else-if="animationKind(animationEvent) === 'safe'">
          <Sparkles class="safe-animation" :size="100" />
        </template>
      </div>
    </main>

    <section v-if="props.snapshot.phase === 'finished'" class="result-overlay" role="dialog" aria-modal="true" aria-labelledby="result-title">
      <article>
        <small>暮市收摊 · 结算完成</small>
        <h3 id="result-title">{{ game.won ? '你把坏果留在了身后' : '坏果留在你的果篮里' }}</h3>
        <p>最后一对的果效已完整结算；本局 {{ game.finished?.loserIds.length ?? 0 }} 人持有 {{ game.oldMaidCount }} 张老鳖。</p>
        <div class="holder-grid">
          <div v-for="holder in resultHolders" :key="holder.playerId">
            <b>{{ playerName(holder.playerId) }}</b>
            <span><FruitCard v-for="card in holder.cards" :key="card.instanceId" :card="card" compact disabled /></span>
          </div>
        </div>
        <button v-if="props.snapshot.actions.canRestart" type="button" class="primary restart" @click="actions.restart()">再开一摊</button>
      </article>
    </section>

    <section v-if="showRules" class="drawer-overlay" role="dialog" aria-modal="true" aria-labelledby="rules-title">
      <article class="rule-drawer">
        <header><span><small>唯一规则集</small><h3 id="rules-title">标准版规则</h3></span><button type="button" aria-label="关闭规则" @click="showRules = false"><X :size="20" /></button></header>
        <div class="rule-columns">
          <section><b>开局</b><p>60 张正常水果加 ⌊人数 ÷ 2⌋ 张不同老鳖。逐张发完后移除所有初始对子，初始对子不发动技能。</p></section>
          <section><b>固定牌序</b><p>任何人不能自行洗牌或整理。正常暗抽牌永远追加最右；甜蜜分享、对半交换、流水果摊收到的牌才可任选插槽。</p></section>
          <section><b>正常回合</b><p>从顺时针最近的有牌玩家处按固定顺序盲抽一张，配对后公开离场并把果效加入 FIFO 队列。</p></section>
          <section><b>果效连锁</b><p>开局之后由任何方式形成的对子都发动。一次操作先完整完成，再按当前玩家起的座次与水果编号排序入队。</p></section>
          <section><b>安全与跳过</b><p>只有整条队列清空后才确认空手玩家安全，并在交接时结算全部“酸住了”跳过次数。</p></section>
          <section><b>胜负</b><p>30 对正常水果全部离场且最后队列清空后结算；没有老鳖者获胜，持有一张或多张老鳖者落败。</p></section>
        </div>
      </article>
    </section>

    <section v-if="showHistory" class="drawer-overlay" role="dialog" aria-modal="true" aria-labelledby="history-title">
      <article class="history-drawer">
        <header><span><small>公开事件</small><h3 id="history-title">暮市记录</h3></span><button type="button" aria-label="关闭记录" @click="showHistory = false"><X :size="20" /></button></header>
        <ol><li v-for="event in [...(game.events ?? [])].reverse()" :key="event.sequence"><b>{{ event.sequence }}</b><span>{{ event.message }}</span></li></ol>
      </article>
    </section>
  </section>
</template>

<style scoped>
.spoiled-fruit {
  --cream: #f6e9cf;
  --plum: #281b32;
  --plum-soft: #513252;
  --leaf: #315b43;
  --leaf-light: #78a763;
  --coral: #d86654;
  --amber: #e9a33a;
  --wood: #865735;
  position: relative;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  height: max(700px, calc(100dvh - 2px));
  overflow: hidden;
  color: var(--cream);
  background-color: var(--plum);
  background-image: var(--market-art);
  background-position: center;
  background-size: cover;
  font-family: Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif;
  isolation: isolate;
}
.spoiled-fruit.fullscreen { height: 100dvh; }
.market-wash { position: absolute; inset: 0; z-index: 0; background: radial-gradient(circle at 50% 47%, transparent 28%, #1e12204f 68%, #130b18ce 100%), linear-gradient(180deg, #24132d66 0 10%, transparent 32% 72%, #170d1fde 100%); pointer-events: none; }
.top-bar { position: absolute; z-index: 50; inset: 0 0 auto; min-width: 0; height: 78px; display: grid; grid-template-columns: minmax(170px, auto) minmax(0, 1fr) auto; align-items: center; gap: 16px; padding: 10px clamp(12px, 2vw, 26px); background: linear-gradient(180deg, #1c1023ed, #1c1023a6 76%, transparent); }
.brand small,.rule-drawer small,.history-drawer small,.result-overlay small { color: var(--amber); font-size: 9px; font-weight: 900; letter-spacing: .16em; }.brand h2 { margin: 2px 0 0; font-family: "Songti SC", STSong, serif; font-size: clamp(23px, 2.3vw, 34px); line-height: 1; text-shadow: 0 3px 8px #100916; }
.metrics { min-width: 0; display: flex; justify-content: center; gap: 7px; }.metrics span { border: 1px solid #f6e9cf2b; border-radius: 999px; padding: 6px 9px; color: #f6e9cfbb; background: #281b32a8; font-size: 9px; white-space: nowrap; backdrop-filter: blur(8px); }.metrics b { color: var(--amber); font-size: 12px; }
.table-tools { display: flex; gap: 6px; }.table-tools button,.drawer-overlay header button { min-width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid #f6e9cf30; border-radius: 12px; color: var(--cream); background: #281b32c7; cursor: pointer; backdrop-filter: blur(9px); }.table-tools .fullscreen-button { padding: 0 11px; }.fullscreen-button span { font-size: 9px; font-weight: 900; }
.table-stage { position: absolute; z-index: 2; inset: 70px 0 0; overflow: hidden; contain: layout paint; }
.seat { position: absolute; z-index: 20; left: var(--seat-x); top: var(--seat-y); width: clamp(104px, 11vw, 156px); min-height: 67px; transform: translate(-50%, -50%); border: 1px solid #f6e9cf33; border-radius: 13px; padding: 7px; background: linear-gradient(145deg, #2b1b32e8, #1d1225d9); box-shadow: 0 10px 24px #140b1c9e, inset 0 1px #fff1d31c; backdrop-filter: blur(8px); transition: border-color .25s ease, transform .25s ease, opacity .25s ease; }.seat.current { border-color: var(--amber); box-shadow: 0 0 0 3px #e9a33a26, 0 10px 24px #140b1c9e; }.seat.source { transform: translate(-50%, -50%) scale(1.06); border-color: var(--leaf-light); }.seat.safe { opacity: .68; border-color: #78a7638f; }.seat.waiting { animation: seat-wait 1.4s ease-in-out infinite; }.seat header { display: grid; grid-template-columns: 23px minmax(0, 1fr) auto; align-items: center; gap: 6px; }.seat-number { width: 23px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 50%; color: var(--plum); background: var(--amber); font-size: 9px; font-weight: 1000; }.seat header > span:nth-child(2) { min-width: 0; display: grid; gap: 2px; }.seat b,.seat small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.seat b { font-size: 10px; }.seat small { color: #f6e9cf9e; font-size: 7px; }.mini-hand { position: relative; height: 31px; margin: 5px 2px 0; }.mini-hand i { position: absolute; left: calc(var(--mini-index) * min(8px, .72vw)); bottom: 0; width: 21px; aspect-ratio: 2/3; transform: rotate(calc((var(--mini-index) - 5) * 1.7deg)); transform-origin: 50% 100%; border: 1px solid #e9a33a8a; border-radius: 3px; background-image: url('../assets/cards/card-back.png'); background-position: center; background-size: cover; box-shadow: 0 2px 5px #100915; }.mini-hand i.protected { border-color: var(--cream); box-shadow: 0 0 0 2px #865735, 0 2px 5px #100915; }.mini-hand em { position: absolute; right: 0; bottom: 2px; color: var(--amber); font-size: 8px; font-style: normal; font-weight: 900; }.safe-spark { display: block; margin: 5px auto 0; color: var(--leaf-light); }
.effect-ribbon { position: absolute; z-index: 23; top: 10px; left: 14px; width: min(190px, 18vw); border: 1px solid #f6e9cf29; border-radius: 14px; padding: 9px; background: #211429d9; box-shadow: 0 10px 25px #140b1c87; backdrop-filter: blur(10px); }.ribbon-label { display: block; margin-bottom: 7px; color: #f6e9cf7e; font-size: 7px; font-weight: 900; letter-spacing: .12em; }.effect-ribbon ol { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }.effect-ribbon li { display: grid; grid-template-columns: 22px minmax(0, 1fr); align-items: center; gap: 5px; border-left: 2px solid var(--effect); padding: 4px 5px; opacity: .66; }.effect-ribbon li.active { opacity: 1; background: color-mix(in srgb, var(--effect) 18%, transparent); }.effect-ribbon li > b { width: 20px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 50%; color: var(--plum); background: var(--effect); font-size: 8px; }.effect-ribbon li > span { min-width: 0; display: grid; font-size: 8px; font-weight: 900; }.effect-ribbon li small { overflow: hidden; color: #f6e9cf8c; font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }.effect-ribbon p { margin: 4px 0; color: #f6e9cf73; font-size: 8px; }
.market-core { position: absolute; z-index: 22; left: 50%; top: 42%; width: min(650px, 58vw); max-height: 54%; display: grid; gap: 8px; transform: translate(-50%, -50%); }.status-card { min-width: 0; min-height: 62px; display: grid; grid-template-columns: 38px minmax(0, 1fr); align-items: center; gap: 9px; border: 1px solid color-mix(in srgb, var(--effect) 58%, #f6e9cf30); border-radius: 16px; padding: 9px 13px; background: linear-gradient(140deg, #281b32ed, #201226da); box-shadow: 0 14px 30px #130b18a8; backdrop-filter: blur(10px); }.status-orb { width: 36px; aspect-ratio: 1; display: grid; place-items: center; border-radius: 50%; color: var(--plum); background: var(--effect); box-shadow: 0 0 18px color-mix(in srgb, var(--effect) 58%, transparent); }.status-card > span:last-child { min-width: 0; display: grid; gap: 3px; }.status-card strong { overflow: hidden; font-family: "Songti SC", STSong, serif; font-size: clamp(15px, 1.4vw, 19px); text-overflow: ellipsis; white-space: nowrap; }.status-card small { overflow: hidden; color: #f6e9cfa9; font-size: 8px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.draw-tray,.choice-panel,.peek-panel { min-width: 0; border: 1px solid #f6e9cf2e; border-radius: 15px; padding: 10px 12px; background: #24162ce8; box-shadow: 0 14px 30px #130b18a8; backdrop-filter: blur(12px); }.draw-tray header,.peek-panel header { display: flex; align-items: center; justify-content: space-between; gap: 9px; margin-bottom: 8px; }.draw-tray header b,.peek-panel header b { font-size: 10px; }.draw-tray header small,.peek-panel header small { color: #f6e9cf8c; font-size: 7px; }.draw-sequence,.peek-cards,.choice-cards { display: flex; gap: 5px; overflow-x: auto; overflow-y: hidden; padding: 5px 3px 8px; scrollbar-color: #e9a33a88 transparent; }.draw-sequence :deep(.fruit-card) { flex-basis: 39px; width: 39px; }.draw-sequence :deep(.fruit-card:disabled) { opacity: .42; }.peek-panel { border-color: #5b76a58e; }.peek-panel header > span { display: flex; align-items: center; gap: 6px; color: #9eb5df; }
.choice-panel { max-height: min(410px, 47dvh); overflow: auto; border-color: color-mix(in srgb, var(--effect) 62%, #f6e9cf2e); }.choice-panel > header { display: grid; grid-template-columns: minmax(120px, .7fr) minmax(0, 1.3fr); align-items: end; gap: 10px; border-bottom: 1px solid #f6e9cf24; padding-bottom: 8px; }.choice-panel > header span { display: grid; gap: 1px; }.choice-panel > header small { color: var(--effect); font-size: 7px; font-weight: 900; letter-spacing: .1em; }.choice-panel > header b { font-family: "Songti SC", STSong, serif; font-size: 16px; }.choice-panel > header em { color: #f6e9cf9e; font-size: 8px; font-style: normal; line-height: 1.45; }.choice-block { display: grid; gap: 6px; margin-top: 9px; }.choice-block > label,.position-picker label { color: #f6e9cf8e; font-size: 7px; font-weight: 900; letter-spacing: .08em; }.chip-row { display: flex; flex-wrap: wrap; gap: 5px; }.chip-row button,.return-slots button { border: 1px solid #f6e9cf2e; border-radius: 999px; padding: 6px 10px; color: var(--cream); background: #1d1225; font-size: 8px; cursor: pointer; }.chip-row button.selected,.return-slots button.selected { border-color: var(--effect); color: var(--plum); background: var(--effect); }.return-slots { display: flex; flex-wrap: wrap; gap: 4px; }.return-slots button { width: 28px; height: 28px; padding: 0; }.return-slots button.protected { opacity: .35; text-decoration: line-through; }.choice-cards :deep(.fruit-card) { flex-basis: 49px; width: 49px; }.choice-cards.wide :deep(.fruit-card) { flex-basis: 68px; width: 68px; }.position-picker { grid-template-columns: auto minmax(100px, 1fr) auto; align-items: center; }.position-picker input { accent-color: var(--effect); }.position-picker b { color: var(--effect); font-size: 9px; }.choice-note { margin: 10px 0 4px; color: #f6e9cfb0; font-size: 8px; line-height: 1.5; }.choice-panel footer { display: flex; justify-content: space-between; gap: 8px; border-top: 1px solid #f6e9cf1f; margin-top: 9px; padding-top: 8px; }.choice-panel footer button,.result-overlay button { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; border-radius: 10px; padding: 7px 12px; font-size: 8px; font-weight: 900; cursor: pointer; }.choice-panel .ghost { border: 1px solid #f6e9cf2e; color: #f6e9cfa6; background: transparent; }.primary { border: 1px solid color-mix(in srgb, var(--effect, var(--amber)) 80%, #fff); color: var(--plum); background: var(--effect, var(--amber)); }.choice-panel button:disabled { opacity: .35; cursor: not-allowed; }.incoming-list { display: flex; gap: 8px; overflow-x: auto; padding-top: 8px; }.incoming-list article { flex: 0 0 112px; display: grid; grid-template-columns: 50px 1fr; gap: 4px; border: 1px solid #f6e9cf20; border-radius: 10px; padding: 6px; }.incoming-list article > :deep(.fruit-card) { grid-row: 1 / 3; width: 46px; flex-basis: 46px; }.order-tools { display: flex; align-items: center; gap: 2px; }.order-tools button { width: 25px; height: 25px; display: grid; place-items: center; border: 1px solid #f6e9cf27; border-radius: 7px; color: var(--cream); background: #1b1022; }.incoming-list label { align-self: end; display: grid; gap: 2px; color: #f6e9cf8d; font-size: 7px; }.incoming-list select { width: 52px; border: 1px solid #f6e9cf30; border-radius: 6px; color: var(--cream); background: var(--plum); font-size: 8px; }
.self-marker { position: absolute; z-index: 29; left: 50%; bottom: 28.5%; display: grid; transform: translateX(-50%); border: 1px solid #f6e9cf36; border-radius: 999px; padding: 6px 15px; color: #f6e9cf; background: #24162ce8; text-align: center; backdrop-filter: blur(9px); }.self-marker.current { border-color: var(--amber); box-shadow: 0 0 16px #e9a33a4a; }.self-marker b { font-size: 10px; }.self-marker small { color: #f6e9cf85; font-size: 7px; }
.self-hand { position: absolute; z-index: 28; inset: auto 0 0; height: 28%; display: grid; align-items: end; border-top: 1px solid #f6e9cf2c; padding: 20px max(14px, 3vw) 10px; background: linear-gradient(180deg, transparent, #1b1022bd 16%, #160d1ff4 100%); }.hand-scroll { min-width: 0; display: flex; align-items: flex-end; gap: 7px; overflow-x: auto; overflow-y: hidden; padding: 14px 3px 10px; scroll-snap-type: x proximity; scrollbar-color: #e9a33a7d transparent; }.hand-slot { position: relative; flex: 0 0 auto; scroll-snap-align: center; }.position-number { position: absolute; z-index: 5; top: -13px; left: 50%; transform: translateX(-50%); color: #f6e9cfa2; font-size: 8px; font-weight: 900; }.right-edge { flex: 0 0 72px; height: 85px; display: grid; align-content: center; gap: 3px; border-left: 1px dashed #e9a33a91; padding-left: 9px; color: var(--amber); }.right-edge b { font-size: 9px; }.right-edge small { color: #f6e9cf7b; font-size: 7px; line-height: 1.35; }.empty-basket { align-self: center; display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--leaf-light); font-size: 11px; }
.animation-layer { position: absolute; z-index: 16; inset: 7% 20% 29%; overflow: hidden; pointer-events: none; contain: layout paint; isolation: isolate; }.animation-caption { position: absolute; z-index: 6; left: 50%; bottom: 8%; max-width: 75%; transform: translateX(-50%); border: 1px solid #f6e9cf36; border-radius: 999px; padding: 7px 13px; color: var(--cream); background: #211429e6; box-shadow: 0 7px 18px #130b18a1; font-size: 8px; font-weight: 900; text-align: center; animation: caption-in .72s ease both; }.flying-card,.shuffle-card { position: absolute; left: calc(50% - 30px); top: calc(50% - 45px); width: 60px; height: 90px; border-radius: 8px; object-fit: cover; box-shadow: 0 12px 28px #100813b8; }.animation-draw .flying-card { animation: draw-flight .72s cubic-bezier(.2,.8,.2,1) both; animation-delay: calc((var(--i) - 1) * 50ms); }.animation-deal .flying-card { animation: deal-flight .72s ease-out both; }.animation-exchange .flying-card { animation: exchange-flight .72s ease-in-out both; animation-direction: alternate; }.animation-conveyor .flying-card { animation: conveyor-flight .72s ease-in-out both; animation-delay: calc((var(--i) - 1) * 40ms); }.animation-move .flying-card { animation: move-flight .72s ease both; }.shuffle-card { transform-origin: 50% 110%; animation: shuffle-fan .72s ease-in-out both; animation-delay: calc((var(--i) - 1) * 35ms); }.pair-card { position: absolute; left: calc(50% - 44px); top: calc(50% - 66px); width: 88px; height: 132px; border: 2px solid var(--amber); border-radius: 12px; background: var(--cream); box-shadow: 0 14px 30px #130b18b5; animation: pair-meet .72s ease-out both; }.pair-card.left { --pair-start: -180px; }.pair-card.right { --pair-start: 180px; }.pair-card img { width: 100%; height: 100%; object-fit: contain; }.pair-spark,.shield-animation,.peek-animation,.safe-animation { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); color: var(--amber); filter: drop-shadow(0 0 15px currentColor); animation: icon-bloom .72s ease both; }.shield-animation { color: #d6a36f; }.peek-animation { color: #91aee5; }.safe-animation { color: var(--leaf-light); }.skip-animation { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); color: #d8dc68; font-family: "Songti SC", STSong, serif; font-size: 72px; font-weight: 1000; text-shadow: 0 0 28px #b9b849; animation: icon-bloom .72s ease both; }
.drawer-overlay,.result-overlay { position: absolute; z-index: 80; inset: 0; display: grid; place-items: center; padding: 18px; background: #160d1fd9; backdrop-filter: blur(12px); }.rule-drawer,.history-drawer,.result-overlay > article { width: min(820px, 94vw); max-height: 88dvh; overflow: auto; border: 1px solid #f6e9cf3b; border-radius: 22px; padding: clamp(16px, 3vw, 28px); background: linear-gradient(145deg, #34213eea, #211429f5); box-shadow: 0 28px 70px #0b060ed4; }.drawer-overlay header { display: flex; align-items: center; justify-content: space-between; gap: 10px; border-bottom: 1px solid #f6e9cf24; padding-bottom: 12px; }.drawer-overlay header span { display: grid; }.drawer-overlay h3,.result-overlay h3 { margin: 2px 0 0; font-family: "Songti SC", STSong, serif; font-size: clamp(24px, 4vw, 38px); }.rule-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }.rule-columns section { border: 1px solid #f6e9cf20; border-radius: 12px; padding: 12px; background: #1d12256e; }.rule-columns b { color: var(--amber); font-size: 10px; }.rule-columns p { margin: 5px 0 0; color: #f6e9cfad; font-size: 9px; line-height: 1.65; }.history-drawer ol { display: grid; gap: 6px; margin: 12px 0 0; padding: 0; list-style: none; }.history-drawer li { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 8px; border-left: 2px solid var(--amber); padding: 7px 9px; color: #f6e9cfb5; background: #1d122573; font-size: 9px; }.history-drawer li b { color: var(--amber); }.result-overlay > article { text-align: center; }.result-overlay p { color: #f6e9cfaa; font-size: 10px; line-height: 1.6; }.holder-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; margin-top: 15px; }.holder-grid > div { display: grid; gap: 7px; border: 1px solid #8650528c; border-radius: 13px; padding: 10px; background: #211429; }.holder-grid b { color: #e7aeb0; font-size: 10px; }.holder-grid span { display: flex; justify-content: center; gap: 5px; }.restart { margin-top: 16px; }
@keyframes seat-wait { 50% { box-shadow: 0 0 0 4px #e9a33a2d, 0 10px 24px #140b1c9e; } }
@keyframes caption-in { 0% { opacity: 0; transform: translate(-50%, 8px); } 18%,78% { opacity: 1; transform: translate(-50%, 0); } 100% { opacity: 0; } }
@keyframes draw-flight { 0% { opacity: 0; transform: translate(190px, -120px) rotate(18deg) scale(.6); } 45% { opacity: 1; } 100% { opacity: 0; transform: translate(0, 170px) rotate(0) scale(1); } }
@keyframes deal-flight { 0% { opacity: 0; transform: scale(.3) rotate(-20deg); } 45% { opacity: 1; } 100% { opacity: 0; transform: translate(calc((var(--i) * 2 - 3) * 170px), -120px) rotate(calc((var(--i) * 2 - 3) * 9deg)); } }
@keyframes exchange-flight { 0% { opacity: 0; transform: translate(calc((var(--i) * 2 - 3) * 190px), 20px) rotate(calc((var(--i) * 2 - 3) * 12deg)); } 38%,70% { opacity: 1; } 100% { opacity: 0; transform: translate(calc((3 - var(--i) * 2) * 190px), -20px) rotate(calc((3 - var(--i) * 2) * 12deg)); } }
@keyframes conveyor-flight { 0% { opacity: 0; transform: rotate(calc(var(--i) * 60deg)) translateX(80px) rotate(calc(var(--i) * -60deg)) scale(.5); } 35% { opacity: 1; } 100% { opacity: 0; transform: rotate(calc((var(--i) + 1) * 60deg)) translateX(180px) rotate(calc((var(--i) + 1) * -60deg)) scale(.8); } }
@keyframes move-flight { 0% { opacity: 0; transform: translateX(-190px) rotate(-14deg); } 45% { opacity: 1; } 100% { opacity: 0; transform: translateX(190px) rotate(14deg); } }
@keyframes shuffle-fan { 0% { opacity: 0; transform: rotate(0) translateX(0); } 45% { opacity: 1; transform: rotate(calc((var(--i) - 3) * 13deg)) translateX(calc((var(--i) - 3) * 27px)); } 100% { opacity: 0; transform: rotate(calc((3 - var(--i)) * 8deg)) translateX(calc((3 - var(--i)) * 15px)); } }
@keyframes pair-meet { 0% { opacity: 0; transform: translateX(var(--pair-start)) rotate(calc(var(--pair-start) / 14)); } 55% { opacity: 1; transform: translateX(0) rotate(0) scale(1.06); } 100% { opacity: 0; transform: translateX(0) scale(.86); } }
@keyframes icon-bloom { 0% { opacity: 0; transform: translate(-50%, -50%) scale(.25) rotate(-20deg); } 45% { opacity: 1; transform: translate(-50%, -50%) scale(1.15) rotate(0); } 100% { opacity: 0; transform: translate(-50%, -50%) scale(1.5); } }
@media (hover: hover) { .table-tools button:hover,.drawer-overlay header button:hover { border-color: var(--amber); color: var(--amber); }.choice-panel button:hover:not(:disabled),.return-slots button:hover:not(:disabled),.chip-row button:hover { filter: brightness(1.12); } }
@media (max-width: 900px) {
  .spoiled-fruit { height: max(720px, 100dvh); }
  .top-bar { height: 70px; grid-template-columns: auto 1fr auto; gap: 8px; padding: 8px 10px; }.brand small { display: none; }.brand h2 { font-size: 22px; }.metrics span:nth-child(1),.metrics span:nth-child(2) { display: none; }.table-stage { top: 64px; }.effect-ribbon { width: 132px; }.effect-ribbon li small { display: none; }.market-core { top: 39%; width: min(620px, 70vw); }.seat { width: 104px; }.self-hand { height: 30%; }.self-marker { bottom: 30.5%; }.animation-layer { inset-right: 14%; inset-left: 14%; }
}
@media (max-width: 650px) {
  .spoiled-fruit { height: max(760px, 100dvh); background-position: center top; }.top-bar { grid-template-columns: 1fr auto; }.metrics { position: absolute; top: 54px; left: 8px; justify-content: flex-start; }.metrics span { padding: 4px 7px; }.table-tools button:not(.fullscreen-button) { display: none; }.fullscreen-button span { display: none; }.table-stage { inset: 62px 0 0; }.seat { left: clamp(35px, var(--seat-x), calc(100% - 35px)); width: 66px; min-height: 43px; padding: 4px; border-radius: 10px; }.seat header { grid-template-columns: 17px minmax(0, 1fr); gap: 4px; }.seat header > svg { display: none; }.seat-number { width: 17px; }.seat b { font-size: 7px; }.seat small { font-size: 5px; }.mini-hand { display: none; }.effect-ribbon { top: 38px; left: 6px; width: 108px; padding: 6px; }.effect-ribbon li { grid-template-columns: 18px minmax(0, 1fr); }.effect-ribbon li > b { width: 17px; }.market-core { top: 42%; width: 64vw; max-height: 48%; }.status-card { min-height: 52px; grid-template-columns: 29px minmax(0,1fr); padding: 7px 9px; }.status-orb { width: 28px; }.status-card strong { font-size: 13px; }.status-card small { font-size: 7px; }.choice-panel { max-height: 39dvh; }.choice-panel > header { grid-template-columns: 1fr; }.choice-panel > header em { display: none; }.draw-tray header small { display: none; }.self-hand { height: 28%; padding-inline: 9px; }.self-marker { bottom: 28.5%; }.hand-scroll { gap: 5px; }.rule-columns { grid-template-columns: 1fr; }.animation-layer { inset: 14% 4% 29%; }
}
@media (max-height: 760px) and (min-width: 651px) {
  .spoiled-fruit { height: 100dvh; min-height: 600px; }.top-bar { height: 64px; }.table-stage { top: 58px; }.market-core { top: 38%; max-height: 52%; }.self-hand { height: 27%; }.self-marker { bottom: 27.5%; }.hand-scroll :deep(.fruit-card) { width: 72px; flex-basis: 72px; }
}
@media (prefers-reduced-motion: reduce) {
  .seat,.seat.waiting { transition: none; animation: none; }.animation-layer { display: none; }
}
</style>
