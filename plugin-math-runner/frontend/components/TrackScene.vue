<script setup lang="ts">
import { computed } from 'vue'
import RunnerModel from './RunnerModel.vue'
import {
  RUNNER_ACTION_META,
  laneLabel,
  type MathRunnerGameView,
  type RunnerAction,
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
const SLEEPER_INDEXES = Array.from({ length: 10 }, (_, index) => index)
const MARKER_INDEXES = Array.from({ length: 7 }, (_, index) => index)
const optionByLane = computed(() => new Map(
  (props.game.options ?? []).map((option) => [option.lane, option]),
))
const speedLineIndexes = computed(() => Array.from(
  { length: Math.max(0, props.game.speed?.speedLines ?? 4) },
  (_, index) => index,
))
const remainingRatio = computed(() => {
  const limit = Math.max(1, props.game.timeLimitMs ?? 1)
  return Math.min(1, Math.max(0, props.remainingMs / limit))
})
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
    ? '，前方是地面障碍'
    : option.obstacle === 'overhead'
      ? '，前方是高空障碍'
      : ''
  const result = props.game.endReason && props.game.correctAction === option.action
    ? '，这是正确路线'
    : ''
  return `${laneLabel(option.lane)}，按 ${meta.key} ${meta.label}${obstacle}，等式 ${option.equation}${result}`
}

function lineStyle(index: number) {
  return {
    left: `${7 + ((index * 37) % 86)}%`,
    animationDelay: `${-((index * 113) % 900)}ms`,
    opacity: `${0.1 + (index % 4) * 0.04}`,
  }
}

function sleeperStyle(index: number) {
  const period = props.game.speed?.trackPeriodMs ?? 1500
  return {
    animationDelay: `${-(period * index / SLEEPER_INDEXES.length)}ms`,
  }
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
    aria-label="算途疾行三跑道桥面与题目障碍"
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

    <div class="speed-lines" aria-hidden="true">
      <span
        v-for="index in speedLineIndexes"
        :key="index"
        class="speed-line"
        :style="lineStyle(index)"
      />
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
        <span class="bridge-motion-grid" />
        <span class="bridge-center-glow" />
        <span
          v-for="index in SLEEPER_INDEXES"
          :key="`sleeper-${index}`"
          class="bridge-sleeper"
          :style="sleeperStyle(index)"
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
        >
          <i v-if="!optionForLane(lane)" class="broken-edge" />
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
        class="closed-route-sign"
        :class="`closed-route-sign--${lane}`"
        aria-hidden="true"
      >
        <b>断桥</b>
        <span>╱╲</span>
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
          <span class="ground-block ground-block--one" />
          <span class="ground-block ground-block--two" />
          <span class="ground-block ground-block--three" />
        </template>
        <template v-else>
          <span class="overhead-post overhead-post--left" />
          <span class="overhead-post overhead-post--right" />
          <span class="overhead-beam" />
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
        :run-cycle-ms="game.speed?.runCycleMs ?? 720"
      />
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
      <b>{{ game.branchCount ?? game.options?.length ?? 2 }} 路分叉</b>
      <span>W 跳 · S 蹲 · A/D 变道</span>
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

.speed-lines {
  position: absolute;
  z-index: 7;
  inset: 42% 6% 0;
  overflow: hidden;
  clip-path: polygon(27% 0, 73% 0, 100% 100%, 0 100%);
  pointer-events: none;
}
.speed-line {
  position: absolute;
  top: -20%;
  width: 2px;
  height: 19%;
  border-radius: 999px;
  background: linear-gradient(transparent, rgba(184, 244, 255, .92));
  animation: speed-line-fall var(--track-period) linear infinite;
}

.bridge-world { position: absolute; z-index: 2; inset: 0; transform-origin: 50% 66%; }
.bridge-deck {
  position: absolute;
  inset: 34% -7% -8%;
  overflow: hidden;
  isolation: isolate;
  clip-path: polygon(44% 0, 56% 0, 92% 100%, 8% 100%);
  background:
    repeating-linear-gradient(180deg, transparent 0 9%, rgba(119, 184, 204, .14) 9.4% 10.4%, transparent 10.8% 19%),
    linear-gradient(90deg, #0b1420, #2b4053 18% 50%, #263b4f 82%, #0b1420);
  box-shadow: 0 24px 38px rgba(2, 8, 17, .5);
  animation: bridge-scroll var(--track-period) linear infinite;
}
.bridge-deck::before {
  position: absolute;
  z-index: 1;
  inset: 0;
  background:
    linear-gradient(108deg, transparent 0 23%, rgba(130, 231, 242, .05) 27%, transparent 31% 69%, rgba(130, 231, 242, .05) 73%, transparent 77%),
    linear-gradient(180deg, rgba(211, 249, 255, .14), transparent 21%);
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
.bridge-motion-grid {
  position: absolute;
  z-index: 2;
  inset: 0;
  background:
    repeating-linear-gradient(180deg, transparent 0 7%, rgba(236, 250, 255, .075) 7.5% 8.2%, transparent 8.8% 15%),
    repeating-linear-gradient(90deg, transparent 0 16.3%, rgba(90, 216, 232, .055) 16.5% 16.8%, transparent 17% 33%);
  background-size: 100% 125%, 100% 100%;
  animation: bridge-grid-rush var(--track-period) linear infinite;
}

.bridge-center-glow {
  position: absolute;
  z-index: 2;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 38%;
  background: linear-gradient(180deg, rgba(105, 229, 242, .18), rgba(105, 229, 242, 0) 58%);
  filter: blur(12px);
  transform: translateX(-50%);
}

.bridge-sleeper {
  position: absolute;
  z-index: 5;
  top: 0;
  left: 50%;
  width: 7%;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(197, 240, 246, .78) 16% 84%, transparent);
  box-shadow: 0 0 8px rgba(100, 219, 234, .26);
  opacity: 0;
  transform: translateX(-50%);
  animation: sleeper-approach var(--track-period) linear infinite;
  will-change: top, width, opacity;
}

.bridge-marker {
  position: absolute;
  z-index: 6;
  top: 2%;
  width: 4px;
  height: 7px;
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

.route-lanes { position: absolute; z-index: 3; inset: 34% 5% -4%; pointer-events: none; }
.route-lane {
  position: absolute;
  bottom: 0;
  width: 31%;
  height: 100%;
  clip-path: polygon(43% 0, 57% 0, 100% 100%, 0 100%);
  border-top: 2px solid rgba(120, 230, 244, .42);
  background: linear-gradient(180deg, rgba(82, 209, 226, .12), rgba(82, 209, 226, .025));
  transition: filter 160ms ease, opacity 160ms ease;
  animation: lane-flow var(--track-period) linear infinite;
}
.route-lane--left { left: 4%; transform: rotate(-5.5deg); transform-origin: 100% 0; }
.route-lane--center { left: 34.5%; }
.route-lane--right { right: 4%; transform: rotate(5.5deg); transform-origin: 0 0; }
.route-lane--selected { filter: drop-shadow(0 0 11px rgba(85, 221, 239, .75)); }
.route-lane--correct { filter: drop-shadow(0 0 13px var(--mr-success-glow)); }
.route-lane--closed {
  opacity: .5;
  background: repeating-linear-gradient(135deg, rgba(255, 160, 77, .18) 0 8px, rgba(16, 25, 37, .36) 8px 16px);
  clip-path: polygon(43% 0, 57% 0, 79% 47%, 65% 55%, 91% 100%, 4% 100%, 35% 57%, 23% 47%);
}
.broken-edge {
  position: absolute;
  top: 47%;
  left: 31%;
  width: 38%;
  height: 3px;
  background: var(--mr-warning);
  box-shadow: 0 0 9px var(--mr-warning-glow);
  transform: rotate(-7deg);
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

.closed-route-sign {
  position: absolute;
  z-index: 8;
  top: 27%;
  width: min(18%, 150px);
  min-height: 57px;
  display: grid;
  place-content: center;
  gap: 2px;
  border: 2px dashed rgba(255, 176, 86, .58);
  border-radius: 11px;
  color: #ffd09a;
  background: rgba(12, 22, 34, .72);
  text-align: center;
  opacity: .8;
  animation: closed-route-approach var(--question-period) linear both;
  animation-delay: var(--question-delay);
  will-change: top, scale;
}
.closed-route-sign--left { left: 8%; }
.closed-route-sign--center { left: 50%; transform: translateX(-50%); }
.closed-route-sign--right { right: 8%; }
.closed-route-sign b { font-size: 9px; }
.closed-route-sign span { color: var(--mr-warning); font-size: 18px; letter-spacing: -.25em; transform: translateX(-.12em); }

.lane-obstacle {
  position: absolute;
  z-index: 9;
  left: 50%;
  top: 52%;
  width: clamp(72px, 13%, 122px);
  height: 77px;
  transform: translateX(-50%);
  pointer-events: none;
  animation: obstacle-approach var(--question-period) linear both;
  animation-delay: var(--question-delay);
  will-change: top, scale;
}
.lane-obstacle > kbd { position: absolute; top: -7px; right: -9px; z-index: 3; background: #dffbff; box-shadow: 0 0 10px rgba(78, 213, 231, .65); }
.ground-block {
  position: absolute;
  bottom: 0;
  width: 34%;
  height: 43%;
  border: 2px solid #8b5c28;
  background: linear-gradient(145deg, #f0bd65, #a65f24);
  clip-path: polygon(50% 0, 100% 24%, 100% 100%, 0 100%, 0 24%);
  box-shadow: 0 7px 13px rgba(0, 0, 0, .35);
}
.ground-block--one { left: 0; transform: rotate(-4deg); }
.ground-block--two { left: 33%; height: 54%; }
.ground-block--three { right: 0; transform: rotate(4deg); }
.overhead-post,
.overhead-beam {
  position: absolute;
  border: 2px solid #287a89;
  background: linear-gradient(90deg, #143c4b, #66d7e5, #173f4c);
  box-shadow: 0 0 10px rgba(77, 215, 232, .42);
}
.overhead-post { bottom: 0; width: 12px; height: 72%; border-radius: 5px; }
.overhead-post--left { left: 5px; }
.overhead-post--right { right: 5px; }
.overhead-beam { top: 5px; left: 0; right: 0; height: 17px; border-radius: 6px; }

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
.track-scene--wrong .speed-line,
.track-scene--timeout .speed-line,
.track-scene--completed .speed-line,
.track-scene--wrong .bridge-deck,
.track-scene--timeout .bridge-deck,
.track-scene--completed .bridge-deck,
.track-scene--wrong .bridge-motion-grid,
.track-scene--timeout .bridge-motion-grid,
.track-scene--completed .bridge-motion-grid,
.track-scene--wrong .bridge-sleeper,
.track-scene--timeout .bridge-sleeper,
.track-scene--completed .bridge-sleeper,
.track-scene--wrong .bridge-marker,
.track-scene--timeout .bridge-marker,
.track-scene--completed .bridge-marker,
.track-scene--wrong .route-lane,
.track-scene--timeout .route-lane,
.track-scene--completed .route-lane,
.track-scene--wrong .scene-backdrop,
.track-scene--timeout .scene-backdrop,
.track-scene--completed .scene-backdrop,
.track-scene--wrong .lane-gate,
.track-scene--timeout .lane-gate,
.track-scene--completed .lane-gate,
.track-scene--wrong .closed-route-sign,
.track-scene--timeout .closed-route-sign,
.track-scene--completed .closed-route-sign,
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
@keyframes bridge-scroll { to { background-position: 0 146%, 0 0; } }
@keyframes bridge-grid-rush { to { background-position: 0 125%, 0 0; } }
@keyframes sleeper-approach {
  0% { top: 0; width: 7%; height: 2px; opacity: 0; }
  9% { opacity: .38; }
  70% { opacity: .62; }
  100% { top: 103%; width: 88%; height: 7px; opacity: 0; }
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
@keyframes lane-flow { to { background-position: 0 116%; } }
@keyframes gate-approach {
  0% { top: 22%; scale: .9; }
  100% { top: 36%; scale: 1.12; }
}
@keyframes closed-route-approach {
  0% { top: 25%; scale: .88; }
  100% { top: 39%; scale: 1.08; }
}
@keyframes obstacle-approach {
  0% { top: 47%; scale: .78; opacity: .78; }
  100% { top: 65%; scale: 1.18; opacity: 1; }
}
@keyframes speed-line-fall { from { transform: translateY(-80%) scaleY(.5); } to { transform: translateY(650%) scaleY(2.5); } }
@keyframes runner-lane-left { 0%, 100% { transform: translateX(-50%) scale(.88); } 62% { transform: translateX(-155%) scale(.9) rotate(-6deg); } }
@keyframes runner-lane-right { 0%, 100% { transform: translateX(-50%) scale(.88); } 62% { transform: translateX(55%) scale(.9) rotate(6deg); } }
@keyframes world-left { 0%, 100% { transform: translateX(0) rotate(0); } 58% { transform: translateX(6.5%) rotate(2.4deg) scale(1.02); } }
@keyframes world-right { 0%, 100% { transform: translateX(0) rotate(0); } 58% { transform: translateX(-6.5%) rotate(-2.4deg) scale(1.02); } }
@keyframes world-jump { 0%, 100% { transform: scale(1); } 55% { transform: translateY(2%) scale(1.055); } }
@keyframes world-slide { 0%, 100% { transform: translateY(0) scale(1); } 55% { transform: translateY(-2.5%) scale(.975); } }
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
  .closed-route-sign { top: 27%; min-height: 47px; }
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
  .closed-route-sign { top: 22%; min-height: 42px; }
  .lane-obstacle { top: 49%; transform: translateX(-50%) scale(.64); }
  .runner-anchor { bottom: -8%; transform: translateX(-50%) scale(.55); }
  .scene-timer { width: 48px; }
  .section-radar span { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .speed-line,
  .bridge-deck,
  .bridge-motion-grid,
  .bridge-sleeper,
  .bridge-marker,
  .route-lane,
  .scene-camera,
  .scene-backdrop,
  .bridge-world,
  .runner-anchor,
  .lane-gate,
  .closed-route-sign,
  .lane-obstacle,
  .scene-timer,
  .level-up-flash,
  .track-scene--level-up::after { animation: none !important; }
  .lane-gate { transition: none; }
}
</style>
