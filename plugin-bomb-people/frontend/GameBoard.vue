<script setup lang="ts">
import { computed } from 'vue'
import { ITEM_ART, MAP_ART, PLAYER_ART } from './catalog'
import type { BombEffect, BombGame, BombObject, BombPlayer } from './types'

const props = defineProps<{
  game: BombGame
  selfId: string
  selfInputMask?: number
}>()

const flatCells = computed(() => props.game.board.flatMap((row, y) => (
  row.map((value, x) => ({ x, y, value, key: `${x}:${y}` }))
)))

const dangerSet = computed(() => new Set(props.game.dangerCells.map(([x, y]) => `${x}:${y}`)))
const background = computed(() => MAP_ART[props.game.selectedMap] ?? MAP_ART.magma_crucible)
const effects = computed(() => props.game.effects ?? [])
const carriedBombsByPlayer = computed(() => new Map(
  props.game.bombs
    .filter(bomb => bomb.carriedBy)
    .map(bomb => [bomb.carriedBy as string, bomb]),
))
const latestActionByPlayer = computed(() => {
  const result = new Map<string, BombEffect>()
  for (const effect of effects.value) {
    if (effect.actorId && ['bomb_kicked', 'bomb_punched', 'bomb_picked_up', 'bomb_thrown'].includes(effect.kind)) {
      result.set(effect.actorId, effect)
    }
  }
  return result
})
const placedBombIds = computed(() => new Set(
  effects.value.filter(effect => effect.kind === 'bomb_placed').map(effect => effect.bombId),
))
const thrownBombIds = computed(() => new Set(
  effects.value.filter(effect => effect.kind === 'bomb_thrown').map(effect => effect.bombId),
))

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

function localMovementDirection(player: BombPlayer): [number, number] {
  if (player.id !== props.selfId) return [0, 0]
  const mask = props.selfInputMask ?? 0
  const horizontal = Number(Boolean(mask & 8)) - Number(Boolean(mask & 4))
  const vertical = Number(Boolean(mask & 2)) - Number(Boolean(mask & 1))
  if (horizontal && vertical) {
    if (player.facingX === horizontal) return [horizontal, 0]
    if (player.facingY === vertical) return [0, vertical]
    return [horizontal, 0]
  }
  return [horizontal, vertical]
}

function playerStyle(player: BombPlayer) {
  const size = 100 / props.game.boardSize
  const fallbackInterval = Math.max(2, 4 - player.equipment.speedLevel * 0.65)
  const intervalTicks = player.moveIntervalTicks ?? fallbackInterval
  const [localX, localY] = localMovementDirection(player)
  const locallyMoving = Boolean(localX || localY)
  const facingX = locallyMoving ? localX : player.facingX
  const facingY = locallyMoving ? localY : player.facingY
  const moveDurationMs = player.moving || locallyMoving
    ? Math.max(90, Math.round(intervalTicks * 1_000 / Math.max(1, props.game.tickRate)))
    : 70
  const action = latestActionByPlayer.value.get(player.id)
  return {
    left: '0',
    top: '0',
    width: `${size}%`,
    height: `${size}%`,
    transform: `translate3d(${player.x * 100}%, ${player.y * 100}%, 0)`,
    '--player-color': player.color,
    '--face-scale': facingX < 0 ? -1 : 1,
    '--travel-lean': `${facingX * 4}deg`,
    '--counter-lean': `${facingX * -1.6}deg`,
    '--move-duration': `${moveDurationMs}ms`,
    '--walk-step-duration': `${Math.max(90, moveDurationMs)}ms`,
    '--walk-body-duration': `${Math.max(70, Math.round(moveDurationMs * 0.62))}ms`,
    '--pickup-x': `${(action?.directionX ?? facingX) * 88}%`,
    '--pickup-near-x': `${(action?.directionX ?? facingX) * 23}%`,
    '--pickup-y': `${112 + (action?.directionY ?? facingY) * 30}%`,
  }
}

function bombStyle(bomb: BombObject) {
  return {
    ...objectStyle(bomb.x, bomb.y, 14),
    '--roll-angle': `${(bomb.motionX < 0 || bomb.motionY < 0 ? -1 : 1) * 28}deg`,
  }
}

function playerAnimationClass(player: BombPlayer) {
  const action = latestActionByPlayer.value.get(player.id)
  const [localX, localY] = localMovementDirection(player)
  const locallyMoving = Boolean(localX || localY)
  const facingY = locallyMoving ? localY : player.facingY
  return {
    walking: (player.moving || locallyMoving) && player.alive,
    'local-input': locallyMoving,
    carrying: carriedBombsByPlayer.value.has(player.id),
    'facing-up': facingY < 0,
    'facing-down': facingY > 0,
    'action-kick': action?.kind === 'bomb_kicked',
    'action-punch': action?.kind === 'bomb_punched',
    'action-pickup': action?.kind === 'bomb_picked_up',
    'action-throw': action?.kind === 'bomb_thrown',
  }
}

function carriedBombFor(playerId: string) {
  return carriedBombsByPlayer.value.get(playerId)
}

function carriedFuseText(playerId: string) {
  const bomb = carriedBombFor(playerId)
  return bomb ? fuseText(bomb.fuseTicks) : ''
}

function playerVisualKey(player: BombPlayer) {
  return `${player.id}:${latestActionByPlayer.value.get(player.id)?.id ?? 'idle'}`
}

function impactStyle(effect: BombEffect) {
  return {
    ...objectStyle(effect.targetX ?? effect.x, effect.targetY ?? effect.y, 31),
    '--impact-from-x': `${effect.directionX * -65}%`,
    '--impact-from-y': `${effect.directionY * -65}%`,
    '--impact-to-x': `${effect.directionX * 38}%`,
    '--impact-to-y': `${effect.directionY * 38}%`,
  }
}

function trajectoryStyle(effect: BombEffect) {
  const travelX = (effect.targetX ?? effect.x) - effect.x
  const travelY = (effect.targetY ?? effect.y) - effect.y
  return {
    ...objectStyle(effect.x, effect.y, 30),
    '--travel-x': `${travelX * 100}%`,
    '--travel-y': `${travelY * 100}%`,
    '--half-x': `${travelX * 50}%`,
    '--half-y': `${travelY * 50}%`,
    '--release-x': `${travelX * 17}%`,
    '--release-y': `${travelY * 17 - 145}%`,
    '--spin-release': `${(effect.directionX < 0 || effect.directionY < 0 ? -1 : 1) * 80}deg`,
    '--spin-mid': `${(effect.directionX < 0 || effect.directionY < 0 ? -1 : 1) * 210}deg`,
    '--spin-end': `${(effect.directionX < 0 || effect.directionY < 0 ? -1 : 1) * 430}deg`,
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
      aria-label="炸弹超人 20×20 实时地图。使用 WASD 移动，空格放炸弹，C 引爆遥控定时炸弹，Z 打雷，第一次按 X 拿雷、第二次按 X 扔雷。"
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
        v-show="!bomb.carriedBy"
        :key="`bomb:${bomb.id}`"
        class="board-object bomb"
        :class="{ moving: bomb.moving, remote: bomb.remote, 'just-placed': placedBombIds.has(bomb.id), landing: thrownBombIds.has(bomb.id) }"
        :style="bombStyle(bomb)"
        :title="bomb.remote ? '遥控定时炸弹：仅所有者按 C 引爆' : `炸弹剩余 ${fuseText(bomb.fuseTicks)} 秒`"
      >
        <span class="bomb-body"><i /></span>
        <small>{{ bomb.remote ? 'C' : fuseText(bomb.fuseTicks) }}</small>
      </div>

      <div
        v-for="flame in game.flames"
        :key="`flame:${flame.x}:${flame.y}`"
        class="board-object flame"
        :style="objectStyle(flame.x, flame.y, 18)"
        aria-label="爆炸火焰"
      ><span /></div>

      <template v-for="effect in effects" :key="`effect:${effect.id}`">
        <div
          v-if="effect.kind === 'bomb_exploded'"
          class="board-object explosion-effect"
          :style="objectStyle(effect.x, effect.y, 32)"
          aria-hidden="true"
        >
          <span class="explosion-core" />
          <span class="explosion-ring" />
          <span class="explosion-sparks"><i v-for="spark in 8" :key="spark" /></span>
        </div>
        <div
          v-else-if="effect.kind === 'bomb_kicked' || effect.kind === 'bomb_punched'"
          class="board-object action-impact"
          :class="effect.kind === 'bomb_kicked' ? 'kick-impact' : 'punch-impact'"
          :style="impactStyle(effect)"
          aria-hidden="true"
        >
          <span class="impact-burst" />
          <img :src="ITEM_ART[effect.kind === 'bomb_kicked' ? 'kick' : 'punch']" alt="" draggable="false" />
        </div>
        <div
          v-else-if="effect.kind === 'bomb_thrown'"
          class="board-object throw-effect"
          :style="trajectoryStyle(effect)"
          aria-hidden="true"
        >
          <span class="throw-shadow" />
          <span class="airborne-bomb"><i /></span>
        </div>
        <div
          v-else-if="effect.kind === 'bomb_placed'"
          class="board-object place-effect"
          :style="objectStyle(effect.x, effect.y, 13)"
          aria-hidden="true"
        ><span /><i /></div>
      </template>

      <div
        v-for="player in game.players"
        :key="player.id"
        class="player-piece"
        :class="[{ self: player.id === selfId, eliminated: !player.alive, cursed: player.equipment.cursedTicks > 0, invincible: player.equipment.invincibleTicks > 0 }, playerAnimationClass(player)]"
        :style="playerStyle(player)"
      >
        <span class="player-visual">
          <span class="player-ground-shadow" aria-hidden="true" />
          <span :key="playerVisualKey(player)" class="player-avatar">
            <img class="player-layer player-torso" :src="PLAYER_ART[player.character]" :alt="player.name" draggable="false" />
            <img class="player-layer player-leg player-leg-left" :src="PLAYER_ART[player.character]" alt="" draggable="false" aria-hidden="true" />
            <img class="player-layer player-leg player-leg-right" :src="PLAYER_ART[player.character]" alt="" draggable="false" aria-hidden="true" />
          </span>
          <span
            v-if="carriedBombFor(player.id)"
            :key="`carried:${carriedBombFor(player.id)?.id}`"
            class="carried-bomb-rig"
            :class="{ remote: carriedBombFor(player.id)?.remote }"
            :title="carriedBombFor(player.id)?.remote ? '手中的遥控定时炸弹：所有者按 C 可引爆' : `手中炸弹剩余 ${carriedFuseText(player.id)} 秒`"
          >
            <span class="carry-arm carry-arm-left" aria-hidden="true" />
            <span class="carry-arm carry-arm-right" aria-hidden="true" />
            <span class="carried-bomb-body" aria-hidden="true"><i /></span>
            <small>{{ carriedBombFor(player.id)?.remote ? 'C' : carriedFuseText(player.id) }}</small>
          </span>
          <span class="player-name">{{ player.name }}</span>
        </span>
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
.arena-board { position: relative; width: min(100%, calc(100vh - 112px)); max-width: 100%; aspect-ratio: 1; overflow: hidden; contain: layout paint style; isolation: isolate; border: 3px solid #333b43; border-radius: 16px; background: #151a1e; box-shadow: 0 24px 70px #0009, inset 0 0 0 2px #ffffff12; outline: none; user-select: none; }
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
.bomb { color: white; font-variant-numeric: tabular-nums; transition: left .09s cubic-bezier(.2, .72, .2, 1), top .09s cubic-bezier(.2, .72, .2, 1); }
.bomb-body { position: absolute; width: 72%; height: 72%; border-radius: 50%; background: radial-gradient(circle at 30% 27%, #65717a 0 7%, #222a30 25%, #06080a 72%); border: 1px solid #8b969d; box-shadow: 0 2px 5px #000, inset -3px -4px 5px #000; }
.bomb-body::before { content: ''; position: absolute; width: 32%; height: 22%; left: 55%; top: -12%; border: 3px solid #b88643; border-bottom: 0; border-radius: 50% 50% 0 0; transform: rotate(35deg); }
.bomb-body i { position: absolute; width: 14%; height: 14%; right: -5%; top: -15%; border-radius: 50%; background: #fff3a1; box-shadow: 0 0 6px 2px #ff7a18; animation: fuse .18s infinite alternate; }
.bomb small { z-index: 2; margin-top: 1px; font: 800 clamp(6px, .7vw, 10px)/1 system-ui; text-shadow: 0 1px 2px #000; }
.bomb.remote { color: #dffcff; filter: drop-shadow(0 0 4px #31dbea88); }
.bomb.remote .bomb-body { width: 80%; height: 68%; border: 2px solid #68edf5; border-radius: 24%; background: linear-gradient(145deg, #397987 0 12%, #153a43 13% 58%, #07191e 59% 100%); box-shadow: 0 2px 5px #000, inset 2px 2px 3px #c9fbff55, inset -3px -3px 5px #001014; }
.bomb.remote .bomb-body::before { width: 30%; height: 24%; left: 35%; top: -27%; border: 2px solid #70eaf2; border-bottom: 0; border-radius: 60% 60% 0 0; transform: none; }
.bomb.remote .bomb-body::after { content: ''; position: absolute; inset: 14% 18%; border: 1px solid #78f5fc88; border-radius: 18%; box-shadow: inset 0 0 4px #20e1ef66; }
.bomb.remote .bomb-body i { width: 20%; height: 24%; right: 40%; top: 38%; z-index: 1; background: #91fbff; box-shadow: 0 0 7px 2px #20dcec; animation: remote-signal .65s ease-in-out infinite alternate; }
.bomb.remote small { min-width: 42%; padding: 1px 2px; border: 1px solid #8bf8ff99; border-radius: 3px; color: #dffcff; background: #08262dcc; text-align: center; text-shadow: 0 0 3px #23ddec; }
.bomb.moving .bomb-body { animation: bomb-roll .16s linear infinite; }
.bomb.just-placed { animation: bomb-drop .26s cubic-bezier(.2, 1.4, .5, 1) both; }
.bomb.landing { animation: bomb-land .44s ease-out both; }
.flame { animation: flame-bloom .2s cubic-bezier(.12, .88, .25, 1.35) both; }
.flame span { width: 108%; height: 108%; border-radius: 45% 48% 40% 52%; background: radial-gradient(circle, #fff 0 13%, #ffe16b 14% 34%, #ff7b24 35% 66%, #ed2d24 67% 80%, transparent 81%); filter: drop-shadow(0 0 4px #ff6b1a); animation: flame .13s infinite alternate; }
.ice-tile { background: radial-gradient(circle, #b9fbff99, #3ebbe555 58%, transparent 72%); box-shadow: inset 0 0 5px #dff; }
.place-effect span { position: absolute; width: 82%; height: 82%; border: 2px solid #ffd16c; border-radius: 50%; animation: place-ring .3s ease-out both; }
.place-effect i { position: absolute; width: 20%; height: 20%; border-radius: 50%; background: #fff7bf; box-shadow: 0 0 9px 4px #ffb11b; animation: place-flash .28s ease-out both; }
.explosion-effect { overflow: visible; }
.explosion-core { position: absolute; width: 260%; height: 260%; border-radius: 50%; background: radial-gradient(circle, #fff 0 8%, #fff3a3 9% 20%, #ffb21f 21% 39%, #ff4d16 40% 58%, #c5120b99 59% 70%, transparent 71%); filter: drop-shadow(0 0 9px #ff6a00); animation: explosion-core .36s cubic-bezier(.12, .72, .18, 1) both; }
.explosion-ring { position: absolute; width: 100%; height: 100%; border: 3px solid #fff4af; border-radius: 50%; box-shadow: 0 0 10px #ff841b, inset 0 0 8px #ff5c16; animation: explosion-ring .38s ease-out both; }
.explosion-sparks { position: absolute; inset: 50%; }
.explosion-sparks i { position: absolute; left: -6%; top: -6%; width: 12%; height: 12%; border-radius: 50%; background: #fff5a6; box-shadow: 0 0 5px #ff5b0a; animation: explosion-spark .38s ease-out both; }
.explosion-sparks i:nth-child(1) { --spark-angle: 0deg; }.explosion-sparks i:nth-child(2) { --spark-angle: 45deg; }.explosion-sparks i:nth-child(3) { --spark-angle: 90deg; }.explosion-sparks i:nth-child(4) { --spark-angle: 135deg; }.explosion-sparks i:nth-child(5) { --spark-angle: 180deg; }.explosion-sparks i:nth-child(6) { --spark-angle: 225deg; }.explosion-sparks i:nth-child(7) { --spark-angle: 270deg; }.explosion-sparks i:nth-child(8) { --spark-angle: 315deg; }
.action-impact { overflow: visible; }
.action-impact img { position: absolute; width: 145%; height: 145%; object-fit: contain; filter: drop-shadow(0 0 6px #fff); animation: impact-icon .38s cubic-bezier(.18, .86, .25, 1.25) both; }
.action-impact.kick-impact img { transform-origin: 50% 80%; }
.impact-burst { position: absolute; width: 190%; height: 190%; background: conic-gradient(from 8deg, transparent 0 8%, #fff8b8 9% 12%, transparent 13% 20%, #ff9d2f 21% 25%, transparent 26% 35%, #fff8b8 36% 40%, transparent 41% 55%, #ff9d2f 56% 61%, transparent 62% 72%, #fff8b8 73% 77%, transparent 78%); clip-path: polygon(50% 0, 58% 37%, 88% 12%, 68% 44%, 100% 50%, 68% 56%, 88% 88%, 58% 63%, 50% 100%, 42% 63%, 12% 88%, 32% 56%, 0 50%, 32% 44%, 12% 12%, 42% 37%); animation: impact-burst .34s ease-out both; }
.throw-effect { overflow: visible; }
.airborne-bomb { position: absolute; width: 76%; height: 76%; border: 1px solid #a5b0b6; border-radius: 50%; background: radial-gradient(circle at 30% 26%, #87939b 0 7%, #2a3237 23%, #07090a 72%); box-shadow: inset -3px -4px 5px #000, 0 7px 9px #0009; animation: throw-flight .5s cubic-bezier(.18, .72, .18, 1) both; }
.airborne-bomb::before { content: ''; position: absolute; width: 34%; height: 24%; left: 54%; top: -13%; border: 3px solid #b88643; border-bottom: 0; border-radius: 50% 50% 0 0; transform: rotate(35deg); }
.airborne-bomb i { position: absolute; width: 15%; height: 15%; right: -5%; top: -16%; border-radius: 50%; background: #fff5aa; box-shadow: 0 0 7px 2px #ff7818; }
.throw-shadow { position: absolute; width: 72%; height: 22%; border-radius: 50%; background: #0009; filter: blur(2px); animation: throw-shadow .5s ease-in-out both; }
.player-piece { position: absolute; z-index: 22; pointer-events: none; filter: drop-shadow(0 4px 3px #000b); transition: transform var(--move-duration, 180ms) linear; will-change: transform; backface-visibility: hidden; }
.player-visual { position: absolute; left: 50%; top: 50%; width: 170%; height: 195%; transform: translate(-50%, -58%); }
.player-avatar { position: absolute; inset: 0; display: block; transform: scaleX(var(--face-scale)); transform-origin: 50% 76%; }
.player-layer { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.player-torso { z-index: 3; clip-path: polygon(0 0, 100% 0, 100% 74%, 62% 77%, 50% 75%, 38% 77%, 0 74%); transform-origin: 50% 72%; }
.player-leg { z-index: 2; transform-origin: 50% 67%; }
.player-leg-left { clip-path: polygon(0 61%, 52% 61%, 54% 100%, 0 100%); transform-origin: 43% 67%; }
.player-leg-right { clip-path: polygon(48% 61%, 100% 61%, 100% 100%, 46% 100%); transform-origin: 57% 67%; }
.player-ground-shadow { position: absolute; z-index: -1; left: 23%; right: 23%; bottom: 7%; height: 14%; border-radius: 50%; background: #0009; filter: blur(2px); transform-origin: center; }
.carried-bomb-rig { position: absolute; z-index: 5; left: 50%; top: -2%; width: 43%; height: 43%; transform: translate(-50%, 0); transform-origin: 50% 115%; filter: drop-shadow(0 5px 4px #000b); animation: carry-idle 1s ease-in-out infinite alternate; }
.carried-bomb-body { position: absolute; z-index: 3; inset: 7%; border: 1px solid #a5b0b6; border-radius: 50%; background: radial-gradient(circle at 30% 26%, #87939b 0 7%, #2a3237 23%, #07090a 72%); box-shadow: inset -3px -4px 5px #000, 0 3px 5px #0009; }
.carried-bomb-body::before { content: ''; position: absolute; width: 34%; height: 24%; left: 54%; top: -13%; border: 3px solid #b88643; border-bottom: 0; border-radius: 50% 50% 0 0; transform: rotate(35deg); }
.carried-bomb-body i { position: absolute; width: 15%; height: 15%; right: -5%; top: -16%; border-radius: 50%; background: #fff5aa; box-shadow: 0 0 7px 2px #ff7818; animation: fuse .18s infinite alternate; }
.carried-bomb-rig > small { position: absolute; z-index: 5; left: 50%; top: 49%; transform: translate(-50%, -50%); color: #fff; font: 900 clamp(5px, .58vw, 8px)/1 ui-monospace, monospace; text-shadow: 0 1px 2px #000, 0 0 3px #000; }
.carried-bomb-rig.remote .carried-bomb-body { border-color: #68edf5; border-radius: 24%; background: linear-gradient(145deg, #397987, #153a43 55%, #07191e); box-shadow: inset 0 0 5px #74f5ff66, 0 3px 5px #0009; }
.carried-bomb-rig.remote .carried-bomb-body::before { left: 35%; border-color: #70eaf2; transform: none; }
.carried-bomb-rig.remote .carried-bomb-body i { right: 40%; top: 38%; background: #91fbff; box-shadow: 0 0 7px 2px #20dcec; animation: remote-signal .65s ease-in-out infinite alternate; }
.carried-bomb-rig.remote > small { color: #dffcff; text-shadow: 0 0 4px #20dcec; }
.carry-arm { position: absolute; z-index: 4; top: 62%; width: 42%; height: 16%; border: 1px solid #d6dde0; border-radius: 999px; background: linear-gradient(90deg, var(--player-color), #edf2f4 68%); box-shadow: 0 2px 3px #0008; transform-origin: 12% 50%; }
.carry-arm::after { content: ''; position: absolute; right: -8%; top: -28%; width: 34%; aspect-ratio: 1; border: 1px solid #fff8; border-radius: 50%; background: #f3c7a2; box-shadow: inset -1px -2px #9b654a66; }
.carry-arm-left { left: -16%; transform: rotate(-37deg); }
.carry-arm-right { right: -16%; transform: scaleX(-1) rotate(-37deg); }
.player-name { position: absolute; z-index: 6; left: 50%; bottom: -3%; transform: translateX(-50%); max-width: 160%; padding: 1px 4px; overflow: hidden; color: white; background: #0a0d10d9; border: 1px solid var(--player-color); border-radius: 4px; font: 700 clamp(5px, .62vw, 9px)/1.25 system-ui; text-overflow: ellipsis; white-space: nowrap; }
.player-piece.walking .player-torso { animation: walk-body var(--walk-body-duration, 110ms) ease-in-out infinite alternate; }
.player-piece.walking .player-leg-left { animation: walk-leg-left var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.walking .player-leg-right { animation: walk-leg-right var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.walking .player-ground-shadow { animation: walk-shadow var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.walking .player-visual::after { content: ''; position: absolute; z-index: 1; left: 36%; bottom: 5%; width: 28%; height: 12%; border-radius: 50%; background: radial-gradient(ellipse, #d5c7a66b, transparent 68%); animation: foot-dust var(--walk-step-duration, 180ms) ease-out infinite; }
.player-piece.carrying .player-avatar { transform: scaleX(var(--face-scale)) translateY(3%) scale(.98); }
.player-piece.walking.carrying:not(.action-pickup) .carried-bomb-rig { animation: carry-walk var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.walking.carrying:not(.action-pickup) .carry-arm-left { animation: carry-arm-left var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.walking.carrying:not(.action-pickup) .carry-arm-right { animation: carry-arm-right var(--walk-step-duration, 180ms) ease-in-out infinite alternate; }
.player-piece.action-punch .player-avatar { animation: punch-lunge .38s cubic-bezier(.18, .8, .25, 1) both; }
.player-piece.action-punch .player-torso { animation: punch-body .38s ease-out both; }
.player-piece.action-kick .player-avatar { animation: kick-balance .4s ease-out both; }
.player-piece.action-kick .player-leg-right { z-index: 4; animation: kick-leg .4s cubic-bezier(.2, .72, .24, 1) both; }
.player-piece.action-pickup .player-avatar { animation: pickup-player .5s cubic-bezier(.2, .76, .24, 1) both; }
.player-piece.action-pickup .player-torso { animation: pickup-body .5s cubic-bezier(.2, .76, .24, 1) both; }
.player-piece.action-pickup .carried-bomb-rig { animation: pickup-bomb .5s cubic-bezier(.16, .8, .2, 1) both; }
.player-piece.action-throw .player-visual::before { --arm-face: var(--face-scale); content: ''; position: absolute; z-index: 4; left: 47%; top: 35%; width: 42%; height: 10%; border: 1px solid #d6dde0; border-radius: 999px; background: linear-gradient(90deg, var(--player-color), #edf2f4 68%); box-shadow: 0 2px 3px #0008; transform-origin: 8% 50%; animation: throw-arm .5s cubic-bezier(.18, .78, .2, 1) both; }
.player-piece.action-throw .player-avatar { animation: throw-player .5s cubic-bezier(.2, .7, .2, 1) both; }
.player-piece.action-throw .player-torso { animation: throw-body .5s cubic-bezier(.2, .72, .2, 1) both; }
.player-piece.facing-up .player-avatar { filter: brightness(.88) saturate(.92); }
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
@keyframes remote-signal { to { opacity: .42; transform: scale(.72); box-shadow: 0 0 3px 1px #20dcec; } }
@keyframes bomb-roll { to { transform: rotate(var(--roll-angle)) translateY(-7%); } }
@keyframes bomb-drop { 0% { opacity: 0; transform: translateY(-95%) scale(.45); } 68% { opacity: 1; transform: translateY(8%) scale(1.16, .84); } 100% { transform: none; } }
@keyframes bomb-land { 0%, 62% { opacity: 0; transform: scale(.55); } 72% { opacity: 1; transform: scale(1.28, .76); } 86% { transform: scale(.9, 1.1); } 100% { opacity: 1; transform: none; } }
@keyframes flame-bloom { from { opacity: 0; transform: scale(.08); } 72% { opacity: 1; transform: scale(1.24); } to { transform: none; } }
@keyframes flame { to { transform: scale(.84) rotate(8deg); filter: drop-shadow(0 0 7px #ffbe24); } }
@keyframes place-ring { from { opacity: 1; transform: scale(.25); } to { opacity: 0; transform: scale(1.7); } }
@keyframes place-flash { from { opacity: 1; transform: scale(1.8); } to { opacity: 0; transform: scale(.2); } }
@keyframes explosion-core { 0% { opacity: 0; transform: scale(.06); } 18% { opacity: 1; transform: scale(.56); } 58% { opacity: 1; transform: scale(1.18); } 100% { opacity: 0; transform: scale(1.7); } }
@keyframes explosion-ring { 0% { opacity: 1; transform: scale(.12); } 100% { opacity: 0; transform: scale(3.7); border-width: 1px; } }
@keyframes explosion-spark { 0% { opacity: 1; transform: rotate(var(--spark-angle)) translateX(28%) scale(1); } 100% { opacity: 0; transform: rotate(var(--spark-angle)) translateX(280%) scale(.2); } }
@keyframes impact-icon { 0% { opacity: 0; transform: translate(var(--impact-from-x), var(--impact-from-y)) scale(.35) rotate(-24deg); } 45% { opacity: 1; transform: translate(0) scale(1.35) rotate(9deg); } 100% { opacity: 0; transform: translate(var(--impact-to-x), var(--impact-to-y)) scale(.78) rotate(18deg); } }
@keyframes impact-burst { 0% { opacity: 0; transform: scale(.2) rotate(-12deg); } 42% { opacity: 1; transform: scale(1.08) rotate(4deg); } 100% { opacity: 0; transform: scale(1.65) rotate(18deg); } }
@keyframes throw-flight { 0% { opacity: 1; transform: translate(0, -105%) scale(.92) rotate(0deg); } 18% { transform: translate(var(--release-x), var(--release-y)) scale(1.08) rotate(var(--spin-release)); } 56% { opacity: 1; transform: translate(var(--half-x), calc(var(--half-y) - 175%)) scale(1.3) rotate(var(--spin-mid)); } 88% { opacity: 1; transform: translate(var(--travel-x), calc(var(--travel-y) - 16%)) scale(.92) rotate(var(--spin-end)); } 100% { opacity: 0; transform: translate(var(--travel-x), var(--travel-y)) scale(.84, .72) rotate(var(--spin-end)); } }
@keyframes throw-shadow { 0% { opacity: .32; transform: translate(0, 35%) scale(.48); } 52% { opacity: .14; transform: translate(var(--half-x), calc(var(--half-y) + 35%)) scale(.38); } 88%, 100% { opacity: .55; transform: translate(var(--travel-x), calc(var(--travel-y) + 35%)) scale(.82); } }
@keyframes walk-body { from { transform: translateY(1%) rotate(var(--counter-lean)); } to { transform: translateY(-5%) rotate(var(--travel-lean)); } }
@keyframes walk-leg-left { from { transform: translate(-3%, -1%) rotate(-9deg); } to { transform: translate(5%, 3%) rotate(10deg); } }
@keyframes walk-leg-right { from { transform: translate(5%, 3%) rotate(10deg); } to { transform: translate(-3%, -1%) rotate(-9deg); } }
@keyframes walk-shadow { from { transform: scaleX(.88); opacity: .58; } to { transform: scaleX(1.12); opacity: .82; } }
@keyframes foot-dust { 0% { opacity: 0; transform: translateY(0) scale(.45); } 38% { opacity: .75; } 100% { opacity: 0; transform: translateY(-45%) scale(1.5); } }
@keyframes carry-idle { from { transform: translate(-50%, 1%) rotate(-1.5deg); } to { transform: translate(-50%, -5%) rotate(1.5deg); } }
@keyframes carry-walk { from { transform: translate(-50%, 2%) rotate(-3deg); } to { transform: translate(-50%, -8%) rotate(3deg); } }
@keyframes carry-arm-left { from { transform: rotate(-34deg); } to { transform: rotate(-41deg); } }
@keyframes carry-arm-right { from { transform: scaleX(-1) rotate(-34deg); } to { transform: scaleX(-1) rotate(-41deg); } }
@keyframes pickup-bomb { 0% { opacity: .45; transform: translate(calc(-50% + var(--pickup-x)), var(--pickup-y)) scale(.52) rotate(-24deg); } 42% { opacity: 1; transform: translate(calc(-50% + var(--pickup-near-x)), 34%) scale(.82) rotate(8deg); } 72% { transform: translate(-50%, -12%) scale(1.13, .9) rotate(-3deg); } 100% { opacity: 1; transform: translate(-50%, 0) scale(1) rotate(0); } }
@keyframes pickup-player { 0%, 100% { transform: scaleX(var(--face-scale)) translate(0); } 28% { transform: scaleX(var(--face-scale)) translate(5%, 8%) rotate(5deg) scale(1.02, .94); } 64% { transform: scaleX(var(--face-scale)) translate(-2%, -3%) rotate(-3deg); } }
@keyframes pickup-body { 0%, 100% { transform: none; } 30% { transform: translate(4%, 7%) rotate(7deg); } 68% { transform: translate(-2%, -4%) rotate(-4deg); } }
@keyframes punch-lunge { 0%, 100% { transform: scaleX(var(--face-scale)) translate(0); } 26% { transform: scaleX(var(--face-scale)) translateX(-7%) rotate(-5deg); } 58% { transform: scaleX(var(--face-scale)) translateX(15%) rotate(7deg) scale(1.08, .94); } }
@keyframes punch-body { 0%, 100% { transform: none; } 34% { transform: rotate(-5deg) translateY(2%); } 62% { transform: rotate(8deg) translate(8%, -2%); } }
@keyframes kick-balance { 0%, 100% { transform: scaleX(var(--face-scale)) translate(0); } 35% { transform: scaleX(var(--face-scale)) translateX(-8%) rotate(-7deg); } 64% { transform: scaleX(var(--face-scale)) translateX(7%) rotate(5deg); } }
@keyframes kick-leg { 0%, 100% { transform: none; } 30% { transform: translate(-5%, -2%) rotate(-16deg); } 62% { transform: translate(19%, -15%) rotate(27deg) scaleY(.94); } }
@keyframes throw-player { 0%, 100% { transform: scaleX(var(--face-scale)) translate(0); } 18% { transform: scaleX(var(--face-scale)) translate(-7%, 5%) rotate(-7deg) scale(1.02, .96); } 44% { transform: scaleX(var(--face-scale)) translate(9%, -7%) rotate(11deg) scale(.97, 1.04); } 72% { transform: scaleX(var(--face-scale)) translate(4%, -2%) rotate(5deg); } }
@keyframes throw-body { 0%, 100% { transform: none; } 20% { transform: translate(-4%, 5%) rotate(-9deg); } 45% { transform: translate(9%, -8%) rotate(13deg); } 74% { transform: translate(3%, -2%) rotate(4deg); } }
@keyframes throw-arm { 0% { opacity: 0; transform: scaleX(var(--arm-face)) rotate(-76deg) translateX(-8%); } 16% { opacity: 1; transform: scaleX(var(--arm-face)) rotate(-64deg) translateX(-4%); } 46% { opacity: 1; transform: scaleX(var(--arm-face)) rotate(20deg) translateX(12%); } 78% { opacity: .72; transform: scaleX(var(--arm-face)) rotate(48deg) translateX(6%); } 100% { opacity: 0; transform: scaleX(var(--arm-face)) rotate(36deg); } }
@keyframes invincible { to { filter: drop-shadow(0 0 9px #fff) drop-shadow(0 0 12px #ffd53d); } }
@media (hover: none) and (pointer: coarse) { .arena-frame { height: 100%; align-items: start; }.arena-board { width: min(100%, calc(100dvh - 96px - env(safe-area-inset-top) - env(safe-area-inset-bottom))); max-height: calc(100dvh - 96px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); border-radius: 10px; border-width: 2px; touch-action: none; } }
@media (prefers-reduced-motion: reduce) { .item, .bomb, .bomb-body, .flame, .flame span, .player-piece, .player-piece *, .player-visual::before, .place-effect *, .explosion-effect *, .action-impact *, .throw-effect *, .tile.danger::after { animation: none !important; transition: none; } }
</style>
