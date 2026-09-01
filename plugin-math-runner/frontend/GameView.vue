<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  BookOpen,
  Gauge,
  Maximize2,
  Minimize2,
  Route,
  Sparkles,
  Trophy,
} from '@lucide/vue'
import {
  PluginButton,
  PluginIconButton,
  PluginMetricGrid,
  PluginModal,
  PluginResultCard,
  PluginRuleGuide,
  formatPluginDuration,
  formatPluginScore,
  usePluginFullscreen,
  usePluginGameActions,
  usePluginTheme,
  type ArcadeSnapshot,
  type PluginMetricItem,
} from '@game-hall/plugin-sdk'
import DirectionPad from './components/DirectionPad.vue'
import TrackScene from './components/TrackScene.vue'
import { mathRunnerRuleGuide } from './rules'
import {
  KEY_TO_DIRECTION,
  directionLabel,
  type Direction,
  type MathRunnerGameView,
} from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const showRules = ref(false)
const selectedDirection = ref<Direction | null>(null)
const turnDirection = ref<Direction | null>(null)
const displayRemainingMs = ref(0)
const submitting = ref(false)
const restarting = ref(false)
const timeoutSentFor = ref<number | null>(null)
let countdownTimer: number | null = null
let turnTimer: number | null = null
let localDeadline = 0
const viewportLockClass = 'math-runner-viewport-lock'

const game = computed(() => props.snapshot.game as MathRunnerGameView)
const { materials } = usePluginTheme()
const {
  isFullscreen,
  isSupported: isFullscreenSupported,
  toggle: toggleFullscreen,
} = usePluginFullscreen(gameRoot)

const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const availableDirections = computed(() => new Set(
  (game.value.options ?? []).map((option) => option.direction),
))
const canControl = computed(() => (
  props.snapshot.phase === 'playing'
  && props.snapshot.actions.canAct
  && !isSpectator.value
  && !submitting.value
  && displayRemainingMs.value > 0
))
const remainingRatio = computed(() => Math.min(1, Math.max(
  0,
  displayRemainingMs.value / Math.max(1, game.value.timeLimitMs ?? 1),
)))
const currentQuestionLabel = computed(() => (
  game.value.questionId
    ? `第 ${game.value.questionId} / ${game.value.totalQuestions ?? 100} 题`
    : '等待路口'
))
const levelProgress = computed(() => (
  (game.value.streakInLevel ?? 0) / Math.max(1, game.value.questionsPerLevel ?? 10) * 100
))
const levelProgressLabel = computed(() => {
  if (game.value.endReason === 'completed') return '十级赛道已完成'
  return `本级 ${game.value.streakInLevel ?? 0} / ${game.value.questionsPerLevel ?? 10}`
})

const rootStyle = computed<Record<string, string>>(() => {
  const value = materials.value
  return {
    '--mr-scene-top': value.scene.top,
    '--mr-scene-center': value.scene.center,
    '--mr-scene-bottom': value.scene.bottom,
    '--mr-scene-glow': value.scene.glow,
    '--mr-scene-fog': value.scene.fog,
    '--mr-scene-particle': value.scene.particle,
    '--mr-stage-top': value.stage.top,
    '--mr-stage-bottom': value.stage.bottom,
    '--mr-stage-edge': value.stage.edge,
    '--mr-stage-inner-edge': value.stage.innerEdge,
    '--mr-stage-detail': value.stage.detail,
    '--mr-stage-glow': value.stage.glow,
    '--mr-shadow': value.stage.shadow,
    '--mr-metal-body': value.metal.body,
    '--mr-metal-side': value.metal.side,
    '--mr-metal-edge': value.metal.edge,
    '--mr-metal-glass': value.metal.glass,
    '--mr-metal-glow': value.metal.glow,
    '--mr-copy-primary': value.copy.primary,
    '--mr-copy-secondary': value.copy.secondary,
    '--mr-copy-on-stage': value.copy.onStage,
    '--mr-copy-outline': value.copy.onStageOutline,
    '--mr-accent': value.stage.glow,
    '--mr-danger': value.semantic.danger,
    '--mr-danger-strong': value.semantic.dangerStrong,
    '--mr-danger-glow': value.semantic.dangerGlow,
    '--mr-warning': value.semantic.warning,
    '--mr-warning-strong': value.semantic.warningStrong,
    '--mr-warning-glow': value.semantic.warningGlow,
    '--mr-success': value.semantic.success,
    '--mr-success-strong': value.semantic.successStrong,
    '--mr-success-glow': value.semantic.successGlow,
    '--mr-line': 'var(--line)',
    '--mr-surface-inset': 'var(--surface-inset)',
  }
})

const metricItems = computed<PluginMetricItem[]>(() => [
  {
    label: '速度等级',
    value: `${game.value.level ?? 1} / ${game.value.maxLevel ?? 10}`,
    tone: game.value.levelUp ? 'success' : 'default',
  },
  {
    label: '连续答对',
    value: `${game.value.correctAnswers ?? 0} 题`,
  },
  {
    label: '最大路程榜',
    value: formatPluginScore(game.value.distanceMeters ?? 0, { unit: '米' }),
    tone: 'success',
  },
  {
    label: '技巧得分',
    value: formatPluginScore(game.value.score ?? 0),
  },
])

const resultMetrics = computed<PluginMetricItem[]>(() => [
  { label: '答对', value: `${game.value.correctAnswers ?? 0} / ${game.value.totalQuestions ?? 100}` },
  { label: '最高等级', value: `${game.value.level ?? 1} 级` },
  { label: '技巧得分', value: formatPluginScore(game.value.score ?? 0, { unit: '分' }) },
  {
    label: '平均反应',
    value: game.value.averageResponseMs == null
      ? '—'
      : formatPluginDuration(game.value.averageResponseMs, { style: 'readable', fractionDigits: 2 }),
  },
])

const resultTitle = computed(() => ({
  completed: '十级赛道通关',
  timeout: '未能及时转向',
  wrong: '这次方向算错了',
}[game.value.endReason ?? 'wrong']))

const resultDescription = computed(() => {
  if (game.value.endReason === 'completed') {
    return `连续通过 ${game.value.correctAnswers ?? 100} 个路口，用时 ${formatPluginDuration(game.value.elapsedMs, { style: 'readable', fractionDigits: 1 })}。`
  }
  const correct = directionLabel(game.value.correctDirection)
  if (game.value.endReason === 'timeout') {
    return `跑者到达路口前没有收到方向输入；正确路线是${correct}。`
  }
  return `所选方向的等式不成立；这道题的正确路线是${correct}。`
})

const resultTone = computed<'success' | 'danger'>(() => (
  game.value.endReason === 'completed' ? 'success' : 'danger'
))

const statusAnnouncement = computed(() => {
  if (game.value.endReason === 'completed') {
    return `挑战完成，最大路程 ${game.value.distanceMeters ?? 0} 米`
  }
  if (game.value.endReason === 'timeout') {
    return `挑战因超时结束，正确方向是${directionLabel(game.value.correctDirection)}`
  }
  if (game.value.endReason === 'wrong') {
    return `挑战因错答结束，正确方向是${directionLabel(game.value.correctDirection)}`
  }
  if (game.value.levelUp) return `升级到第 ${game.value.level ?? 1} 级`
  const directions = (game.value.options ?? [])
    .map((option) => directionLabel(option.direction))
    .join('、')
  return `${currentQuestionLabel.value}，开放方向：${directions}`
})

function stopCountdown() {
  if (countdownTimer !== null) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function tickCountdown() {
  if (props.snapshot.phase !== 'playing') {
    displayRemainingMs.value = 0
    stopCountdown()
    return
  }
  displayRemainingMs.value = Math.max(0, Math.ceil(localDeadline - performance.now()))
  if (displayRemainingMs.value <= 0) {
    stopCountdown()
    void submitTimeout()
  }
}

function syncCountdown() {
  stopCountdown()
  displayRemainingMs.value = Math.max(0, game.value.remainingMs ?? 0)
  if (props.snapshot.phase !== 'playing' || typeof window === 'undefined') return
  localDeadline = performance.now() + displayRemainingMs.value
  tickCountdown()
  if (displayRemainingMs.value > 0) {
    countdownTimer = window.setInterval(tickCountdown, 50)
  }
}

async function submitTimeout() {
  const questionId = game.value.questionId
  if (
    questionId == null
    || timeoutSentFor.value === questionId
    || props.snapshot.phase !== 'playing'
    || !props.snapshot.actions.canAct
    || isSpectator.value
  ) return

  timeoutSentFor.value = questionId
  submitting.value = true
  const accepted = await actions.action('timeout', { questionId })
  if (!accepted && props.snapshot.phase === 'playing' && game.value.questionId === questionId) {
    timeoutSentFor.value = null
    localDeadline = performance.now() + 80
    countdownTimer = window.setInterval(tickCountdown, 50)
  }
  submitting.value = false
}

async function chooseDirection(direction: Direction) {
  if (!canControl.value || !availableDirections.value.has(direction)) return
  const questionId = game.value.questionId
  if (questionId == null) return

  selectedDirection.value = direction
  submitting.value = true
  const accepted = await actions.action('choose', { questionId, direction })
  if (!accepted && game.value.questionId === questionId && props.snapshot.phase === 'playing') {
    selectedDirection.value = null
  }
  submitting.value = false
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

function handleKeydown(event: KeyboardEvent) {
  if (
    event.repeat
    || event.altKey
    || event.ctrlKey
    || event.metaKey
    || showRules.value
    || isEditableTarget(event.target)
  ) return
  const direction = KEY_TO_DIRECTION[event.key.toLowerCase()]
  if (!direction || !availableDirections.value.has(direction)) return
  event.preventDefault()
  void chooseDirection(direction)
}

async function restartGame() {
  if (!props.snapshot.actions.canRestart || restarting.value) return
  restarting.value = true
  await actions.restart()
  restarting.value = false
}

watch(
  () => game.value.questionId,
  (questionId, previousQuestionId) => {
    if (
      previousQuestionId != null
      && questionId != null
      && questionId !== previousQuestionId
      && game.value.lastDirection
    ) {
      turnDirection.value = game.value.lastDirection
      if (turnTimer !== null) window.clearTimeout(turnTimer)
      turnTimer = window.setTimeout(() => {
        turnDirection.value = null
      }, 650)
    }
    if (questionId !== previousQuestionId) {
      selectedDirection.value = null
      timeoutSentFor.value = null
      submitting.value = false
    }
  },
)

watch(
  () => [game.value.questionId, game.value.remainingMs, props.snapshot.phase],
  syncCountdown,
  { immediate: true },
)

onMounted(() => {
  document.documentElement.classList.add(viewportLockClass)
  document.body.classList.add(viewportLockClass)
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  stopCountdown()
  if (turnTimer !== null) window.clearTimeout(turnTimer)
  window.removeEventListener('keydown', handleKeydown)
  document.documentElement.classList.remove(viewportLockClass)
  document.body.classList.remove(viewportLockClass)
})
</script>

<template>
  <section
    ref="gameRoot"
    class="math-runner"
    :style="rootStyle"
    aria-label="算途疾行单人数学跑酷"
  >
    <span class="viewport-ambient viewport-ambient--left" aria-hidden="true" />
    <span class="viewport-ambient viewport-ambient--right" aria-hidden="true" />

    <header class="runner-header">
      <div class="runner-brand">
        <span class="brand-mark" aria-hidden="true"><Route :size="24" /></span>
        <div>
          <small>MATHWAY SPRINT · SOLO</small>
          <h2>算途疾行</h2>
        </div>
      </div>

      <PluginMetricGrid
        class="runner-metrics"
        :items="metricItems"
        :columns="4"
        value-first
        aria-label="本局跑酷数据"
      />

      <div class="header-actions">
        <PluginIconButton label="查看算途疾行规则" @click="showRules = true">
          <BookOpen :size="18" />
        </PluginIconButton>
        <PluginIconButton
          v-if="isFullscreenSupported"
          :label="isFullscreen ? '退出游戏全屏' : '进入游戏全屏'"
          @click="toggleFullscreen()"
        >
          <Minimize2 v-if="isFullscreen" :size="18" />
          <Maximize2 v-else :size="18" />
        </PluginIconButton>
      </div>
    </header>

    <main
      class="runner-cockpit"
      :class="{ 'runner-cockpit--finished': snapshot.phase === 'finished' }"
    >
      <div class="scene-shell">
        <TrackScene
          :game="game"
          :remaining-ms="displayRemainingMs"
          :selected-direction="selectedDirection"
          :turn-direction="turnDirection"
          :disabled="!canControl"
          @choose="chooseDirection"
        />
      </div>

      <aside v-if="snapshot.phase === 'playing'" class="control-deck">
        <div class="level-progress" :class="{ 'level-progress--up': game.levelUp }">
          <div>
            <span><Gauge :size="15" />{{ levelProgressLabel }}</span>
            <b>{{ currentQuestionLabel }}</b>
          </div>
          <span class="level-progress-track" aria-hidden="true">
            <i :style="{ width: `${levelProgress}%` }" />
          </span>
        </div>

        <div class="control-copy">
          <small>{{ isSpectator ? '只读观战' : '方向控制' }}</small>
          <strong>
            {{ submitting ? '正在确认路线…' : isSpectator ? '正在观看挑战者作答' : 'WASD / 点击四向键' }}
          </strong>
          <span :class="{ urgent: remainingRatio <= .25 }">
            必须在路口前完成选择 · 剩余 {{ (displayRemainingMs / 1000).toFixed(1) }} 秒
          </span>
        </div>

        <DirectionPad
          :options="game.options ?? []"
          :selected-direction="selectedDirection"
          :disabled="!canControl"
          @choose="chooseDirection"
        />

        <footer class="runner-footer">
          <span>每题 24 米 · 每 10 题升级</span>
          <PluginButton compact variant="secondary" @click="showRules = true">
            <BookOpen :size="15" /> 规则
          </PluginButton>
        </footer>
      </aside>

      <PluginResultCard
        v-else-if="snapshot.phase === 'finished'"
        class="runner-result"
        eyebrow="最大路程排行榜成绩"
        :title="resultTitle"
        :description="resultDescription"
        :score="formatPluginScore(game.distanceMeters ?? 0)"
        score-unit="米"
        :metrics="resultMetrics"
        restart-label="重新起跑"
        :can-restart="snapshot.actions.canRestart"
        :busy="restarting"
        :tone="resultTone"
        @restart="restartGame"
      >
        <template #icon>
          <Trophy v-if="game.endReason === 'completed'" :size="22" />
          <Route v-else :size="22" />
        </template>
        <template #note>
          <span class="leaderboard-note"><Sparkles :size="14" />大厅用户榜按本局路程取个人历史最大值。</span>
        </template>
      </PluginResultCard>
    </main>

    <div class="orientation-hint" role="status">
      <Route :size="34" />
      <strong>请将手机旋转为横屏</strong>
      <span>横屏可同时看清四向题牌、跑者和触控方向键。</span>
    </div>

    <p class="sr-announcement" aria-live="polite" aria-atomic="true">
      {{ statusAnnouncement }}
    </p>

    <PluginModal
      v-if="showRules"
      title="算途疾行规则"
      aria-label="算途疾行完整规则"
      size="large"
      mobile-sheet
      @close="showRules = false"
    >
      <PluginRuleGuide :content="mathRunnerRuleGuide" />
    </PluginModal>
  </section>
</template>

<style scoped>
.math-runner {
  width: min(100%, 1180px);
  min-width: 0;
  max-width: 100%;
  display: grid;
  gap: clamp(12px, 2vw, 20px);
  margin: 0 auto;
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 55%, var(--mr-line));
  border-radius: clamp(20px, 3vw, 34px);
  padding: clamp(14px, 2.5vw, 28px);
  overflow: clip;
  color: var(--mr-copy-primary);
  background:
    radial-gradient(circle at 92% 0, color-mix(in srgb, var(--mr-accent) 10%, transparent), transparent 26%),
    color-mix(in srgb, var(--mr-surface-inset) 93%, var(--mr-scene-bottom));
  box-shadow: 0 24px 70px color-mix(in srgb, var(--mr-shadow) 22%, transparent);
}

.math-runner:fullscreen {
  width: 100%;
  max-width: none;
  height: 100%;
  overflow: auto;
  border-radius: 0;
  padding: clamp(12px, 2vw, 26px);
}

.runner-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
}

.runner-brand {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 13px;
}

.brand-mark {
  width: 48px;
  aspect-ratio: 1;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--mr-accent) 45%, var(--mr-line));
  border-radius: 15px;
  color: var(--mr-accent);
  background: linear-gradient(145deg, color-mix(in srgb, var(--mr-accent) 13%, transparent), var(--mr-surface-inset));
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 10%, transparent);
}

.runner-brand div { min-width: 0; }
.runner-brand small { display: block; color: var(--mr-accent); font-size: 8px; font-weight: 950; letter-spacing: .17em; }
.runner-brand h2 { margin: 4px 0 2px; font-family: "Songti SC", "STSong", serif; font-size: clamp(27px, 4vw, 42px); line-height: 1; }
.runner-brand p { margin: 0; color: var(--mr-copy-secondary); font-size: 11px; }
.header-actions { display: flex; flex: 0 0 auto; gap: 8px; }

.runner-metrics :deep(.solo-metric-grid) { gap: 9px; }
.runner-metrics :deep(.solo-metric-card) {
  min-width: 0;
  border-color: color-mix(in srgb, var(--mr-stage-edge) 48%, var(--mr-line));
  background: color-mix(in srgb, var(--mr-metal-glass) 24%, var(--mr-surface-inset));
}
.runner-metrics :deep(.solo-metric-card strong) { font-size: clamp(16px, 2.6vw, 24px); }

.level-progress {
  display: grid;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 45%, var(--mr-line));
  border-radius: 14px;
  padding: 10px 13px;
  background: color-mix(in srgb, var(--mr-metal-glass) 16%, var(--mr-surface-inset));
}

.level-progress > div { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.level-progress span { display: flex; align-items: center; gap: 6px; color: var(--mr-copy-secondary); font-size: 9px; font-weight: 850; }
.level-progress b { font-size: 10px; }
.level-progress-track { width: 100%; height: 6px; overflow: hidden; border-radius: 99px; background: color-mix(in srgb, var(--mr-stage-detail) 48%, transparent); }
.level-progress-track i { display: block; width: 0; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--mr-accent), var(--mr-success)); box-shadow: 0 0 10px color-mix(in srgb, var(--mr-accent) 50%, transparent); transition: width 260ms ease; }
.level-progress--up { border-color: color-mix(in srgb, var(--mr-success) 70%, var(--mr-line)); }

.control-deck {
  display: grid;
  grid-template-columns: minmax(190px, .7fr) minmax(230px, 1fr);
  align-items: center;
  gap: clamp(14px, 3vw, 28px);
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 45%, var(--mr-line));
  border-radius: 19px;
  padding: 14px clamp(13px, 3vw, 24px);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--mr-metal-glass) 18%, transparent), transparent),
    var(--mr-surface-inset);
}

.control-copy { display: grid; gap: 4px; }
.control-copy small { color: var(--mr-accent); font-size: 8px; font-weight: 950; letter-spacing: .15em; }
.control-copy strong { font-size: clamp(14px, 2vw, 19px); }
.control-copy span { color: var(--mr-copy-secondary); font-size: 10px; }
.control-copy span.urgent { color: var(--mr-warning); font-weight: 900; }

.runner-result { width: min(100%, 760px); margin: 0 auto; }
.leaderboard-note { display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: var(--mr-copy-secondary); font-size: 10px; }
.leaderboard-note svg { color: var(--mr-accent); }

.runner-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--mr-line);
  padding-top: 12px;
  color: var(--mr-copy-secondary);
  font-size: 9px;
}

.sr-announcement {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.math-runner :deep(.plugin-rule-guide) { margin: 0; }

@media (max-width: 760px) {
  .math-runner { gap: 12px; padding: 13px; border-radius: 21px; }
  .runner-header { align-items: flex-start; }
  .brand-mark { width: 43px; border-radius: 13px; }
  .runner-brand p { display: none; }
  .runner-metrics :deep(.solo-metric-grid) { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
  .control-deck { grid-template-columns: 1fr; justify-items: center; padding: 13px; }
  .control-copy { justify-items: center; text-align: center; }
  .runner-footer { align-items: flex-start; }
}

@media (max-width: 390px) {
  .math-runner { padding: 10px; }
  .runner-brand { gap: 9px; }
  .brand-mark { width: 38px; }
  .runner-brand h2 { font-size: 25px; }
  .runner-brand small { font-size: 7px; letter-spacing: .12em; }
  .header-actions { gap: 5px; }
  .level-progress > div { align-items: flex-start; }
  .runner-footer { display: grid; justify-items: center; text-align: center; }
}

@media (prefers-reduced-motion: reduce) {
  .level-progress-track i { transition: none; }
}
</style>

<style scoped>
:global(html.math-runner-viewport-lock),
:global(body.math-runner-viewport-lock) {
  width: 100%;
  height: 100%;
  overflow: hidden !important;
  overscroll-behavior: none;
}

.math-runner,
.math-runner:fullscreen {
  position: fixed;
  z-index: 38;
  inset: 0;
  width: 100%;
  min-width: 0;
  max-width: none;
  height: 100dvh;
  min-height: 0;
  max-height: 100dvh;
  grid-template-rows: auto minmax(0, 1fr);
  gap: clamp(7px, 1.15vmin, 13px);
  margin: 0;
  border: 0;
  border-radius: 0;
  padding:
    max(8px, env(safe-area-inset-top))
    max(9px, env(safe-area-inset-right))
    max(8px, env(safe-area-inset-bottom))
    max(9px, env(safe-area-inset-left));
  overflow: clip;
  overscroll-behavior: none;
  touch-action: manipulation;
  background:
    radial-gradient(circle at 10% 4%, color-mix(in srgb, #ffc56e 22%, transparent), transparent 30%),
    radial-gradient(circle at 88% 12%, color-mix(in srgb, var(--mr-scene-glow) 42%, transparent), transparent 28%),
    linear-gradient(160deg, var(--mr-scene-top), var(--mr-scene-center) 52%, var(--mr-scene-bottom));
  box-shadow: none;
}

.viewport-ambient {
  position: absolute;
  z-index: 0;
  width: min(42vw, 620px);
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--mr-accent) 16%, transparent);
  border-radius: 50%;
  opacity: .42;
  pointer-events: none;
}

.viewport-ambient::before,
.viewport-ambient::after {
  position: absolute;
  inset: 14%;
  border: 1px dashed color-mix(in srgb, var(--mr-accent) 18%, transparent);
  border-radius: inherit;
  content: '';
}

.viewport-ambient::after { inset: 31%; border-style: solid; }
.viewport-ambient--left { bottom: -31%; left: -12%; }
.viewport-ambient--right { top: -34%; right: -9%; }

.runner-header {
  position: relative;
  z-index: 2;
  min-height: 52px;
  display: grid;
  grid-template-columns: auto minmax(300px, 720px) auto;
  align-items: center;
  justify-content: center;
  gap: clamp(8px, 1.5vw, 18px);
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 58%, var(--mr-line));
  border-radius: 17px;
  padding: 6px clamp(7px, 1.3vw, 15px);
  background:
    linear-gradient(115deg, color-mix(in srgb, #ffe1a8 8%, transparent), transparent 28%),
    color-mix(in srgb, var(--mr-metal-body) 86%, transparent);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 13%, transparent), 0 9px 28px color-mix(in srgb, var(--mr-shadow) 22%, transparent);
  backdrop-filter: blur(18px) saturate(118%);
}

.runner-brand { gap: 9px; }
.brand-mark { width: 40px; border-radius: 12px; }
.runner-brand small { font-size: 7px; }
.runner-brand h2 { margin: 2px 0 0; font-size: clamp(19px, 2.2vw, 27px); }

.runner-metrics { width: 100%; min-width: 0; }
.runner-metrics :deep(.solo-metric-grid) { gap: 6px; }
.runner-metrics :deep(.solo-metric-card) {
  gap: 2px;
  min-height: 40px;
  padding: 5px 7px;
  border-radius: 11px;
  background: color-mix(in srgb, var(--mr-metal-glass) 22%, var(--mr-surface-inset));
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 12%, transparent);
}
.runner-metrics :deep(.solo-metric-card small) { font-size: 7px; }
.runner-metrics :deep(.solo-metric-card strong) { font-size: clamp(12px, 1.7vw, 17px); }

.runner-cockpit {
  position: relative;
  z-index: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(230px, 23vw, 305px);
  gap: clamp(7px, 1.2vw, 14px);
  overflow: hidden;
}

.runner-cockpit--finished { grid-template-columns: minmax(0, 1fr); }

.scene-shell {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, #d9a95f 45%, var(--mr-stage-edge));
  border-radius: clamp(15px, 2vw, 26px);
  background: var(--mr-scene-center);
  box-shadow: 0 18px 54px color-mix(in srgb, var(--mr-shadow) 35%, transparent);
}

.control-deck {
  min-width: 0;
  min-height: 0;
  height: 100%;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  align-items: center;
  justify-items: stretch;
  gap: clamp(7px, 1.35vmin, 12px);
  border-color: color-mix(in srgb, #d9a95f 45%, var(--mr-stage-edge));
  border-radius: clamp(15px, 2vw, 24px);
  padding: clamp(9px, 1.55vmin, 16px);
  overflow: hidden;
  background:
    linear-gradient(145deg, color-mix(in srgb, #dffaff 9%, transparent), transparent 40%),
    color-mix(in srgb, var(--mr-metal-body) 90%, var(--mr-surface-inset));
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 13%, transparent), 0 18px 46px color-mix(in srgb, var(--mr-shadow) 25%, transparent);
}

.level-progress {
  gap: 6px;
  border-radius: 12px;
  padding: 8px 9px;
  background: color-mix(in srgb, var(--mr-metal-glass) 19%, var(--mr-surface-inset));
}
.level-progress > div { align-items: center; }
.level-progress span { font-size: 8px; }
.level-progress b { font-size: 9px; white-space: nowrap; }
.level-progress-track { height: 5px; }

.control-copy {
  justify-items: center;
  gap: 3px;
  text-align: center;
}
.control-copy small { font-size: 7px; }
.control-copy strong { font-size: clamp(12px, 1.45vw, 17px); }
.control-copy span { font-size: 9px; line-height: 1.35; }

.control-deck :deep(.direction-pad) { align-self: center; }

.runner-footer {
  min-width: 0;
  gap: 6px;
  padding-top: 8px;
  font-size: 8px;
}
.runner-footer span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.runner-result {
  position: absolute;
  z-index: 18;
  top: 50%;
  left: 50%;
  width: min(calc(100% - 26px), 650px);
  max-height: calc(100% - 20px);
  margin: 0;
  overflow: hidden;
  border-color: color-mix(in srgb, var(--mr-accent) 48%, var(--mr-line));
  padding: clamp(13px, 2.1vmin, 22px);
  background: color-mix(in srgb, var(--mr-surface-inset) 92%, transparent);
  box-shadow: 0 22px 70px color-mix(in srgb, var(--mr-shadow) 55%, transparent), inset 0 1px 0 color-mix(in srgb, white 16%, transparent);
  transform: translate(-50%, -50%);
  backdrop-filter: blur(22px) saturate(115%);
}
.runner-result :deep(.solo-result-score) { font-size: clamp(34px, 7vmin, 56px); }
.runner-result :deep(.solo-result-metrics) { margin: 4px 0 0; }
.runner-result :deep(.solo-metric-card) { gap: 2px; padding: 7px 5px; }
.runner-result :deep(.solo-result-restart) { margin-top: 3px; }
.leaderboard-note { font-size: 9px; }

.orientation-hint {
  position: absolute;
  z-index: 30;
  inset: 0;
  display: none;
  place-content: center;
  justify-items: center;
  gap: 8px;
  padding: 28px;
  color: var(--mr-copy-primary);
  background:
    radial-gradient(circle at 50% 35%, color-mix(in srgb, var(--mr-accent) 16%, transparent), transparent 32%),
    var(--mr-scene-bottom);
  text-align: center;
}
.orientation-hint svg { color: var(--mr-accent); animation: phone-rotate-hint 1.8s ease-in-out infinite; }
.orientation-hint strong { font-size: 22px; }
.orientation-hint span { max-width: 280px; color: var(--mr-copy-secondary); font-size: 11px; line-height: 1.55; }

@keyframes phone-rotate-hint {
  0%, 20%, 100% { transform: rotate(0); }
  55%, 80% { transform: rotate(90deg); }
}

@media (orientation: landscape) and (max-width: 980px), (max-height: 620px) {
  .math-runner,
  .math-runner:fullscreen {
    gap: 6px;
    padding:
      max(5px, env(safe-area-inset-top))
      max(6px, env(safe-area-inset-right))
      max(5px, env(safe-area-inset-bottom))
      max(6px, env(safe-area-inset-left));
  }

  .runner-header {
    min-height: 42px;
    grid-template-columns: auto minmax(220px, 1fr) auto;
    gap: 6px;
    border-radius: 12px;
    padding: 4px 6px;
  }

  .runner-brand { gap: 6px; }
  .brand-mark { width: 34px; border-radius: 10px; }
  .runner-brand small { display: none; }
  .runner-brand h2 { margin: 0; font-size: 17px; }
  .header-actions { gap: 4px; }

  .runner-metrics :deep(.solo-metric-grid) { gap: 4px; }
  .runner-metrics :deep(.solo-metric-card) { min-height: 33px; padding: 3px 4px; border-radius: 8px; }
  .runner-metrics :deep(.solo-metric-card small) { font-size: 6px; }
  .runner-metrics :deep(.solo-metric-card strong) { font-size: clamp(10px, 2.2vw, 13px); }

  .runner-cockpit {
    grid-template-columns: minmax(0, 1fr) clamp(176px, 28vw, 220px);
    gap: 6px;
  }
  .runner-cockpit--finished { grid-template-columns: minmax(0, 1fr); }
  .scene-shell,
  .control-deck { border-radius: 12px; }
  .control-deck { gap: 5px; padding: 6px; }
  .level-progress { gap: 4px; border-radius: 9px; padding: 5px 6px; }
  .level-progress span { font-size: 7px; }
  .level-progress b { font-size: 7px; }
  .level-progress-track { height: 3px; }
  .control-copy { gap: 1px; }
  .control-copy small { font-size: 6px; }
  .control-copy strong { font-size: 10px; }
  .control-copy span { font-size: 7px; }
  .runner-footer { padding-top: 4px; }
  .runner-footer span { display: none; }
  .runner-footer :deep(button) { width: 100%; min-height: 30px; }

  .runner-result {
    width: min(calc(100% - 14px), 560px);
    max-height: calc(100% - 10px);
    gap: 4px;
    padding: 9px 12px;
  }
  .runner-result :deep(.solo-result-eyebrow) { font-size: 8px; }
  .runner-result :deep(.solo-result-score) { font-size: clamp(28px, 8vh, 40px); }
  .runner-result :deep(h2) { font-size: 10px; }
  .runner-result :deep(p) { font-size: 8px; line-height: 1.35; }
  .runner-result :deep(.solo-result-metrics) { margin: 2px 0 0; }
  .runner-result :deep(.solo-metric-grid) { gap: 4px; }
  .runner-result :deep(.solo-metric-card) { min-height: 34px; padding: 3px; }
  .runner-result :deep(.solo-metric-card small) { font-size: 6px; }
  .runner-result :deep(.solo-metric-card strong) { font-size: 11px; }
  .runner-result :deep(.solo-result-restart) { min-height: 30px; margin-top: 1px; font-size: 9px; }
  .leaderboard-note { font-size: 7px; }
}

@media (orientation: landscape) and (max-width: 700px) {
  .runner-brand > div { display: none; }
  .runner-header { grid-template-columns: auto minmax(0, 1fr) auto; }
}

@media (orientation: landscape) and (max-height: 360px) {
  .runner-header { min-height: 38px; }
  .brand-mark { width: 30px; }
  .runner-metrics :deep(.solo-metric-card) { min-height: 29px; }
  .control-copy span,
  .runner-footer { display: none; }
  .control-deck { grid-template-rows: auto auto minmax(0, 1fr); }
}

@media (orientation: portrait) and (max-width: 760px) {
  .orientation-hint { display: grid; }
}

@media (prefers-reduced-motion: reduce) {
  .orientation-hint svg { animation: none; transform: rotate(90deg); }
}
</style>
