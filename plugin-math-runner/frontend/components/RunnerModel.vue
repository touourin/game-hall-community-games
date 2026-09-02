<script setup lang="ts">
import { computed } from 'vue'
import type { EndReason, RunnerAction } from '../types'

const props = withDefaults(defineProps<{
  action?: RunnerAction | null
  endReason?: EndReason
  runCycleMs?: number
}>(), {
  action: null,
  endReason: null,
  runCycleMs: 720,
})

const runnerClass = computed(() => ({
  [`runner-model--${props.action}`]: Boolean(props.action && !props.endReason),
  'runner-model--wrong': props.endReason === 'wrong',
  'runner-model--timeout': props.endReason === 'timeout',
  'runner-model--completed': props.endReason === 'completed',
}))

const poseAction = computed<RunnerAction | null>(() => {
  if (props.endReason === 'wrong') return 'left'
  if (props.endReason === 'timeout') return 'slide'
  if (props.endReason) return null
  return props.action
})

const runnerStyle = computed(() => ({
  '--runner-cycle': `${Math.max(360, props.runCycleMs)}ms`,
}))
</script>

<template>
  <div
    class="runner-model"
    :class="runnerClass"
    :style="runnerStyle"
    aria-hidden="true"
  >
    <span class="runner-shadow" />
    <span class="runner-wake runner-wake--left" />
    <span class="runner-wake runner-wake--right" />
    <span class="runner-sprite runner-sprite--run-a" />
    <span class="runner-sprite runner-sprite--run-b" />
    <span
      v-if="poseAction"
      class="runner-sprite runner-sprite--action"
      :class="`runner-sprite--${poseAction}`"
      :data-runner-pose="poseAction"
    />
  </div>
</template>

<style scoped>
.runner-model {
  --runner-cycle: 720ms;
  position: relative;
  width: clamp(154px, 15vw, 218px);
  aspect-ratio: 1;
  transform-origin: 50% 88%;
  filter:
    brightness(1.08)
    saturate(1.06)
    drop-shadow(0 10px 10px rgba(2, 7, 14, .5))
    drop-shadow(0 0 7px rgba(255, 188, 86, .28));
  will-change: transform;
}

.runner-sprite {
  position: absolute;
  z-index: 2;
  inset: 0;
  display: block;
  background-image: url('../assets/runner-motion-atlas.png');
  background-repeat: no-repeat;
  background-size: 300% 200%;
  transform-origin: 50% 83%;
  will-change: opacity, transform;
}

.runner-sprite--run-a {
  background-position: 0 0;
  animation: runner-frame-a var(--runner-cycle) steps(1, end) infinite;
}

.runner-sprite--run-b {
  background-position: 50% 0;
  animation: runner-frame-b var(--runner-cycle) steps(1, end) infinite;
}

.runner-sprite--right { background-position: 100% 0; }
.runner-sprite--left { background-position: 0 100%; }
.runner-sprite--jump { background-position: 50% 100%; }
.runner-sprite--slide {
  background-position: 100% 100%;
  transform: translateY(-7%) scale(1.08);
}

.runner-sprite--action {
  z-index: 3;
  animation: runner-action-pose 620ms ease-in-out both;
}

.runner-model--left .runner-sprite--run-a,
.runner-model--left .runner-sprite--run-b,
.runner-model--right .runner-sprite--run-a,
.runner-model--right .runner-sprite--run-b,
.runner-model--jump .runner-sprite--run-a,
.runner-model--jump .runner-sprite--run-b,
.runner-model--slide .runner-sprite--run-a,
.runner-model--slide .runner-sprite--run-b,
.runner-model--wrong .runner-sprite--run-a,
.runner-model--wrong .runner-sprite--run-b,
.runner-model--timeout .runner-sprite--run-a,
.runner-model--timeout .runner-sprite--run-b {
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
  background: radial-gradient(ellipse, rgba(1, 6, 12, .68), rgba(1, 6, 12, 0) 72%);
  transform: translateX(-50%);
  animation: runner-shadow var(--runner-cycle) ease-in-out infinite;
}

.runner-wake {
  position: absolute;
  z-index: 1;
  bottom: 17%;
  width: 2px;
  height: 22%;
  border-radius: 999px;
  background: linear-gradient(0deg, rgba(94, 225, 241, 0), rgba(157, 240, 250, .62));
  filter: blur(.35px);
  opacity: .45;
  transform-origin: 50% 100%;
  animation: runner-wake var(--runner-cycle) linear infinite;
}

.runner-wake--left { left: 42%; animation-delay: calc(var(--runner-cycle) * -.5); }
.runner-wake--right { right: 42%; }

.runner-model--left { animation: runner-turn-left 620ms cubic-bezier(.18, .78, .18, 1); }
.runner-model--right { animation: runner-turn-right 620ms cubic-bezier(.18, .78, .18, 1); }
.runner-model--jump { animation: runner-jump 620ms cubic-bezier(.2, .74, .24, 1); }
.runner-model--slide { animation: runner-slide 620ms cubic-bezier(.18, .78, .2, 1); }
.runner-model--wrong { animation: runner-stumble 540ms cubic-bezier(.2, .8, .2, 1) forwards; }
.runner-model--timeout { animation: runner-brake 480ms cubic-bezier(.2, .8, .2, 1) forwards; }
.runner-model--completed { animation: runner-finish 1100ms cubic-bezier(.2, .8, .2, 1) forwards; }

.runner-model--jump .runner-shadow {
  animation: runner-jump-shadow 620ms ease-in-out both;
}

.runner-model--slide .runner-shadow,
.runner-model--timeout .runner-shadow {
  width: 68%;
}

.runner-model--wrong .runner-wake,
.runner-model--timeout .runner-wake,
.runner-model--completed .runner-wake {
  animation-play-state: paused;
  opacity: 0;
}

.runner-model--completed .runner-sprite,
.runner-model--completed .runner-shadow {
  animation-play-state: paused;
}

@keyframes runner-frame-a {
  0%, 46% { opacity: 1; transform: translateY(0) rotate(-.45deg); }
  50%, 100% { opacity: 0; transform: translateY(-2px) rotate(.45deg); }
}

@keyframes runner-frame-b {
  0%, 46% { opacity: 0; transform: translateY(-2px) rotate(.45deg); }
  50%, 100% { opacity: 1; transform: translateY(0) rotate(-.45deg); }
}

@keyframes runner-action-pose {
  0% { opacity: .2; }
  8%, 90% { opacity: 1; }
  100% { opacity: .12; }
}

@keyframes runner-shadow {
  0%, 100% { opacity: .72; transform: translateX(-50%) scaleX(.92); }
  50% { opacity: .46; transform: translateX(-50%) scaleX(.7); }
}

@keyframes runner-wake {
  0% { opacity: 0; transform: translateY(-8%) scaleY(.25); }
  24% { opacity: .52; }
  100% { opacity: 0; transform: translateY(155%) scaleY(1.25); }
}

@keyframes runner-turn-left {
  0%, 100% { transform: translate(0, 0) rotate(0); }
  20% { transform: translate(-6px, -1px) rotate(-2deg); }
  58% { transform: translate(-34px, -5px) rotate(-8deg); }
  82% { transform: translate(-23px, -2px) rotate(-5deg); }
}

@keyframes runner-turn-right {
  0%, 100% { transform: translate(0, 0) rotate(0); }
  20% { transform: translate(6px, -1px) rotate(2deg); }
  58% { transform: translate(34px, -5px) rotate(8deg); }
  82% { transform: translate(23px, -2px) rotate(5deg); }
}

@keyframes runner-jump {
  0%, 100% { transform: translateY(0) scale(1); }
  16% { transform: translateY(-10px) scale(.98, 1.02); }
  52%, 62% { transform: translateY(-82px) scale(.98, 1.02); }
  86% { transform: translateY(-9px) scale(1.025, .975); }
}

@keyframes runner-jump-shadow {
  0%, 100% { opacity: .68; transform: translateX(-50%) scaleX(.9); }
  52%, 62% { opacity: .2; transform: translateX(-50%) scaleX(.42); }
}

@keyframes runner-slide {
  0%, 100% { transform: translateY(0) scale(1); }
  22% { transform: translateY(-3px) scale(1.025, .975); }
  42%, 78% { transform: translate(8px, -10px) scale(1.1, .96); }
}

@keyframes runner-stumble {
  0% { transform: translateY(0) rotate(0); }
  62% { transform: translate(-13px, 8px) rotate(-10deg) scale(.98); }
  100% { transform: translate(-10px, 8px) rotate(-7deg) scale(.98); }
}

@keyframes runner-brake {
  0% { transform: translateY(0) scale(1); }
  70% { transform: translateY(15px) scale(1.045, .96); }
  100% { transform: translateY(13px) scale(1.03, .97); }
}

@keyframes runner-finish {
  0% { transform: translateY(0) scale(1); opacity: 1; }
  55% { transform: translateY(-24px) scale(.82); opacity: 1; }
  100% { transform: translateY(-70px) scale(.52); opacity: .45; }
}

@media (max-width: 620px) {
  .runner-model { width: 164px; }
}

@media (orientation: landscape) and (max-height: 620px) {
  .runner-model { width: 174px; }
}

@media (prefers-reduced-motion: reduce) {
  .runner-model,
  .runner-sprite,
  .runner-shadow,
  .runner-wake {
    animation: none !important;
  }

  .runner-sprite--run-a { opacity: 1; }
  .runner-sprite--run-b { opacity: 0; }
  .runner-sprite--action { opacity: 1; }
  .runner-model--left { transform: translateX(-18px) rotate(-5deg); }
  .runner-model--right { transform: translateX(18px) rotate(5deg); }
  .runner-model--jump { transform: translateY(-34px); }
  .runner-model--slide { transform: translateY(11px); }
  .runner-model--wrong { transform: translate(-8px, 6px) rotate(-5deg); }
  .runner-model--timeout { transform: translateY(10px); }
  .runner-model--completed { transform: translateY(-25px) scale(.74); }
}
</style>
