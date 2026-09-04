<script setup lang="ts">
import { computed } from 'vue'
import type { LoveEvent } from '../types'

const props = defineProps<{ event: LoveEvent | null }>()

const presentations: Record<string, { glyph: string; eyebrow: string }> = {
  round_deal: { glyph: '✉', eyebrow: '密封发牌' },
  draw_card: { glyph: '↓', eyebrow: '抽牌' },
  play_card: { glyph: '↑', eyebrow: '公开出牌' },
  spy_mark: { glyph: '◉', eyebrow: '间谍暗记' },
  guess_miss: { glyph: '?', eyebrow: '盘问未中' },
  guess_hit: { glyph: '!', eyebrow: '身份识破' },
  peek_hand: { glyph: '⌁', eyebrow: '烛光窥信' },
  compare_hands: { glyph: '⚖', eyebrow: '秘密比点' },
  gain_protection: { glyph: '◇', eyebrow: '侍女守护' },
  protection_expired: { glyph: '⌁', eyebrow: '守护消退' },
  force_redraw: { glyph: '↻', eyebrow: '王子重写' },
  prince_princess: { glyph: '✕', eyebrow: '公主失信' },
  chancellor_draw: { glyph: 'Ⅲ', eyebrow: '大臣筹谋' },
  chancellor_no_draw: { glyph: 'Ⅰ', eyebrow: '封存不动' },
  bottom_cards: { glyph: '⇊', eyebrow: '压回牌底' },
  trade_hands: { glyph: '⇄', eyebrow: '国王易手' },
  queen_escape: { glyph: '♛', eyebrow: '皇后防卫' },
  princess_discard: { glyph: '✕', eyebrow: '主动失信' },
  no_legal_target: { glyph: '∅', eyebrow: '无人可选' },
  round_end: { glyph: '♥', eyebrow: '本轮结算' },
  forfeit: { glyph: '↗', eyebrow: '离席' },
}
const presentation = computed(() => presentations[props.event?.kind ?? ''] ?? { glyph: '✦', eyebrow: '宫廷动向' })
</script>

<template>
  <div
    v-if="event"
    class="effect-layer"
    :class="`effect-${event.kind}`"
    :data-animation-kind="event.kind"
    role="status"
    aria-live="polite"
  >
    <div class="cinema-vignette" />
    <div class="effect-path" aria-hidden="true">
      <i class="flight-card one">{{ presentation.glyph }}</i>
      <i class="flight-card two">{{ presentation.glyph }}</i>
      <i class="energy-ring ring-one" />
      <i class="energy-ring ring-two" />
      <i class="beam" />
    </div>
    <div class="effect-caption">
      <small>{{ presentation.eyebrow }}</small>
      <strong>{{ presentation.glyph }}</strong>
      <p>{{ event.messageZh }}</p>
    </div>
  </div>
</template>

<style scoped>
.effect-layer { position: absolute; inset: 0; z-index: 90; overflow: hidden; pointer-events: none; display: grid; place-items: center; }
.cinema-vignette { position: absolute; inset: 0; background: radial-gradient(circle at center, transparent 18%, rgba(19, 5, 12, .18) 55%, rgba(12, 3, 8, .72)); animation: veil 1.08s ease both; }
.effect-path { position: absolute; inset: 12% 8% 15%; }
.flight-card { position: absolute; left: 49%; top: 48%; display: grid; place-items: center; width: 68px; aspect-ratio: 2/3; border: 2px solid #f3d78d; border-radius: 8px; color: #ffeab4; background: linear-gradient(145deg, #a11d46, #401426); box-shadow: 0 14px 35px rgba(10, 0, 5, .7); font: normal 900 29px/1 Georgia, serif; opacity: 0; }
.flight-card.two { filter: hue-rotate(40deg); }
.energy-ring { position: absolute; left: 50%; top: 50%; width: 90px; aspect-ratio: 1; border: 2px solid #f0cc77; border-radius: 50%; opacity: 0; transform: translate(-50%, -50%); animation: ring 1s ease-out both; }
.ring-two { animation-delay: .14s; }
.beam { position: absolute; left: 20%; right: 20%; top: 50%; height: 2px; background: linear-gradient(90deg, transparent, #f5d98a, transparent); filter: drop-shadow(0 0 10px #fff1b9); opacity: 0; animation: beam .8s .12s ease both; }
.effect-caption { position: relative; display: grid; justify-items: center; width: min(520px, 80%); padding: 18px 26px; border: 1px solid rgba(238, 202, 119, .66); border-radius: 18px; color: #fff6dc; background: rgba(42, 14, 27, .9); box-shadow: 0 25px 80px rgba(13, 2, 8, .68), inset 0 0 35px rgba(199, 53, 87, .14); backdrop-filter: blur(9px); animation: caption 1.08s ease both; }
.effect-caption small { color: #e7c66e; font: 800 10px/1 system-ui; letter-spacing: .26em; }
.effect-caption strong { margin: 5px 0; color: #ffe8a1; font: 900 40px/1.05 Georgia, serif; text-shadow: 0 0 24px #d74b74; }
.effect-caption p { margin: 0; max-width: 46ch; font: 700 14px/1.45 system-ui; text-align: center; }
.effect-draw_card .flight-card.one { animation: fly-deck-hand .92s cubic-bezier(.2,.8,.2,1) both; }
.effect-play_card .flight-card.one { animation: fly-hand-table .92s cubic-bezier(.2,.8,.2,1) both; }
.effect-round_deal .flight-card.one { animation: deal-left 1s ease both; }.effect-round_deal .flight-card.two { animation: deal-right 1s .08s ease both; }
.effect-trade_hands .flight-card.one { animation: trade-left 1s ease both; }.effect-trade_hands .flight-card.two { animation: trade-right 1s ease both; }
.effect-guess_hit .effect-caption, .effect-prince_princess .effect-caption, .effect-princess_discard .effect-caption { border-color: #fb7185; animation: impact 1.08s ease both; }
.effect-guess_miss .energy-ring, .effect-peek_hand .energy-ring, .effect-gain_protection .energy-ring, .effect-queen_escape .energy-ring { border-width: 4px; }
.effect-compare_hands .beam, .effect-trade_hands .beam { height: 4px; animation-duration: 1s; }
.effect-bottom_cards .flight-card.one { animation: sink-card .95s ease both; }
@keyframes veil { 0%,100%{opacity:0} 18%,72%{opacity:1} }
@keyframes caption { 0%{opacity:0;transform:translateY(16px) scale(.94)} 20%,72%{opacity:1;transform:none} 100%{opacity:0;transform:translateY(-8px) scale(1.02)} }
@keyframes impact { 0%{opacity:0;transform:scale(.6) rotate(-2deg)} 22%{opacity:1;transform:scale(1.05) rotate(1deg)} 35%,72%{opacity:1;transform:none} 100%{opacity:0;transform:scale(1.08)} }
@keyframes ring { 0%{opacity:.9;transform:translate(-50%,-50%) scale(.3)} 75%{opacity:.2} 100%{opacity:0;transform:translate(-50%,-50%) scale(7)} }
@keyframes beam { 0%{opacity:0;transform:scaleX(.1)} 28%,70%{opacity:1;transform:scaleX(1)} 100%{opacity:0;transform:scaleX(.4)} }
@keyframes fly-deck-hand { 0%{opacity:0;transform:translate(0,-40px) rotate(8deg) scale(.6)} 20%{opacity:1} 78%{opacity:1;transform:translate(-15vw,28vh) rotate(-10deg)} 100%{opacity:0;transform:translate(-15vw,34vh) scale(.8)} }
@keyframes fly-hand-table { 0%{opacity:0;transform:translate(-10vw,34vh) rotate(-8deg)} 18%,72%{opacity:1} 100%{opacity:0;transform:translate(2vw,-3vh) rotate(4deg)} }
@keyframes deal-left { 0%{opacity:0;transform:scale(.4)} 18%{opacity:1} 100%{opacity:0;transform:translate(-34vw,-20vh) rotate(-20deg)} }
@keyframes deal-right { 0%{opacity:0;transform:scale(.4)} 18%{opacity:1} 100%{opacity:0;transform:translate(34vw,-20vh) rotate(20deg)} }
@keyframes trade-left { 0%{opacity:0;transform:translate(-30vw,0)} 20%,70%{opacity:1} 100%{opacity:0;transform:translate(30vw,0) rotate(180deg)} }
@keyframes trade-right { 0%{opacity:0;transform:translate(30vw,0)} 20%,70%{opacity:1} 100%{opacity:0;transform:translate(-30vw,0) rotate(-180deg)} }
@keyframes sink-card { 0%{opacity:0;transform:translate(0,-22vh)} 25%,72%{opacity:1} 100%{opacity:0;transform:translate(0,20vh) scale(.55)} }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-delay: 0ms !important; }
  .effect-layer { outline: 3px solid #f0cc77; outline-offset: -7px; }
}
</style>
