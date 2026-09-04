<script setup lang="ts">
import { computed } from 'vue'
import type { DevelopmentCardView, StandardColor } from '../types'
import { colorInfo, standardColors } from '../types'

const props = withDefaults(defineProps<{
  card: DevelopmentCardView | null
  interactive?: boolean
  selected?: boolean
  faceDownLevel?: number | null
  compact?: boolean
}>(), {
  interactive: false,
  selected: false,
  faceDownLevel: null,
  compact: false,
})

const emit = defineEmits<{ select: [] }>()
const costs = computed(() => props.card
  ? standardColors.filter(color => props.card!.cost[color] > 0).map(color => ({ color, amount: props.card!.cost[color] }))
  : [])
const bonus = computed(() => props.card ? colorInfo[props.card.bonusColor] : colorInfo.black)
const element = computed(() => props.interactive ? 'button' : 'article')
const ariaLabel = computed(() => props.card?.labelZh ?? `${props.faceDownLevel ?? 1} 级发展牌牌背`)

function costClass(color: StandardColor) {
  return `cost-${color}`
}
</script>

<template>
  <component
    :is="element"
    class="development-card"
    :class="[
      card ? `bonus-${card.bonusColor}` : 'card-back',
      `level-${card?.level ?? faceDownLevel ?? 1}`,
      { interactive, selected, compact },
    ]"
    :type="interactive ? 'button' : undefined"
    :aria-label="ariaLabel"
    :aria-pressed="interactive ? selected : undefined"
    @click="interactive && emit('select')"
  >
    <template v-if="card">
      <header class="card-crown">
        <strong>{{ card.prestige || '–' }}</strong>
        <span>{{ card.level }} 级</span>
        <i :style="{ '--gem': bonus.hex }">{{ bonus.symbol }}</i>
      </header>
      <div class="card-art" :data-variant="card.artVariant" aria-hidden="true">
        <svg viewBox="0 0 120 78" role="presentation">
          <path class="horizon" d="M8 64h104M16 57h88" />
          <path class="building" d="M22 61V35l18-13 18 13v26M58 61V27l19-13 22 15v32" />
          <path class="awning" d="M14 40h37l-5 9H20zM62 37h42l-6 9H67z" />
          <path class="facet" d="M47 16l13-10 13 10-13 14zM53 16h14M60 6v24" />
          <circle cx="32" cy="29" r="5" /><circle cx="84" cy="25" r="6" />
        </svg>
        <span class="art-seal">GUILD {{ card.artVariant }}</span>
      </div>
      <footer class="card-costs" aria-label="购买费用">
        <span
          v-for="entry in costs"
          :key="entry.color"
          class="cost-chip"
          :class="costClass(entry.color)"
          :title="`${colorInfo[entry.color].name} ${entry.amount}`"
        >
          <i>{{ colorInfo[entry.color].symbol }}</i><b>{{ entry.amount }}</b>
        </span>
        <span v-if="costs.length === 0" class="cost-free">免费</span>
      </footer>
    </template>
    <template v-else>
      <span class="back-medallion">{{ faceDownLevel ?? 1 }}</span>
      <small>{{ faceDownLevel ?? 1 }} 级牌堆</small>
    </template>
  </component>
</template>
