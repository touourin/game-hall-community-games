<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'
import FruitCard from './FruitCard.vue'
import type { HalliGalliEvent, HalliGalliPlayerView } from '../types'

type Point = { x: number; y: number | string }
type Flight = { id: string; style: CSSProperties; delay: number }

const props = defineProps<{
  event: HalliGalliEvent
  players: HalliGalliPlayerView[]
}>()

const widePositions: Record<number, Point[]> = {
  2: [{ x: 50, y: 80 }, { x: 50, y: 16 }],
  3: [{ x: 50, y: 80 }, { x: 18, y: 22 }, { x: 82, y: 22 }],
  4: [{ x: 50, y: 80 }, { x: 15, y: 48 }, { x: 50, y: 14 }, { x: 85, y: 48 }],
  5: [{ x: 50, y: 81 }, { x: 14, y: 65 }, { x: 20, y: 20 }, { x: 80, y: 20 }, { x: 86, y: 65 }],
  6: [{ x: 50, y: 81 }, { x: 12, y: 65 }, { x: 17, y: 20 }, { x: 50, y: 12 }, { x: 83, y: 20 }, { x: 88, y: 65 }],
}

function point(playerId: string | null | undefined): Point {
  const player = props.players.find(item => item.id === playerId)
  return widePositions[props.players.length]?.[player?.relativeSeat ?? 0] ?? { x: 50, y: 50 }
}

function compactPoint(playerId: string | null | undefined): Point {
  const player = props.players.find(item => item.id === playerId)
  if (!player || player.relativeSeat === 0) return { x: 50, y: 'var(--compact-self-y)' }
  const opponentColumns = Math.max(1, props.players.length - 1)
  return { x: ((player.relativeSeat - .5) / opponentColumns) * 100, y: 'var(--compact-opponent-y)' }
}

function coordinate(value: number | string): string {
  return typeof value === 'number' ? `${value}%` : value
}

function styleBetween(from: Point, to: Point, delay: number): CSSProperties {
  return {
    '--from-x': coordinate(from.x), '--from-y': coordinate(from.y),
    '--to-x': coordinate(to.x), '--to-y': coordinate(to.y),
    '--flight-delay': `${delay}ms`,
  } as CSSProperties
}

function flightStyle(fromId: string | null | undefined, toId: string | null | undefined, delay: number): CSSProperties {
  const wide = styleBetween(point(fromId), point(toId), delay)
  const from = compactPoint(fromId)
  const to = compactPoint(toId)
  return {
    ...wide,
    '--compact-from-x': coordinate(from.x), '--compact-from-y': coordinate(from.y),
    '--compact-to-x': coordinate(to.x), '--compact-to-y': coordinate(to.y),
  } as CSSProperties
}

const flights = computed<Flight[]>(() => {
  const cue = props.event.cue
  const result: Flight[] = []
  if (cue === 'collect_piles') {
    const winnerId = String(props.event.data.winnerPlayerId ?? props.event.targetPlayerIds[0] ?? props.event.actorPlayerId ?? '')
    const sources = (props.event.data.sourceCounts ?? {}) as Record<string, number>
    Object.entries(sources).filter(([, count]) => count > 0).forEach(([sourceId], index) => {
      result.push({ id: `collect-${sourceId}`, style: flightStyle(sourceId, winnerId, index * 34), delay: index * 34 })
    })
  } else if (cue === 'penalty_transfer') {
    const penalties = (props.event.data.penalties ?? []) as { toPlayerId: string; count: number }[]
    penalties.forEach((penalty, index) => {
      result.push({ id: `penalty-${penalty.toPlayerId}`, style: flightStyle(props.event.actorPlayerId, penalty.toPlayerId, index * 42), delay: index * 42 })
    })
  }
  return result
})

const actorStyle = computed<CSSProperties>(() => {
  const actor = point(props.event.actorPlayerId)
  const compactActor = compactPoint(props.event.actorPlayerId)
  return {
    '--actor-x': `${actor.x}%`, '--actor-y': `${actor.y}%`,
    '--compact-actor-x': coordinate(compactActor.x), '--compact-actor-y': coordinate(compactActor.y),
  } as CSSProperties
})
</script>

<template>
  <div
    class="motion-layer"
    :class="`cue-${event.cue.replaceAll('_', '-')}`"
    :data-animation-cue="event.cue"
    :style="actorStyle"
    aria-hidden="true"
  >
    <div v-if="event.cue === 'round_deal'" class="deal-fan">
      <FruitCard v-for="index in 5" :key="index" face-down compact decorative />
    </div>
    <div v-if="event.cue === 'card_flip' && event.data.card" class="flip-flight">
      <FruitCard :card="event.data.card" compact decorative />
    </div>
    <div v-if="event.cue === 'bell_press_local' || event.cue === 'bell_confirmed'" class="bell-wave">
      <i /><i /><i />
    </div>
    <div
      v-for="flight in flights"
      :key="flight.id"
      class="flying-card"
      :class="event.cue === 'penalty_transfer' ? 'penalty-card' : 'collection-card'"
      :style="flight.style"
    >
      <FruitCard face-down compact decorative />
    </div>
    <div v-if="event.cue === 'player_eliminated'" class="elimination-mark">退出</div>
    <div v-if="event.cue === 'final_duel_armed'" class="duel-ribbon">FINAL BELL · 下一次铃决定终局</div>
    <div v-if="event.cue === 'result_enter'" class="result-burst">
      <i v-for="index in 12" :key="index" :style="({ '--ray': index } as CSSProperties)" />
      <strong>结算完成</strong>
    </div>
  </div>
</template>
