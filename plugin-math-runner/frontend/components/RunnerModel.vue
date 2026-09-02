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

const runnerStyle = computed(() => ({
  '--runner-cycle': `${props.runCycleMs}ms`,
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
    <span class="runner-body">
      <span class="runner-head">
        <span class="runner-hair runner-hair--one" />
        <span class="runner-hair runner-hair--two" />
        <span class="runner-face-mark" />
      </span>
      <span class="runner-neck" />
      <span class="runner-torso">
        <span class="runner-jacket runner-jacket--left" />
        <span class="runner-jacket runner-jacket--right" />
        <span class="runner-core" />
      </span>
      <span class="runner-arm runner-arm--left"><span class="runner-hand" /></span>
      <span class="runner-arm runner-arm--right"><span class="runner-hand" /></span>
      <span class="runner-leg runner-leg--left"><span class="runner-shoe" /></span>
      <span class="runner-leg runner-leg--right"><span class="runner-shoe" /></span>
    </span>
  </div>
</template>

<style scoped>
.runner-model {
  --runner-cycle: 720ms;
  position: relative;
  width: 58px;
  height: 112px;
  transform-origin: 50% 94%;
  filter: drop-shadow(0 7px 8px color-mix(in srgb, var(--mr-shadow) 70%, transparent));
}

.runner-shadow {
  position: absolute;
  z-index: 0;
  left: 50%;
  bottom: 1px;
  width: 43px;
  height: 10px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--mr-shadow) 72%, transparent);
  transform: translateX(-50%);
  animation: runner-shadow var(--runner-cycle) ease-in-out infinite;
}

.runner-body {
  position: absolute;
  z-index: 1;
  inset: 0;
  transform-origin: 50% 86%;
  animation: runner-bob var(--runner-cycle) ease-in-out infinite;
}

.runner-head {
  position: absolute;
  z-index: 5;
  top: 5px;
  left: 50%;
  width: 27px;
  height: 30px;
  border: 2px solid var(--mr-metal-edge);
  border-radius: 48% 48% 44% 44%;
  background: color-mix(in srgb, var(--mr-copy-on-stage) 84%, #c78d64);
  transform: translateX(-50%);
  box-shadow: inset -5px -3px 0 color-mix(in srgb, var(--mr-metal-side) 18%, transparent);
}

.runner-hair {
  position: absolute;
  z-index: 2;
  display: block;
  background: var(--mr-metal-body);
  border: 1px solid var(--mr-metal-edge);
  transform-origin: 100% 50%;
}

.runner-hair--one {
  width: 24px;
  height: 12px;
  top: -4px;
  left: 0;
  border-radius: 70% 40% 55% 30%;
  transform: rotate(-9deg);
}

.runner-hair--two {
  width: 17px;
  height: 8px;
  top: 1px;
  right: -3px;
  border-radius: 30% 80% 30% 70%;
  transform: rotate(24deg);
}

.runner-face-mark {
  position: absolute;
  left: 50%;
  bottom: 7px;
  width: 11px;
  height: 3px;
  border-top: 2px solid color-mix(in srgb, var(--mr-metal-edge) 70%, transparent);
  transform: translateX(-50%);
}

.runner-neck {
  position: absolute;
  z-index: 2;
  top: 31px;
  left: 50%;
  width: 10px;
  height: 9px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--mr-copy-on-stage) 78%, #c78d64);
  transform: translateX(-50%);
}

.runner-torso {
  position: absolute;
  z-index: 3;
  top: 37px;
  left: 50%;
  width: 35px;
  height: 39px;
  overflow: hidden;
  border: 2px solid var(--mr-metal-edge);
  border-radius: 10px 10px 13px 13px;
  background: var(--mr-metal-body);
  transform: translateX(-50%);
  clip-path: polygon(10% 0, 90% 0, 78% 100%, 22% 100%);
}

.runner-jacket {
  position: absolute;
  top: 0;
  width: 45%;
  height: 100%;
  background: linear-gradient(150deg, var(--mr-metal-body), var(--mr-metal-side));
}

.runner-jacket--left { left: 0; border-right: 1px solid color-mix(in srgb, var(--mr-accent) 58%, transparent); }
.runner-jacket--right { right: 0; border-left: 1px solid color-mix(in srgb, var(--mr-accent) 58%, transparent); }

.runner-core {
  position: absolute;
  z-index: 2;
  top: 12px;
  left: 50%;
  width: 9px;
  height: 9px;
  border: 1px solid color-mix(in srgb, var(--mr-accent) 76%, white);
  background: var(--mr-accent);
  transform: translateX(-50%) rotate(45deg);
  box-shadow: 0 0 10px color-mix(in srgb, var(--mr-accent) 60%, transparent);
}

.runner-arm,
.runner-leg {
  position: absolute;
  z-index: 2;
  display: block;
  border: 2px solid var(--mr-metal-edge);
  background: linear-gradient(var(--mr-metal-body), var(--mr-metal-side));
}

.runner-arm {
  top: 40px;
  width: 11px;
  height: 39px;
  border-radius: 7px;
  transform-origin: 50% 7px;
}

.runner-arm--left {
  left: 5px;
  animation: runner-arm-left var(--runner-cycle) ease-in-out infinite;
}

.runner-arm--right {
  right: 5px;
  animation: runner-arm-right var(--runner-cycle) ease-in-out infinite;
}

.runner-hand {
  position: absolute;
  left: 50%;
  bottom: -6px;
  width: 9px;
  height: 10px;
  border: 1px solid var(--mr-metal-edge);
  border-radius: 50%;
  background: color-mix(in srgb, var(--mr-copy-on-stage) 80%, #c78d64);
  transform: translateX(-50%);
}

.runner-leg {
  top: 70px;
  width: 13px;
  height: 35px;
  border-radius: 6px 6px 8px 8px;
  transform-origin: 50% 4px;
}

.runner-leg--left {
  left: 14px;
  animation: runner-leg-left var(--runner-cycle) ease-in-out infinite;
}

.runner-leg--right {
  right: 14px;
  animation: runner-leg-right var(--runner-cycle) ease-in-out infinite;
}

.runner-shoe {
  position: absolute;
  left: -3px;
  bottom: -6px;
  width: 18px;
  height: 9px;
  border: 2px solid var(--mr-metal-edge);
  border-radius: 7px 8px 5px 4px;
  background: linear-gradient(90deg, var(--mr-copy-on-stage), var(--mr-metal-side));
}

.runner-model--left { animation: runner-turn-left 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--right { animation: runner-turn-right 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--jump { animation: runner-jump 620ms cubic-bezier(.22, .75, .25, 1); }
.runner-model--slide { animation: runner-slide 620ms cubic-bezier(.2, .8, .2, 1); }

.runner-model--jump .runner-leg--left { animation: runner-jump-leg-left 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--jump .runner-leg--right { animation: runner-jump-leg-right 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--jump .runner-arm--left { animation: runner-jump-arm-left 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--jump .runner-arm--right { animation: runner-jump-arm-right 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--slide .runner-body { animation: runner-slide-body 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--slide .runner-leg--left { animation: runner-slide-leg-left 620ms cubic-bezier(.2, .8, .2, 1); }
.runner-model--slide .runner-leg--right { animation: runner-slide-leg-right 620ms cubic-bezier(.2, .8, .2, 1); }

.runner-model--wrong {
  animation: runner-stumble 540ms cubic-bezier(.2, .8, .2, 1) forwards;
}

.runner-model--timeout {
  animation: runner-brake 480ms cubic-bezier(.2, .8, .2, 1) forwards;
}

.runner-model--completed {
  animation: runner-finish 1100ms cubic-bezier(.2, .8, .2, 1) forwards;
}

.runner-model--wrong .runner-body,
.runner-model--wrong .runner-arm,
.runner-model--wrong .runner-leg,
.runner-model--timeout .runner-body,
.runner-model--timeout .runner-arm,
.runner-model--timeout .runner-leg,
.runner-model--completed .runner-body,
.runner-model--completed .runner-arm,
.runner-model--completed .runner-leg {
  animation-play-state: paused;
}

@keyframes runner-bob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-3px) rotate(.6deg); }
}

@keyframes runner-shadow {
  0%, 100% { opacity: .55; transform: translateX(-50%) scaleX(1); }
  50% { opacity: .34; transform: translateX(-50%) scaleX(.78); }
}

@keyframes runner-arm-left { 0%, 100% { transform: rotate(26deg); } 50% { transform: rotate(-24deg); } }
@keyframes runner-arm-right { 0%, 100% { transform: rotate(-24deg); } 50% { transform: rotate(26deg); } }
@keyframes runner-leg-left { 0%, 100% { transform: rotate(-27deg); } 50% { transform: rotate(25deg); } }
@keyframes runner-leg-right { 0%, 100% { transform: rotate(25deg); } 50% { transform: rotate(-27deg); } }

@keyframes runner-turn-left {
  0% { transform: translateX(0) rotate(0deg); }
  36% { transform: translateX(-7px) rotate(-14deg); }
  72% { transform: translateX(-19px) rotate(-30deg); }
  100% { transform: translateX(0) rotate(0deg); }
}

@keyframes runner-turn-right {
  0% { transform: translateX(0) rotate(0deg); }
  36% { transform: translateX(7px) rotate(14deg); }
  72% { transform: translateX(19px) rotate(30deg); }
  100% { transform: translateX(0) rotate(0deg); }
}

@keyframes runner-jump {
  0%, 100% { transform: translateY(0) scale(1); }
  18% { transform: translateY(-8px) scale(.98, 1.03); }
  55% { transform: translateY(-39px) scale(.96, 1.04); }
  82% { transform: translateY(-9px) scale(1.02, .97); }
}

@keyframes runner-jump-leg-left {
  0%, 100% { transform: rotate(-27deg); }
  45%, 68% { transform: translateY(-7px) rotate(58deg); }
}

@keyframes runner-jump-leg-right {
  0%, 100% { transform: rotate(25deg); }
  45%, 68% { transform: translateY(-9px) rotate(-52deg); }
}

@keyframes runner-jump-arm-left {
  0%, 100% { transform: rotate(26deg); }
  45%, 68% { transform: rotate(-58deg); }
}

@keyframes runner-jump-arm-right {
  0%, 100% { transform: rotate(-24deg); }
  45%, 68% { transform: rotate(54deg); }
}

@keyframes runner-slide {
  0%, 100% { transform: translateY(0) rotate(0) scale(1); }
  28%, 72% { transform: translateY(22px) rotate(-12deg) scale(1.08, .62); }
}

@keyframes runner-slide-body {
  0%, 100% { transform: translateY(0) rotate(0); }
  28%, 72% { transform: translate(7px, 9px) rotate(18deg); }
}

@keyframes runner-slide-leg-left {
  0%, 100% { transform: rotate(-27deg); }
  28%, 72% { transform: translate(2px, 5px) rotate(74deg); }
}

@keyframes runner-slide-leg-right {
  0%, 100% { transform: rotate(25deg); }
  28%, 72% { transform: translate(-2px, 4px) rotate(-68deg); }
}

@keyframes runner-stumble {
  0% { transform: translateY(0) rotate(0deg); }
  62% { transform: translateY(4px) rotate(18deg) scaleY(.94); }
  100% { transform: translateY(5px) rotate(14deg) scaleY(.95); }
}

@keyframes runner-brake {
  0% { transform: translateY(0) rotate(0deg); }
  70% { transform: translateY(6px) rotate(-9deg) scaleY(.96); }
  100% { transform: translateY(5px) rotate(-7deg) scaleY(.97); }
}

@keyframes runner-finish {
  0% { transform: translateY(0) scale(1); opacity: 1; }
  55% { transform: translateY(-15px) scale(.88); opacity: 1; }
  100% { transform: translateY(-31px) scale(.72); opacity: .55; }
}

@media (max-width: 620px) {
  .runner-model { transform: scale(.82); }
}

/* Material pass derived from the character sheet: charcoal jacket, ivory core,
   warm orange piping and one cyan route watch. Geometry stays DOM/CSS so every
   limb can continue to animate independently. */
.runner-head {
  border-color: #17191d;
  background: linear-gradient(145deg, #e0ad86, #b97855);
  box-shadow: inset -5px -3px 0 rgba(88, 43, 28, .2);
}
.runner-hair { border-color: #121418; background: linear-gradient(145deg, #303137, #111318); }
.runner-face-mark { border-color: rgba(80, 39, 25, .58); }
.runner-neck,
.runner-hand { background: #c98d68; border-color: #1b1c20; }
.runner-torso {
  border-color: #15171b;
  background: #262a31;
  box-shadow: inset 0 0 0 1px rgba(241, 167, 75, .18);
}
.runner-torso::before {
  position: absolute;
  z-index: 1;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 34%;
  background: linear-gradient(#f4efe4, #c9c4ba);
  content: '';
  transform: translateX(-50%);
}
.runner-jacket { background: linear-gradient(150deg, #343942, #1e2229); }
.runner-jacket--left { border-right-color: #e69a3f; }
.runner-jacket--right { border-left-color: #e69a3f; }
.runner-core { border-color: #dffcff; background: #4fd4e4; box-shadow: 0 0 10px rgba(79, 212, 228, .72); }
.runner-arm,
.runner-leg { border-color: #14171b; background: linear-gradient(#343942, #1b1f25); }
.runner-arm--right::after {
  position: absolute;
  right: -4px;
  top: 15px;
  width: 8px;
  aspect-ratio: 1;
  border: 1px solid #dffcff;
  border-radius: 50%;
  background: #42cedf;
  box-shadow: 0 0 6px rgba(66, 206, 223, .72);
  content: '';
}
.runner-shoe { border-color: #111318; background: linear-gradient(90deg, #f0eee7 0 28%, #242932 29%); }

@media (orientation: landscape) and (max-height: 620px) {
  .runner-model { transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .runner-model,
  .runner-shadow,
  .runner-body,
  .runner-arm,
  .runner-leg {
    animation: none !important;
  }

  .runner-model--left { transform: translateX(-8px) rotate(-8deg); }
  .runner-model--right { transform: translateX(8px) rotate(8deg); }
  .runner-model--jump { transform: translateY(-18px); }
  .runner-model--slide { transform: translateY(12px) scaleY(.7); }
  .runner-model--wrong { transform: rotate(8deg); }
  .runner-model--timeout { transform: rotate(-5deg); }
  .runner-model--completed { transform: translateY(-12px) scale(.88); }
}
</style>
