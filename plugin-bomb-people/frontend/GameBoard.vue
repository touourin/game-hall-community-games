<script setup lang="ts">
import { computed } from 'vue'
import { ITEM_ART, MAP_ART, PLAYER_ART } from './catalog'
import type { BombGame } from './types'

const props = defineProps<{
  game: BombGame
  selfId: string
}>()

const flatCells = computed(() => props.game.board.flatMap((row, y) => (
  row.map((value, x) => ({ x, y, value, key: `${x}:${y}` }))
)))

const dangerSet = computed(() => new Set(props.game.dangerCells.map(([x, y]) => `${x}:${y}`)))
const background = computed(() => MAP_ART[props.game.selectedMap] ?? MAP_ART.magma_crucible)

function objectStyle(x: number, y: number, z = 10) {
  const size = 100 / props.game.boardSize
  return {
    left: `${x * size}%`,
    top: `${y * size}%`,
    width: `${size}%`,
    height: `${size}%`,
    zIndex: z,
  }
}

function playerStyle(x: number, y: number, color: string) {
  const size = 100 / props.game.boardSize
  return {
    left: `${(x + 0.5) * size}%`,
    top: `${(y + 0.5) * size}%`,
    width: `${size * 1.7}%`,
    height: `${size * 1.95}%`,
    '--player-color': color,
  }
}

function tileClass(value: number) {
  return {
    hard: value === 1,
    soft: value === 2,
    stone: value === 3,
  }
}

function fuseText(ticks: number) {
  return Math.max(0, ticks / props.game.tickRate).toFixed(1)
}
</script>

<template>
  <div class="arena-frame">
    <div
      class="arena-board"
      role="application"
      tabindex="0"
      aria-label="炸弹超人 20×20 实时地图。使用 WASD 移动，空格放炸弹，Z 打雷，X 扔雷。"
    >
      <img class="map-art" :src="background" :alt="`${game.currentMap.name}地图背景`" draggable="false" />
      <div class="floor-grid" aria-hidden="true" />

      <div class="tile-grid" aria-hidden="true">
        <div
          v-for="cell in flatCells"
          :key="cell.key"
          class="tile"
          :class="[tileClass(cell.value), { danger: dangerSet.has(cell.key) }]"
        />
      </div>

      <div
        v-for="tile in game.iceTiles"
        :key="`ice:${tile.x}:${tile.y}`"
        class="board-object ice-tile"
        :style="objectStyle(tile.x, tile.y, 5)"
        aria-hidden="true"
      />

      <div
        v-for="item in game.items"
        :key="`item:${item.id}`"
        class="board-object item"
        :style="objectStyle(item.x, item.y, 12)"
        :title="game.itemLabels[item.kind] ?? item.kind"
      >
        <img :src="ITEM_ART[item.kind]" :alt="game.itemLabels[item.kind] ?? item.kind" draggable="false" />
      </div>

      <div
        v-for="bomb in game.bombs"
        :key="`bomb:${bomb.id}`"
        class="board-object bomb"
        :class="{ moving: bomb.moving }"
        :style="objectStyle(bomb.x, bomb.y, 14)"
        :title="`炸弹剩余 ${fuseText(bomb.fuseTicks)} 秒`"
      >
        <span class="bomb-body"><i /></span>
        <small>{{ fuseText(bomb.fuseTicks) }}</small>
      </div>

      <div
        v-for="flame in game.flames"
        :key="`flame:${flame.x}:${flame.y}`"
        class="board-object flame"
        :style="objectStyle(flame.x, flame.y, 18)"
        aria-label="爆炸火焰"
      ><span /></div>

      <div
        v-for="player in game.players"
        :key="player.id"
        class="player-piece"
        :class="{ self: player.id === selfId, eliminated: !player.alive, cursed: player.equipment.cursedTicks > 0, invincible: player.equipment.invincibleTicks > 0 }"
        :style="playerStyle(player.x, player.y, player.color)"
      >
        <img :src="PLAYER_ART[player.character]" :alt="player.name" draggable="false" />
        <span>{{ player.name }}</span>
      </div>

      <div v-if="game.stage === 'countdown'" class="stage-overlay countdown" aria-live="assertive">
        <small>GET READY</small>
        <strong>{{ Math.max(1, Math.ceil(game.stageTicksRemaining / game.tickRate)) }}</strong>
        <span>{{ game.currentMap.name }}</span>
      </div>
      <div v-else-if="game.frozen" class="stage-overlay frozen" aria-live="polite">
        <strong>对局暂停</strong><span>等待至少一位玩家恢复连接</span>
      </div>
      <div v-else-if="game.stage === 'collapse'" class="collapse-alert" aria-live="assertive">
        落石封场 · {{ game.collapsePlaced }}/{{ game.collapseTotal }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.arena-frame { width: 100%; min-width: 0; display: grid; place-items: center; }
.arena-board { position: relative; width: min(100%, calc(100vh - 112px)); max-width: 100%; aspect-ratio: 1; overflow: hidden; isolation: isolate; border: 3px solid #333b43; border-radius: 16px; background: #151a1e; box-shadow: 0 24px 70px #0009, inset 0 0 0 2px #ffffff12; outline: none; user-select: none; }
.arena-board:focus-visible { border-color: #f8c45b; box-shadow: 0 0 0 3px #f8c45b55, 0 24px 70px #0009; }
.map-art { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; object-fit: cover; opacity: .34; filter: saturate(.88) contrast(1.08) brightness(.75); }
.floor-grid { position: absolute; inset: 0; z-index: 1; background-image: linear-gradient(#aab3b41f 1px, transparent 1px), linear-gradient(90deg, #aab3b41f 1px, transparent 1px); background-size: 5% 5%; box-shadow: inset 0 0 80px #000a; }
.tile-grid { position: absolute; inset: 0; z-index: 4; display: grid; grid-template-columns: repeat(20, 1fr); grid-template-rows: repeat(20, 1fr); pointer-events: none; }
.tile { position: relative; min-width: 0; min-height: 0; }
.tile.hard::before, .tile.soft::before, .tile.stone::before { content: ''; position: absolute; inset: 4%; border-radius: 19%; }
.tile.hard::before { background: linear-gradient(145deg, #8b9497 0 16%, #464f53 17% 58%, #22292d 59% 100%); border: 1px solid #b3bec0; box-shadow: inset 2px 2px 2px #e7eeee55, inset -3px -3px 4px #05070899, 0 2px 3px #000a; }
.tile.hard::after { content: ''; position: absolute; inset: 29%; border: 1px solid #bec7c966; border-radius: 30%; box-shadow: 0 0 0 2px #1f2528; }
.tile.soft::before { background: linear-gradient(135deg, transparent 42%, #5d3012 43% 53%, transparent 54%), linear-gradient(45deg, transparent 42%, #6b3815 43% 53%, transparent 54%), linear-gradient(#dc8a34, #94501c); border: 1px solid #ffbd66; box-shadow: inset 2px 2px #ffd09155, inset -3px -3px #4a220d88, 0 2px 3px #000a; }
.tile.soft::after { content: ''; position: absolute; inset: 12%; border: 1px solid #663210bb; border-radius: 10%; }
.tile.stone::before { background: radial-gradient(circle at 32% 25%, #899095 0 12%, transparent 13%), linear-gradient(145deg, #4d5358, #15191c 64%); border: 2px solid #0b0d0f; box-shadow: inset 2px 2px #aab0b055, 0 3px 5px #000c; clip-path: polygon(11% 20%, 29% 4%, 57% 8%, 85% 27%, 95% 59%, 76% 91%, 33% 96%, 5% 70%); }
.tile.danger:not(.stone)::after { content: ''; position: absolute; inset: 7%; border: 2px solid #ff4747; border-radius: 24%; box-shadow: 0 0 8px #ff3b30; animation: danger-pulse .42s infinite alternate; }
.board-object { position: absolute; pointer-events: none; display: grid; place-items: center; }
.item { padding: .25%; filter: drop-shadow(0 1px 2px #000) drop-shadow(0 0 4px #fff8); animation: item-bob .85s ease-in-out infinite alternate; }
.item img { width: 88%; height: 88%; object-fit: contain; }
.bomb { color: white; font-variant-numeric: tabular-nums; }
.bomb-body { position: absolute; width: 72%; height: 72%; border-radius: 50%; background: radial-gradient(circle at 30% 27%, #65717a 0 7%, #222a30 25%, #06080a 72%); border: 1px solid #8b969d; box-shadow: 0 2px 5px #000, inset -3px -4px 5px #000; }
.bomb-body::before { content: ''; position: absolute; width: 32%; height: 22%; left: 55%; top: -12%; border: 3px solid #b88643; border-bottom: 0; border-radius: 50% 50% 0 0; transform: rotate(35deg); }
.bomb-body i { position: absolute; width: 14%; height: 14%; right: -5%; top: -15%; border-radius: 50%; background: #fff3a1; box-shadow: 0 0 6px 2px #ff7a18; animation: fuse .18s infinite alternate; }
.bomb small { z-index: 2; margin-top: 1px; font: 800 clamp(6px, .7vw, 10px)/1 system-ui; text-shadow: 0 1px 2px #000; }
.bomb.moving { animation: bomb-roll .12s linear infinite; }
.flame span { width: 92%; height: 92%; border-radius: 45% 48% 40% 52%; background: radial-gradient(circle, #fff 0 13%, #ffe16b 14% 34%, #ff7b24 35% 66%, #ed2d24 67% 80%, transparent 81%); filter: drop-shadow(0 0 4px #ff6b1a); animation: flame .13s infinite alternate; }
.ice-tile { background: radial-gradient(circle, #b9fbff99, #3ebbe555 58%, transparent 72%); box-shadow: inset 0 0 5px #dff; }
.player-piece { position: absolute; z-index: 22; transform: translate(-50%, -58%); pointer-events: none; filter: drop-shadow(0 4px 3px #000b); transition: left .09s linear, top .09s linear; }
.player-piece img { width: 100%; height: 100%; object-fit: contain; }
.player-piece > span { position: absolute; left: 50%; bottom: -3%; transform: translateX(-50%); max-width: 160%; padding: 1px 4px; overflow: hidden; color: white; background: #0a0d10d9; border: 1px solid var(--player-color); border-radius: 4px; font: 700 clamp(5px, .62vw, 9px)/1.25 system-ui; text-overflow: ellipsis; white-space: nowrap; }
.player-piece.self { filter: drop-shadow(0 0 5px var(--player-color)) drop-shadow(0 4px 3px #000); }
.player-piece.eliminated { opacity: .25; filter: grayscale(1); }
.player-piece.cursed { filter: drop-shadow(0 0 6px #93ff35) hue-rotate(35deg); }
.player-piece.invincible { animation: invincible .24s infinite alternate; }
.stage-overlay { position: absolute; inset: 0; z-index: 40; display: grid; place-content: center; justify-items: center; gap: 8px; color: white; background: #06090c99; text-align: center; backdrop-filter: blur(2px); }
.stage-overlay small { letter-spacing: .3em; font-weight: 800; color: #ffc862; }
.stage-overlay strong { font-size: clamp(64px, 12vw, 160px); line-height: .9; text-shadow: 0 5px 0 #8e341b, 0 0 30px #ffbf54; }
.stage-overlay span { font-weight: 700; letter-spacing: .12em; }
.stage-overlay.frozen strong { font-size: clamp(28px, 5vw, 54px); }
.stage-overlay.frozen span { color: #d9e1e4; }
.collapse-alert { position: absolute; z-index: 35; top: 1.4%; left: 50%; transform: translateX(-50%); padding: 5px 11px; border: 1px solid #ff766e; border-radius: 999px; color: white; background: #8b1616df; box-shadow: 0 0 16px #ff3838aa; font: 800 clamp(8px, .9vw, 12px)/1.2 system-ui; letter-spacing: .08em; }
@keyframes danger-pulse { to { opacity: .25; transform: scale(.82); } }
@keyframes item-bob { to { transform: translateY(-8%) scale(1.04); } }
@keyframes fuse { to { transform: scale(1.5); background: white; } }
@keyframes bomb-roll { to { transform: rotate(18deg); } }
@keyframes flame { to { transform: scale(.84) rotate(8deg); filter: drop-shadow(0 0 7px #ffbe24); } }
@keyframes invincible { to { filter: drop-shadow(0 0 9px #fff) drop-shadow(0 0 12px #ffd53d); } }
@media (max-width: 900px) { .arena-board { width: 100%; border-radius: 10px; border-width: 2px; } }
@media (prefers-reduced-motion: reduce) { .item, .bomb, .flame span, .player-piece, .tile.danger::after { animation: none !important; transition: none; } }
</style>
