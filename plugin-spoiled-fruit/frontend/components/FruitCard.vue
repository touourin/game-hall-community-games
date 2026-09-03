<script setup lang="ts">
import { computed } from 'vue'
import { ShieldCheck } from '@lucide/vue'
import { cardArt, cardBackArt, effectAccent } from '../catalog'
import type { FruitCardView } from '../types'

const props = withDefaults(defineProps<{
  card?: FruitCardView | null
  hidden?: boolean
  protected?: boolean
  compact?: boolean
  selected?: boolean
  disabled?: boolean
  label?: string
}>(), {
  card: null,
  hidden: false,
  protected: false,
  compact: false,
  selected: false,
  disabled: false,
  label: '',
})

defineEmits<{ activate: [] }>()

const accent = computed(() => (
  props.card ? effectAccent[props.card.effectId] ?? '#d89b3c' : '#d89b3c'
))
const accessibleLabel = computed(() => {
  if (props.label) return props.label
  if (props.hidden || !props.card) return '一张牌背'
  return `${props.card.cardCode} 号 ${props.card.nameZh}，${props.card.effectLabelZh}`
})
</script>

<template>
  <button
    type="button"
    class="fruit-card"
    :class="{
      hidden,
      compact,
      selected,
      protected,
      'old-maid': card?.kind === 'old_maid',
    }"
    :style="{ '--card-accent': accent }"
    :disabled="disabled"
    :aria-label="accessibleLabel"
    :aria-pressed="selected || undefined"
    @click="$emit('activate')"
  >
    <template v-if="hidden || !card">
      <img class="card-back" :src="cardBackArt" alt="" draggable="false">
      <span v-if="protected" class="shield-mark" aria-hidden="true"><ShieldCheck :size="14" /></span>
    </template>
    <template v-else>
      <span class="card-code top">{{ card.cardCode }}</span>
      <span class="card-code bottom">{{ card.cardCode }}</span>
      <img class="fruit-art" :src="cardArt[card.catalogId]" alt="" draggable="false">
      <span class="fruit-copy">
        <b>{{ card.nameZh }}</b>
        <small>{{ card.effectLabelZh }}</small>
      </span>
      <span v-if="protected" class="shield-mark" aria-hidden="true"><ShieldCheck :size="14" /></span>
    </template>
  </button>
</template>

<style scoped>
.fruit-card {
  --card-accent: #d89b3c;
  position: relative;
  width: 92px;
  flex: 0 0 92px;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  border: 2px solid color-mix(in srgb, var(--card-accent) 68%, #f6e9cf);
  border-radius: 12px;
  padding: 0;
  color: #281b32;
  background:
    radial-gradient(circle at 50% 34%, color-mix(in srgb, var(--card-accent) 12%, #fff8e8), #f6e9cf 72%),
    #f6e9cf;
  box-shadow: 0 9px 18px #160e19a6, inset 0 0 0 3px #fff5da99;
  cursor: pointer;
  isolation: isolate;
  transition: transform .18s ease, filter .18s ease, box-shadow .18s ease;
}
.fruit-card:disabled { cursor: default; }
.fruit-card:not(:disabled):hover { transform: translateY(-7px); filter: brightness(1.05); }
.fruit-card.selected { transform: translateY(-12px); box-shadow: 0 12px 24px color-mix(in srgb, var(--card-accent) 45%, #160e19), 0 0 0 4px #f6e9cf; }
.fruit-card.old-maid { background: radial-gradient(circle at 50% 36%, #78506b 0, #352039 65%, #211527 100%); color: #fff1d3; }
.card-back { width: 100%; height: 100%; display: block; object-fit: cover; }
.fruit-art { position: absolute; inset: 13% 8% 29%; width: 84%; height: 58%; object-fit: contain; filter: drop-shadow(0 5px 4px #2c182c42); pointer-events: none; }
.fruit-copy { position: absolute; inset: auto 6px 7px; display: grid; gap: 2px; border-top: 1px solid color-mix(in srgb, var(--card-accent) 62%, transparent); padding-top: 5px; text-align: center; }
.fruit-copy b { overflow: hidden; font-family: "Songti SC", "STSong", serif; font-size: 13px; line-height: 1; text-overflow: ellipsis; white-space: nowrap; }
.fruit-copy small { overflow: hidden; color: color-mix(in srgb, currentColor 68%, var(--card-accent)); font-size: 8px; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }
.card-code { position: absolute; z-index: 2; font-size: 9px; font-weight: 1000; line-height: 1; }
.card-code.top { top: 7px; left: 7px; }
.card-code.bottom { right: 7px; bottom: 7px; transform: rotate(180deg); }
.shield-mark { position: absolute; z-index: 4; top: 5px; right: 5px; width: 25px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid #f6e9cf; border-radius: 50%; color: #f6e9cf; background: #865735df; box-shadow: 0 3px 9px #281b32a8; }
.fruit-card.compact { width: 42px; flex-basis: 42px; border-width: 1px; border-radius: 6px; box-shadow: 0 4px 9px #160e198f; }
.fruit-card.compact .fruit-copy,.fruit-card.compact .card-code { display: none; }
.fruit-card.compact .fruit-art { inset: 12% 4%; width: 92%; height: 76%; }
.fruit-card.compact .shield-mark { top: 2px; right: 2px; width: 18px; }
@media (max-width: 720px) {
  .fruit-card { width: 72px; flex-basis: 72px; border-radius: 9px; }
  .fruit-copy b { font-size: 11px; }
  .fruit-copy small { font-size: 7px; }
}
@media (prefers-reduced-motion: reduce) {
  .fruit-card { transition: none; }
}
</style>
