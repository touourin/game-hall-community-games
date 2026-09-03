<script setup lang="ts">
import { computed } from 'vue'
import RunnerModel from './RunnerModel.vue'
import {
  RUNNER_ACTION_META,
  laneLabel,
  type MathRunnerGameView,
  type RunnerAction,
  type RunnerFailureKind,
  type RunnerOption,
  type TrackLane,
} from '../types'

const props = withDefaults(defineProps<{
  game: MathRunnerGameView
  remainingMs: number
  selectedAction?: RunnerAction | null
  runnerAction?: RunnerAction | null
  disabled?: boolean
}>(), {
  selectedAction: null,
  runnerAction: null,
  disabled: false,
})

const emit = defineEmits<{
  choose: [action: RunnerAction]
}>()

const TRACK_LANES: readonly TrackLane[] = ['left', 'center', 'right']
const ROAD_STONE_INDEXES = Array.from({ length: 7 }, (_, index) => index)
const MARKER_INDEXES = Array.from({ length: 4 }, (_, index) => index)
const optionByLane = computed(() => new Map(
  (props.game.options ?? []).map((option) => [option.lane, option]),
))
const remainingRatio = computed(() => {
  const limit = Math.max(1, props.game.timeLimitMs ?? 1)
  return Math.min(1, Math.max(0, props.remainingMs / limit))
})
const failureKind = computed<RunnerFailureKind>(() => {
  if (!props.game.endReason || props.game.endReason === 'completed') return null
  const decisiveAction = props.game.endReason === 'wrong'
    ? props.game.lastAction
    : props.game.correctAction
  return decisiveAction === 'left' || decisiveAction === 'right' ? 'cliff' : 'wall'
})
const forkVariant = computed(() => Math.abs(props.game.questionId ?? 0) % 3)
const stageStyle = computed(() => ({
  '--track-period': `${props.game.speed?.trackPeriodMs ?? 1500}ms`,
  '--backdrop-period': `${(props.game.speed?.trackPeriodMs ?? 1500) * 7}ms`,
  '--question-period': `${Math.max(1000, props.game.timeLimitMs ?? 6500)}ms`,
  '--question-delay': `${-Math.max(
    0,
    (props.game.timeLimitMs ?? 6500) - (props.game.remainingMs ?? props.game.timeLimitMs ?? 6500),
  )}ms`,
  '--timer-angle': `${remainingRatio.value * 360}deg`,
}))
const stageClass = computed(() => ({
  'track-scene--urgent': remainingRatio.value <= 0.25 && !props.game.endReason,
  'track-scene--level-up': Boolean(props.game.levelUp && !props.game.endReason),
  [`track-scene--${props.game.endReason}`]: Boolean(props.game.endReason),
  [`track-scene--failure-${failureKind.value}`]: Boolean(failureKind.value),
  [`track-scene--fork-${forkVariant.value}`]: true,
  [`track-scene--branches-${props.game.branchCount ?? props.game.options?.length ?? 2}`]: true,
}))

function optionForLane(lane: TrackLane): RunnerOption | undefined {
  return optionByLane.value.get(lane)
}

function metaFor(action: RunnerAction) {
  return RUNNER_ACTION_META.find((entry) => entry.id === action)!
}

function laneClass(lane: TrackLane) {
  const option = optionForLane(lane)
  return {
    [`route-lane--${lane}`]: true,
    'route-lane--closed': !option,
    'route-lane--failed': laneFailedAtCliff(lane),
    'route-lane--selected': Boolean(option && props.selectedAction === option.action),
    'route-lane--correct': Boolean(
      option && props.game.endReason && props.game.correctAction === option.action,
    ),
  }
}

function gateClass(option: RunnerOption) {
  return {
    [`lane-gate--${option.lane}`]: true,
    [`lane-gate--${option.action}`]: true,
    'lane-gate--selected': props.selectedAction === option.action
      || Boolean(props.game.endReason && props.game.lastAction === option.action),
    'lane-gate--correct': Boolean(
      props.game.endReason && props.game.correctAction === option.action,
    ),
    'lane-gate--wrong': Boolean(
      props.game.endReason === 'wrong'
      && props.game.lastAction === option.action
      && props.game.correctAction !== option.action,
    ),
  }
}

function gateLabel(option: RunnerOption): string {
  const meta = metaFor(option.action)
  const obstacle = option.obstacle === 'ground'
    ? '，前方是必须跳过的低墙'
    : option.obstacle === 'overhead'
      ? '，前方是必须下蹲穿过的高墙'
      : ''
  const result = props.game.endReason && props.game.correctAction === option.action
    ? '，这是正确路线'
    : ''
  return `${laneLabel(option.lane)}，按 ${meta.key} ${meta.label}${obstacle}，等式 ${option.equation}${result}`
}

function seededUnit(index: number, salt: number): number {
  const seed = (props.game.questionId ?? 1) * 97 + index * 53 + salt * 31
  return Math.abs(Math.sin(seed) * 10_000) % 1
}

function roadStoneStyle(index: number) {
  const period = props.game.speed?.trackPeriodMs ?? 1500
  return {
    '--stone-x': `${18 + seededUnit(index, 1) * 64}%`,
    '--stone-width': `${10 + seededUnit(index, 2) * 14}px`,
    '--stone-rotation': `${-28 + seededUnit(index, 3) * 56}deg`,
    animationDelay: `${-(period * index / ROAD_STONE_INDEXES.length)}ms`,
  }
}

function laneFailedAtCliff(lane: TrackLane): boolean {
  const option = optionForLane(lane)
  return Boolean(
    option
    && failureKind.value === 'cliff'
    && props.game.endReason === 'wrong'
    && props.game.lastAction === option.action
    && props.game.correctAction !== option.action,
  )
}

function markerStyle(index: number) {
  const period = props.game.speed?.trackPeriodMs ?? 1500
  return {
    animationDelay: `${-(period * index / MARKER_INDEXES.length)}ms`,
  }
}
</script>

<template>
  <section
    class="track-scene"
    :class="stageClass"
    :style="stageStyle"
    aria-label="算途疾行随机分叉桥面与高低墙障碍"
  >
    <div
      class="scene-camera"
      :class="runnerAction ? `scene-camera--${runnerAction}` : ''"
      aria-hidden="true"
    >
      <div class="scene-backdrop" />
    </div>
    <div class="scene-vignette" aria-hidden="true" />
    <div class="horizon-haze" aria-hidden="true" />
    <div class="bridge-towers" aria-hidden="true">
      <span class="bridge-tower bridge-tower--left" />
      <span class="bridge-tower bridge-tower--right" />
    </div>

    <div
      class="bridge-world"
      :class="runnerAction ? `bridge-world--${runnerAction}` : ''"
      aria-hidden="true"
    >
      <div class="bridge-deck">
        <span class="bridge-rail bridge-rail--left" />
        <span class="bridge-rail bridge-rail--right" />
        <span class="bridge-seam bridge-seam--left" />
        <span class="bridge-seam bridge-seam--right" />
        <span class="bridge-center-glow" />
        <span
          v-for="index in ROAD_STONE_INDEXES"
          :key="`road-stone-${index}`"
          class="road-stone"
          :style="roadStoneStyle(index)"
        />
        <template v-for="index in MARKER_INDEXES" :key="`marker-${index}`">
          <span class="bridge-marker bridge-marker--left" :style="markerStyle(index)" />
          <span class="bridge-marker bridge-marker--right" :style="markerStyle(index)" />
        </template>
      </div>

      <div class="route-lanes">
        <span
          v-for="lane in TRACK_LANES"
          :key="lane"
          class="route-lane"
          :class="laneClass(lane)"
          :data-route-state="laneFailedAtCliff(lane) ? 'failed-cliff' : optionForLane(lane) ? 'open' : 'cliff'"
        >
          <i v-if="!optionForLane(lane) || laneFailedAtCliff(lane)" class="broken-edge" />
        </span>
      </div>
    </div>

    <template
      v-for="lane in TRACK_LANES"
      :key="`${game.questionId ?? 'end'}-${game.endReason ?? 'running'}-${lane}`"
    >
      <button
        v-if="optionForLane(lane)"
        type="button"
        class="lane-gate"
        :class="gateClass(optionForLane(lane)!)"
        :disabled="disabled"
        :aria-label="gateLabel(optionForLane(lane)!)"
        :data-lane="lane"
        :data-action="optionForLane(lane)!.action"
        @click="emit('choose', optionForLane(lane)!.action)"
      >
        <span class="gate-frame" aria-hidden="true" />
        <span class="gate-action">
          <kbd>{{ metaFor(optionForLane(lane)!.action).key }}</kbd>
          <b>{{ metaFor(optionForLane(lane)!.action).symbol }}</b>
          <span>{{ metaFor(optionForLane(lane)!.action).label }}</span>
        </span>
        <strong class="gate-equation">{{ optionForLane(lane)!.equation }}</strong>
        <small>{{ laneLabel(lane) }}</small>
        <span
          v-if="game.endReason && game.correctAction === optionForLane(lane)!.action"
          class="gate-result gate-result--correct"
          aria-hidden="true"
        >✓</span>
        <span
          v-else-if="game.endReason === 'wrong' && game.lastAction === optionForLane(lane)!.action"
          class="gate-result gate-result--wrong"
          aria-hidden="true"
        >×</span>
      </button>

      <div
        v-else
        class="cliff-mouth"
        :class="`cliff-mouth--${lane}`"
        data-obstacle="cliff"
        aria-hidden="true"
      >
        <span />
        <i />
      </div>
    </template>

    <template
      v-for="option in game.options ?? []"
      :key="`${game.questionId ?? 'end'}-${game.endReason ?? 'running'}-${option.lane}-${option.action}`"
    >
      <div
        v-if="option.obstacle"
        class="lane-obstacle"
        :class="[
          `lane-obstacle--${option.lane}`,
          `lane-obstacle--${option.obstacle}`,
        ]"
        :data-obstacle="option.obstacle"
        aria-hidden="true"
      >
        <template v-if="option.obstacle === 'ground'">
          <span class="wall-face" />
          <span class="ground-block ground-block--one" />
          <span class="ground-block ground-block--two" />
          <span class="ground-block ground-block--three" />
        </template>
        <template v-else>
          <span class="overhead-post overhead-post--left" />
          <span class="overhead-post overhead-post--right" />
          <span class="overhead-beam" />
          <span class="overhead-warning" />
        </template>
        <kbd>{{ metaFor(option.action).key }}</kbd>
      </div>
    </template>

    <div
      class="runner-anchor"
      :class="runnerAction ? `runner-anchor--${runnerAction}` : ''"
    >
      <RunnerModel
        :action="runnerAction"
        :end-reason="game.endReason"
        :failure-kind="failureKind"
        :run-cycle-ms="game.speed?.runCycleMs ?? 720"
      />
    </div>

    <div
      v-if="failureKind"
      class="failure-fx"
      :class="`failure-fx--${failureKind}`"
      :data-failure-effect="failureKind"
      aria-hidden="true"
    >
      <span v-for="index in 6" :key="index" :style="{ '--piece-index': index - 1 }" />
    </div>

    <div
      class="scene-timer"
      :class="{ 'scene-timer--urgent': remainingRatio <= 0.25 && !game.endReason }"
      aria-hidden="true"
    >
      <span>{{ Math.max(0, remainingMs / 1000).toFixed(1) }}</span>
      <small>秒</small>
    </div>

    <div class="section-radar" aria-hidden="true">
      <b>随机 {{ game.branchCount ?? game.options?.length ?? 2 }} 路分叉</b>
      <span>低墙 W 跳 · 高墙 S 蹲 · A/D 转向</span>
    </div>

    <div v-if="game.levelUp && !game.endReason" class="level-up-flash" aria-hidden="true">
      <small>LEVEL UP</small>
      <strong>等级 {{ game.level }}</strong>
    </div>
  </section>
</template>

<style scoped>
.track-scene {
  --track-period: 1500ms;
  --backdrop-period: 10500ms;
  --question-period: 6500ms;
  --question-delay: 0ms;
  --timer-angle: 360deg;
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 420px;
  overflow: hidden;
  isolation: isolate;
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 70%, var(--mr-line));
  border-radius: clamp(18px, 2.2vw, 28px);
  color: var(--mr-copy-on-stage);
  background:
    linear-gradient(180deg, rgba(8, 18, 31, .04) 0 46%, rgba(5, 13, 24, .72) 100%),
    linear-gradient(180deg, var(--mr-scene-top), var(--mr-scene-bottom));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), 0 20px 54px rgba(2, 8, 18, .34);
}

.scene-camera {
  position: absolute;
  z-index: -3;
  inset: -5%;
  overflow: hidden;
  transform-origin: 50% 38%;
  will-change: transform;
}

.scene-backdrop {
  position: absolute;
  inset: -3%;
  background:
    linear-gradient(180deg, rgba(8, 18, 31, 0) 0 55%, rgba(5, 13, 24, .28) 100%),
    url('../assets/runner-bridge-backdrop.png') center / cover no-repeat;
  transform: scale(1.035);
  transform-origin: 50% 42%;
  animation: backdrop-forward var(--backdrop-period) ease-in-out infinite alternate;
  will-change: transform, background-position;
}

.scene-camera--left { animation: camera-turn-left 620ms cubic-bezier(.18, .78, .18, 1); }
.scene-camera--right { animation: camera-turn-right 620ms cubic-bezier(.18, .78, .18, 1); }
.scene-camera--jump { animation: camera-jump 620ms cubic-bezier(.2, .74, .24, 1); }
.scene-camera--slide { animation: camera-slide 620ms cubic-bezier(.18, .78, .2, 1); }

.scene-vignette {
  position: absolute;
  z-index: 0;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(3, 10, 20, .38), transparent 20% 80%, rgba(3, 10, 20, .38)),
    linear-gradient(0deg, rgba(2, 8, 18, .54), transparent 43%);
  pointer-events: none;
}

.horizon-haze {
  position: absolute;
  z-index: 0;
  top: 31%;
  left: 50%;
  width: 46%;
  height: 18%;
  border-radius: 50%;
  background: color-mix(in srgb, #ffe4bd 24%, transparent);
  filter: blur(22px);
  transform: translateX(-50%);
}

.bridge-towers { position: absolute; z-index: 1; inset: 19% 0 auto; height: 30%; pointer-events: none; }
.bridge-tower {
  position: absolute;
  bottom: 0;
  width: 7%;
  min-width: 32px;
  height: 72%;
  border: 2px solid rgba(85, 215, 232, .55);
  border-radius: 44% 44% 10px 10px;
  background: linear-gradient(90deg, #192536, #34485c 48%, #111c2b);
  box-shadow: 0 0 20px rgba(66, 206, 223, .2);
  opacity: .62;
}
.bridge-tower::before {
  position: absolute;
  top: -13px;
  left: 50%;
  width: 15px;
  aspect-ratio: 1;
  border: 1px solid #bff8ff;
  background: #45cada;
  content: '';
  transform: translateX(-50%) rotate(45deg);
  box-shadow: 0 0 14px #4ed6e7;
}
.bridge-tower--left { left: 13%; }
.bridge-tower--right { right: 13%; }

.bridge-world { position: absolute; z-index: 2; inset: 0; transform-origin: 50% 66%; }
.bridge-deck {
  position: absolute;
  inset: 34% -7% -8%;
  overflow: hidden;
  isolation: isolate;
  clip-path: polygon(44% 0, 56% 0, 92% 100%, 8% 100%);
  background:
    linear-gradient(104deg, transparent 0 23%, rgba(132, 177, 184, .07) 24% 25%, transparent 26% 73%, rgba(132, 177, 184, .06) 74% 75%, transparent 76%),
    linear-gradient(90deg, #0a1118, #33464d 18%, #42565b 49%, #34484f 82%, #0a1118);
  box-shadow: 0 24px 38px rgba(2, 8, 17, .5);
}
.bridge-deck::before {
  position: absolute;
  z-index: 1;
  inset: 0;
  background:
    radial-gradient(ellipse at 23% 64%, rgba(14, 22, 25, .38) 0 1.2%, transparent 1.45%),
    radial-gradient(ellipse at 67% 38%, rgba(164, 191, 191, .09) 0 .8%, transparent 1.05%),
    radial-gradient(ellipse at 48% 82%, rgba(10, 18, 20, .3) 0 1%, transparent 1.3%),
    linear-gradient(180deg, rgba(222, 248, 244, .12), transparent 24%);
  content: '';
  pointer-events: none;
}
.bridge-rail {
  position: absolute;
  z-index: 7;
  top: 0;
  bottom: 0;
  width: 3.2%;
  background: linear-gradient(90deg, #8d6536, #f2cf86 45%, #664420);
  box-shadow: 0 0 12px rgba(240, 196, 111, .35);
}
.bridge-rail--left { left: 7.2%; transform: skewX(-12deg); }
.bridge-rail--right { right: 7.2%; transform: skewX(12deg); }
.bridge-seam {
  position: absolute;
  z-index: 3;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(rgba(116, 221, 233, .12), rgba(116, 221, 233, .7));
  box-shadow: 0 0 8px rgba(76, 213, 231, .32);
}
.bridge-seam--left { left: 39%; transform: rotate(-3deg); }
.bridge-seam--right { right: 39%; transform: rotate(3deg); }
.bridge-center-glow {
  position: absolute;
  z-index: 2;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 34%;
  background: linear-gradient(180deg, rgba(105, 229, 242, .14), rgba(105, 229, 242, 0) 58%);
  filter: blur(12px);
  transform: translateX(-50%);
}

.road-stone {
  --stone-x: 50%;
  --stone-width: 16px;
  --stone-rotation: 0deg;
  position: absolute;
  z-index: 5;
  top: -3%;
  left: var(--stone-x);
  width: var(--stone-width);
  aspect-ratio: 1.65;
  border: 1px solid rgba(188, 206, 202, .13);
  border-radius: 46% 54% 38% 62%;
  background: linear-gradient(145deg, rgba(146, 166, 164, .36), rgba(10, 17, 20, .58));
  box-shadow: 0 4px 7px rgba(2, 8, 12, .34);
  clip-path: polygon(9% 24%, 63% 3%, 96% 42%, 73% 92%, 22% 82%);
  opacity: 0;
  transform: translateX(-50%) rotate(var(--stone-rotation)) scale(.18);
  animation: road-stone-approach var(--track-period) linear infinite;
  will-change: top, transform, opacity;
}

.bridge-marker {
  position: absolute;
  z-index: 6;
  top: 2%;
  width: 5px;
  height: 10px;
  border-radius: 3px 3px 1px 1px;
  background: linear-gradient(#f8df9e, #cf8734);
  box-shadow: 0 0 9px rgba(255, 205, 111, .72);
  opacity: 0;
  animation-duration: var(--track-period);
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: top, left, right, transform, opacity;
}

.bridge-marker--left {
  left: 46%;
  animation-name: marker-approach-left;
}

.bridge-marker--right {
  right: 46%;
  animation-name: marker-approach-right;
}

.route-lanes {
  position: absolute;
  z-index: 3;
  inset: 34% 4% -4%;
  pointer-events: none;
  filter: drop-shadow(0 15px 17px rgba(1, 6, 10, .36));
}
.route-lanes::before {
  position: absolute;
  z-index: -1;
  inset: 39% 23% -1%;
  background:
    linear-gradient(103deg, transparent 0 24%, rgba(177, 204, 202, .08) 25% 26%, transparent 27% 73%, rgba(177, 204, 202, .07) 74% 75%, transparent 76%),
    linear-gradient(90deg, #172329, #41545a 18% 82%, #172329);
  clip-path: polygon(43% 0, 57% 0, 100% 100%, 0 100%);
  content: '';
}
.route-lane {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(110deg, transparent 0 31%, rgba(158, 190, 188, .08) 32% 33%, transparent 34% 70%, rgba(158, 190, 188, .06) 71% 72%, transparent 73%),
    linear-gradient(90deg, #18252b, #485b5f 20% 80%, #18252b);
  filter: drop-shadow(0 0 1px rgba(164, 232, 233, .3));
  transition: filter 160ms ease, opacity 160ms ease;
}
.route-lane::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(205, 237, 234, .12), transparent 38%);
  content: '';
}
.route-lane--left { clip-path: polygon(4% 0, 28% 0, 56% 43%, 56% 50%, 44% 50%, 39% 44%); }
.route-lane--center { clip-path: polygon(38% 0, 62% 0, 56% 50%, 44% 50%); }
.route-lane--right { clip-path: polygon(72% 0, 96% 0, 61% 44%, 56% 50%, 44% 50%, 44% 43%); }
.track-scene--fork-1 .route-lane--left { clip-path: polygon(0 0, 24% 0, 55% 43%, 55% 50%, 43% 50%, 36% 44%); }
.track-scene--fork-1 .route-lane--right { clip-path: polygon(68% 0, 94% 0, 61% 44%, 57% 50%, 45% 50%, 45% 42%); }
.track-scene--fork-2 .route-lane--left { clip-path: polygon(7% 0, 32% 0, 57% 44%, 56% 50%, 43% 50%, 41% 43%); }
.track-scene--fork-2 .route-lane--right { clip-path: polygon(76% 0, 100% 0, 64% 44%, 57% 50%, 44% 50%, 45% 43%); }
.route-lane--selected { filter: drop-shadow(0 0 11px rgba(85, 221, 239, .75)); }
.route-lane--correct { filter: drop-shadow(0 0 13px var(--mr-success-glow)); }
.route-lane--closed {
  opacity: .62;
  background: linear-gradient(180deg, #33464b 0 37%, #202e33 38% 43%, transparent 44%);
}
.route-lane--failed {
  opacity: .82;
  background: linear-gradient(180deg, #3d5054 0 32%, #253439 33% 39%, transparent 40%);
  filter: drop-shadow(0 9px 8px rgba(1, 6, 10, .78));
}
.broken-edge {
  position: absolute;
  top: 38%;
  left: 15%;
  width: 70%;
  height: 12%;
  background: linear-gradient(180deg, #536268, #172126 64%, rgba(4, 9, 13, .9));
  box-shadow: 0 10px 12px rgba(1, 5, 8, .72);
  clip-path: polygon(0 0, 13% 18%, 27% 2%, 43% 21%, 58% 4%, 72% 23%, 88% 6%, 100% 17%, 91% 100%, 8% 92%);
}
.broken-edge::after {
  position: absolute;
  inset: 45% 4% -55%;
  background: radial-gradient(ellipse, rgba(2, 7, 12, .96), rgba(3, 9, 15, 0) 72%);
  content: '';
}

.lane-gate {
  position: absolute;
  z-index: 10;
  top: 24%;
  width: min(27%, 260px);
  min-height: 84px;
  display: grid;
  place-content: center;
  gap: 5px;
  border: 1px solid rgba(196, 245, 250, .72);
  border-radius: 14px;
  padding: 9px 10px;
  color: #14202c;
  background: linear-gradient(145deg, rgba(236, 253, 255, .96), rgba(129, 201, 211, .88));
  box-shadow: 0 10px 24px rgba(1, 8, 17, .4), inset 0 1px 0 white;
  font: inherit;
  text-align: center;
  cursor: pointer;
  transition: transform 140ms ease, filter 140ms ease, box-shadow 140ms ease;
  animation: gate-approach var(--question-period) linear both;
  animation-delay: var(--question-delay);
  will-change: top, scale;
}
.lane-gate--left { left: 4%; transform: rotate(-2deg); }
.lane-gate--center { left: 50%; transform: translateX(-50%); }
.lane-gate--right { right: 4%; transform: rotate(2deg); }
.lane-gate:not(:disabled):hover,
.lane-gate:not(:disabled):focus-visible {
  outline: none;
  filter: brightness(1.08);
  box-shadow: 0 0 0 3px rgba(79, 211, 229, .48), 0 12px 29px rgba(1, 8, 17, .48);
}
.lane-gate--left:not(:disabled):hover { transform: rotate(-2deg) translateY(-3px); }
.lane-gate--center:not(:disabled):hover { transform: translateX(-50%) translateY(-3px); }
.lane-gate--right:not(:disabled):hover { transform: rotate(2deg) translateY(-3px); }
.lane-gate:disabled { cursor: default; }
.gate-frame {
  position: absolute;
  inset: -4px;
  z-index: -1;
  border: 2px solid rgba(229, 188, 103, .78);
  border-radius: 17px;
}
.gate-action { display: flex; align-items: center; justify-content: center; gap: 5px; color: #345263; font-size: 9px; font-weight: 900; }
.gate-action kbd,
.lane-obstacle kbd {
  min-width: 22px;
  display: inline-grid;
  place-items: center;
  border: 1px solid rgba(19, 47, 61, .36);
  border-bottom-width: 3px;
  border-radius: 6px;
  padding: 2px 5px;
  color: #103746;
  background: rgba(255, 255, 255, .72);
  font: 900 10px/1 ui-monospace, monospace;
}
.gate-action b { color: #127d92; font-size: 17px; line-height: 1; }
.gate-equation { font: 900 clamp(12px, 1.45vw, 18px)/1.18 ui-monospace, "SFMono-Regular", Consolas, monospace; text-wrap: balance; }
.lane-gate > small { color: #476574; font-size: 8px; font-weight: 850; }
.lane-gate--selected { box-shadow: 0 0 0 3px rgba(73, 211, 230, .65), 0 0 28px rgba(73, 211, 230, .45); }
.lane-gate--correct { box-shadow: 0 0 0 3px var(--mr-success), 0 0 30px var(--mr-success-glow); }
.lane-gate--wrong { box-shadow: 0 0 0 3px var(--mr-danger), 0 0 30px var(--mr-danger-glow); }
.gate-result {
  position: absolute;
  top: -13px;
  right: -11px;
  width: 29px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 2px solid white;
  border-radius: 50%;
  color: white;
  font-size: 18px;
  font-weight: 950;
}
.gate-result--correct { background: var(--mr-success-strong); }
.gate-result--wrong { background: var(--mr-danger-strong); }

.cliff-mouth {
  position: absolute;
  z-index: 8;
  top: 42%;
  width: min(24%, 210px);
  height: clamp(36px, 7vw, 76px);
  overflow: visible;
  background: radial-gradient(ellipse at 50% 26%, #03080d 0 53%, rgba(3, 8, 13, .72) 66%, transparent 72%);
  filter: drop-shadow(0 12px 12px rgba(0, 0, 0, .72));
  opacity: .94;
  transform: translateX(-50%);
  animation: cliff-approach var(--question-period) linear both;
  animation-delay: var(--question-delay);
  will-change: top, scale;
}
.cliff-mouth--left { left: 17%; rotate: -5deg; }
.cliff-mouth--center { left: 50%; }
.cliff-mouth--right { left: 83%; rotate: 5deg; }
.cliff-mouth span {
  position: absolute;
  inset: 18% 10% 2%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(111, 205, 219, .2), transparent 66%);
  filter: blur(5px);
}
.cliff-mouth i {
  position: absolute;
  inset: 30% 17% -14%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(103, 188, 204, .14), transparent 68%);
  filter: blur(6px);
}

.lane-obstacle {
  position: absolute;
  z-index: 9;
  left: 50%;
  top: 52%;
  width: clamp(104px, 18%, 168px);
  height: clamp(88px, 12vw, 128px);
  transform: translateX(-50%);
  pointer-events: none;
  animation: obstacle-approach var(--question-period) linear both;
  animation-delay: var(--question-delay);
  will-change: top, scale;
}
.lane-obstacle > kbd { position: absolute; top: -9px; right: -10px; z-index: 6; background: #dffbff; box-shadow: 0 0 10px rgba(78, 213, 231, .65); }
.lane-obstacle--ground {
  height: clamp(62px, 8vw, 86px);
}
.wall-face {
  position: absolute;
  z-index: 1;
  right: 2%;
  bottom: 0;
  left: 2%;
  height: 64%;
  border: 2px solid #49341f;
  border-radius: 3px 3px 7px 7px;
  background:
    radial-gradient(circle at 22% 34%, rgba(255, 219, 148, .17) 0 3%, transparent 3.5%),
    radial-gradient(circle at 72% 68%, rgba(40, 24, 13, .28) 0 3%, transparent 3.5%),
    linear-gradient(145deg, #ad7742, #65401f 58%, #35251a);
  box-shadow: inset 0 3px 0 rgba(255, 219, 155, .18), 0 10px 15px rgba(0, 0, 0, .42);
  clip-path: polygon(0 9%, 11% 2%, 22% 10%, 36% 0, 49% 8%, 64% 1%, 78% 11%, 90% 3%, 100% 10%, 100% 100%, 0 100%);
}
.ground-block {
  position: absolute;
  z-index: 2;
  bottom: 44%;
  width: 35%;
  height: 34%;
  border: 1px solid #61401e;
  background: linear-gradient(145deg, #d09a55, #75461f);
  clip-path: polygon(8% 18%, 52% 0, 94% 20%, 100% 100%, 0 100%);
  box-shadow: inset 0 2px 0 rgba(255, 226, 168, .22);
}
.ground-block--one { left: 0; transform: rotate(-4deg); }
.ground-block--two { left: 33%; height: 43%; }
.ground-block--three { right: 0; transform: rotate(4deg); }
.overhead-post,
.overhead-beam {
  position: absolute;
  border: 2px solid #273c43;
  background: linear-gradient(90deg, #17282e, #62777a 48%, #1a292e);
  box-shadow: inset 0 0 0 1px rgba(202, 229, 226, .1), 0 7px 14px rgba(0, 0, 0, .42);
}
.overhead-post { top: 0; width: 14px; height: 100%; border-radius: 5px; }
.overhead-post--left { left: 1px; }
.overhead-post--right { right: 1px; }
.overhead-beam {
  z-index: 2;
  top: 0;
  right: 0;
  left: 0;
  height: 58%;
  border-radius: 6px 6px 3px 3px;
  background:
    radial-gradient(circle at 18% 32%, rgba(226, 241, 234, .12) 0 2%, transparent 2.5%),
    linear-gradient(100deg, #15252b, #64787a 44%, #273b40 72%, #121f24);
  clip-path: polygon(0 0, 100% 0, 100% 91%, 88% 84%, 76% 96%, 62% 87%, 48% 100%, 34% 88%, 20% 96%, 8% 86%, 0 92%);
}
.overhead-warning {
  position: absolute;
  z-index: 4;
  top: 49%;
  left: 15%;
  width: 70%;
  height: 5px;
  border-radius: 999px;
  background: #e3a34c;
  box-shadow: 0 0 10px rgba(255, 178, 76, .62);
}

.runner-anchor {
  position: absolute;
  z-index: 12;
  left: 50%;
  bottom: 2.5%;
  transform: translateX(-50%) scale(.88);
  transform-origin: 50% 100%;
}
.runner-anchor--left { animation: runner-lane-left 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-anchor--right { animation: runner-lane-right 620ms cubic-bezier(.2, .8, .2, 1); }

.failure-fx {
  position: absolute;
  z-index: 11;
  pointer-events: none;
}
.failure-fx--wall {
  inset: 0;
  background: radial-gradient(circle at 50% 72%, rgba(255, 192, 91, .28), transparent 4%);
  opacity: 0;
  animation: wall-impact-flash 980ms ease-out both;
}
.failure-fx--wall span {
  --piece-index: 0;
  position: absolute;
  top: 69%;
  left: 50%;
  width: 7px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(#ffe4a3, #ab682a);
  box-shadow: 0 0 8px rgba(255, 189, 88, .72);
  opacity: 0;
  transform: rotate(calc(var(--piece-index) * 60deg));
  animation: wall-fragment 980ms cubic-bezier(.18, .7, .22, 1) both;
  animation-delay: calc(var(--piece-index) * 13ms);
}
.failure-fx--cliff {
  bottom: -3%;
  left: 50%;
  width: 42%;
  height: 31%;
  border-radius: 50% 50% 0 0;
  background:
    radial-gradient(ellipse at 50% 28%, rgba(2, 7, 12, .98) 0 37%, rgba(4, 12, 19, .78) 52%, transparent 70%),
    radial-gradient(ellipse at 50% 58%, rgba(112, 202, 218, .16), transparent 61%);
  filter: drop-shadow(0 -8px 14px rgba(2, 7, 12, .74));
  opacity: 0;
  transform: translateX(-50%) scale(.4);
  animation: cliff-open 1250ms ease-out both;
}
.failure-fx--cliff span {
  --piece-index: 0;
  position: absolute;
  top: 20%;
  left: calc(28% + var(--piece-index) * 8%);
  width: calc(5px + var(--piece-index) * .5px);
  aspect-ratio: 1.4;
  border-radius: 45%;
  background: #536168;
  opacity: 0;
  animation: cliff-fragment 1100ms ease-in both;
  animation-delay: calc(90ms + var(--piece-index) * 35ms);
}

.scene-timer {
  position: absolute;
  z-index: 14;
  top: 14px;
  right: 14px;
  width: 64px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  align-content: center;
  border-radius: 50%;
  color: white;
  background:
    radial-gradient(circle, rgba(12, 27, 42, .94) 56%, transparent 58%),
    conic-gradient(#54d8e9 0 var(--timer-angle), rgba(72, 100, 117, .5) var(--timer-angle) 360deg);
  box-shadow: 0 8px 20px rgba(0, 0, 0, .4);
}
.scene-timer span { font-size: 16px; font-weight: 950; line-height: 1; }
.scene-timer small { margin-top: 2px; color: #b7d2dc; font-size: 8px; }
.scene-timer--urgent { animation: timer-urgent 620ms ease-in-out infinite alternate; }

.section-radar {
  position: absolute;
  z-index: 13;
  top: 14px;
  left: 14px;
  display: grid;
  gap: 2px;
  border: 1px solid rgba(107, 220, 234, .46);
  border-radius: 10px;
  padding: 7px 10px;
  color: white;
  background: rgba(11, 26, 40, .72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .12);
  backdrop-filter: blur(10px);
}
.section-radar b { font-size: 10px; }
.section-radar span { color: #b9d4de; font-size: 8px; }

.level-up-flash {
  position: absolute;
  z-index: 18;
  top: 50%;
  left: 50%;
  display: grid;
  place-items: center;
  gap: 3px;
  min-width: 150px;
  border: 1px solid rgba(130, 238, 250, .8);
  border-radius: 15px;
  padding: 12px 22px;
  color: white;
  background: rgba(11, 28, 43, .9);
  box-shadow: 0 0 35px rgba(67, 214, 233, .4);
  transform: translate(-50%, -50%);
  animation: level-flash 900ms cubic-bezier(.2, .8, .2, 1) both;
}
.level-up-flash small { color: #7de6f3; font-size: 8px; font-weight: 950; letter-spacing: .2em; }
.level-up-flash strong { font-size: 20px; }

.bridge-world--left { animation: world-left 620ms cubic-bezier(.2, .8, .2, 1); }
.bridge-world--right { animation: world-right 620ms cubic-bezier(.2, .8, .2, 1); }
.bridge-world--jump { animation: world-jump 620ms cubic-bezier(.2, .8, .2, 1); }
.bridge-world--slide { animation: world-slide 620ms cubic-bezier(.2, .8, .2, 1); }
.track-scene--failure-wall .scene-camera,
.track-scene--failure-wall .bridge-world { animation: impact-camera-shake 980ms ease-out both; }
.track-scene--failure-cliff .scene-camera { animation: cliff-camera-tilt 1250ms ease-in both; }
.track-scene--failure-cliff .bridge-world { animation: cliff-world-tilt 1250ms ease-in both; }
.track-scene--wrong .road-stone,
.track-scene--timeout .road-stone,
.track-scene--completed .road-stone,
.track-scene--wrong .bridge-marker,
.track-scene--timeout .bridge-marker,
.track-scene--completed .bridge-marker,
.track-scene--wrong .scene-backdrop,
.track-scene--timeout .scene-backdrop,
.track-scene--completed .scene-backdrop,
.track-scene--wrong .lane-gate,
.track-scene--timeout .lane-gate,
.track-scene--completed .lane-gate,
.track-scene--wrong .cliff-mouth,
.track-scene--timeout .cliff-mouth,
.track-scene--completed .cliff-mouth,
.track-scene--wrong .lane-obstacle,
.track-scene--timeout .lane-obstacle,
.track-scene--completed .lane-obstacle { animation-play-state: paused; }
.track-scene--level-up::after {
  position: absolute;
  z-index: 17;
  inset: 0;
  border: 4px solid rgba(82, 217, 234, .55);
  border-radius: inherit;
  content: '';
  pointer-events: none;
  animation: stage-ring 900ms ease-out both;
}

@keyframes backdrop-forward {
  from { transform: translate3d(0, -1.2%, 0) scale(1.035); background-position: 50% 48%; }
  to { transform: translate3d(0, 1.8%, 0) scale(1.09); background-position: 50% 53%; }
}
@keyframes camera-turn-left {
  0%, 100% { transform: translateX(0) rotate(0) scale(1); }
  58% { transform: translateX(4.8%) rotate(2.2deg) scale(1.025); }
}
@keyframes camera-turn-right {
  0%, 100% { transform: translateX(0) rotate(0) scale(1); }
  58% { transform: translateX(-4.8%) rotate(-2.2deg) scale(1.025); }
}
@keyframes camera-jump {
  0%, 100% { transform: translateY(0) scale(1); }
  54% { transform: translateY(2.5%) scale(1.025); }
}
@keyframes camera-slide {
  0%, 100% { transform: translateY(0) scale(1); }
  52% { transform: translateY(-2%) scale(.985); }
}
@keyframes road-stone-approach {
  0% { top: -3%; opacity: 0; transform: translateX(-50%) rotate(var(--stone-rotation)) scale(.16); }
  13% { opacity: .34; }
  74% { opacity: .62; }
  100% { top: 105%; opacity: 0; transform: translateX(-50%) rotate(calc(var(--stone-rotation) + 14deg)) scale(3.4); }
}
@keyframes marker-approach-left {
  0% { top: 1%; left: 46%; opacity: 0; transform: scale(.22); }
  12% { opacity: .72; }
  76% { opacity: .88; }
  100% { top: 97%; left: 8%; opacity: 0; transform: scale(2.9); }
}
@keyframes marker-approach-right {
  0% { top: 1%; right: 46%; opacity: 0; transform: scale(.22); }
  12% { opacity: .72; }
  76% { opacity: .88; }
  100% { top: 97%; right: 8%; opacity: 0; transform: scale(2.9); }
}
@keyframes gate-approach {
  0% { top: 22%; scale: .9; }
  100% { top: 36%; scale: 1.12; }
}
@keyframes cliff-approach {
  0% { top: 39%; scale: .72; opacity: .76; }
  100% { top: 58%; scale: 1.25; opacity: 1; }
}
@keyframes obstacle-approach {
  0% { top: 43%; scale: .68; opacity: .76; }
  100% { top: 66%; scale: 1.26; opacity: 1; }
}
@keyframes runner-lane-left { 0%, 100% { transform: translateX(-50%) scale(.88); } 62% { transform: translateX(-155%) scale(.9) rotate(-6deg); } }
@keyframes runner-lane-right { 0%, 100% { transform: translateX(-50%) scale(.88); } 62% { transform: translateX(55%) scale(.9) rotate(6deg); } }
@keyframes world-left { 0%, 100% { transform: translateX(0) rotate(0); } 58% { transform: translateX(6.5%) rotate(2.4deg) scale(1.02); } }
@keyframes world-right { 0%, 100% { transform: translateX(0) rotate(0); } 58% { transform: translateX(-6.5%) rotate(-2.4deg) scale(1.02); } }
@keyframes world-jump { 0%, 100% { transform: scale(1); } 55% { transform: translateY(2%) scale(1.055); } }
@keyframes world-slide { 0%, 100% { transform: translateY(0) scale(1); } 55% { transform: translateY(-2.5%) scale(.975); } }
@keyframes impact-camera-shake {
  0%, 19%, 100% { transform: translate(0, 0) rotate(0) scale(1); }
  25% { transform: translate(-1.2%, .8%) rotate(-.7deg) scale(1.025); }
  31% { transform: translate(1.4%, -.7%) rotate(.8deg) scale(1.03); }
  38% { transform: translate(-.8%, .5%) rotate(-.45deg) scale(1.02); }
  48% { transform: translate(.5%, -.25%) rotate(.25deg) scale(1.01); }
}
@keyframes cliff-camera-tilt {
  0%, 12% { transform: translate(0, 0) rotate(0) scale(1); }
  42% { transform: translate(1.5%, -1%) rotate(1.4deg) scale(1.02); }
  100% { transform: translate(3%, -4%) rotate(3deg) scale(1.07); }
}
@keyframes cliff-world-tilt {
  0%, 14% { transform: translate(0, 0) rotate(0) scale(1); }
  100% { transform: translate(-2%, -2%) rotate(-2.2deg) scale(1.04); }
}
@keyframes wall-impact-flash {
  0%, 23% { opacity: 0; }
  30% { opacity: 1; }
  58%, 100% { opacity: 0; }
}
@keyframes wall-fragment {
  0%, 23% { opacity: 0; transform: translate(0, 0) rotate(calc(var(--piece-index) * 60deg)) scale(.4); }
  31% { opacity: 1; }
  100% { opacity: 0; transform: translate(calc((var(--piece-index) - 2.5) * 24px), calc(-34px - var(--piece-index) * 7px)) rotate(calc(var(--piece-index) * 108deg)) scale(.85); }
}
@keyframes cliff-open {
  0%, 12% { opacity: 0; transform: translateX(-50%) scale(.35); }
  38% { opacity: .88; transform: translateX(-50%) scale(.82); }
  100% { opacity: 1; transform: translateX(-50%) scale(1.14); }
}
@keyframes cliff-fragment {
  0%, 14% { opacity: 0; transform: translateY(0) rotate(0); }
  28% { opacity: .8; }
  100% { opacity: 0; transform: translate(calc((var(--piece-index) - 2.5) * 9px), 128px) rotate(calc(var(--piece-index) * 94deg)) scale(.35); }
}
@keyframes timer-urgent { from { filter: none; } to { filter: drop-shadow(0 0 12px var(--mr-warning-glow)); } }
@keyframes level-flash { 0% { opacity: 0; transform: translate(-50%, -42%) scale(.82); } 32% { opacity: 1; transform: translate(-50%, -50%) scale(1.04); } 78% { opacity: 1; } 100% { opacity: 0; transform: translate(-50%, -58%) scale(1); } }
@keyframes stage-ring { from { opacity: 1; transform: scale(.985); } to { opacity: 0; transform: scale(1.02); } }

@media (max-width: 760px) {
  .track-scene { min-height: 360px; border-radius: 16px; }
  .lane-gate { top: 25%; min-height: 69px; padding: 6px; border-radius: 11px; }
  .gate-frame { border-radius: 14px; }
  .gate-action { gap: 3px; font-size: 7px; }
  .gate-action kbd { min-width: 18px; font-size: 8px; }
  .gate-action b { font-size: 13px; }
  .gate-equation { font-size: clamp(9px, 2.5vw, 13px); overflow-wrap: anywhere; }
  .lane-gate > small { font-size: 7px; }
  .cliff-mouth { height: 48px; }
  .lane-obstacle { top: 53%; transform: translateX(-50%) scale(.8); }
  .runner-anchor { bottom: 0; transform: translateX(-50%) scale(.7); }
  .scene-timer { top: 9px; right: 9px; width: 54px; }
  .section-radar { top: 9px; left: 9px; }
}

@media (orientation: landscape) and (max-height: 620px) {
  .track-scene { min-height: 0; border-radius: 12px; }
  .lane-gate { top: 19%; min-height: 54px; gap: 2px; padding: 4px 5px; }
  .lane-gate > small { display: none; }
  .gate-equation { font-size: clamp(8px, 1.55vw, 12px); }
  .cliff-mouth { height: 38px; }
  .lane-obstacle { top: 49%; transform: translateX(-50%) scale(.64); }
  .runner-anchor { bottom: -8%; transform: translateX(-50%) scale(.55); }
  .scene-timer { width: 48px; }
  .section-radar span { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .road-stone,
  .bridge-marker,
  .scene-camera,
  .scene-backdrop,
  .bridge-world,
  .runner-anchor,
  .lane-gate,
  .cliff-mouth,
  .lane-obstacle,
  .failure-fx,
  .scene-timer,
  .level-up-flash,
  .track-scene--level-up::after { animation: none !important; }
  .lane-gate { transition: none; }
}
</style>
