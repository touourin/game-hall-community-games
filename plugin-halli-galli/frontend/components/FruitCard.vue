<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'
import type { FruitCardView } from '../types'

type SymbolPosition = { x: number; y: number; scale: number; rotate?: number }

const props = withDefaults(defineProps<{
  card?: FruitCardView | null
  faceDown?: boolean
  compact?: boolean
  justRevealed?: boolean
  decorative?: boolean
}>(), {
  card: null,
  faceDown: false,
  compact: false,
  justRevealed: false,
  decorative: false,
})

const layouts: Record<number, SymbolPosition[]> = {
  1: [{ x: 50, y: 61, scale: 1.18 }],
  2: [{ x: 34, y: 40, scale: .76, rotate: -5 }, { x: 66, y: 81, scale: .76, rotate: 5 }],
  3: [{ x: 31, y: 39, scale: .67 }, { x: 69, y: 39, scale: .67 }, { x: 50, y: 81, scale: .67 }],
  4: [{ x: 31, y: 39, scale: .62 }, { x: 69, y: 39, scale: .62 }, { x: 31, y: 82, scale: .62 }, { x: 69, y: 82, scale: .62 }],
  5: [{ x: 29, y: 35, scale: .53 }, { x: 71, y: 35, scale: .53 }, { x: 50, y: 61, scale: .53 }, { x: 29, y: 87, scale: .53 }, { x: 71, y: 87, scale: .53 }],
}

const symbols = computed(() => layouts[props.card?.fruitCount ?? 1] ?? layouts[1])
const cardStyle = computed<CSSProperties>(() => ({
  '--fruit-base': props.card?.palette.base ?? '#d6b56b',
  '--fruit-dark': props.card?.palette.dark ?? '#7b5725',
  '--fruit-light': props.card?.palette.light ?? '#fff1a8',
}))

function symbolTransform(position: SymbolPosition): string {
  return `translate(${position.x} ${position.y}) rotate(${position.rotate ?? 0}) scale(${position.scale})`
}
</script>

<template>
  <article
    class="fruit-card"
    :class="{ compact, 'face-down': faceDown || !card, revealed: justRevealed }"
    :style="cardStyle"
    :data-card-face="card?.faceId ?? 'back'"
    :data-fruit="card?.fruitId ?? 'hidden'"
    :data-fruit-count="card?.fruitCount ?? 0"
    :aria-label="decorative ? undefined : (faceDown || !card ? '背面朝下的水果牌' : card.altZh)"
    :aria-hidden="decorative ? 'true' : undefined"
  >
    <template v-if="faceDown || !card">
      <div class="back-frame">
        <span class="back-ring ring-one" />
        <span class="back-ring ring-two" />
        <span class="back-clapper" />
      </div>
    </template>
    <template v-else>
      <span class="corner-number">{{ card.fruitCount }}</span>
      <svg class="fruit-field" viewBox="0 0 100 122" aria-hidden="true">
        <g
          v-for="(position, index) in symbols"
          :key="index"
          class="fruit-symbol"
          :transform="symbolTransform(position)"
        >
          <g v-if="card.fruitId === 'banana'" class="banana-symbol">
            <path class="fruit-main" d="M-20-11c5 22 19 31 38 22-9 15-28 20-41 8-9-8-11-21-8-34z" />
            <path class="fruit-highlight" d="M-23-8c6 15 17 23 30 21-9 4-20 1-27-8-4-5-5-9-3-13z" />
            <path class="fruit-stroke" d="M-20-11c5 22 19 31 38 22-9 15-28 20-41 8-9-8-11-21-8-34z" />
            <path class="fruit-dark-fill" d="M-31-16l8-5 6 8-7 5zM15 9l8-1 2 5-7 4z" />
          </g>
          <g v-else-if="card.fruitId === 'strawberry'" class="strawberry-symbol">
            <path class="fruit-main" d="M0-22c17-8 29 5 22 19C16 10 7 22 0 28-7 22-16 10-22-3c-7-14 5-27 22-19z" />
            <path class="fruit-stroke" d="M0-22c17-8 29 5 22 19C16 10 7 22 0 28-7 22-16 10-22-3c-7-14 5-27 22-19z" />
            <path class="leaf-fill" d="M0-23l-9-9 9 3 6-9 2 10 10-1-9 8z" />
            <g class="seed-fill">
              <ellipse cx="-9" cy="-7" rx="2" ry="3"/><ellipse cx="8" cy="-8" rx="2" ry="3"/>
              <ellipse cx="0" cy="3" rx="2" ry="3"/><ellipse cx="-8" cy="11" rx="2" ry="3"/><ellipse cx="8" cy="11" rx="2" ry="3"/>
            </g>
            <path class="fruit-highlight" d="M-14-12c-6 8 0 19 7 27-2-12 0-22 8-32-6-2-11 0-15 5z" />
          </g>
          <g v-else-if="card.fruitId === 'lime'" class="lime-symbol">
            <circle class="fruit-main" r="27" />
            <circle class="fruit-stroke" r="27" />
            <circle class="citrus-core" r="20" />
            <circle class="citrus-center" r="3" />
            <path class="citrus-line" d="M0-20V-3M0 3V20M-20 0H-3M3 0H20M-14-14l12 12M2 2l12 12M14-14L2-2M-2 2l-12 12" />
            <path class="fruit-highlight" d="M-14-18a22 22 0 0 0-6 17" />
          </g>
          <g v-else class="plum-symbol">
            <ellipse class="fruit-main" cx="0" cy="3" rx="23" ry="28" transform="rotate(12)" />
            <ellipse class="fruit-stroke" cx="0" cy="3" rx="23" ry="28" transform="rotate(12)" />
            <path class="leaf-fill" d="M1-24c7-12 20-12 25-3-9 7-17 8-25 3z" />
            <path class="stem-line" d="M0-22c2-6 5-9 9-12" />
            <ellipse class="fruit-highlight" cx="-9" cy="-7" rx="6" ry="12" transform="rotate(25)" />
            <path class="plum-seam" d="M2-20c-7 14-7 31 1 45" />
          </g>
        </g>
      </svg>
      <footer>{{ card.labelZh }}</footer>
    </template>
  </article>
</template>

<style scoped>
.fruit-card{--fruit-base:#d6b56b;--fruit-dark:#7b5725;--fruit-light:#fff1a8;position:relative;isolation:isolate;width:100%;aspect-ratio:56/87;overflow:hidden;border:clamp(1px,.16vw,2px) solid color-mix(in srgb,var(--fruit-dark) 55%,#b9ad94);border-radius:clamp(7px,1vw,13px);color:var(--fruit-dark);background:linear-gradient(145deg,#fffefa 0%,#f8f2e7 62%,#ece2d1 100%);box-shadow:inset 0 0 0 4px rgba(255,255,255,.68),inset 0 0 0 6px color-mix(in srgb,var(--fruit-base) 18%,transparent),0 7px 15px rgba(0,0,0,.26);transform-style:preserve-3d}.fruit-card::after{content:"";position:absolute;z-index:-1;inset:5%;border:1px solid color-mix(in srgb,var(--fruit-dark) 34%,transparent);border-radius:8px;pointer-events:none}.corner-number{position:absolute;z-index:2;top:4%;left:8%;font:900 clamp(16px,2.1vw,32px)/1 Georgia,"Times New Roman",serif;text-shadow:0 1px #fff}.fruit-field{position:absolute;inset:12% 5% 16%;width:90%;height:72%;overflow:visible}.fruit-symbol{filter:drop-shadow(0 2px 1px rgba(0,0,0,.24))}.fruit-main{fill:var(--fruit-base)}.fruit-dark-fill,.leaf-fill{fill:var(--fruit-dark)}.fruit-highlight{fill:var(--fruit-light);stroke:none;opacity:.78}.fruit-stroke{fill:none;stroke:var(--fruit-dark);stroke-width:3;stroke-linejoin:round;stroke-linecap:round}.seed-fill{fill:#ffe7be}.citrus-core{fill:var(--fruit-light);stroke:var(--fruit-dark);stroke-width:2}.citrus-center{fill:var(--fruit-dark)}.citrus-line,.stem-line,.plum-seam{fill:none;stroke:var(--fruit-dark);stroke-width:2.2;stroke-linecap:round}.plum-seam{opacity:.55}.fruit-card footer{position:absolute;right:10%;bottom:6%;left:10%;overflow:hidden;padding:3% 2%;border-radius:999px;color:#fff;background:var(--fruit-dark);font-size:clamp(7px,.85vw,13px);font-weight:900;line-height:1;text-align:center;white-space:nowrap;box-shadow:inset 0 1px rgba(255,255,255,.28)}.face-down{border-color:#bd9451;background:repeating-linear-gradient(135deg,#1f5149 0 9px,#285f55 9px 12px);box-shadow:inset 0 0 0 5px #133d37,inset 0 0 0 7px #c7a65f,0 7px 15px rgba(0,0,0,.3)}.face-down::after{border-color:rgba(242,211,137,.42)}.back-frame{position:absolute;inset:14%;display:grid;place-items:center;border:2px solid #d0ae64;border-radius:12px;background:radial-gradient(circle,#2f6a5f,#183f39 70%);box-shadow:inset 0 0 18px rgba(0,0,0,.35)}.back-ring{position:absolute;border:clamp(2px,.4vw,5px) solid #d6b56b;border-radius:50%}.ring-one{width:66%;aspect-ratio:1}.ring-two{width:38%;aspect-ratio:1}.back-clapper{position:absolute;top:49%;width:15%;aspect-ratio:1;border-radius:50%;background:#e0c278;box-shadow:0 0 0 4px #765525}.compact{border-radius:6px}.compact .corner-number{font-size:clamp(12px,1.2vw,18px)}.compact footer{font-size:clamp(5px,.55vw,8px)}.revealed{animation:fruit-card-reveal 180ms cubic-bezier(.2,.75,.25,1) both}@keyframes fruit-card-reveal{0%{opacity:.35;transform:perspective(500px) rotateY(82deg) scale(.94)}55%{opacity:1;transform:perspective(500px) rotateY(-7deg) scale(1.02)}100%{transform:perspective(500px) rotateY(0) scale(1)}}@media(prefers-reduced-motion:reduce){.revealed{animation:fruit-card-fade 80ms linear both}@keyframes fruit-card-fade{from{opacity:.3}to{opacity:1}}}
</style>
