<script setup lang="ts">
import { computed } from 'vue'
import type { HalliGalliEvent } from '../types'

const props = defineProps<{ event: HalliGalliEvent | null }>()
const tone = computed(() => {
  if (!props.event) return 'neutral'
  if (props.event.type === 'bell_correct' || props.event.type === 'game_finished') return 'success'
  if (props.event.type.includes('wrong')) return 'danger'
  if (props.event.type === 'final_duel_armed') return 'warning'
  return 'neutral'
})
const eyebrow = computed(() => ({
  success: '裁定完成', danger: '误按裁定', warning: '终局提醒', neutral: '牌桌动态',
}[tone.value]))
</script>

<template>
  <aside
    v-if="event && ['bell_correct','bell_wrong','bell_wrong_final','final_duel_armed','game_finished','no_progress_started'].includes(event.type)"
    class="reaction-banner"
    :class="`tone-${tone}`"
    data-zone="reaction_banner"
    role="status"
    aria-live="polite"
  >
    <span>{{ eyebrow }}</span>
    <strong>{{ event.messageZh }}</strong>
  </aside>
</template>

<style scoped>
.reaction-banner{position:absolute;z-index:105;top:18%;left:50%;display:grid;width:min(520px,44vw);min-width:260px;padding:8px 16px;border:1px solid #78938d;border-radius:11px;color:#e8f0eb;background:rgba(12,43,39,.95);box-shadow:0 10px 25px rgba(0,0,0,.35);text-align:center;transform:translateX(-50%);animation:banner-enter 220ms ease-out both}.reaction-banner span{font-size:7px;font-weight:900;letter-spacing:.16em}.reaction-banner strong{overflow:hidden;margin-top:2px;font-size:clamp(9px,.9vw,13px);text-overflow:ellipsis;white-space:nowrap}.tone-success{border-color:#65c48b}.tone-success span{color:#84dda6}.tone-danger{border-color:#db6773}.tone-danger span{color:#ff9ea7}.tone-warning{border-color:#e8b158}.tone-warning span{color:#ffd68c}@keyframes banner-enter{from{opacity:0;transform:translate(-50%,-10px) scale(.96)}to{opacity:1;transform:translate(-50%,0) scale(1)}}@media(max-width:759px){.reaction-banner{top:29%;width:86vw;min-width:0;padding:5px 9px}.reaction-banner strong{font-size:8px}}@media(prefers-reduced-motion:reduce){.reaction-banner{animation:none}}
</style>
