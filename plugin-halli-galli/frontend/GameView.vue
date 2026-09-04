<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  usePluginFullscreen,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import BellButton from './components/BellButton.vue'
import FruitCard from './components/FruitCard.vue'
import MotionLayer from './components/MotionLayer.vue'
import PlayerSeat from './components/PlayerSeat.vue'
import ReactionBanner from './components/ReactionBanner.vue'
import ResultOverlay from './components/ResultOverlay.vue'
import type {
  AnimationCue,
  HalliGalliEvent,
  HalliGalliPlayerView,
  HalliGalliView,
} from './types'
import { fruitNames } from './types'
import './layout.css'
import './motion.css'
import './responsive.css'

type InputMethod = 'pointer' | 'touch' | 'keyboard' | 'button'
type Point = { x: number; y: number }

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported, toggle: toggleFullscreen } = usePluginFullscreen(gameRoot)

const showRules = ref(false)
const flipPending = ref(false)
const bellPending = ref(false)
const sentBellEpoch = ref<number | null>(null)
const localError = ref('')
const clockNow = ref(Date.now())
const motionQueue = ref<HalliGalliEvent[]>([])
const currentMotion = ref<HalliGalliEvent | null>(null)
const localBellMotion = ref<HalliGalliEvent | null>(null)
let motionInitialized = false
let lastMotionSeq = 0
let motionTimer: ReturnType<typeof setTimeout> | undefined
let localBellTimer: ReturnType<typeof setTimeout> | undefined
let clockTimer: ReturnType<typeof setInterval> | undefined
let noProgressTimer: ReturnType<typeof setTimeout> | undefined

const game = computed(() => props.snapshot.game as unknown as HalliGalliView)
const readOnly = computed(() => props.snapshot.viewer?.mode === 'spectator')
const orderedPlayers = computed(() => [...game.value.players].sort((a, b) => a.relativeSeat - b.relativeSeat))
const currentPlayer = computed(() => game.value.players.find(player => player.id === game.value.currentPlayerId) ?? null)
const latestEvents = computed(() => game.value.events.slice(-3).reverse())
const flipWaitMs = computed(() => Math.max(0, game.value.earliestNextFlipAtMs - clockNow.value))
const canFlip = computed(() => (
  !readOnly.value
  && !flipPending.value
  && game.value.actions.canFlipWhenReady
  && flipWaitMs.value === 0
  && props.snapshot.phase === 'playing'
))
const canRing = computed(() => (
  !readOnly.value
  && !bellPending.value
  && game.value.actions.canRing
  && sentBellEpoch.value !== game.value.boardEpoch
  && props.snapshot.phase === 'playing'
))
const statusTitle = computed(() => {
  if (props.snapshot.phase === 'finished') return '本局已经结算'
  if (game.value.finalDuelArmed) return '最终二人 · 下一次有效铃结束游戏'
  if (currentPlayer.value?.id === game.value.selfPlayerId) return flipWaitMs.value ? '准备翻牌' : '轮到你翻牌'
  return `等待 ${currentPlayer.value?.name ?? '牌桌'} 翻牌`
})
const statusDetail = computed(() => {
  if (readOnly.value) return '观战视角 · 所有操作已锁定'
  if (canFlip.value) return '点击自己的抽牌堆，或按 F 翻牌'
  if (game.value.actions.canFlipWhenReady && flipWaitMs.value) return `公平保护 ${Math.ceil(flipWaitMs.value / 100) / 10} 秒`
  return game.value.actions.flipDisabledReason ?? '观察全部顶牌，恰好五个时抢铃'
})

const positions: Record<number, Point[]> = {
  2: [{ x: 50, y: 80 }, { x: 50, y: 16 }],
  3: [{ x: 50, y: 80 }, { x: 18, y: 22 }, { x: 82, y: 22 }],
  4: [{ x: 50, y: 80 }, { x: 15, y: 48 }, { x: 50, y: 14 }, { x: 85, y: 48 }],
  5: [{ x: 50, y: 81 }, { x: 14, y: 65 }, { x: 20, y: 20 }, { x: 80, y: 20 }, { x: 86, y: 65 }],
  6: [{ x: 50, y: 81 }, { x: 12, y: 65 }, { x: 17, y: 20 }, { x: 50, y: 12 }, { x: 83, y: 20 }, { x: 88, y: 65 }],
}

const motionDuration: Record<AnimationCue, number> = {
  round_deal: 720,
  card_flip: 280,
  bell_press_local: 320,
  bell_confirmed: 320,
  collect_piles: 590,
  penalty_transfer: 520,
  player_eliminated: 440,
  final_duel_armed: 560,
  result_enter: 680,
}

function seatStyle(player: HalliGalliPlayerView): Record<string, string> {
  const point = positions[game.value.players.length]?.[player.relativeSeat] ?? { x: 50, y: 50 }
  return { '--seat-x': `${point.x}%`, '--seat-y': `${point.y}%` }
}

function motionTone(player: HalliGalliPlayerView): 'winner' | 'wrong' | 'target' | '' {
  const event = currentMotion.value
  if (!event) return ''
  const winnerId = String(event.data.winnerPlayerId ?? '')
  if ((event.cue === 'collect_piles' || event.cue === 'result_enter') && (player.id === winnerId || event.targetPlayerIds.includes(player.id))) return 'winner'
  if (event.cue === 'penalty_transfer' && player.id === event.actorPlayerId) return 'wrong'
  if (event.targetPlayerIds.includes(player.id)) return 'target'
  return ''
}

function actionId(prefix: string): string {
  const uuid = globalThis.crypto?.randomUUID?.()
  return uuid ? `${prefix}-${uuid}` : `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

async function flipCard(): Promise<void> {
  if (!canFlip.value) return
  flipPending.value = true
  localError.value = ''
  try {
    await actions.action('flip_card', {
      actionId: actionId('flip'),
      revision: props.snapshot.revision,
      expectedBoardEpoch: game.value.boardEpoch,
    })
  } catch (reason) {
    localError.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    flipPending.value = false
  }
}

async function ringBell(method: InputMethod): Promise<void> {
  if (!canRing.value) return
  const epoch = game.value.boardEpoch
  if (localBellTimer) clearTimeout(localBellTimer)
  localBellMotion.value = {
    seq: Date.now(),
    type: 'bell_press_local',
    cue: 'bell_press_local',
    actorPlayerId: game.value.selfPlayerId,
    targetPlayerIds: [],
    messageZh: '抢铃请求已发送',
    boardEpoch: epoch,
    data: { inputMethod: method },
  }
  localBellTimer = setTimeout(() => { localBellMotion.value = null }, motionDuration.bell_press_local)
  sentBellEpoch.value = epoch
  bellPending.value = true
  localError.value = ''
  try {
    await actions.action('ring_bell', {
      actionId: actionId('bell'),
      boardEpoch: epoch,
      inputMethod: method,
    })
  } catch (reason) {
    localError.value = reason instanceof Error ? reason.message : String(reason)
    if (game.value.boardEpoch === epoch) sentBellEpoch.value = null
  } finally {
    bellPending.value = false
  }
}

async function settleNoProgress(): Promise<void> {
  if (readOnly.value || props.snapshot.phase !== 'playing' || !game.value.noProgressDeadlineMs) return
  try {
    await actions.action('settle_no_progress', {
      actionId: actionId('settle'),
      boardEpoch: game.value.boardEpoch,
    })
  } catch (reason) {
    localError.value = reason instanceof Error ? reason.message : String(reason)
  }
}

async function restart(): Promise<void> {
  localError.value = ''
  try { await actions.restart() }
  catch (reason) { localError.value = reason instanceof Error ? reason.message : String(reason) }
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A'].includes(target.tagName) || target.isContentEditable
}

function onGlobalKey(event: KeyboardEvent): void {
  if (event.key === 'Escape' && showRules.value) {
    event.preventDefault(); showRules.value = false; return
  }
  if (showRules.value || props.snapshot.phase === 'finished' || isEditableTarget(event.target)) return
  if (event.code === 'Space' && !event.repeat) {
    event.preventDefault(); void ringBell('keyboard')
  } else if (event.key.toLowerCase() === 'f' && !event.repeat) {
    event.preventDefault(); void flipCard()
  } else if (event.key.toLowerCase() === 'r' && !event.repeat) {
    event.preventDefault(); showRules.value = true
  }
}

function playNextMotion(): void {
  if (currentMotion.value || !motionQueue.value.length) return
  currentMotion.value = motionQueue.value.shift() ?? null
  if (!currentMotion.value) return
  const duration = motionDuration[currentMotion.value.cue] ?? 420
  motionTimer = setTimeout(() => {
    currentMotion.value = null
    playNextMotion()
  }, duration)
}

function expandCommittedMotions(events: HalliGalliEvent[]): HalliGalliEvent[] {
  const expanded: HalliGalliEvent[] = []
  for (const event of events) {
    const bellResolution = ['bell_correct', 'bell_wrong', 'bell_wrong_final'].includes(event.type)
    if (bellResolution) {
      expanded.push({ ...event, cue: 'bell_confirmed' })
    }
    expanded.push(event)
    const eliminated = Array.isArray(event.data.eliminatedPlayerIds)
      ? event.data.eliminatedPlayerIds.filter((id): id is string => typeof id === 'string')
      : []
    for (const playerId of eliminated) {
      expanded.push({
        ...event,
        cue: 'player_eliminated',
        actorPlayerId: playerId,
        targetPlayerIds: [playerId],
        messageZh: `${game.value.players.find(player => player.id === playerId)?.name ?? '玩家'} 已退出本局`,
      })
    }
  }
  return expanded
}

function scheduleNoProgress(): void {
  if (noProgressTimer) clearTimeout(noProgressTimer)
  const deadline = game.value.noProgressDeadlineMs
  if (!deadline || readOnly.value || props.snapshot.phase !== 'playing') return
  noProgressTimer = setTimeout(() => void settleNoProgress(), Math.max(0, deadline - Date.now()) + 30)
}

watch(() => game.value.boardEpoch, () => {
  sentBellEpoch.value = null
  localError.value = ''
})

watch(() => game.value.events, (events) => {
  const latest = events.at(-1)?.seq ?? 0
  if (!motionInitialized || latest < lastMotionSeq) {
    motionInitialized = true
    lastMotionSeq = Math.max(0, latest - 1)
  }
  const additions = events.filter(event => event.seq > lastMotionSeq)
  if (additions.length) {
    motionQueue.value.push(...expandCommittedMotions(additions))
    lastMotionSeq = latest
    playNextMotion()
  }
}, { deep: true, immediate: true })

watch(() => game.value.noProgressDeadlineMs, scheduleNoProgress, { immediate: true })

onMounted(() => {
  window.addEventListener('keydown', onGlobalKey)
  clockTimer = setInterval(() => { clockNow.value = Date.now() }, 100)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKey)
  if (clockTimer) clearInterval(clockTimer)
  if (motionTimer) clearTimeout(motionTimer)
  if (localBellTimer) clearTimeout(localBellTimer)
  if (noProgressTimer) clearTimeout(noProgressTimer)
})
</script>

<template>
  <section
    ref="gameRoot"
    class="halli-galli-game"
    :class="{ fullscreen: isFullscreen, 'final-duel': game.finalDuelArmed }"
    :data-player-count="game.players.length"
    :data-scene="game.sceneId"
    :data-board-epoch="game.boardEpoch"
    data-layout="browser-fill"
    @contextmenu.prevent
  >
    <div class="table-grain" aria-hidden="true" />
    <header class="table-masthead">
      <div class="brand-lockup">
        <small>HALLI GALLI · CLASSIC</small>
        <h1>德国心脏病</h1>
      </div>
      <div class="status-copy" :class="{ final: game.finalDuelArmed }" data-zone="turn_banner">
        <span>第 {{ game.turnNumber + 1 }} 次翻牌 · 桌面版本 {{ game.boardEpoch }}</span>
        <strong>{{ statusTitle }}</strong>
        <small>{{ statusDetail }}</small>
      </div>
      <nav class="mast-actions" aria-label="牌桌工具">
        <button type="button" aria-label="打开规则说明" @click="showRules = true"><span>?</span><small>规则</small></button>
        <button v-if="isSupported" type="button" aria-label="切换全屏" @click="toggleFullscreen"><span>⛶</span><small>{{ isFullscreen ? '退出' : '全屏' }}</small></button>
      </nav>
    </header>

    <main class="table-stage" :data-player-count="game.players.length" data-zone="table_stage">
      <div class="fruit-legend" data-zone="fruit_legend" aria-label="四种水果图例；不显示自动合计">
        <span v-for="fruit in game.fruitLegend" :key="fruit.fruitId" :class="`legend-${fruit.fruitId}`">
          <i :style="{ '--legend-color': fruit.palette.base, '--legend-dark': fruit.palette.dark }" />
          <b>{{ fruit.nameZh }}</b>
        </span>
      </div>

      <div class="seat-layer">
        <PlayerSeat
          v-for="player in orderedPlayers"
          :key="player.id"
          :player="player"
          :style="seatStyle(player)"
          :can-flip="player.isSelf && canFlip"
          :just-flipped="currentMotion?.cue === 'card_flip' && currentMotion.actorPlayerId === player.id"
          :motion-tone="motionTone(player)"
          @flip="flipCard"
        />
      </div>

      <div class="bell-zone">
        <BellButton
          :enabled="canRing"
          :pending="bellPending"
          :final-duel="game.finalDuelArmed"
          @ring="ringBell"
        />
        <p>{{ game.actions.ringDisabledReason ?? '任一水果恰好 5 个时抢铃' }}</p>
      </div>

      <ReactionBanner :event="game.latestEvent" />
      <MotionLayer
        v-if="currentMotion"
        :key="`${currentMotion.seq}-${currentMotion.cue}-${currentMotion.actorPlayerId ?? 'table'}`"
        :event="currentMotion"
        :players="game.players"
      />
      <MotionLayer
        v-if="localBellMotion"
        :key="`local-${localBellMotion.seq}`"
        :event="localBellMotion"
        :players="game.players"
      />

      <aside class="event-strip" data-zone="event_strip" aria-label="最近牌桌事件">
        <header><span>LIVE</span><strong>牌桌记录</strong></header>
        <ol>
          <li v-for="event in latestEvents" :key="event.seq"><b>{{ String(event.seq).padStart(2, '0') }}</b><span>{{ event.messageZh }}</span></li>
        </ol>
      </aside>

      <div class="self-controls" data-zone="self_controls">
        <button type="button" data-action="flip-card" :disabled="!canFlip" @click="flipCard">
          <strong>{{ flipPending ? '正在翻牌…' : '翻开一张' }}</strong><small>F · 仅当前玩家</small>
        </button>
        <p>{{ statusDetail }}</p>
      </div>

      <aside v-if="game.noProgressDeadlineMs" class="no-progress-banner">
        无人可翻牌；{{ Math.max(0, Math.ceil((game.noProgressDeadlineMs - clockNow) / 1000)) }} 秒后执行安全裁决
      </aside>
      <p v-if="localError" class="local-error" role="alert">{{ localError }}</p>

      <ResultOverlay
        v-if="game.result"
        :result="game.result"
        :can-restart="Boolean(snapshot.actions.canRestart)"
        @restart="restart"
      />
    </main>

    <div v-if="showRules" class="modal-scrim" data-zone="rules_drawer" role="dialog" aria-modal="true" aria-labelledby="halli-rules-title" @click.self="showRules = false">
      <section class="rules-sheet">
        <header><div><small>CLASSIC · 官方常规终局</small><h2 id="halli-rules-title">快速规则</h2></div><button type="button" aria-label="关闭规则" @click="showRules = false">×</button></header>
        <div class="rules-grid">
          <article><b>1</b><div><strong>轮流翻牌</strong><p>向桌心快速翻开一张，盖住自己的旧顶牌；只有每堆最上方参与计数。</p></div></article>
          <article><b>2</b><div><strong>恰好五个</strong><p>任一同种水果在全部顶牌中合计恰好 5 个即可抢铃；6 或 10 都不算。</p></div></article>
          <article><b>3</b><div><strong>正确抢铃</strong><p>第一个正确按铃者收走所有人的完整明牌堆，并由其继续翻牌。</p></div></article>
          <article><b>4</b><div><strong>误按处罚</strong><p>向其他每名在局玩家各付一张；最终二人误按则由对手收走全部明牌并结算。</p></div></article>
          <article><b>5</b><div><strong>最后机会</strong><p>抽牌用尽但自己的明牌仍在时，不能翻牌却仍可抢铃；抢对即可复活。</p></div></article>
          <article><b>6</b><div><strong>常规终局</strong><p>降至两人后的下一次铃结束；两人开局则第一次铃结束。持牌最多者获胜，平手共享胜利。</p></div></article>
        </div>
        <h3>20 种牌面 · 每种水果 14 张</h3>
        <div class="catalog-grid">
          <FruitCard v-for="card in game.cardCatalog" :key="card.faceId" :card="card" compact />
        </div>
        <footer><span>快捷键：F 翻牌 · Space 抢铃 · R 规则 · Esc 关闭</span><button type="button" @click="showRules = false">返回牌桌</button></footer>
      </section>
    </div>

    <p class="sr-live" aria-live="polite">{{ game.latestEvent?.messageZh }}</p>
  </section>
</template>
