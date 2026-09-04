<script setup lang="ts">
import { computed } from 'vue'
import type { NobleView } from '../types'
import { colorInfo, standardColors } from '../types'

const props = withDefaults(defineProps<{ noble: NobleView, interactive?: boolean, selected?: boolean }>(), {
  interactive: false,
  selected: false,
})
const emit = defineEmits<{ select: [] }>()
const requirements = computed(() => standardColors
  .filter(color => props.noble.requirement[color] > 0)
  .map(color => ({ color, amount: props.noble.requirement[color] })))
</script>

<template>
  <button
    v-if="interactive"
    type="button"
    class="noble-tile"
    :class="{ selected, eligible: noble.eligible }"
    :aria-label="noble.labelZh"
    :aria-pressed="selected"
    @click="emit('select')"
  >
    <strong>3</strong>
    <svg viewBox="0 0 72 60" aria-hidden="true">
      <circle cx="36" cy="19" r="11" />
      <path d="M14 57c2-18 10-27 22-27s20 9 22 27M24 34l12 10 12-10M30 8l6-5 6 5" />
    </svg>
    <footer><span v-for="item in requirements" :key="item.color" :style="{ '--noble-gem': colorInfo[item.color].hex }">{{ colorInfo[item.color].symbol }} {{ item.amount }}</span></footer>
  </button>
  <article v-else class="noble-tile" :class="{ selected, eligible: noble.eligible }" :aria-label="noble.labelZh">
    <strong>3</strong>
    <svg viewBox="0 0 72 60" aria-hidden="true"><circle cx="36" cy="19" r="11" /><path d="M14 57c2-18 10-27 22-27s20 9 22 27M24 34l12 10 12-10M30 8l6-5 6 5" /></svg>
    <footer><span v-for="item in requirements" :key="item.color" :style="{ '--noble-gem': colorInfo[item.color].hex }">{{ colorInfo[item.color].symbol }} {{ item.amount }}</span></footer>
  </article>
</template>
