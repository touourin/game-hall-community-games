<script setup lang="ts">
import { computed } from 'vue'
import type { TrainCardModel } from '../types'

const props = withDefaults(defineProps<{
  card?: TrainCardModel | null
  faceDown?: boolean
  selected?: boolean
  interactive?: boolean
  disabled?: boolean
  compact?: boolean
  label?: string
}>(), {
  card: null,
  faceDown: false,
  selected: false,
  interactive: false,
  disabled: false,
  compact: false,
  label: '',
})

defineEmits<{ select: [] }>()

const styleVars = computed(() => ({
  '--card-accent': props.card?.visual.accent ?? '#31404a',
}))
const ariaLabel = computed(() => props.label || (props.faceDown ? '车票牌背' : props.card?.label ?? '车票牌'))
</script>

<template>
  <button
    type="button"
    class="train-card"
    :class="[
      `train-card--${card?.color ?? 'back'}`,
      `pattern--${card?.visual.pattern ?? 'back'}`,
      { 'is-face-down': faceDown, 'is-selected': selected, 'is-interactive': interactive, 'is-compact': compact },
    ]"
    :style="styleVars"
    :disabled="disabled || !interactive"
    :aria-label="ariaLabel"
    :aria-pressed="interactive ? selected : undefined"
    @click="$emit('select')"
  >
    <template v-if="faceDown || !card">
      <span class="back-frame" aria-hidden="true">
        <i class="back-rail rail-a" /><i class="back-rail rail-b" />
        <b>EUR</b><small>RAIL PASS</small>
      </span>
    </template>
    <template v-else>
      <span class="foil" aria-hidden="true" />
      <span class="card-code">{{ card.visual.accessibilityCode }}</span>
      <span class="card-type">{{ card.color === 'locomotive' ? 'WILD' : 'CARRIAGE' }}</span>
      <span class="pattern" aria-hidden="true">
        <i v-for="index in 9" :key="index" />
      </span>
      <span class="locomotive" aria-hidden="true">
        <i class="engine"><em /></i>
        <i class="carriage" />
        <i class="wheel wheel-a" /><i class="wheel wheel-b" /><i class="wheel wheel-c" />
      </span>
      <span class="card-label">{{ card.label }}</span>
    </template>
    <span v-if="selected" class="selected-check" aria-hidden="true">✓</span>
  </button>
</template>

<style scoped>
.train-card {
  --card-width: 86px;
  position: relative;
  width: var(--card-width);
  aspect-ratio: 11 / 17;
  flex: 0 0 auto;
  overflow: hidden;
  border: 2px solid color-mix(in srgb, var(--card-accent), white 25%);
  border-radius: 11px;
  padding: 0;
  color: #f8f5ec;
  background: #10171d;
  box-shadow: 0 12px 22px rgb(0 0 0 / .36), inset 0 0 0 3px rgb(255 255 255 / .055);
  transform: translateZ(0);
  transition: transform .18s ease, border-color .18s ease, filter .18s ease, box-shadow .18s ease;
}
.train-card.is-compact { --card-width: 62px; border-radius: 8px; }
.train-card.is-interactive { cursor: pointer; }
.train-card.is-interactive:hover:not(:disabled), .train-card.is-interactive:focus-visible {
  z-index: 4;
  transform: translateY(-8px) rotate(-1deg);
  border-color: #fff3c7;
  filter: saturate(1.08) brightness(1.04);
  box-shadow: 0 17px 27px rgb(0 0 0 / .48), 0 0 0 3px rgb(224 179 91 / .2);
  outline: none;
}
.train-card.is-selected { transform: translateY(-11px); border-color: #f2c66d; box-shadow: 0 17px 28px rgb(0 0 0 / .5), 0 0 0 3px rgb(242 198 109 / .35); }
.foil { position:absolute; inset:6px; border-radius:7px; background: linear-gradient(145deg, color-mix(in srgb, var(--card-accent), white 14%), var(--card-accent) 50%, color-mix(in srgb, var(--card-accent), black 23%)); }
.foil::after { content:""; position:absolute; inset:0; background: linear-gradient(115deg, transparent 22%, rgb(255 255 255 / .24) 38%, transparent 55%); transform: translateX(-105%); transition: transform .55s ease; }
.train-card:hover .foil::after { transform: translateX(105%); }
.card-code { position:absolute; z-index:2; left:10px; top:8px; font-size:13px; line-height:1; font-weight:900; letter-spacing:.08em; text-shadow:0 1px 2px rgb(0 0 0 / .7); }
.card-type { position:absolute; z-index:2; right:7px; top:8px; font-size:5px; letter-spacing:.16em; opacity:.78; }
.pattern { position:absolute; z-index:1; inset:28px 10px 35px; display:grid; grid-template-columns:repeat(3,1fr); align-items:center; justify-items:center; opacity:.42; }
.pattern i { position:relative; width:7px; height:7px; border:1.5px solid currentColor; border-radius:50%; }
.pattern--horizontal .pattern { display:flex; flex-direction:column; justify-content:space-evenly; }
.pattern--horizontal .pattern i { width:100%; height:2px; border:0; border-radius:2px; background:currentColor; }
.pattern--diagonal .pattern i { width:3px; height:35px; border:0; border-radius:2px; background:currentColor; transform:rotate(25deg); }
.pattern--cross .pattern i::before, .pattern--cross .pattern i::after { content:""; position:absolute; width:8px; height:2px; background:#4b5157; }
.pattern--cross .pattern i::after { transform:rotate(90deg); }
.pattern--diamonds .pattern i { border-radius:0; transform:rotate(45deg); }
.pattern--waves .pattern i { width:13px; height:5px; border:0; border-top:2px solid currentColor; border-radius:50%; }
.pattern--grid .pattern i { width:13px; height:13px; border-radius:0; }
.pattern--triangles .pattern i { width:0; height:0; border:0; border-left:5px solid transparent; border-right:5px solid transparent; border-bottom:9px solid currentColor; }
.pattern--spectrum .pattern { display:flex; gap:3px; transform:skew(-14deg); opacity:.7; }
.pattern--spectrum .pattern i { width:5px; height:58px; border:0; border-radius:2px; background:var(--spectrum,#e05a51); }
.pattern--spectrum .pattern i:nth-child(2n) { background:#e1b74b; }.pattern--spectrum .pattern i:nth-child(3n) { background:#4fa273; }.pattern--spectrum .pattern i:nth-child(4n) { background:#4b88c2; }.pattern--spectrum .pattern i:nth-child(5n) { background:#8c62ae; }
.locomotive { position:absolute; z-index:3; left:13%; right:13%; bottom:25%; height:24%; border-bottom:3px solid rgb(10 15 19 / .76); }
.engine { position:absolute; left:3%; bottom:7px; width:38%; height:42%; border-radius:5px 5px 2px 2px; background:#121a20; box-shadow:inset 0 0 0 1px rgb(255 255 255 / .2); }
.engine::before { content:""; position:absolute; right:4px; top:-40%; width:42%; height:48%; border-radius:2px 2px 0 0; background:#172229; }
.engine::after { content:""; position:absolute; left:2px; top:-18%; width:12%; height:22%; background:#172229; }
.engine em { position:absolute; right:6px; top:-29%; width:18%; height:20%; background:#f0c86f; }
.carriage { position:absolute; right:1%; bottom:7px; width:49%; height:31%; border-radius:3px 5px 2px 2px; background:#151e24; box-shadow:inset 0 0 0 1px rgb(255 255 255 / .2); }
.wheel { position:absolute; bottom:1px; width:11px; height:11px; border:2px solid #d9e0df; border-radius:50%; background:#0b1115; }.wheel-a{left:16%;}.wheel-b{left:47%;}.wheel-c{right:10%;}
.card-label { position:absolute; z-index:4; left:5px; right:5px; bottom:8px; overflow:hidden; font-size:8px; line-height:1.1; font-weight:800; white-space:nowrap; text-overflow:ellipsis; text-shadow:0 1px 2px #000; }
.train-card--white, .train-card--yellow { color:#19232b; }.train-card--white .card-label,.train-card--yellow .card-label { text-shadow:none; }.train-card--white .wheel,.train-card--yellow .wheel{border-color:#1d2931;}
.back-frame { position:absolute; inset:5px; display:grid; place-content:center; border:1px solid #c79a55; border-radius:7px; background:repeating-linear-gradient(45deg,#22313a 0 7px,#273a45 7px 14px); }
.back-frame::before { content:""; position:absolute; inset:12%; border:2px solid rgb(199 154 85 / .7); border-radius:50%; }
.back-frame b { z-index:1; font-size:15px; letter-spacing:.16em; color:#e4c187; }.back-frame small{z-index:1;font-size:5px;letter-spacing:.18em;color:#d7e0e3;}
.back-rail { position:absolute; left:14%; right:14%; top:43%; height:3px; background:#c79a55; transform:rotate(34deg); }.back-rail.rail-b{transform:rotate(-34deg);}
.selected-check { position:absolute; z-index:8; top:4px; right:4px; display:grid; place-items:center; width:19px; height:19px; border-radius:50%; color:#12202a; background:#f3cd78; box-shadow:0 2px 8px #0008; font-size:12px; font-weight:900; }
.train-card:disabled { opacity:1; }
@media (max-width: 720px) { .train-card { --card-width:72px; }.train-card.is-compact{--card-width:51px;} }
@media (prefers-reduced-motion: reduce) { .train-card, .foil::after { transition:none !important; } }
</style>
