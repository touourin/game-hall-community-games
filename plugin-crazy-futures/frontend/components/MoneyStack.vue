<script setup lang="ts">
import { computed } from 'vue'

import money1 from '../../image/money-001.svg'
import money5 from '../../image/money-005.svg'
import money10 from '../../image/money-010.svg'
import money50 from '../../image/money-050.svg'
import money100 from '../../image/money-100.svg'

const props = withDefaults(defineProps<{
  amount: number
  delta?: number | null
}>(), { delta: null })

const denominations = [
  { value: 100, image: money100 },
  { value: 50, image: money50 },
  { value: 10, image: money10 },
  { value: 5, image: money5 },
  { value: 1, image: money1 },
]

const notes = computed(() => {
  let remaining = Math.max(0, Math.floor(props.amount))
  return denominations
    .map((denomination) => {
      const count = Math.floor(remaining / denomination.value)
      remaining %= denomination.value
      return { ...denomination, count }
    })
    .filter((denomination) => denomination.count > 0)
})

const fractional = computed(() => Math.round((Math.abs(props.amount) % 1) * 100) / 100)
</script>

<template>
  <div class="money-stack" :class="{ gain: (delta ?? 0) > 0, loss: (delta ?? 0) < 0 }">
    <div v-if="notes.length" class="notes">
      <span v-for="note in notes" :key="note.value">
        <img :src="note.image" :alt="`${note.value} 万金币`"><b>×{{ note.count }}</b>
      </span>
    </div>
    <span v-else class="empty">无可用现金</span>
    <small v-if="fractional">另有 {{ fractional }} 万零钱</small>
    <i v-if="delta" :key="delta">{{ delta > 0 ? '+' : '' }}{{ delta }}</i>
  </div>
</template>

<style scoped>
.money-stack { position: relative; min-width: 0; display: grid; gap: 5px; }.notes { min-width: 0; display: flex; flex-wrap: wrap; gap: 5px; }.notes span { position: relative; width: 74px; }.notes img { display: block; width: 100%; border-radius: 3px; filter: drop-shadow(0 3px 5px color-mix(in srgb, var(--bg) 35%, transparent)); }.notes b { position: absolute; right: -3px; bottom: -3px; min-width: 20px; border-radius: 999px; padding: 2px 4px; color: var(--accent-contrast); background: var(--gold); font-size: 7px; text-align: center; }.empty,.money-stack > small { color: var(--muted); font-size: 8px; }.money-stack > i { position: absolute; right: 4px; top: -9px; color: #65c787; font-size: 12px; font-style: normal; font-weight: 900; animation: money-fly .7s ease both; }.money-stack.loss > i { color: #e36b70; }
@keyframes money-fly { from { opacity: 0; transform: translateY(12px) scale(.85); } 35% { opacity: 1; } to { opacity: 0; transform: translateY(-16px) scale(1.05); } }
@media (prefers-reduced-motion: reduce) { .money-stack > i { animation: none; } }
</style>
