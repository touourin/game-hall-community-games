<script setup lang="ts">
import { computed } from 'vue'
import FruitCard from './FruitCard.vue'
import type { HalliGalliPlayerView } from '../types'

const props = withDefaults(defineProps<{
  player: HalliGalliPlayerView
  canFlip?: boolean
  justFlipped?: boolean
  motionTone?: 'winner' | 'wrong' | 'target' | ''
}>(), { canFlip: false, justFlipped: false, motionTone: '' })

const emit = defineEmits<{ flip: [] }>()

const statusLabel = computed(() => ({
  current_turn: '轮到翻牌',
  last_chance: '无牌 · 仍可抢铃',
  eliminated: '已退出',
  resigned: '已离桌',
  eligible: '可抢铃',
}[props.player.displayStatus]))

const ariaLabel = computed(() => {
  const top = props.player.topCard ? `，顶牌${props.player.topCard.altZh}` : '，尚无明牌'
  return `${props.player.name}，抽牌 ${props.player.drawCount} 张，明牌堆 ${props.player.discardCount} 张${top}，${statusLabel.value}`
})
</script>

<template>
  <article
    class="player-seat"
    :class="[
      `status-${player.displayStatus}`,
      { 'is-self': player.isSelf, disconnected: !player.connected, 'just-flipped': justFlipped },
      motionTone ? `motion-${motionTone}` : '',
    ]"
    :data-player-id="player.id"
    :data-relative-seat="player.relativeSeat"
    :data-self="player.isSelf"
    :data-status="player.displayStatus"
    data-zone="player_seat"
    :aria-label="ariaLabel"
  >
    <header>
      <span class="seat-index">P{{ player.seat + 1 }}</span>
      <strong :title="player.name">{{ player.name }}</strong>
      <span v-if="player.isSelf" class="self-chip">你</span>
      <span v-if="!player.connected" class="connection-chip">重连中</span>
    </header>
    <div class="seat-cards">
      <button
        v-if="player.isSelf"
        type="button"
        class="draw-stack"
        :class="{ actionable: canFlip }"
        :disabled="!canFlip"
        :aria-label="canFlip ? `翻开一张牌，剩余 ${player.drawCount} 张` : `抽牌堆剩余 ${player.drawCount} 张`"
        data-zone="draw_stack"
        data-action="flip-deck"
        @click="emit('flip')"
      >
        <span v-if="player.drawCount" class="stack-card stack-back-two" />
        <span v-if="player.drawCount" class="stack-card stack-back-one" />
        <FruitCard v-if="player.drawCount" face-down compact decorative />
        <span v-else class="empty-stack">空</span>
        <b>{{ player.drawCount }}</b>
      </button>
      <div v-else class="draw-stack" data-zone="draw_stack" aria-hidden="true">
        <span v-if="player.drawCount" class="stack-card stack-back-two" />
        <span v-if="player.drawCount" class="stack-card stack-back-one" />
        <FruitCard v-if="player.drawCount" face-down compact decorative />
        <span v-else class="empty-stack">空</span>
        <b>{{ player.drawCount }}</b>
      </div>
      <div class="discard-stack" data-zone="top_discard">
        <span v-if="player.discardCount > 2" class="discard-shadow shadow-two" />
        <span v-if="player.discardCount > 1" class="discard-shadow shadow-one" />
        <FruitCard
          v-if="player.topCard"
          :key="`${player.topCard.faceId}-${player.discardCount}`"
          :card="player.topCard"
          compact
          :just-revealed="justFlipped"
        />
        <span v-else class="empty-discard">等待翻牌</span>
        <b v-if="player.discardCount">{{ player.discardCount }}</b>
      </div>
    </div>
    <footer>
      <span class="status-chip">{{ statusLabel }}</span>
      <span class="owned-count">共 {{ player.ownedCount }} 张</span>
    </footer>
  </article>
</template>

<style scoped>
.player-seat{position:absolute;z-index:30;left:var(--seat-x);top:var(--seat-y);display:grid;grid-template-rows:25px minmax(0,1fr) 24px;width:clamp(170px,15vw,238px);height:clamp(142px,19vh,208px);min-width:0;padding:5px;border:1px solid rgba(147,185,175,.48);border-radius:14px;color:#edf4ee;background:linear-gradient(145deg,rgba(8,39,36,.94),rgba(17,59,53,.91));box-shadow:0 10px 20px rgba(0,0,0,.2),inset 0 0 22px rgba(0,0,0,.14);transform:translate(-50%,-50%);transition:border-color 160ms ease,filter 180ms ease,box-shadow 180ms ease}.player-seat header{display:flex;align-items:center;gap:5px;min-width:0;padding:0 3px}.player-seat header strong{overflow:hidden;min-width:0;color:#fff8e6;font-size:clamp(10px,.9vw,14px);text-overflow:ellipsis;white-space:nowrap}.seat-index{flex:0 0 auto;color:#d6b56b;font:900 8px/1 ui-monospace,monospace;letter-spacing:.08em}.self-chip,.connection-chip{flex:0 0 auto;padding:2px 5px;border-radius:999px;font-size:7px;font-weight:900}.self-chip{color:#243026;background:#f7d774}.connection-chip{margin-left:auto;color:#ffe5af;background:#7b5725}.seat-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px;min-width:0;min-height:0;padding:2px 5px}.draw-stack,.discard-stack{position:relative;display:grid;min-width:0;min-height:0;place-items:center;margin:0;padding:0;border:0;background:transparent}.draw-stack{border-radius:8px}.draw-stack .fruit-card,.discard-stack .fruit-card{z-index:3;width:auto;height:100%;max-width:100%}.draw-stack.actionable{cursor:pointer;filter:drop-shadow(0 0 8px rgba(247,215,116,.45))}.draw-stack.actionable::after{content:"翻牌";position:absolute;z-index:7;bottom:3px;padding:2px 7px;border:1px solid #ffe69d;border-radius:999px;color:#23332c;background:#f7d774;font-size:7px;font-weight:900;box-shadow:0 2px 7px rgba(0,0,0,.3)}.draw-stack:focus-visible{outline:3px solid #f7d774;outline-offset:2px}.draw-stack:disabled{opacity:1}.stack-card,.discard-shadow{position:absolute;width:auto;height:92%;aspect-ratio:56/87;border:1px solid #b68d48;border-radius:6px;background:#1f5149}.stack-back-two{transform:translate(6px,-5px)}.stack-back-one{transform:translate(3px,-2px)}.discard-shadow{background:#e8dfcf;border-color:#b8a88b}.shadow-two{transform:translate(5px,-4px) rotate(1deg)}.shadow-one{transform:translate(2px,-2px) rotate(-1deg)}.draw-stack>b,.discard-stack>b{position:absolute;z-index:8;right:0;bottom:1px;display:grid;min-width:22px;height:22px;place-items:center;padding:0 4px;border:2px solid #f5db98;border-radius:999px;color:#172d29;background:#e2bd69;font:900 9px/1 ui-monospace,monospace;box-shadow:0 2px 5px rgba(0,0,0,.35)}.empty-stack,.empty-discard{display:grid;width:72%;height:86%;place-items:center;border:1px dashed #5b7d76;border-radius:8px;color:#78918c;font-size:8px}.player-seat footer{display:flex;align-items:center;justify-content:space-between;gap:4px;min-width:0;padding:2px 3px 0}.status-chip{overflow:hidden;padding:3px 6px;border:1px solid #52766f;border-radius:999px;color:#bdd0cb;background:#143e39;font-size:7px;font-weight:900;text-overflow:ellipsis;white-space:nowrap}.owned-count{flex:0 0 auto;color:#91aaa5;font-size:7px}.status-current_turn{border-color:#f7d774;box-shadow:0 0 0 2px rgba(247,215,116,.25),0 10px 24px rgba(0,0,0,.28)}.status-current_turn .status-chip{border-color:#f7d774;color:#273129;background:#f7d774}.status-last_chance{border-color:#e6a95b}.status-last_chance .status-chip{color:#ffe5a8;border-color:#b87b35;background:#6a431e}.status-eliminated,.status-resigned{filter:grayscale(.72) brightness(.67)}.status-eliminated .status-chip,.status-resigned .status-chip{color:#bac1bd;background:#3e4946}.motion-winner{border-color:#72d49a;box-shadow:0 0 0 3px rgba(78,191,121,.28),0 0 28px rgba(78,191,121,.28)}.motion-wrong{border-color:#e16d78;box-shadow:0 0 0 3px rgba(225,109,120,.24)}.motion-target{border-color:#e7bd68}.just-flipped .discard-stack{filter:drop-shadow(0 0 8px rgba(247,215,116,.48))}@media(max-width:1000px){.player-seat{width:clamp(142px,17vw,185px);height:clamp(128px,18vh,172px)}.seat-cards{gap:5px;padding-inline:3px}}@media(max-width:759px){.player-seat{position:relative;left:auto!important;top:auto!important;order:1;width:100%;height:min(23vh,142px);padding:3px;border-radius:8px;transform:none}.player-seat.is-self{grid-column:1/-1;order:2;justify-self:center;width:min(210px,58vw);height:min(24vh,150px)}.player-seat header{gap:2px;padding:0 1px}.player-seat header strong{font-size:8px}.seat-index{font-size:7px}.self-chip,.connection-chip{font-size:6px}.seat-cards{gap:3px;padding:1px}.draw-stack .fruit-card{display:none}.stack-card{height:78%}.draw-stack.actionable::after{font-size:6px}.status-chip{max-width:100%;font-size:6px}.owned-count{display:none}.player-seat footer{justify-content:center}.empty-discard,.empty-stack{font-size:6px}}@media(max-width:374px){.player-seat{height:min(20vh,118px);border-radius:6px}.player-seat:not(.is-self) .draw-stack{display:none}.player-seat:not(.is-self) .seat-cards{grid-template-columns:1fr}.player-seat:not(.is-self) header strong{display:none}.player-seat.is-self{height:128px}.player-seat footer{height:19px}}
</style>
