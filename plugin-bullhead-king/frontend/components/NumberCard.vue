<script setup lang="ts">
import { computed } from 'vue'
import type { BullCard } from '../types'

const props = withDefaults(defineProps<{
  card?: BullCard | null
  interactive?: boolean
  selected?: boolean
  disabled?: boolean
  faceDown?: boolean
  compact?: boolean
  ownerLabel?: string
}>(), {
  card: null,
  interactive: false,
  selected: false,
  disabled: false,
  faceDown: false,
  compact: false,
  ownerLabel: '',
})

const emit = defineEmits<{ select: [] }>()
const element = computed(() => props.interactive ? 'button' : 'div')
const cardLabel = computed(() => {
  if (props.faceDown || !props.card) {
    return props.ownerLabel ? `${props.ownerLabel} 已锁定一张牌` : '背面朝上的数字牌'
  }
  return `${props.card.number}，${props.card.bullheads} 牛头分`
})
</script>

<template>
  <component
    :is="element"
    class="number-card"
    :class="[
      card ? `tier-${card.tier}` : 'tier-back',
      { interactive, selected, disabled, facedown: faceDown, compact },
    ]"
    :type="interactive ? 'button' : undefined"
    :disabled="interactive ? disabled : undefined"
    :aria-pressed="interactive ? selected : undefined"
    :aria-label="cardLabel"
    :data-card-id="card?.id"
    :data-card-number="card?.number"
    @click="interactive && !disabled && emit('select')"
  >
    <template v-if="!faceDown && card">
      <span class="corner-number">{{ card.number }}</span>
      <strong>{{ card.number }}</strong>
      <span class="bull-row" :aria-label="`${card.bullheads} 牛头分`">
        <i v-for="pip in card.bullheads" :key="pip" class="bull-pip" aria-hidden="true" />
      </span>
      <small>{{ card.bullheads }} 分</small>
    </template>
    <template v-else>
      <span class="back-mark" aria-hidden="true"><i /><b /><i /></span>
      <small>LOCKED</small>
    </template>
  </component>
</template>

<style scoped>
.number-card {
  --card-ink: #214d4d;
  --card-accent: #5f8f82;
  position: relative;
  width: clamp(54px, 6.3vw, 82px);
  aspect-ratio: 68 / 96;
  display: grid;
  grid-template-rows: 1fr auto auto;
  align-items: center;
  justify-items: center;
  flex: 0 0 auto;
  overflow: hidden;
  border: 2px solid color-mix(in srgb, var(--card-ink) 72%, #101c1e);
  border-radius: clamp(7px, 1vw, 10px);
  padding: 8px 4px 6px;
  color: var(--card-ink);
  background:
    linear-gradient(145deg, rgb(255 255 255 / .56), transparent 34%),
    repeating-linear-gradient(0deg, transparent 0 3px, rgb(44 38 24 / .025) 3px 4px),
    #fff8e9;
  box-shadow:
    inset 0 0 0 3px #fff8e9,
    inset 0 0 0 4px color-mix(in srgb, var(--card-accent) 62%, transparent),
    0 7px 16px rgb(0 0 0 / .2);
  font: inherit;
  transform-origin: 50% 84%;
}
.number-card::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid color-mix(in srgb, var(--card-accent) 52%, transparent);
  border-radius: 6px;
  pointer-events: none;
}
.number-card strong {
  align-self: end;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: clamp(27px, 3.7vw, 48px);
  line-height: .95;
  letter-spacing: -.06em;
}
.number-card .corner-number {
  position: absolute;
  top: 6px;
  left: 8px;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 9px;
  font-weight: 800;
}
.number-card small {
  position: relative;
  z-index: 1;
  font-size: 7px;
  font-weight: 900;
  letter-spacing: .08em;
}
.bull-row {
  min-height: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 2px 0 1px;
}
.bull-pip {
  position: relative;
  width: 7px;
  height: 8px;
  display: inline-block;
  border-radius: 55% 55% 48% 48%;
  background: var(--card-accent);
}
.bull-pip::before,
.bull-pip::after {
  content: '';
  position: absolute;
  top: -2px;
  width: 5px;
  height: 4px;
  border-top: 2px solid var(--card-accent);
}
.bull-pip::before { right: 4px; border-left: 2px solid var(--card-accent); border-radius: 7px 0 0; transform: rotate(16deg); }
.bull-pip::after { left: 4px; border-right: 2px solid var(--card-accent); border-radius: 0 7px 0 0; transform: rotate(-16deg); }
.tier-double { --card-ink: #78541f; --card-accent: #d6a447; }
.tier-triple { --card-ink: #994835; --card-accent: #df7354; }
.tier-quintuple { --card-ink: #6f365f; --card-accent: #b9679b; }
.tier-royal { --card-ink: #7f281f; --card-accent: #e24d35; }
.interactive {
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
}
.interactive:hover:not(:disabled),
.interactive:focus-visible {
  transform: translateY(-8px);
  outline: 3px solid color-mix(in srgb, var(--gold, #d6a447) 70%, white);
  outline-offset: 3px;
}
.interactive.selected {
  transform: translateY(-12px) rotate(-1deg);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--gold, #d6a447) 58%, transparent), 0 16px 24px rgb(0 0 0 / .3);
}
.disabled { cursor: not-allowed; opacity: .58; }
.facedown {
  grid-template-rows: 1fr auto;
  color: #ead7aa;
  background:
    radial-gradient(circle at 50% 44%, rgb(214 164 71 / .2), transparent 30%),
    repeating-linear-gradient(45deg, transparent 0 7px, rgb(214 164 71 / .13) 7px 9px),
    #0a3437;
  border-color: #bd8e43;
  box-shadow: inset 0 0 0 3px #0a3437, inset 0 0 0 4px rgb(214 164 71 / .65), 0 7px 16px rgb(0 0 0 / .25);
}
.facedown::after { border-color: rgb(214 164 71 / .48); }
.back-mark { position: relative; width: 32px; height: 20px; display: flex; align-items: center; justify-content: center; }
.back-mark b { width: 10px; height: 12px; border-radius: 50%; background: #bd8e43; }
.back-mark i { width: 14px; height: 10px; border-top: 3px solid #bd8e43; }
.back-mark i:first-child { margin-right: -3px; border-left: 3px solid #bd8e43; border-radius: 12px 0 0; transform: rotate(12deg); }
.back-mark i:last-child { margin-left: -3px; border-right: 3px solid #bd8e43; border-radius: 0 12px 0 0; transform: rotate(-12deg); }
.compact { width: clamp(42px, 5.1vw, 62px); border-width: 1px; }
.compact strong { font-size: clamp(22px, 3vw, 35px); }
.compact .corner-number { display: none; }
.compact small { font-size: 6px; }
.compact .bull-pip { width: 6px; height: 7px; }
@media (max-width: 560px) {
  .number-card { width: clamp(44px, 13vw, 58px); }
  .number-card strong { font-size: clamp(23px, 8vw, 34px); }
  .number-card .corner-number { font-size: 8px; top: 5px; left: 6px; }
}
@media (min-width: 561px) and (max-height: 820px) {
  .number-card { width: clamp(48px, 5.4vw, 68px); }
  .number-card strong { font-size: clamp(24px, 3.2vw, 40px); }
  .compact { width: clamp(40px, 4.7vw, 56px); }
}
@media (prefers-reduced-motion: reduce) {
  .interactive { transition-duration: 0ms; }
  .interactive:hover:not(:disabled), .interactive:focus-visible, .interactive.selected { transform: none; }
}
</style>
