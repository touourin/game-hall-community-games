<script setup lang="ts">
import type { PendingChoiceView } from '../types'
import LootCard from './LootCard.vue'

defineProps<{ choice: PendingChoiceView; playerName?: (id: string | null) => string }>()
const emit = defineEmits<{ select: [optionId: string] }>()
</script>

<template>
  <aside class="effect-sheet" role="dialog" aria-modal="true" aria-labelledby="effect-title">
    <small>必须结算 · {{ choice.kind }}</small>
    <h3 id="effect-title">{{ choice.promptZh }}</h3>
    <div class="choice-grid">
      <button
        v-for="option in choice.options"
        :key="option.labelZh"
        type="button"
        class="choice-option"
        :class="{ danger: option.causesImmediateBust }"
        :disabled="!option.actionable || !option.optionId"
        :aria-label="option.labelZh"
        @click="option.optionId && emit('select', option.optionId)"
      >
        <LootCard v-if="option.card" :card="option.card" compact />
        <span><b>{{ option.labelZh }}</b><em v-if="option.causesImmediateBust">会立即爆牌</em></span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.effect-sheet { position: absolute; z-index: 20; left: 50%; bottom: 18px; width: min(760px, calc(100% - 28px)); max-height: min(58vh, 520px); overflow: auto; transform: translateX(-50%); padding: 16px; border: 1px solid #f2c96d; border-radius: 18px; color: #fff9ea; background: #102c2bea; box-shadow: 0 24px 60px #020c0bd9, inset 0 1px #fff3; backdrop-filter: blur(16px); }
.effect-sheet > small { color: #f2c96d; font: 800 10px/1.2 system-ui; letter-spacing: .14em; text-transform: uppercase; }
.effect-sheet h3 { margin: 5px 0 12px; font-size: clamp(16px, 2.2vw, 22px); }
.choice-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; }
.choice-option { min-width: 0; display: flex; align-items: center; gap: 10px; padding: 8px; border: 1px solid #557370; border-radius: 12px; color: #fff9ea; text-align: left; background: #1c4441; cursor: pointer; transition: transform .16s, border-color .16s, background .16s; }
.choice-option:hover:not(:disabled), .choice-option:focus-visible { transform: translateY(-2px); border-color: #f2c96d; background: #28514d; outline: none; }
.choice-option:disabled { cursor: default; opacity: .68; }
.choice-option.danger { border-color: #a3473d; background: #422a28; }
.choice-option > span { min-width: 0; display: grid; gap: 4px; }
.choice-option b { font-size: 12px; line-height: 1.35; }
.choice-option em { color: #ffb1a8; font: 800 10px/1.2 system-ui; font-style: normal; }
@media (max-width: 560px) {
  .effect-sheet { position: fixed; bottom: 0; width: 100%; max-height: 62dvh; border-radius: 18px 18px 0 0; }
  .choice-grid { grid-template-columns: 1fr 1fr; }
}
</style>
