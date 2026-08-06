<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

import type { MarketView } from '../types'

import futuresTrack from '../../image/price-track-futures.svg'
import spotTrack from '../../image/price-track-spot.svg'

const props = defineProps<{
  markets: MarketView[]
  ladder: number[]
  flashes?: Record<string, 'up' | 'down'>
}>()

const railScroll = ref<HTMLDivElement | null>(null)

onMounted(async () => {
  await nextTick()
  const scroller = railScroll.value
  if (!scroller || !props.markets.length) return
  const averageIndex = props.markets.reduce(
    (total, market) => total + market.spotIndex + market.currentIndex,
    0,
  ) / (props.markets.length * 2)
  const markerCenter = (averageIndex / Math.max(1, props.ladder.length - 1)) * scroller.scrollWidth
  scroller.scrollLeft = Math.max(0, markerCenter - scroller.clientWidth / 2)
})

function markerStyle(index: number, row: number) {
  return {
    left: `${(index / Math.max(1, props.ladder.length - 1)) * 100}%`,
    top: `${20 + row * 20}%`,
  }
}
</script>

<template>
  <section class="price-board" aria-label="现货与期货价格图板">
    <header><b>双轨价格图板</b><small>牌只移动现货 · 成交只移动期货</small></header>
    <div ref="railScroll" class="rail-scroll">
      <div class="rail-stack">
        <div class="rail spot">
          <img :src="spotTrack" alt="现货价格条">
          <span
            v-for="(market, row) in markets"
            :key="`spot-${market.commodity}`"
            class="marker"
            :class="[market.commodity, flashes?.[`spot-${market.commodity}`]]"
            :style="markerStyle(market.spotIndex, row)"
            :title="`${market.name}现货 ${market.spotPrice}`"
          >{{ market.name.slice(0, 1) }}<i>{{ market.spotPrice }}</i></span>
        </div>
        <div class="rail futures">
          <img :src="futuresTrack" alt="期货价格条">
          <span
            v-for="(market, row) in markets"
            :key="`futures-${market.commodity}`"
            class="marker"
            :class="[market.commodity, flashes?.[`futures-${market.commodity}`]]"
            :style="markerStyle(market.currentIndex, row)"
            :title="`${market.name}期货 ${market.currentPrice}`"
          >{{ market.name.slice(0, 1) }}<i>{{ market.currentPrice }}</i></span>
        </div>
      </div>
    </div>
    <footer>
      <span v-for="market in markets" :key="market.commodity" :style="{ '--market': market.color }">
        <i />{{ market.name }}：现 {{ market.spotPrice }} / 期 {{ market.currentPrice }}
      </span>
    </footer>
  </section>
</template>

<style scoped>
.price-board { min-width: 0; display: grid; gap: 14px; border: 1px solid var(--line); border-radius: 19px; padding: clamp(16px, 1.7vw, 24px); background: color-mix(in srgb, var(--surface-elevated) 52%, transparent); }.price-board > header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }.price-board header b { color: var(--gold); font-size: 12px; letter-spacing: .08em; }.price-board header small { color: var(--muted); font-size: 9px; }.rail-scroll { min-width: 0; overflow-x: hidden; overscroll-behavior-inline: contain; scrollbar-width: thin; }.rail-stack { width: 100%; display: grid; gap: 12px; }.rail { position: relative; width: 100%; height: clamp(190px, 16vw, 238px); overflow: hidden; border: 1px solid color-mix(in srgb, var(--gold) 28%, var(--line)); border-radius: 15px; background: var(--surface-inset); }.rail > img { width: 100%; height: 100%; display: block; object-fit: fill; opacity: .9; }.marker { position: absolute; z-index: 2; width: 30px; height: 30px; display: grid; place-items: center; transform: translate(-50%, -50%); border: 2px solid white; border-radius: 50%; color: white; background: #728392; box-shadow: 0 5px 14px rgb(0 0 0 / 38%); font-size: 9px; font-weight: 900; transition: left .42s cubic-bezier(.2,.8,.2,1); }.marker i { position: absolute; left: 50%; top: 100%; transform: translateX(-50%); border-radius: 5px; padding: 2px 4px; color: #fff; background: rgb(16 28 39 / 88%); font-size: 7px; font-style: normal; white-space: nowrap; }.marker.oil { background: #a85c35; }.marker.gold { background: #c89b28; }.marker.cotton { background: #609b6d; }.marker.copper { background: #ad6538; }.marker.up { animation: marker-up .7s ease; }.marker.down { animation: marker-down .7s ease; }.price-board footer { display: flex; flex-wrap: wrap; gap: 7px 14px; color: var(--muted); font-size: 9px; }.price-board footer span { display: inline-flex; align-items: center; gap: 5px; }.price-board footer i { width: 8px; height: 8px; border-radius: 50%; background: var(--market); }
@keyframes marker-up { 45% { transform: translate(-50%, -65%) scale(1.18); box-shadow: 0 0 0 8px rgb(80 200 120 / 18%); } } @keyframes marker-down { 45% { transform: translate(-50%, -35%) scale(1.18); box-shadow: 0 0 0 8px rgb(220 80 90 / 18%); } }
@media (prefers-reduced-motion: reduce) { .marker { transition: none; }.marker.up,.marker.down { animation: none; } }
@media (max-width: 700px) { .price-board { gap: 10px; padding: 11px; }.price-board > header { align-items: flex-start; flex-direction: column; gap: 3px; }.rail-scroll { overflow-x: auto; }.rail-stack { width: 1040px; }.rail { height: 178px; }.marker { width: 27px; height: 27px; } }
</style>
