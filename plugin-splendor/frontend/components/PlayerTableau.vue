<script setup lang="ts">
import type { PlayerView } from '../types'
import { colorInfo, pieceColors, standardColors } from '../types'

withDefaults(defineProps<{ player: PlayerView, self?: boolean, compact?: boolean }>(), {
  self: false,
  compact: false,
})
</script>

<template>
  <article class="player-tableau" :class="{ self, compact, active: player.isActive, forfeited: player.forfeited }" :data-player-id="player.id">
    <header>
      <span class="turn-lamp">{{ player.isActive ? '轮到' : player.connected ? '在线' : '离线' }}</span>
      <strong>{{ player.name }}<small v-if="self">（你）</small></strong>
      <i v-if="player.isFirstPlayer" title="首位玩家标记">Ⅰ</i>
      <b>{{ player.score }}<small>分</small></b>
    </header>
    <div class="engine-strip" aria-label="永久奖励">
      <span v-for="color in standardColors" :key="color" :class="`engine-${color}`">
        <i>{{ colorInfo[color].symbol }}</i><b>{{ player.bonuses[color] }}</b>
      </span>
    </div>
    <div class="piece-strip" aria-label="持有棋子">
      <span v-for="color in pieceColors" :key="color" :class="`piece-${color}`" :title="colorInfo[color].name">
        {{ colorInfo[color].short }} {{ player.pieces[color] }}
      </span>
    </div>
    <footer>
      <span>发展 {{ player.purchasedCount }}</span>
      <span>贵族 {{ player.nobles.length }}</span>
      <span>保留 {{ player.reservations.length }}/3</span>
    </footer>
  </article>
</template>
