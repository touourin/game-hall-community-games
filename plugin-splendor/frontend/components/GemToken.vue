<script setup lang="ts">
import type { PieceColor } from '../types'
import { colorInfo } from '../types'

withDefaults(defineProps<{
  color: PieceColor
  count: number
  interactive?: boolean
  selected?: boolean
  disabled?: boolean
  sequence?: number | null
  subtitle?: string
}>(), {
  interactive: false,
  selected: false,
  disabled: false,
  sequence: null,
  subtitle: '',
})
const emit = defineEmits<{ select: [] }>()
</script>

<template>
  <button
    type="button"
    class="gem-token"
    :class="[`gem-${color}`, { interactive, selected }]"
    :disabled="disabled || !interactive"
    :aria-label="`${colorInfo[color].name}，${count} 枚${subtitle ? `，${subtitle}` : ''}`"
    :aria-pressed="interactive ? selected : undefined"
    @click="emit('select')"
  >
    <i class="gem-disc"><span>{{ colorInfo[color].symbol }}</span><b>{{ count }}</b><em v-if="sequence">{{ sequence }}</em></i>
    <strong>{{ colorInfo[color].name }}</strong>
    <small>{{ subtitle || `供应 ${count}` }}</small>
  </button>
</template>
