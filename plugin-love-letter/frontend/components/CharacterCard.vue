<script setup lang="ts">
import { computed } from 'vue'
import type { CardCatalogItem, LoveCard } from '../types'

const props = withDefaults(defineProps<{
  card?: LoveCard | CardCatalogItem | null
  concealed?: boolean
  compact?: boolean
  mini?: boolean
  selectable?: boolean
  disabled?: boolean
  selected?: boolean
  count?: number | null
  ariaLabel?: string
}>(), {
  card: null,
  concealed: false,
  compact: false,
  mini: false,
  selectable: false,
  disabled: false,
  selected: false,
  count: null,
  ariaLabel: '',
})

const emit = defineEmits<{ select: [] }>()
const displayValue = computed(() => props.card?.value === 7.5 ? '7½' : String(props.card?.value ?? ''))
const label = computed(() => props.ariaLabel || (
  props.concealed ? '一张牌背朝上的隐藏角色牌' : `${props.card?.nameZh}，点数 ${displayValue.value}`
))
</script>

<template>
  <component
    :is="selectable ? 'button' : 'article'"
    class="character-card"
    :class="{
      'is-concealed': concealed,
      'is-compact': compact,
      'is-mini': mini,
      'is-selectable': selectable,
      'is-selected': selected,
      'is-disabled': disabled,
    }"
    :type="selectable ? 'button' : undefined"
    :disabled="selectable ? disabled : undefined"
    :aria-label="label"
    :aria-pressed="selectable ? selected : undefined"
    :data-card-type="card?.typeId ?? 'back'"
    :data-card-value="card?.value ?? undefined"
    :style="card ? { '--card-accent': card.color } : undefined"
    @click="selectable && !disabled && emit('select')"
  >
    <template v-if="concealed || !card">
      <span class="back-filigree" aria-hidden="true">
        <i class="back-diamond" />
        <i class="wax-seal">情</i>
        <i class="back-flourish top">❦</i>
        <i class="back-flourish bottom">❦</i>
      </span>
      <strong class="back-title">密封宫廷</strong>
      <small class="back-subtitle">SEALED LETTER</small>
    </template>
    <template v-else>
      <span class="card-grain" aria-hidden="true" />
      <span class="corner-value corner-top">{{ displayValue }}</span>
      <span class="corner-value corner-bottom">{{ displayValue }}</span>
      <span v-if="count" class="edition-count">×{{ count }}</span>
      <header class="card-title">
        <small>{{ card.nameEn }}</small>
        <strong>{{ card.nameZh }}</strong>
      </header>
      <span class="portrait" aria-hidden="true">
        <i class="halo one" />
        <i class="halo two" />
        <b>{{ card.symbol }}</b>
        <em>{{ card.motif }}</em>
      </span>
      <p class="card-effect">{{ card.effectZh }}</p>
      <footer>
        <span>LOVE LETTER</span>
        <b>{{ card.typeId === 'queen' ? '项目扩展' : '宫廷角色' }}</b>
      </footer>
    </template>
    <span v-if="selected" class="selected-ribbon">已选择</span>
  </component>
</template>

<style scoped>
.character-card {
  --card-accent: #8f1d3d;
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  width: clamp(124px, 9.2vw, 154px);
  aspect-ratio: 2 / 3;
  padding: 11px 12px 9px;
  overflow: hidden;
  border: 2px solid #d8b770;
  border-radius: 13px;
  color: #30161e;
  background:
    linear-gradient(135deg, transparent 9px, rgba(125, 77, 44, .08) 10px, transparent 11px) 0 0 / 22px 22px,
    radial-gradient(circle at 50% 43%, #fffdf4 0 28%, #f8edda 67%, #ead5ae 100%);
  box-shadow: 0 14px 26px rgba(18, 6, 12, .42), inset 0 0 0 3px #fff8e8, inset 0 0 0 5px var(--card-accent);
  font: inherit;
  text-align: left;
  isolation: isolate;
  transform-origin: center 85%;
}
.character-card::before,
.character-card::after {
  content: '';
  position: absolute;
  z-index: 0;
  width: 44px;
  height: 44px;
  border: 1px solid color-mix(in srgb, var(--card-accent) 70%, #d8b770);
  transform: rotate(45deg);
  opacity: .42;
}
.character-card::before { left: -24px; top: -24px; }
.character-card::after { right: -24px; bottom: -24px; }
.card-grain { position: absolute; inset: 6px; z-index: -1; border: 1px solid rgba(98, 48, 55, .28); border-radius: 8px; }
.corner-value { position: absolute; z-index: 2; color: var(--card-accent); font: 900 20px/1 Georgia, serif; }
.corner-top { left: 12px; top: 11px; }
.corner-bottom { right: 12px; bottom: 10px; transform: rotate(180deg); }
.edition-count { position: absolute; right: 12px; top: 10px; color: #765b42; font: 700 10px/1.2 system-ui; }
.card-title { position: relative; z-index: 1; display: grid; justify-items: center; gap: 1px; padding: 0 23px; text-align: center; }
.card-title small { color: #896f58; font: 600 8px/1.1 Georgia, serif; letter-spacing: .16em; text-transform: uppercase; }
.card-title strong { color: var(--card-accent); font: 800 clamp(15px, 1.25vw, 20px)/1.15 'Noto Serif SC', STSong, serif; letter-spacing: .12em; }
.portrait { align-self: center; justify-self: center; position: relative; display: grid; place-items: center; width: 76%; aspect-ratio: 1; border: 1px solid #d5bb82; border-radius: 50%; background: radial-gradient(circle, #fffaf0 0 34%, color-mix(in srgb, var(--card-accent) 16%, #efe0c5) 35% 66%, #f6e9d1 67%); box-shadow: inset 0 0 0 4px #fbf1dc, 0 4px 12px rgba(72, 31, 37, .22); }
.portrait::before { content: ''; position: absolute; inset: 8%; border: 1px dashed color-mix(in srgb, var(--card-accent) 50%, #b89961); border-radius: 50%; }
.portrait b { z-index: 2; color: var(--card-accent); font: 900 clamp(30px, 3.3vw, 46px)/1 'Noto Serif SC', STSong, serif; text-shadow: 0 2px #fff; }
.portrait em { position: absolute; bottom: 11%; z-index: 2; padding: 2px 7px; border-radius: 9px; color: #fff; background: var(--card-accent); font: normal 700 8px/1.2 system-ui; letter-spacing: .12em; }
.halo { position: absolute; border: 1px solid var(--card-accent); border-radius: 50%; opacity: .24; }
.halo.one { inset: -5px; border-style: dotted; }
.halo.two { inset: 17%; border-left-color: transparent; border-right-color: transparent; transform: rotate(25deg); }
.card-effect { position: relative; z-index: 1; align-self: center; margin: 3px 2px; display: -webkit-box; overflow: hidden; color: #4e3840; font: 600 clamp(8px, .72vw, 10px)/1.35 system-ui, sans-serif; text-align: center; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
footer { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid rgba(103, 68, 48, .25); padding: 5px 3px 0; color: #876e58; font: 700 6px/1 system-ui; letter-spacing: .09em; }
footer b { color: var(--card-accent); font-size: 7px; }
.is-selectable { cursor: pointer; transition: transform .18s ease, filter .18s ease, box-shadow .18s ease; }
.is-selectable:hover:not(:disabled), .is-selectable:focus-visible { z-index: 6; outline: none; transform: translateY(-13px) scale(1.025); box-shadow: 0 22px 38px rgba(18, 6, 12, .52), 0 0 0 4px #7dd3fc, inset 0 0 0 3px #fff8e8, inset 0 0 0 5px var(--card-accent); }
.is-selected { transform: translateY(-17px) scale(1.035); box-shadow: 0 24px 42px rgba(18, 6, 12, .55), 0 0 0 4px #f7d271, inset 0 0 0 3px #fff8e8, inset 0 0 0 5px var(--card-accent); }
.is-disabled { filter: grayscale(.7) brightness(.7); cursor: not-allowed; }
.selected-ribbon { position: absolute; left: 50%; bottom: 13px; z-index: 5; transform: translateX(-50%); padding: 4px 9px; border-radius: 999px; color: #2d1820; background: #f7d271; font: 800 9px/1 system-ui; white-space: nowrap; }
.is-compact { width: 74px; padding: 6px; border-radius: 8px; }
.is-compact .card-title strong { font-size: 11px; }
.is-compact .card-title small, .is-compact .card-effect, .is-compact footer, .is-compact .portrait em, .is-compact .corner-bottom { display: none; }
.is-compact .portrait { width: 84%; }
.is-compact .portrait b { font-size: 25px; }
.is-compact .corner-value { left: 7px; top: 7px; font-size: 14px; }
.is-mini { width: 30px; padding: 2px; border-radius: 4px; border-width: 1px; box-shadow: 0 4px 8px rgba(18, 6, 12, .35), inset 0 0 0 2px var(--card-accent); }
.is-mini .card-title, .is-mini .card-effect, .is-mini footer, .is-mini .corner-bottom, .is-mini .edition-count { display: none; }
.is-mini .portrait { width: 92%; }
.is-mini .portrait b { font-size: 13px; }
.is-mini .portrait em, .is-mini .halo { display: none; }
.is-mini .corner-value { left: 4px; top: 4px; font-size: 8px; }
.is-concealed { grid-template-rows: 1fr auto auto; place-items: center; color: #f8e8c3; background: repeating-linear-gradient(45deg, rgba(212, 168, 75, .12) 0 2px, transparent 2px 9px), radial-gradient(circle at center, #4c1e30, #251019 72%); box-shadow: 0 14px 26px rgba(18, 6, 12, .48), inset 0 0 0 3px #260e17, inset 0 0 0 5px #c99c49; }
.is-concealed::before, .is-concealed::after { border-color: #d6a84b; opacity: .7; }
.back-filigree { position: relative; align-self: end; display: grid; place-items: center; width: 72%; aspect-ratio: 1; border: 1px solid rgba(231, 196, 118, .65); transform: rotate(45deg); }
.back-diamond { position: absolute; inset: 15%; border: 1px solid rgba(231, 196, 118, .42); }
.wax-seal { z-index: 2; display: grid; place-items: center; width: 49%; aspect-ratio: 1; border: 3px double #f1c86d; border-radius: 50%; color: #ffe9aa; background: radial-gradient(circle at 35% 30%, #d94a68, #8e1738 68%); box-shadow: 0 5px 12px #17060b; font: normal 900 21px/1 'Noto Serif SC', serif; transform: rotate(-45deg); }
.back-flourish { position: absolute; color: #d8ae59; font-style: normal; transform: rotate(-45deg); }
.back-flourish.top { top: -3px; left: -3px; }.back-flourish.bottom { right: -3px; bottom: -3px; transform: rotate(135deg); }
.back-title { color: #f2d48f; font: 800 12px/1.1 'Noto Serif SC', serif; letter-spacing: .16em; }
.back-subtitle { color: rgba(248, 232, 195, .62); font: 600 6px/1 system-ui; letter-spacing: .23em; }
.is-mini .back-title, .is-mini .back-subtitle { display: none; }
.is-mini .back-filigree { width: 74%; }
.is-mini .wax-seal { border-width: 1px; font-size: 8px; }
@media (max-width: 760px) {
  .character-card:not(.is-compact):not(.is-mini) { width: 112px; }
}
@media (prefers-reduced-motion: reduce) {
  .is-selectable { transition: outline-color .01ms; }
  .is-selectable:hover:not(:disabled), .is-selectable:focus-visible, .is-selected { transform: none; }
}
</style>
