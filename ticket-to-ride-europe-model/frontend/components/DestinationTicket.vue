<script setup lang="ts">
import type { DestinationTicketModel } from '../types'

withDefaults(defineProps<{
  ticket?: DestinationTicketModel | null
  hidden?: boolean
  selected?: boolean
  interactive?: boolean
  compact?: boolean
}>(), {
  ticket: null,
  hidden: false,
  selected: false,
  interactive: false,
  compact: false,
})

defineEmits<{ select: [] }>()
</script>

<template>
  <button
    type="button"
    class="destination-ticket"
    :class="{ 'is-hidden': hidden, 'is-selected': selected, 'is-interactive': interactive, 'is-compact': compact, 'is-long': ticket?.category === 'long' }"
    :disabled="!interactive"
    :aria-label="hidden ? '任务牌背' : `${ticket?.fromLabel}至${ticket?.toLabel}，${ticket?.points}分`"
    :aria-pressed="interactive ? selected : undefined"
    @click="$emit('select')"
  >
    <template v-if="hidden || !ticket">
      <span class="ticket-back-mark"><i /><b>ROUTE</b><small>DESTINATION</small></span>
    </template>
    <template v-else>
      <span class="ticket-paper" />
      <span class="ticket-category">{{ ticket.category === 'long' ? '长程任务' : '任务牌' }}</span>
      <span class="ticket-route" aria-hidden="true"><i class="origin" /><em /><i class="target" /></span>
      <span class="ticket-cities"><b>{{ ticket.fromLabel }}</b><i>→</i><b>{{ ticket.toLabel }}</b></span>
      <strong class="ticket-points">{{ ticket.points }}</strong>
      <span class="ticket-status" :class="{ complete: ticket.completed }">{{ ticket.completed ? '当前已连通' : '尚未连通' }}</span>
      <span v-if="selected" class="ticket-check">✓</span>
    </template>
  </button>
</template>

<style scoped>
.destination-ticket { position:relative; width:220px; aspect-ratio:17/11; flex:0 0 auto; overflow:hidden; border:2px solid #75644d; border-radius:13px; padding:0; color:#23303a; background:#e9dfc9; box-shadow:0 12px 24px #0006,inset 0 0 0 4px #fff5; transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease; }
.destination-ticket.is-compact{width:154px;border-radius:10px}.destination-ticket.is-interactive{cursor:pointer}.destination-ticket.is-interactive:hover:not(:disabled),.destination-ticket:focus-visible{z-index:3;transform:translateY(-7px) rotate(-.7deg);border-color:#e8b85d;box-shadow:0 17px 28px #0008,0 0 0 3px #e8b85d33;outline:none}.destination-ticket.is-selected{transform:translateY(-9px);border-color:#d69635;box-shadow:0 16px 28px #0008,0 0 0 4px #e8b85d44}.ticket-paper{position:absolute;inset:5px;border-radius:8px;background:radial-gradient(circle at 16% 24%,#fff8e9,#eadfc6 68%),repeating-linear-gradient(0deg,transparent 0 12px,#594a3620 13px);}.ticket-paper::after{content:"";position:absolute;inset:8px;border:1px solid #806b4b55;border-radius:5px}.is-long .ticket-paper{background:radial-gradient(circle at 20% 20%,#fff3d4,#dbc28a 70%)}.ticket-category{position:absolute;z-index:2;left:13px;top:10px;font-size:7px;font-weight:900;letter-spacing:.13em;color:#7a5830}.ticket-route{position:absolute;z-index:2;left:22px;right:53px;top:44%;height:18px}.ticket-route em{position:absolute;left:8px;right:8px;top:7px;border-top:3px dashed #657581}.ticket-route i{position:absolute;top:0;width:17px;height:17px;border:3px solid #f5ead5;border-radius:50%;box-shadow:0 1px 4px #0006}.ticket-route .origin{left:0;background:#b64f46}.ticket-route .target{right:0;background:#347eb7}.ticket-cities{position:absolute;z-index:2;left:12px;right:48px;bottom:13px;display:flex;align-items:center;justify-content:space-between;gap:4px;font-size:8px}.ticket-cities b{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.ticket-cities i{color:#9c7440;font-style:normal}.ticket-points{position:absolute;z-index:3;right:12px;top:33%;display:grid;place-items:center;width:37px;height:37px;border:2px solid #a87d3e;border-radius:50%;color:#172733;background:#f8e9c5;box-shadow:0 3px 8px #0003;font-size:19px}.ticket-status{position:absolute;z-index:3;right:9px;top:9px;padding:2px 5px;border-radius:8px;color:#7f473e;background:#fff8;font-size:5.5px;font-weight:800}.ticket-status.complete{color:#286850;background:#e6f2e9}.ticket-check{position:absolute;z-index:5;right:6px;bottom:5px;display:grid;place-items:center;width:20px;height:20px;border-radius:50%;color:#15242c;background:#ecc46f;font-weight:900}.ticket-back-mark{position:absolute;inset:5px;display:grid;place-content:center;border:1px solid #b9965c;border-radius:8px;color:#e8d4a8;background:repeating-linear-gradient(45deg,#263943 0 8px,#2c444f 8px 16px)}.ticket-back-mark i{position:absolute;inset:20%;border:2px solid #b9965c;border-radius:50%}.ticket-back-mark b,.ticket-back-mark small{position:relative;letter-spacing:.16em}.ticket-back-mark b{font-size:14px}.ticket-back-mark small{font-size:5px}.destination-ticket:disabled{opacity:1}@media(max-width:720px){.destination-ticket{width:185px}.destination-ticket.is-compact{width:132px}}@media(prefers-reduced-motion:reduce){.destination-ticket{transition:none!important}}
</style>
