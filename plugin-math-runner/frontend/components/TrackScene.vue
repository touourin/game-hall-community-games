<script setup lang="ts">
import { computed } from 'vue'
import RunnerModel from './RunnerModel.vue'
import {
  DIRECTION_META,
  type Direction,
  type DirectionMeta,
  type MathRunnerGameView,
} from '../types'

const props = withDefaults(defineProps<{
  game: MathRunnerGameView
  remainingMs: number
  selectedDirection?: Direction | null
  turnDirection?: Direction | null
  disabled?: boolean
}>(), {
  selectedDirection: null,
  turnDirection: null,
  disabled: false,
})

const emit = defineEmits<{
  choose: [direction: Direction]
}>()

const optionMap = computed(() => new Map(
  (props.game.options ?? []).map((option) => [option.direction, option]),
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
  '--timer-angle': `${remainingRatio.value * 360}deg`,
}))

const stageClass = computed(() => ({
  'track-scene--urgent': remainingRatio.value <= 0.25 && !props.game.endReason,
  'track-scene--level-up': Boolean(props.game.levelUp && !props.game.endReason),
  [`track-scene--${props.game.endReason}`]: Boolean(props.game.endReason),
}))

function optionFor(direction: Direction) {
  return optionMap.value.get(direction)
}

function gateClass(meta: DirectionMeta) {
  const option = optionFor(meta.id)
  const selected = props.selectedDirection === meta.id
    || (Boolean(props.game.endReason) && props.game.lastDirection === meta.id)
  return {
    [`question-gate--${meta.id}`]: true,
    'question-gate--blocked': !option,
    'question-gate--selected': selected,
    'question-gate--correct': Boolean(
      props.game.endReason && props.game.correctDirection === meta.id,
    ),
    'question-gate--wrong': Boolean(
      props.game.endReason === 'wrong'
      && props.game.lastDirection === meta.id
      && props.game.correctDirection !== meta.id,
    ),
  }
}

function routeClass(direction: Direction) {
  return {
    [`track-branch--${direction}`]: true,
    'track-branch--blocked': !optionFor(direction),
    'track-branch--correct': Boolean(
      props.game.endReason && props.game.correctDirection === direction,
    ),
  }
}

function gateLabel(meta: DirectionMeta): string {
  const option = optionFor(meta.id)
  if (!option) return `${meta.label}方向封闭`
  const result = props.game.endReason && props.game.correctDirection === meta.id
    ? '，这是正确方向'
    : ''
  return `${meta.label}方向，${option.equation}${result}`
}

function lineStyle(index: number) {
  return {
    left: `${10 + ((index * 37) % 80)}%`,
    animationDelay: `${-((index * 113) % 900)}ms`,
    opacity: `${0.08 + (index % 4) * 0.035}`,
  }
}
</script>

<template>
  <section
    class="track-scene"
    :class="stageClass"
    :style="stageStyle"
    aria-label="算途疾行跑道与题目路口"
  >
    <div class="sky-glow" />
    <div class="cloud cloud--one" />
    <div class="cloud cloud--two" />
    <div class="cloud cloud--three" />
    <div class="horizon-architecture" aria-hidden="true">
      <span class="tower tower--left" />
      <span class="tower tower--center" />
      <span class="tower tower--right" />
      <span class="horizon-ring" />
      <span class="observatory-dome" />
    </div>

    <div class="floating-islands" aria-hidden="true">
      <span class="floating-island floating-island--one" />
      <span class="floating-island floating-island--two" />
      <span class="floating-island floating-island--three" />
    </div>

    <div class="crystal-beacons" aria-hidden="true">
      <span class="crystal-beacon crystal-beacon--one" />
      <span class="crystal-beacon crystal-beacon--two" />
      <span class="crystal-beacon crystal-beacon--three" />
      <span class="crystal-beacon crystal-beacon--four" />
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
      class="track-world"
      :class="turnDirection ? `track-world--turn-${turnDirection}` : ''"
      aria-hidden="true"
    >
      <div class="approach-track">
        <span class="track-rail track-rail--left" />
        <span class="track-rail track-rail--right" />
        <span class="track-seams" />
        <span class="track-route-arrows" />
      </div>
      <div class="junction-disc">
        <span class="junction-ring junction-ring--outer" />
        <span class="junction-ring junction-ring--inner" />
        <span class="junction-core" />
      </div>
      <span
        v-for="meta in DIRECTION_META"
        :key="meta.id"
        class="track-branch"
        :class="routeClass(meta.id)"
      />
    </div>

    <button
      v-for="meta in DIRECTION_META"
      :key="meta.id"
      type="button"
      class="question-gate"
      :class="gateClass(meta)"
      :disabled="disabled || !optionFor(meta.id)"
      :aria-label="gateLabel(meta)"
      :data-direction="meta.id"
      @click="emit('choose', meta.id)"
    >
      <span class="gate-frame" aria-hidden="true" />
      <span v-if="optionFor(meta.id)" class="gate-content">
        <span class="gate-direction">
          <b>{{ meta.symbol }}</b>
          <span>{{ meta.label }} · {{ meta.key }}</span>
        </span>
        <strong class="gate-equation">{{ optionFor(meta.id)?.equation }}</strong>
      </span>
      <span v-else class="gate-barrier">
        <b aria-hidden="true">╱╲</b>
        <span>封闭</span>
      </span>
      <span
        v-if="game.endReason && game.correctDirection === meta.id"
        class="gate-result-mark gate-result-mark--correct"
        aria-hidden="true"
      >✓</span>
      <span
        v-else-if="game.endReason === 'wrong' && game.lastDirection === meta.id"
        class="gate-result-mark gate-result-mark--wrong"
        aria-hidden="true"
      >×</span>
    </button>

    <div class="runner-anchor">
      <RunnerModel
        :turn-direction="turnDirection"
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

    <div v-if="game.levelUp && !game.endReason" class="level-up-flash" aria-hidden="true">
      <small>LEVEL UP</small>
      <strong>等级 {{ game.level }}</strong>
    </div>
  </section>
</template>

<style scoped>
.track-scene {
  --track-period: 1500ms;
  --timer-angle: 360deg;
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  isolation: isolate;
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 70%, var(--mr-line));
  border-radius: clamp(20px, 3vw, 34px);
  background:
    radial-gradient(circle at 14% 5%, color-mix(in srgb, #ffd58f 38%, transparent), transparent 30%),
    radial-gradient(circle at 50% 20%, color-mix(in srgb, var(--mr-scene-glow) 72%, transparent), transparent 29%),
    linear-gradient(180deg, var(--mr-scene-top), var(--mr-scene-center) 48%, var(--mr-scene-bottom));
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, white 15%, transparent),
    0 24px 60px color-mix(in srgb, var(--mr-shadow) 32%, transparent);
  color: var(--mr-copy-on-stage);
}

.sky-glow {
  position: absolute;
  z-index: -5;
  inset: 0;
  background:
    radial-gradient(circle at 16% 10%, color-mix(in srgb, var(--mr-accent) 20%, transparent), transparent 24%),
    linear-gradient(110deg, transparent 34%, color-mix(in srgb, white 7%, transparent) 48%, transparent 60%);
}

.cloud {
  position: absolute;
  z-index: -4;
  width: 36%;
  height: 17%;
  border-radius: 50%;
  background: color-mix(in srgb, var(--mr-scene-fog) 72%, transparent);
  filter: blur(19px);
  opacity: .48;
  animation: cloud-drift calc(var(--track-period) * 9) ease-in-out infinite alternate;
}

.cloud--one { top: 22%; left: -10%; }
.cloud--two { top: 31%; right: -8%; animation-delay: -2.2s; }
.cloud--three { top: 43%; left: 31%; width: 42%; opacity: .22; animation-delay: -4.1s; }

.horizon-architecture {
  position: absolute;
  z-index: -3;
  inset: 8% 5% auto;
  height: 31%;
  opacity: .38;
  filter: saturate(.7);
}

.tower {
  position: absolute;
  bottom: 0;
  width: 7%;
  min-width: 28px;
  border: 1px solid color-mix(in srgb, var(--mr-stage-edge) 65%, transparent);
  border-radius: 42% 42% 10% 10%;
  background:
    linear-gradient(90deg, var(--mr-stage-bottom), var(--mr-stage-top), var(--mr-stage-bottom));
  box-shadow: 0 0 22px color-mix(in srgb, var(--mr-scene-glow) 20%, transparent);
}

.tower::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -18px;
  width: 44%;
  aspect-ratio: 1;
  border: 2px solid var(--mr-stage-edge);
  background: var(--mr-metal-glass);
  transform: translateX(-50%) rotate(45deg);
}

.tower--left { left: 9%; height: 58%; }
.tower--center { left: 47%; height: 82%; transform: scale(.72); }
.tower--right { right: 8%; height: 64%; }

.horizon-ring {
  position: absolute;
  left: 50%;
  bottom: 8%;
  width: 65%;
  height: 26%;
  border: 5px solid color-mix(in srgb, var(--mr-stage-edge) 54%, transparent);
  border-bottom: 0;
  border-radius: 50% 50% 0 0;
  transform: translateX(-50%);
}

.observatory-dome {
  position: absolute;
  right: 18%;
  bottom: 0;
  width: 15%;
  min-width: 64px;
  aspect-ratio: 1.7;
  border: 3px solid color-mix(in srgb, #d9ad64 62%, var(--mr-stage-edge));
  border-bottom-width: 7px;
  border-radius: 100% 100% 18% 18%;
  background:
    radial-gradient(circle at 50% 45%, color-mix(in srgb, #9ce9f2 55%, transparent), transparent 17%),
    repeating-linear-gradient(90deg, transparent 0 18%, color-mix(in srgb, var(--mr-stage-edge) 45%, transparent) 19% 21%),
    color-mix(in srgb, var(--mr-metal-glass) 44%, var(--mr-stage-bottom));
  box-shadow: 0 0 24px color-mix(in srgb, #8fe8f3 24%, transparent);
}

.floating-islands {
  position: absolute;
  z-index: -2;
  inset: 0;
  pointer-events: none;
}

.floating-island {
  position: absolute;
  width: 8%;
  min-width: 36px;
  height: 4%;
  border-top: 3px solid color-mix(in srgb, #d9ad64 56%, var(--mr-stage-edge));
  background: linear-gradient(180deg, var(--mr-stage-bottom), color-mix(in srgb, var(--mr-shadow) 65%, transparent));
  clip-path: polygon(0 0, 100% 0, 74% 42%, 57% 100%, 43% 100%, 25% 42%);
  filter: drop-shadow(0 10px 8px color-mix(in srgb, var(--mr-shadow) 28%, transparent));
  opacity: .52;
  animation: island-float calc(var(--track-period) * 4.2) ease-in-out infinite alternate;
}
.floating-island--one { top: 17%; left: 4%; }
.floating-island--two { top: 12%; right: 7%; width: 6%; animation-delay: -1.2s; }
.floating-island--three { top: 37%; right: 24%; width: 4%; animation-delay: -2.4s; opacity: .32; }

.crystal-beacons {
  position: absolute;
  z-index: 5;
  inset: 0;
  pointer-events: none;
}
.crystal-beacon {
  position: absolute;
  width: clamp(7px, 1.1vw, 13px);
  aspect-ratio: .68;
  border: 1px solid color-mix(in srgb, white 62%, #68dae9);
  background: linear-gradient(145deg, #d9fbff, #4fc8dc 58%, #277d93);
  clip-path: polygon(50% 0, 100% 42%, 72% 100%, 28% 100%, 0 42%);
  box-shadow: 0 0 14px color-mix(in srgb, #71e8f5 70%, transparent);
  animation: crystal-pulse calc(var(--track-period) * 1.4) ease-in-out infinite alternate;
}
.crystal-beacon::after {
  position: absolute;
  top: 100%;
  left: 50%;
  width: 18px;
  height: 7px;
  border: 1px solid color-mix(in srgb, #d9ad64 62%, var(--mr-stage-edge));
  border-radius: 2px;
  background: var(--mr-stage-bottom);
  content: '';
  transform: translateX(-50%);
}
.crystal-beacon--one { top: 39%; left: 17%; }
.crystal-beacon--two { top: 39%; right: 17%; animation-delay: -.4s; }
.crystal-beacon--three { top: 57%; left: 31%; animation-delay: -.8s; }
.crystal-beacon--four { top: 57%; right: 31%; animation-delay: -1.2s; }

.speed-lines {
  position: absolute;
  z-index: -1;
  inset: 16% 0 0;
  overflow: hidden;
  clip-path: polygon(28% 0, 72% 0, 100% 100%, 0 100%);
}

.speed-line {
  position: absolute;
  top: 8%;
  width: 2px;
  height: 18%;
  border-radius: 999px;
  background: linear-gradient(transparent, var(--mr-scene-particle));
  transform: perspective(300px) rotateX(60deg);
  animation: speed-line-fall var(--track-period) linear infinite;
}

.track-world {
  position: absolute;
  z-index: 0;
  inset: 0;
  transform-origin: 50% 48%;
}

.approach-track {
  position: absolute;
  z-index: 1;
  inset: 28% 0 0;
  clip-path: polygon(45% 0, 55% 0, 86% 100%, 14% 100%);
  border-bottom: 8px solid var(--mr-stage-edge);
  background:
    repeating-linear-gradient(
      180deg,
      transparent 0 12%,
      color-mix(in srgb, var(--mr-stage-detail) 75%, transparent) 12.5% 13.5%,
      transparent 14% 25%
    ),
    linear-gradient(
      90deg,
      color-mix(in srgb, #141b24 76%, var(--mr-stage-bottom)),
      color-mix(in srgb, #29313d 78%, var(--mr-stage-top)) 18% 82%,
      color-mix(in srgb, #141b24 76%, var(--mr-stage-bottom))
    );
  background-size: 100% 120%, 100% 100%;
  animation: track-scroll var(--track-period) linear infinite;
  filter: drop-shadow(0 18px 16px color-mix(in srgb, var(--mr-shadow) 38%, transparent));
}

.track-seams {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 48.8%,
    color-mix(in srgb, var(--mr-stage-detail) 58%, transparent) 49.5% 50.5%,
    transparent 51.2%
  );
}

.track-route-arrows {
  position: absolute;
  inset: 17% 35% 8%;
  opacity: .72;
  background:
    linear-gradient(135deg, transparent 42%, color-mix(in srgb, #f4c56e 82%, var(--mr-accent)) 43% 57%, transparent 58%) 50% 10% / 22px 22px repeat-y,
    linear-gradient(45deg, transparent 42%, color-mix(in srgb, #f4c56e 82%, var(--mr-accent)) 43% 57%, transparent 58%) 50% 10% / 22px 22px repeat-y;
  filter: drop-shadow(0 0 6px color-mix(in srgb, #f2bd5f 45%, transparent));
  animation: track-scroll var(--track-period) linear infinite;
}

.track-rail {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3.4%;
  background: linear-gradient(90deg, #71512a, #f0c873 45%, #8b6635);
  box-shadow: 0 0 12px color-mix(in srgb, #f0c873 28%, transparent);
}

.track-rail--left { left: 0; }
.track-rail--right { right: 0; }

.junction-disc {
  position: absolute;
  z-index: 4;
  top: 31%;
  left: 50%;
  width: clamp(170px, 29%, 330px);
  aspect-ratio: 1;
  border: clamp(8px, 1vw, 14px) solid var(--mr-stage-edge);
  border-radius: 50%;
  background:
    radial-gradient(circle, var(--mr-stage-top) 0 25%, transparent 26%),
    conic-gradient(from 45deg, var(--mr-stage-top), var(--mr-stage-bottom), var(--mr-stage-top));
  transform: translate(-50%, -50%) perspective(520px) rotateX(58deg);
  box-shadow:
    inset 0 0 0 4px var(--mr-stage-inner-edge),
    0 24px 32px color-mix(in srgb, var(--mr-shadow) 40%, transparent);
}

.junction-ring {
  position: absolute;
  border: 2px solid color-mix(in srgb, var(--mr-accent) 52%, var(--mr-stage-detail));
  border-radius: 50%;
}

.junction-ring--outer { inset: 17%; }
.junction-ring--inner { inset: 31%; }
.junction-core {
  position: absolute;
  inset: 42%;
  background: var(--mr-accent);
  transform: rotate(45deg);
  box-shadow: 0 0 16px color-mix(in srgb, var(--mr-accent) 55%, transparent);
}

.track-branch {
  position: absolute;
  z-index: 2;
  display: block;
  border: 3px solid var(--mr-stage-edge);
  background:
    repeating-linear-gradient(90deg, transparent 0 28px, color-mix(in srgb, var(--mr-stage-detail) 48%, transparent) 29px 31px),
    linear-gradient(
      color-mix(in srgb, #2c3541 80%, var(--mr-stage-top)),
      color-mix(in srgb, #171e28 78%, var(--mr-stage-bottom))
    );
  box-shadow: 0 14px 22px color-mix(in srgb, var(--mr-shadow) 34%, transparent);
  transition: filter 180ms ease, opacity 180ms ease;
}

.track-branch--up {
  top: 8%;
  left: 43%;
  width: 14%;
  height: 31%;
  clip-path: polygon(31% 0, 69% 0, 100% 100%, 0 100%);
}

.track-branch--left,
.track-branch--right {
  top: 29%;
  width: 37%;
  height: 17%;
}

.track-branch--left {
  left: 5%;
  clip-path: polygon(0 27%, 100% 0, 100% 100%, 0 73%);
}

.track-branch--right {
  right: 5%;
  clip-path: polygon(0 0, 100% 27%, 100% 73%, 0 100%);
}

.track-branch--down {
  left: 40%;
  bottom: 8%;
  width: 20%;
  height: 44%;
  clip-path: polygon(17% 0, 83% 0, 100% 100%, 0 100%);
}

.track-branch--blocked { filter: grayscale(.65) brightness(.72); opacity: .56; }
.track-branch--correct { filter: drop-shadow(0 0 10px var(--mr-success-glow)); }

.question-gate {
  position: absolute;
  z-index: 7;
  display: grid;
  min-width: 0;
  min-height: 58px;
  overflow: visible;
  border: 0;
  padding: 7px 10px;
  border-radius: 13px;
  color: var(--mr-copy-primary);
  background:
    radial-gradient(circle at 50% 0, rgba(240, 255, 255, .88), transparent 58%),
    linear-gradient(145deg, rgba(219, 250, 252, .9), rgba(130, 191, 199, .76));
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, white 18%, transparent),
    0 8px 20px color-mix(in srgb, var(--mr-shadow) 40%, transparent),
    0 0 0 1px var(--mr-metal-edge);
  font: inherit;
  text-align: center;
  cursor: pointer;
  transform-origin: 50% 100%;
  transition: transform 150ms ease, filter 150ms ease, box-shadow 150ms ease;
}

.question-gate:not(:disabled):hover,
.question-gate:not(:disabled):focus-visible {
  z-index: 12;
  outline: none;
  filter: brightness(1.12);
  box-shadow:
    0 10px 24px color-mix(in srgb, var(--mr-shadow) 42%, transparent),
    0 0 0 3px color-mix(in srgb, var(--mr-accent) 68%, transparent),
    0 0 22px color-mix(in srgb, var(--mr-accent) 25%, transparent);
}

.question-gate:disabled { cursor: default; }

.question-gate--up {
  top: 6.5%;
  left: 50%;
  width: clamp(150px, 25%, 260px);
  transform: translateX(-50%);
}

.question-gate--left,
.question-gate--right {
  top: 29%;
  width: clamp(138px, 23%, 240px);
}

.question-gate--left { left: 3%; }
.question-gate--right { right: 3%; }

.question-gate--down {
  left: 50%;
  bottom: 25%;
  width: clamp(150px, 27%, 275px);
  transform: translateX(-50%);
}

.question-gate--up:not(:disabled):hover,
.question-gate--up:not(:disabled):focus-visible,
.question-gate--down:not(:disabled):hover,
.question-gate--down:not(:disabled):focus-visible {
  transform: translateX(-50%) translateY(-2px);
}

.gate-frame {
  position: absolute;
  inset: -4px;
  z-index: -1;
  border: 2px solid color-mix(in srgb, #d9ad64 70%, var(--mr-metal-edge));
  border-radius: 16px;
  pointer-events: none;
}

.gate-content { display: grid; gap: 4px; min-width: 0; }
.gate-direction { display: flex; align-items: center; justify-content: center; gap: 5px; color: var(--mr-copy-secondary); font-size: 9px; font-weight: 850; letter-spacing: .08em; }
.gate-direction b { color: var(--mr-accent); font-size: 15px; line-height: 1; }
.gate-equation { min-width: 0; font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; font-size: clamp(12px, 1.55vw, 19px); font-weight: 900; line-height: 1.18; text-wrap: balance; text-shadow: 0 1px 2px var(--mr-copy-outline); }

.question-gate--blocked {
  color: var(--mr-copy-secondary);
  background:
    repeating-linear-gradient(135deg, transparent 0 8px, color-mix(in srgb, var(--mr-stage-detail) 48%, transparent) 8px 11px),
    linear-gradient(var(--mr-stage-bottom), var(--mr-metal-body));
  filter: saturate(.55) brightness(.78);
}

.question-gate--blocked .gate-frame { border-style: dashed; opacity: .62; }
.gate-barrier { display: grid; place-items: center; gap: 1px; font-size: 9px; font-weight: 900; letter-spacing: .14em; }
.gate-barrier b { font-size: 21px; color: var(--mr-warning); letter-spacing: -.35em; transform: translateX(-.18em); }

.question-gate--selected:not(.question-gate--wrong) {
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--mr-accent) 70%, transparent),
    0 0 28px color-mix(in srgb, var(--mr-accent) 32%, transparent);
}

.question-gate--correct {
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--mr-success) 78%, transparent),
    0 0 32px var(--mr-success-glow);
}

.question-gate--wrong {
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--mr-danger) 78%, transparent),
    0 0 30px var(--mr-danger-glow);
}

.gate-result-mark {
  position: absolute;
  top: -14px;
  right: -12px;
  width: 30px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 2px solid currentColor;
  border-radius: 50%;
  color: var(--mr-copy-on-stage);
  font-size: 19px;
  font-weight: 950;
  box-shadow: 0 5px 16px color-mix(in srgb, var(--mr-shadow) 40%, transparent);
}

.gate-result-mark--correct { background: var(--mr-success-strong); }
.gate-result-mark--wrong { background: var(--mr-danger-strong); }

.runner-anchor {
  position: absolute;
  z-index: 8;
  left: 50%;
  bottom: 4.5%;
  transform: translateX(-50%);
}

.scene-timer {
  position: absolute;
  z-index: 9;
  top: 16px;
  right: 16px;
  width: 66px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  align-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, var(--mr-metal-body) 57%, transparent 59%),
    conic-gradient(var(--mr-accent) 0 var(--timer-angle), color-mix(in srgb, var(--mr-stage-detail) 55%, transparent) var(--timer-angle) 360deg);
  color: var(--mr-copy-on-stage);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--mr-shadow) 35%, transparent);
}

.scene-timer span { font-size: 17px; font-weight: 950; line-height: 1; }
.scene-timer small { margin-top: 2px; color: var(--mr-copy-secondary); font-size: 8px; font-weight: 850; letter-spacing: .08em; }
.scene-timer--urgent { animation: timer-urgent 700ms ease-in-out infinite alternate; }

.level-up-flash {
  position: absolute;
  z-index: 10;
  top: 50%;
  left: 50%;
  display: grid;
  place-items: center;
  gap: 3px;
  min-width: 150px;
  border: 1px solid color-mix(in srgb, var(--mr-accent) 65%, white);
  border-radius: 16px;
  padding: 12px 22px;
  background: color-mix(in srgb, var(--mr-metal-body) 88%, transparent);
  box-shadow: 0 0 34px color-mix(in srgb, var(--mr-accent) 38%, transparent);
  transform: translate(-50%, -50%);
  animation: level-flash 900ms cubic-bezier(.2, .8, .2, 1) both;
}

.level-up-flash small { color: var(--mr-accent); font-size: 8px; font-weight: 950; letter-spacing: .2em; }
.level-up-flash strong { font-size: 20px; }

.track-world--turn-left { animation: world-turn-left 620ms cubic-bezier(.2, .8, .2, 1); }
.track-world--turn-right { animation: world-turn-right 620ms cubic-bezier(.2, .8, .2, 1); }
.track-world--turn-up { animation: world-turn-up 540ms cubic-bezier(.2, .8, .2, 1); }
.track-world--turn-down { animation: world-turn-down 540ms cubic-bezier(.2, .8, .2, 1); }

.track-scene--wrong .speed-line,
.track-scene--timeout .speed-line,
.track-scene--completed .speed-line,
.track-scene--wrong .approach-track,
.track-scene--timeout .approach-track,
.track-scene--completed .approach-track {
  animation-play-state: paused;
}

.track-scene--level-up::after {
  content: '';
  position: absolute;
  z-index: 6;
  inset: 0;
  border: 4px solid color-mix(in srgb, var(--mr-accent) 65%, transparent);
  border-radius: inherit;
  pointer-events: none;
  animation: stage-level-ring 900ms ease-out both;
}

@keyframes track-scroll { to { background-position: 0 120%, 0 0; } }
@keyframes speed-line-fall { from { transform: translateY(-80%) scaleY(.5); } to { transform: translateY(640%) scaleY(2.4); } }
@keyframes cloud-drift { from { transform: translateX(-3%); } to { transform: translateX(5%); } }
@keyframes island-float { from { transform: translateY(-2px); } to { transform: translateY(6px); } }
@keyframes crystal-pulse { from { filter: brightness(.88); transform: translateY(0); } to { filter: brightness(1.18); transform: translateY(-2px); } }
@keyframes timer-urgent { from { filter: none; } to { filter: drop-shadow(0 0 12px var(--mr-warning-glow)); } }
@keyframes level-flash { 0% { opacity: 0; transform: translate(-50%, -42%) scale(.82); } 32% { opacity: 1; transform: translate(-50%, -50%) scale(1.04); } 78% { opacity: 1; } 100% { opacity: 0; transform: translate(-50%, -58%) scale(1); } }
@keyframes stage-level-ring { from { opacity: 1; transform: scale(.985); } to { opacity: 0; transform: scale(1.02); } }
@keyframes world-turn-left { 0%, 100% { transform: translateX(0) rotate(0); } 60% { transform: translateX(6%) rotate(2deg); } }
@keyframes world-turn-right { 0%, 100% { transform: translateX(0) rotate(0); } 60% { transform: translateX(-6%) rotate(-2deg); } }
@keyframes world-turn-up { 0%, 100% { transform: scale(1); } 58% { transform: scale(1.055); } }
@keyframes world-turn-down { 0%, 100% { transform: translateY(0) scale(1); } 58% { transform: translateY(-3%) scale(.96); } }

@media (max-width: 720px) {
  .track-scene { min-height: 0; border-radius: 22px; }
  .horizon-architecture { inset-inline: -8%; }
  .question-gate { min-height: 52px; padding: 6px 7px; border-radius: 11px; }
  .question-gate--up { top: 6%; width: min(46%, 200px); }
  .question-gate--left,
  .question-gate--right { top: 30%; width: min(36%, 156px); }
  .question-gate--left { left: 2%; }
  .question-gate--right { right: 2%; }
  .question-gate--down { bottom: 25%; width: min(48%, 210px); }
  .gate-direction span { font-size: 8px; }
  .gate-equation { font-size: clamp(11px, 3.25vw, 15px); }
  .scene-timer { top: 10px; right: 10px; width: 56px; }
  .scene-timer span { font-size: 14px; }
  .runner-anchor { bottom: 3%; transform: translateX(-50%) scale(.86); }
  .junction-disc { top: 34%; width: clamp(145px, 44%, 230px); }
  .track-branch--left,
  .track-branch--right { top: 31%; }
  .approach-track { inset: 30% 0 0; }
}

@media (max-width: 390px) {
  .track-scene { min-height: 0; }
  .question-gate--left,
  .question-gate--right { width: 36%; }
  .gate-direction { gap: 3px; font-size: 7px; }
  .gate-direction b { font-size: 12px; }
  .gate-equation { font-size: 10px; overflow-wrap: anywhere; }
  .question-gate--down { bottom: 26%; }
  .runner-anchor { bottom: 1.5%; transform: translateX(-50%) scale(.76); }
}

@media (orientation: landscape) and (max-height: 620px) {
  .track-scene { border-radius: 12px; }
  .horizon-architecture { inset: 4% 2% auto; height: 29%; }
  .floating-island--three { display: none; }
  .question-gate { min-height: 43px; padding: 4px 6px; border-radius: 9px; }
  .question-gate--up { top: 3%; width: min(38%, 220px); }
  .question-gate--left,
  .question-gate--right { top: 27%; width: min(31%, 190px); }
  .question-gate--left { left: 1.5%; }
  .question-gate--right { right: 1.5%; }
  .question-gate--down { bottom: 36%; width: min(40%, 225px); }
  .gate-content { gap: 2px; }
  .gate-direction { font-size: 7px; }
  .gate-direction b { font-size: 11px; }
  .gate-equation { font-size: clamp(9px, 1.75vw, 13px); }
  .scene-timer { top: 7px; right: 7px; width: 48px; }
  .scene-timer span { font-size: 12px; }
  .runner-anchor { bottom: 1%; transform: translateX(-50%) scale(.63); }
  .junction-disc { top: 33%; width: clamp(118px, 30%, 205px); }
  .approach-track { inset: 28% 0 0; }
  .crystal-beacon--three,
  .crystal-beacon--four { top: 55%; }
}

@media (prefers-reduced-motion: reduce) {
  .cloud,
  .floating-island,
  .crystal-beacon,
  .speed-line,
  .approach-track,
  .scene-timer,
  .level-up-flash,
  .track-world,
  .track-scene--level-up::after {
    animation: none !important;
  }

  .question-gate { transition-duration: 0s; }
}
</style>
