<script setup lang="ts">
import { computed } from 'vue'
import type { UnoCardModel } from '../types'

const props = withDefaults(defineProps<{
  card?: UnoCardModel | null
  faceDown?: boolean
  selected?: boolean
  playable?: boolean
  disabled?: boolean
  compact?: boolean
  drawn?: boolean
}>(), {
  card: null,
  faceDown: false,
  selected: false,
  playable: false,
  disabled: false,
  compact: false,
  drawn: false,
})

const emit = defineEmits<{ activate: [] }>()

const colorClass = computed(() => props.card?.color ?? 'wild')
const displayValue = computed(() => {
  if (!props.card) return ''
  if (props.card.kind === 'number') return String(props.card.value)
  if (props.card.kind === 'draw_two') return '+2'
  if (props.card.kind === 'wild_draw_four') return '+4'
  if (props.card.kind === 'wild') return '✦'
  return ''
})

const accessibleLabel = computed(() => {
  if (props.faceDown) return '牌堆'
  return props.card?.label ?? '空牌位'
})
</script>

<template>
  <button
    type="button"
    class="prism-card"
    :class="[
      `is-${colorClass}`,
      {
        'is-back': faceDown,
        'is-selected': selected,
        'is-playable': playable,
        'is-compact': compact,
        'is-drawn': drawn,
      },
    ]"
    :aria-label="accessibleLabel"
    :aria-pressed="selected || undefined"
    :disabled="disabled"
    @click="emit('activate')"
  >
    <span v-if="faceDown" class="card-back" aria-hidden="true">
      <span class="back-core" />
    </span>

    <span v-else-if="card" class="card-face" aria-hidden="true">
      <span class="foil-line foil-line-one" />
      <span class="foil-line foil-line-two" />
      <span class="corner corner-top">
        <b>{{ displayValue }}</b>
        <i v-if="card.kind === 'skip'" class="mini-skip" />
        <i v-else-if="card.kind === 'reverse'" class="mini-reverse">↻</i>
      </span>
      <span class="center-orbit">
        <strong v-if="card.kind === 'number'" class="number-glyph">
          {{ card.value }}
        </strong>

        <svg v-else-if="card.kind === 'skip'" class="action-glyph" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="31" fill="none" stroke="currentColor" stroke-width="12" />
          <path d="M25 75 75 25" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="12" />
        </svg>

        <svg v-else-if="card.kind === 'reverse'" class="action-glyph reverse-glyph" viewBox="0 0 100 100">
          <path d="M22 46c3-17 17-29 35-29 10 0 19 4 25 10" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="11" />
          <path d="m77 10 9 21-23-2" fill="currentColor" />
          <path d="M78 54c-3 17-17 29-35 29-10 0-19-4-25-10" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="11" />
          <path d="m23 90-9-21 23 2" fill="currentColor" />
        </svg>

        <strong v-else-if="card.kind === 'draw_two'" class="draw-glyph">
          <span>+</span><b>2</b>
        </strong>

        <span v-else class="wild-glyph">
          <i class="wild-shard shard-red" />
          <i class="wild-shard shard-yellow" />
          <i class="wild-shard shard-green" />
          <i class="wild-shard shard-blue" />
          <b v-if="card.kind === 'wild_draw_four'">+4</b>
        </span>
      </span>
      <span class="corner corner-bottom">
        <b>{{ displayValue }}</b>
        <i v-if="card.kind === 'skip'" class="mini-skip" />
        <i v-else-if="card.kind === 'reverse'" class="mini-reverse">↻</i>
      </span>
      <span class="card-sheen" />
    </span>
  </button>
</template>

<style scoped>
.prism-card {
  --card-color: #4f8cff;
  --card-deep: #173e95;
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  display: block;
  flex: 0 0 auto;
  border: 0;
  border-radius: 13.5%;
  padding: 0;
  color: white;
  background: #080a0f;
  box-shadow:
    0 1px 0 rgb(255 255 255 / 0.42) inset,
    0 -1px 0 rgb(0 0 0 / 0.8) inset,
    0 12px 22px rgb(0 0 0 / 0.34),
    0 2px 4px rgb(0 0 0 / 0.52);
  isolation: isolate;
  cursor: pointer;
  transform: translateZ(0);
  transition: transform 180ms cubic-bezier(.2, .8, .2, 1), filter 180ms ease, opacity 180ms ease;
}

.prism-card::before {
  content: '';
  position: absolute;
  inset: 2.8%;
  z-index: 3;
  border: 1px solid rgb(255 255 255 / 0.56);
  border-radius: 12%;
  box-shadow: 0 0 0 1px rgb(0 0 0 / 0.55), 0 0 14px rgb(255 255 255 / 0.12) inset;
  pointer-events: none;
}

.prism-card:disabled { cursor: default; }
.prism-card.is-red { --card-color: #ff4d5f; --card-deep: #8f152b; }
.prism-card.is-yellow { --card-color: #ffc83d; --card-deep: #a45e05; }
.prism-card.is-green { --card-color: #35d68a; --card-deep: #087449; }
.prism-card.is-blue { --card-color: #3e8cff; --card-deep: #1644a0; }
.prism-card.is-wild { --card-color: #b7c1d9; --card-deep: #151923; }

.card-face,
.card-back {
  position: absolute;
  inset: 5.2%;
  overflow: hidden;
  border-radius: 10%;
}

.card-face {
  background:
    radial-gradient(circle at 76% 12%, rgb(255 255 255 / 0.38), transparent 25%),
    linear-gradient(145deg, var(--card-color), var(--card-deep) 66%, #070910 112%);
}

.is-wild .card-face {
  background:
    radial-gradient(circle at 50% 42%, rgb(255 255 255 / 0.2), transparent 34%),
    linear-gradient(145deg, #303747, #080a0f 70%);
}

.card-face::before {
  content: '';
  position: absolute;
  inset: 12% 8%;
  border: 1px solid rgb(255 255 255 / 0.28);
  border-radius: 50%;
  background: linear-gradient(145deg, rgb(255 255 255 / 0.22), rgb(255 255 255 / 0.04));
  box-shadow: 0 0 34px rgb(255 255 255 / 0.12) inset;
  transform: rotate(-17deg);
}

.foil-line {
  position: absolute;
  inset: -26% 47%;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, rgb(255 255 255 / 0.5), transparent);
  opacity: 0.26;
  transform: rotate(36deg);
}

.foil-line-two { transform: rotate(-42deg); opacity: 0.13; }

.corner {
  position: absolute;
  z-index: 2;
  display: grid;
  justify-items: center;
  line-height: 1;
  filter: drop-shadow(0 2px 1px rgb(0 0 0 / 0.35));
}

.corner b {
  font-family: Inter, ui-rounded, system-ui, sans-serif;
  font-size: clamp(11px, 1.55vw, 22px);
  font-weight: 950;
  letter-spacing: -0.08em;
}

.corner-top { top: 7.5%; left: 8%; }
.corner-bottom { right: 8%; bottom: 7.5%; transform: rotate(180deg); }

.mini-skip {
  width: 9px;
  aspect-ratio: 1;
  display: block;
  border: 2px solid currentColor;
  border-radius: 50%;
  transform: rotate(-42deg);
}

.mini-skip::after {
  content: '';
  width: 120%;
  height: 2px;
  display: block;
  margin: 3px 0 0 -10%;
  background: currentColor;
}

.mini-reverse { font-size: 12px; font-style: normal; font-weight: 950; }

.center-orbit {
  position: absolute;
  inset: 20% 12%;
  z-index: 2;
  display: grid;
  place-items: center;
  filter: drop-shadow(0 5px 4px rgb(0 0 0 / 0.34));
  transform: rotate(-12deg);
}

.number-glyph {
  font-family: Inter, ui-rounded, system-ui, sans-serif;
  font-size: clamp(34px, 7.4vw, 92px);
  font-weight: 950;
  line-height: 1;
  letter-spacing: -0.1em;
  text-shadow: 0 3px 0 rgb(0 0 0 / 0.18), 0 0 22px rgb(255 255 255 / 0.25);
}

.action-glyph { width: 72%; color: white; filter: drop-shadow(0 2px 0 rgb(0 0 0 / 0.16)); }
.reverse-glyph { width: 78%; }

.draw-glyph {
  display: flex;
  align-items: flex-start;
  font-family: Inter, ui-rounded, system-ui, sans-serif;
  line-height: 0.8;
}

.draw-glyph span { margin-top: 8%; font-size: clamp(18px, 3vw, 36px); }
.draw-glyph b { font-size: clamp(38px, 7vw, 88px); font-weight: 950; letter-spacing: -0.12em; }

.wild-glyph {
  position: relative;
  width: 74%;
  aspect-ratio: 1;
  display: block;
  transform: rotate(45deg);
  filter: drop-shadow(0 0 9px rgb(255 255 255 / 0.25));
}

.wild-shard {
  position: absolute;
  width: 48%;
  height: 48%;
  border: 1px solid rgb(255 255 255 / 0.5);
  box-shadow: 0 0 12px currentColor inset, 0 0 12px currentColor;
}

.shard-red { top: 0; left: 0; color: #ff4158; background: #d8223d; border-radius: 75% 10% 8% 10%; }
.shard-yellow { top: 0; right: 0; color: #ffd14b; background: #eaa510; border-radius: 10% 75% 10% 8%; }
.shard-green { bottom: 0; left: 0; color: #3be19a; background: #0ba565; border-radius: 10% 8% 10% 75%; }
.shard-blue { right: 0; bottom: 0; color: #4a9cff; background: #2867d8; border-radius: 8% 10% 75% 10%; }

.wild-glyph b {
  position: absolute;
  inset: 22%;
  z-index: 2;
  display: grid;
  place-items: center;
  border-radius: 22%;
  color: white;
  background: rgb(5 7 12 / 0.9);
  font-family: Inter, ui-rounded, system-ui, sans-serif;
  font-size: clamp(17px, 3.4vw, 42px);
  font-weight: 950;
  letter-spacing: -0.12em;
  transform: rotate(-45deg);
}

.card-sheen {
  position: absolute;
  inset: -35%;
  z-index: 4;
  background: linear-gradient(110deg, transparent 35%, rgb(255 255 255 / 0.32) 48%, transparent 58%);
  opacity: 0;
  transform: translateX(-55%);
  pointer-events: none;
}

.card-back {
  background: #080a0f url('../assets/cards/prism-card-back.png') center / cover no-repeat;
  box-shadow: 0 0 20px rgb(95 140 255 / 0.18) inset;
}

.back-core {
  position: absolute;
  inset: 20%;
  border: 1px solid rgb(255 255 255 / 0.18);
  transform: rotate(45deg);
  box-shadow: 0 0 22px rgb(91 146 255 / 0.23);
}

.is-playable:not(:disabled) { filter: saturate(1.05) brightness(1.04); }
.is-playable:not(:disabled)::after {
  content: '';
  position: absolute;
  inset: -4px;
  z-index: -1;
  border-radius: 15%;
  background: linear-gradient(135deg, rgb(255 255 255 / 0.55), var(--card-color), transparent 70%);
  opacity: 0.64;
  filter: blur(5px);
}

.is-selected {
  transform: translateY(-15px) scale(1.035);
  filter: saturate(1.14) brightness(1.12);
}

.is-selected .card-sheen { animation: card-sheen 800ms ease-out; }
.is-drawn { animation: drawn-card 700ms cubic-bezier(.17, .84, .24, 1); }
.is-compact .corner b { font-size: clamp(9px, 1.1vw, 15px); }
.is-compact .mini-skip { width: 7px; border-width: 1.5px; }

@media (hover: hover) {
  .is-playable:not(:disabled):hover { transform: translateY(-10px) rotate(-1deg); }
  .is-playable.is-selected:not(:disabled):hover { transform: translateY(-16px) scale(1.035); }
}

@keyframes card-sheen { to { opacity: 0.7; transform: translateX(55%); } }
@keyframes drawn-card {
  0% { opacity: 0; transform: translateY(-60px) rotate(8deg) scale(0.82); }
  70% { opacity: 1; transform: translateY(4px) rotate(-1deg) scale(1.03); }
  100% { transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  .prism-card { transition: none; }
  .is-drawn, .is-selected .card-sheen { animation: none; }
}
</style>
