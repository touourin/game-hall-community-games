<script setup lang="ts">
import { computed } from 'vue'
import type { EndReason, RunnerAction, RunnerFailureKind } from '../types'

const props = withDefaults(defineProps<{
  action?: RunnerAction | null
  endReason?: EndReason
  failureKind?: RunnerFailureKind
  runCycleMs?: number
}>(), {
  action: null,
  endReason: null,
  failureKind: null,
  runCycleMs: 720,
})

const activeAction = computed<RunnerAction | null>(() => (
  props.endReason ? null : props.action
))

const activeFailure = computed<Exclude<RunnerFailureKind, null> | null>(() => {
  if (!props.endReason || props.endReason === 'completed') return null
  if (props.failureKind) return props.failureKind
  return props.endReason === 'timeout' ? 'cliff' : 'wall'
})

const runnerClass = computed(() => ({
  [`runner-model--${activeAction.value}`]: Boolean(activeAction.value),
  [`runner-model--failure-${activeFailure.value}`]: Boolean(activeFailure.value),
  'runner-model--completed': props.endReason === 'completed',
}))

const runnerStyle = computed(() => ({
  '--runner-cycle': `${Math.max(420, props.runCycleMs)}ms`,
}))

const runFrames = computed(() => {
  const cycle = Math.max(420, props.runCycleMs)
  return Array.from({ length: 8 }, (_, index) => ({
    number: index + 1,
    style: { animationDelay: `${cycle * index / 8}ms` },
  }))
})
</script>

<template>
  <div
    class="runner-model"
    :class="runnerClass"
    :style="runnerStyle"
    :data-runner-motion="activeFailure ?? activeAction ?? (endReason === 'completed' ? 'completed' : 'run')"
    aria-hidden="true"
  >
    <span class="runner-shadow" />
    <span class="runner-wake runner-wake--left" />
    <span class="runner-wake runner-wake--right" />
    <span
      v-for="frame in runFrames"
      :key="frame.number"
      class="runner-sprite runner-sprite--run-frame"
      :class="`runner-sprite--run-frame-${frame.number}`"
      :style="frame.style"
      :data-runner-frame="frame.number"
    />
    <template v-if="activeAction === 'left' || activeAction === 'right'">
      <span
        class="runner-sprite runner-sprite--action runner-sprite--turn-entry"
        :class="`runner-sprite--action-${activeAction}-entry`"
        :data-runner-pose="activeAction"
      />
      <span
        class="runner-sprite runner-sprite--action runner-sprite--turn-apex"
        :class="`runner-sprite--action-${activeAction}-apex`"
      />
    </template>
    <span
      v-else-if="activeAction"
      class="runner-sprite runner-sprite--action"
      :class="`runner-sprite--action-${activeAction}`"
      :data-runner-pose="activeAction"
    />
    <span
      v-if="activeFailure"
      class="runner-sprite runner-sprite--failure"
      :class="`runner-sprite--failure-${activeFailure}`"
      :data-runner-failure="activeFailure"
    />
    <span v-if="activeFailure === 'wall'" class="runner-impact" aria-hidden="true">
      <i v-for="index in 8" :key="index" :style="{ '--spark-index': index - 1 }" />
    </span>
  </div>
</template>

<style scoped>
.runner-model {
  --runner-cycle: 720ms;
  position: relative;
  width: clamp(158px, 15.4vw, 224px);
  aspect-ratio: 1;
  transform-origin: 50% 88%;
  filter:
    brightness(1.08)
    saturate(1.06)
    drop-shadow(0 10px 10px rgba(2, 7, 14, .5))
    drop-shadow(0 0 7px rgba(255, 188, 86, .24));
  will-change: transform, opacity;
}

.runner-sprite {
  position: absolute;
  z-index: 2;
  inset: 0;
  display: block;
  background-image: url('../assets/runner-animation-atlas-v2.png');
  background-repeat: no-repeat;
  background-size: 400% 400%;
  transform-origin: 50% 84%;
  will-change: background-position, opacity, transform;
}

.runner-sprite--run-frame {
  opacity: 0;
  animation: runner-frame-visibility var(--runner-cycle) linear infinite;
}
.runner-sprite--run-frame-1 { background-position: 0 0; }
.runner-sprite--run-frame-2 { background-position: 33.333% 0; }
.runner-sprite--run-frame-3 { background-position: 66.667% 0; }
.runner-sprite--run-frame-4 { background-position: 100% 0; }
.runner-sprite--run-frame-5 { background-position: 0 33.333%; }
.runner-sprite--run-frame-6 { background-position: 33.333% 33.333%; }
.runner-sprite--run-frame-7 { background-position: 66.667% 33.333%; }
.runner-sprite--run-frame-8 { background-position: 100% 33.333%; }

.runner-sprite--action,
.runner-sprite--failure {
  z-index: 3;
}

.runner-sprite--action-left-entry {
  background-position: 0 0;
}
.runner-sprite--action-left-apex {
  background-position: 0 100%;
}
.runner-sprite--action-right-entry {
  background-position: 0 0;
}
.runner-sprite--action-right-apex {
  background-position: 100% 0;
}

.runner-sprite--turn-entry,
.runner-sprite--turn-apex {
  background-image: url('../assets/runner-turn-atlas-v2.png');
  background-size: 200% 200%;
}
.runner-sprite--turn-entry { animation: runner-turn-entry-frame 660ms linear both; }
.runner-sprite--turn-apex { animation: runner-turn-apex-frame 660ms linear both; }

.runner-sprite--action-jump {
  background-position: 0 100%;
  animation: runner-action-visibility 680ms ease-in-out both;
}

.runner-sprite--action-slide {
  background-position: 33.333% 100%;
  animation: runner-action-visibility 680ms ease-in-out both;
}

.runner-sprite--failure-wall {
  background-position: 66.667% 100%;
  animation: runner-failure-visibility 980ms ease-out both;
}

.runner-sprite--failure-cliff {
  background-position: 100% 100%;
  animation: runner-failure-visibility 1250ms ease-out both;
}

.runner-model--left .runner-sprite--run-frame,
.runner-model--right .runner-sprite--run-frame,
.runner-model--jump .runner-sprite--run-frame,
.runner-model--slide .runner-sprite--run-frame,
.runner-model--failure-wall .runner-sprite--run-frame,
.runner-model--failure-cliff .runner-sprite--run-frame {
  opacity: 0;
  animation: none;
}

.runner-shadow {
  position: absolute;
  z-index: 0;
  left: 50%;
  bottom: 12%;
  width: 47%;
  height: 8%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(1, 6, 12, .7), rgba(1, 6, 12, 0) 72%);
  transform: translateX(-50%);
  animation: runner-shadow var(--runner-cycle) ease-in-out infinite;
}

.runner-wake {
  position: absolute;
  z-index: 1;
  bottom: 17%;
  width: 2px;
  height: 21%;
  border-radius: 999px;
  background: linear-gradient(0deg, rgba(94, 225, 241, 0), rgba(157, 240, 250, .58));
  filter: blur(.35px);
  opacity: .42;
  transform-origin: 50% 100%;
  animation: runner-wake var(--runner-cycle) linear infinite;
}

.runner-wake--left { left: 42%; animation-delay: calc(var(--runner-cycle) * -.5); }
.runner-wake--right { right: 42%; }

.runner-model--left { animation: runner-turn-left 660ms cubic-bezier(.16, .78, .18, 1); }
.runner-model--right { animation: runner-turn-right 660ms cubic-bezier(.16, .78, .18, 1); }
.runner-model--jump { animation: runner-jump 680ms cubic-bezier(.18, .72, .2, 1); }
.runner-model--slide { animation: runner-slide 680ms cubic-bezier(.16, .78, .18, 1); }
.runner-model--failure-wall { animation: runner-wall-crash 980ms cubic-bezier(.16, .72, .2, 1) forwards; }
.runner-model--failure-cliff { animation: runner-cliff-fall 1250ms cubic-bezier(.3, .04, .74, .4) forwards; }
.runner-model--completed { animation: runner-finish 1100ms cubic-bezier(.2, .8, .2, 1) forwards; }

.runner-model--jump .runner-shadow {
  animation: runner-jump-shadow 680ms ease-in-out both;
}

.runner-model--slide .runner-shadow,
.runner-model--failure-wall .runner-shadow {
  width: 67%;
}

.runner-model--failure-cliff .runner-shadow {
  animation: runner-cliff-shadow 720ms ease-in forwards;
}

.runner-model--failure-wall .runner-wake,
.runner-model--failure-cliff .runner-wake,
.runner-model--completed .runner-wake {
  animation-play-state: paused;
  opacity: 0;
}

.runner-model--completed .runner-sprite,
.runner-model--completed .runner-shadow {
  animation-play-state: paused;
}

.runner-impact {
  position: absolute;
  z-index: 5;
  top: 31%;
  left: 50%;
  width: 18px;
  aspect-ratio: 1;
  border: 3px solid rgba(255, 211, 122, .9);
  border-radius: 50%;
  opacity: 0;
  transform: translate(-50%, -50%);
  animation: impact-ring 980ms ease-out both;
}

.runner-impact i {
  --spark-index: 0;
  position: absolute;
  top: 50%;
  left: 50%;
  width: 3px;
  height: 24px;
  border-radius: 99px;
  background: linear-gradient(#fff7cf, #ffad3e 58%, transparent);
  transform: translate(-50%, -50%) rotate(calc(var(--spark-index) * 45deg)) translateY(-24px);
  transform-origin: 50% 100%;
}

@keyframes runner-frame-visibility {
  0%, 12.35% { opacity: 1; transform: translateY(0) rotate(-.35deg); }
  12.5%, 100% { opacity: 0; transform: translateY(-2.4%) rotate(.35deg); }
}

@keyframes runner-turn-entry-frame {
  0% { opacity: .2; }
  8%, 46% { opacity: 1; }
  47%, 100% { opacity: 0; }
}

@keyframes runner-turn-apex-frame {
  0%, 45% { opacity: 0; }
  47%, 90% { opacity: 1; }
  100% { opacity: .18; }
}

@keyframes runner-action-visibility {
  0% { opacity: .18; }
  10%, 88% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes runner-failure-visibility {
  0% { opacity: .2; }
  8%, 92% { opacity: 1; }
  100% { opacity: .86; }
}

@keyframes runner-shadow {
  0%, 100% { opacity: .72; transform: translateX(-50%) scaleX(.92); }
  12.5%, 62.5% { opacity: .5; transform: translateX(-50%) scaleX(.73); }
  37.5%, 87.5% { opacity: .36; transform: translateX(-50%) scaleX(.61); }
}

@keyframes runner-wake {
  0% { opacity: 0; transform: translateY(-8%) scaleY(.25); }
  24% { opacity: .48; }
  100% { opacity: 0; transform: translateY(155%) scaleY(1.25); }
}

@keyframes runner-turn-left {
  0%, 100% { transform: translate(0, 0) rotate(0); }
  18% { transform: translate(-7px, -1px) rotate(-2deg); }
  56% { transform: translate(-40px, -7px) rotate(-11deg); }
  82% { transform: translate(-25px, -3px) rotate(-5deg); }
}

@keyframes runner-turn-right {
  0%, 100% { transform: translate(0, 0) rotate(0); }
  18% { transform: translate(7px, -1px) rotate(2deg); }
  56% { transform: translate(40px, -7px) rotate(11deg); }
  82% { transform: translate(25px, -3px) rotate(5deg); }
}

@keyframes runner-jump {
  0%, 100% { transform: translateY(0) scale(1); }
  13% { transform: translateY(6px) scale(1.035, .96); }
  28% { transform: translateY(-34px) scale(.99, 1.02); }
  52%, 61% { transform: translateY(-94px) scale(.96, 1.03); }
  84% { transform: translateY(-16px) scale(1.01, .99); }
  92% { transform: translateY(5px) scale(1.04, .95); }
}

@keyframes runner-jump-shadow {
  0%, 100% { opacity: .7; transform: translateX(-50%) scaleX(.92); }
  52%, 61% { opacity: .16; transform: translateX(-50%) scaleX(.35); }
}

@keyframes runner-slide {
  0%, 100% { transform: translateY(0) scale(1); }
  17% { transform: translateY(4px) scale(1.03, .96); }
  35%, 78% { transform: translate(12px, 17px) scale(1.12, .9); }
  90% { transform: translateY(5px) scale(1.035, .96); }
}

@keyframes runner-wall-crash {
  0% { transform: translateY(0) scale(1); }
  20% { transform: translateY(-3px) scale(1.035); }
  31% { transform: translate(-2px, 8px) rotate(-2deg) scale(1.08, .93); }
  38% { transform: translate(9px, 12px) rotate(7deg) scale(.98); }
  52% { transform: translate(-7px, 11px) rotate(-5deg) scale(.98); }
  72%, 100% { transform: translate(3px, 14px) rotate(3deg) scale(.97); }
}

@keyframes runner-cliff-fall {
  0% { transform: translate(0, 0) rotate(0) scale(1); opacity: 1; }
  16% { transform: translate(8px, -5px) rotate(7deg) scale(1.02); opacity: 1; }
  38% { transform: translate(28px, 30px) rotate(22deg) scale(.9); opacity: 1; }
  72% { transform: translate(55px, 135px) rotate(58deg) scale(.58); opacity: .85; }
  100% { transform: translate(72px, 260px) rotate(96deg) scale(.24); opacity: 0; }
}

@keyframes runner-cliff-shadow {
  0%, 20% { opacity: .62; transform: translateX(-50%) scaleX(.9); }
  60% { opacity: .16; transform: translateX(-30%) scaleX(.38); }
  100% { opacity: 0; transform: translateX(30%) scaleX(.12); }
}

@keyframes impact-ring {
  0%, 25% { opacity: 0; transform: translate(-50%, -50%) scale(.25) rotate(0); }
  32% { opacity: 1; transform: translate(-50%, -50%) scale(.72) rotate(8deg); }
  68%, 100% { opacity: 0; transform: translate(-50%, -50%) scale(2.9) rotate(18deg); }
}

@keyframes runner-finish {
  0% { transform: translateY(0) scale(1); opacity: 1; }
  55% { transform: translateY(-24px) scale(.82); opacity: 1; }
  100% { transform: translateY(-70px) scale(.52); opacity: .45; }
}

@media (max-width: 620px) {
  .runner-model { width: 166px; }
}

@media (orientation: landscape) and (max-height: 620px) {
  .runner-model { width: 176px; }
}

@media (prefers-reduced-motion: reduce) {
  .runner-model,
  .runner-sprite,
  .runner-shadow,
  .runner-wake,
  .runner-impact {
    animation: none !important;
  }

  .runner-sprite--run-frame { opacity: 0; }
  .runner-sprite--run-frame-1 { opacity: 1; }
  .runner-sprite--action,
  .runner-sprite--failure { opacity: 1; }
  .runner-model--left { transform: translateX(-20px) rotate(-6deg); }
  .runner-model--right { transform: translateX(20px) rotate(6deg); }
  .runner-model--jump { transform: translateY(-38px); }
  .runner-model--slide { transform: translateY(13px); }
  .runner-model--failure-wall { transform: translate(3px, 12px) rotate(3deg); }
  .runner-model--failure-cliff { transform: translate(34px, 92px) rotate(42deg) scale(.62); opacity: .6; }
  .runner-model--completed { transform: translateY(-25px) scale(.74); }
}
</style>
