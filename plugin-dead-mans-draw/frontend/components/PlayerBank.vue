<script setup lang="ts">
import type { PlayerView, SuitView } from '../types'
import LootCard from './LootCard.vue'
import SuitIcon from './SuitIcon.vue'

withDefaults(defineProps<{
  player: PlayerView
  suits: SuitView[]
  self?: boolean
  compact?: boolean
}>(), {
  self: false,
  compact: false,
})
</script>

<template>
  <section class="player-bank" :class="{ self, compact, active: player.isActive, forfeited: player.forfeited }" :data-player-id="player.id">
    <header>
      <span class="avatar">{{ player.displayName.slice(0, 1) }}</span>
      <div><strong>{{ player.displayName }}<em v-if="self"> · 你</em></strong><small>{{ player.trait?.nameZh || (player.selectingTrait ? '选择特性中' : '无特性') }}</small></div>
      <b>{{ player.liveScore }}<small>分</small></b>
    </header>
    <div class="bank-grid" :aria-label="`${player.displayName}的银行`">
      <article v-for="(stack, index) in player.bank" :key="stack.suit" class="bank-slot" :class="{ filled: stack.count > 0 }" :data-suit="stack.suit">
        <LootCard v-if="stack.cards[0]" :card="stack.cards[0]" compact />
        <div v-else class="empty-card" :style="{ '--suit-color': suits[index]?.color }">
          <SuitIcon :suit="stack.suit" :size="compact ? 18 : 22" :label="suits[index]?.nameZh" />
        </div>
        <span>{{ suits[index]?.nameZh }}<i>{{ stack.count ? `×${stack.count}` : '—' }}</i></span>
      </article>
    </div>
  </section>
</template>

<style scoped>
.player-bank { min-width: 0; padding: 10px; border: 1px solid #557370; border-radius: 17px; color: #fff9ea; background: linear-gradient(145deg, #193b39, #153332); box-shadow: inset 0 1px #ffffff12, 0 10px 22px #06181755; transition: border-color .2s, box-shadow .2s, opacity .2s; }
.player-bank.active { border-color: #f2c96d; box-shadow: 0 0 0 2px #b28a4a66, 0 10px 26px #06181780; }
.player-bank.forfeited { opacity: .48; filter: grayscale(.65); }
.player-bank > header { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 9px; align-items: center; margin-bottom: 8px; }
.avatar { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 50%; color: #142f2f; background: #b28a4a; font-weight: 900; }
.player-bank header div { min-width: 0; display: grid; }
.player-bank header strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.player-bank header strong em { color: #f2c96d; font-style: normal; }
.player-bank header div small { overflow: hidden; color: #afc0b9; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.player-bank header > b { color: #f2c96d; font-size: 24px; line-height: 1; }
.player-bank header > b small { margin-left: 2px; font-size: 9px; }
.bank-grid { display: grid; grid-template-columns: repeat(10, minmax(46px, 1fr)); gap: 5px; }
.bank-slot { min-width: 0; display: grid; justify-items: center; gap: 3px; }
.bank-slot :deep(.loot-card) { width: min(100%, 58px); min-width: 0; }
.empty-card { display: grid; width: min(100%, 58px); aspect-ratio: 5 / 7; place-items: center; border: 1px dashed #6c8a86; border-radius: 8px; color: var(--suit-color, #6c8a86); background: #0f2b2a; }
.bank-slot > span { width: 100%; overflow: hidden; color: #c9d5cf; font-size: 8px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }
.bank-slot > span i { margin-left: 2px; color: #f2c96d; font-style: normal; }
.player-bank.compact { padding: 8px; }
.player-bank.compact > header { margin-bottom: 6px; }
.player-bank.compact .bank-grid { grid-template-columns: repeat(5, minmax(34px, 1fr)); gap: 3px; }
.player-bank.compact .bank-slot :deep(.loot-card), .player-bank.compact .empty-card { width: 36px; min-width: 36px; }
.player-bank.compact .bank-slot > span { display: none; }
.player-bank.compact .avatar { width: 28px; height: 28px; font-size: 12px; }
.player-bank.compact header > b { font-size: 21px; }
@media (max-width: 920px) {
  .player-bank.self .bank-grid { grid-template-columns: repeat(5, minmax(48px, 1fr)); row-gap: 8px; }
}
</style>
