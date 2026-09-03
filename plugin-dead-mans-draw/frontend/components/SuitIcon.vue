<script setup lang="ts">
import type { SuitId } from '../types'

withDefaults(defineProps<{ suit: SuitId; size?: number; label?: string }>(), {
  size: 44,
  label: '',
})
</script>

<template>
  <svg
    class="suit-icon"
    viewBox="-50 -50 100 100"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="5"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    :aria-label="label || suit"
  >
    <template v-if="suit === 'anchor'">
      <circle cx="0" cy="-25" r="10"/><path d="M0-15V31M-29 10C-22 31-9 39 0 31 9 39 22 31 29 10M-29 10l12-4m46 4-12-4"/>
    </template>
    <template v-else-if="suit === 'hook'">
      <path d="M4-38V10c0 19-11 29-26 24-14-5-16-22-7-32m0 0-2 16m2-16 15 6M-6-38h20"/>
    </template>
    <template v-else-if="suit === 'cannon'">
      <path d="m-35-14 55 9-4 22-55-9zm55 12 15-6M-35-4l-8-3M18-9c6-11 11-13 17-17"/><circle cx="-8" cy="24" r="13"/>
    </template>
    <template v-else-if="suit === 'key'">
      <circle cx="-21" cy="-10" r="15"/><circle cx="-21" cy="-10" r="5"/><path d="M-9 0l38 30M13 16l9-9m1 18 8-8"/>
    </template>
    <template v-else-if="suit === 'chest'">
      <path d="M-36-3v-9c0-15 13-24 36-24s36 9 36 24v9M-39-3h78v37h-78zm0 11h78M0-3v37"/><rect x="-7" y="8" width="14" height="13" rx="3"/>
    </template>
    <template v-else-if="suit === 'map'">
      <path d="m-38-31 25-7 26 8 25-8v69l-25 7-26-8-25 8zm25-7v68m26-60v68M-27 17C-12 2-8-14 4-12c12 2 9 19 24 25m-5-5 7 7m0-7-7 7"/>
    </template>
    <template v-else-if="suit === 'oracle'">
      <circle cy="-5" r="32"/><path d="m-25 24-9 13h68l-9-13M-18-8C-7-24 9-25 20-12 9-14 1-7 0 4-9-1-15-4-18-12Z"/>
    </template>
    <template v-else-if="suit === 'sword'">
      <path d="m-29 31 53-62 7-8-2 12-51 63zm-4-19 26 22m-21 3 9 9"/>
    </template>
    <template v-else-if="suit === 'kraken'">
      <path d="M-27 12V1c0-24 11-37 27-37S27-23 27 1v11M-27 10c-15 8-10 29 7 27 14-1 8-21 19-24 13-4 4 26 21 25 18-1 22-21 7-28M-10 15c-9 10-5 27 6 28m15-28c9 10 6 27-4 29"/><circle cx="-9" cy="-9" r="3" fill="currentColor" stroke="none"/><circle cx="9" cy="-9" r="3" fill="currentColor" stroke="none"/>
    </template>
    <template v-else>
      <path d="M0-37C-18-30-29-15-29 4c0 22 17 35 29 41 12-6 29-19 29-41 0-19-11-34-29-41Zm0 6v70M-23-8c13 5 33 5 46 0M-27 9c16 5 38 5 54 0M-19 27c12 1 26 1 38 0"/>
    </template>
  </svg>
</template>

<style scoped>
.suit-icon { display: block; overflow: visible; }
</style>
