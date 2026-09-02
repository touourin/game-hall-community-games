<script setup lang="ts">
import { computed } from 'vue'
import type { UnoEvent } from '../types'

const props = defineProps<{ event: UnoEvent }>()

const effectClass = computed(() => `uno-fx--${props.event.type.replaceAll('_', '-')}`)
const title = computed(() => {
  const labels: Record<string, string> = {
    skip: '时间切断',
    reverse: '轨道反转',
    draw_two: '能量汲取 +2',
    wild: '光谱重构',
    wild_draw_four: '棱镜奇点 +4',
    take_penalty: '累计惩罚坠落',
    catch_uno: '漏喊捕获',
  }
  return labels[props.event.type] ?? (props.event.calledUno ? 'UNO!' : '出牌')
})

const countLabel = computed(() => props.event.count > 0 ? `+${props.event.count}` : '')
const stackLabel = computed(() => (
  props.event.stackTotal > props.event.count
    ? `累计 +${props.event.stackTotal}`
    : ''
))
</script>

<template>
  <div class="uno-fx" :class="effectClass" role="status" aria-live="polite">
    <div class="uno-fx__veil" />
    <div class="uno-fx__speed-lines" aria-hidden="true">
      <i v-for="index in 12" :key="index" :style="{ '--i': index }" />
    </div>

    <div class="uno-fx__ring" aria-hidden="true">
      <span /><span /><span /><span />
    </div>

    <img
      v-if="event.type === 'wild_draw_four'"
      class="uno-fx__burst"
      src="../assets/effects/wild-draw-four-burst.png"
      alt=""
    >

    <div class="uno-fx__symbol" aria-hidden="true">
      <svg v-if="event.type === 'skip'" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="31" fill="none" stroke="currentColor" stroke-width="10" />
        <path d="M25 75 75 25" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="10" />
      </svg>
      <svg v-else-if="event.type === 'reverse'" viewBox="0 0 100 100">
        <path d="M18 46c3-19 19-33 39-33 11 0 21 4 28 12" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="9" />
        <path d="m79 8 9 22-24-2" fill="currentColor" />
        <path d="M82 54c-3 19-19 33-39 33-11 0-21-4-28-12" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="9" />
        <path d="m21 92-9-22 24 2" fill="currentColor" />
      </svg>
      <strong v-else-if="countLabel">{{ countLabel }}</strong>
      <strong v-else>✦</strong>
    </div>

    <div v-if="stackLabel" class="uno-fx__stack-total">{{ stackLabel }}</div>

    <div class="uno-fx__copy">
      <small>PRISM EFFECT</small>
      <b>{{ title }}</b>
      <span>{{ event.message }}</span>
    </div>

    <div v-if="event.calledUno" class="uno-fx__uno">UNO!</div>
  </div>
</template>
