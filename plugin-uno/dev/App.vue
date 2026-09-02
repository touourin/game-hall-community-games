<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type { UnoCardModel, UnoEvent, UnoGameView } from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

const playerNames = ['晨星', '余烬', '青岚', '星河', '琥珀', '霜蓝', '弦月', '黑曜']
const requestedPlayers = Number(new URLSearchParams(window.location.search).get('players'))
const playerCount = ref(Math.min(8, Math.max(3, Number.isFinite(requestedPlayers) ? requestedPlayers : 8)))
const eventSequence = ref(20)

const cards: Record<string, UnoCardModel> = {
  redSeven: { id: 'red-7-a', color: 'red', kind: 'number', value: 7, label: '赤红 7' },
  yellowThree: { id: 'yellow-3-a', color: 'yellow', kind: 'number', value: 3, label: '琥珀 3' },
  greenSkip: { id: 'green-skip-a', color: 'green', kind: 'skip', value: null, label: '翠绿 跳过' },
  blueReverse: { id: 'blue-reverse-a', color: 'blue', kind: 'reverse', value: null, label: '湛蓝 反转' },
  redDrawTwo: { id: 'red-draw-two-a', color: 'red', kind: 'draw_two', value: null, label: '赤红 +2' },
  wild: { id: 'wild-1', color: null, kind: 'wild', value: null, label: '变色' },
  wildFour: { id: 'wild-draw-four-1', color: null, kind: 'wild_draw_four', value: null, label: '变色 +4' },
  blueFive: { id: 'blue-5-a', color: 'blue', kind: 'number', value: 5, label: '湛蓝 5' },
}

const hand = Object.values(cards)

function makeSnapshot(count: number): ArcadeSnapshot {
  const players = playerNames.slice(0, count).map((name, index) => ({
    id: `p${index + 1}`,
    name,
    seat: index,
    online: true,
  }))
  const cardCounts = Object.fromEntries(players.map((player, index) => [
    player.id,
    index === 0 ? hand.length : Math.max(1, 8 - index),
  ]))
  const game: UnoGameView = {
    colors: [
      { id: 'red', label: '赤红' },
      { id: 'yellow', label: '琥珀' },
      { id: 'green', label: '翠绿' },
      { id: 'blue', label: '湛蓝' },
    ],
    turnOrder: players.map((player) => player.id),
    currentPlayerId: 'p1',
    direction: 1,
    activeColor: 'red',
    stage: 'turn',
    topCard: { id: 'red-5-a', color: 'red', kind: 'number', value: 5, label: '赤红 5' },
    hand,
    cardCounts,
    drawPileCount: 43,
    discardPileCount: 17,
    drawnCardId: null,
    playableCardIds: [cards.redSeven.id, cards.redDrawTwo.id, cards.wild.id],
    pendingDrawTotal: 0,
    pendingDrawTargetPlayerId: null,
    pendingDrawSourcePlayerId: null,
    canTakePenalty: false,
    canDraw: true,
    canKeepDrawn: false,
    canCatchUno: false,
    unoVulnerablePlayerId: null,
    forfeitedPlayerIds: [],
    winnerPlayerIds: [],
    latestEvent: null,
    history: [
      { type: 'start', message: `${playerNames[0]} 先手，翻开赤红 5` },
      { type: 'play', playerId: 'p3', message: '青岚打出琥珀 5' },
      { type: 'reverse', playerId: 'p2', message: '余烬打出湛蓝反转' },
    ],
  }
  return {
    revision: 1,
    roomCode: 'PRISM',
    gameKey: 'plugin-uno',
    gameName: 'UNO · 光域对决',
    phase: 'playing',
    options: {},
    hostId: 'p1',
    self: players[0],
    viewer: { mode: 'player' },
    players,
    requiredPlayers: 2,
    roundNumber: 1,
    winner: null,
    winnerPlayerIds: [],
    winReason: null,
    actions: {
      canStart: false,
      canRestart: false,
      canAct: true,
      canKickPlayers: false,
      canDissolve: true,
      canEditRules: false,
      canRequestUndo: false,
      canRequestDraw: false,
      canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 200, messages: [] },
    game,
  } as unknown as ArcadeSnapshot
}

const snapshot = ref(makeSnapshot(playerCount.value))

watch(playerCount, (count) => {
  snapshot.value = makeSnapshot(Number(count))
})

function gameState(): UnoGameView {
  return snapshot.value.game as unknown as UnoGameView
}

function eventCard(type: string): UnoCardModel | null {
  return ({
    skip: cards.greenSkip,
    reverse: cards.blueReverse,
    draw_two: cards.redDrawTwo,
    wild: cards.wild,
    wild_draw_four: cards.wildFour,
    play: cards.blueFive,
  } as Record<string, UnoCardModel>)[type] ?? null
}

function triggerEffect(type: string): void {
  const current = gameState()
  eventSequence.value += 1
  const targetId = snapshot.value.players[1]?.id ?? 'p1'
  const messages: Record<string, string> = {
    skip: '晨星打出翠绿跳过；余烬失去本次行动机会',
    reverse: '晨星打出湛蓝反转；行动轨道切换为逆时针',
    draw_two: '晨星打出赤红 +2；惩罚累计至 +6，余烬可继续叠加或接牌',
    wild: '晨星打出万能变色，指定翠绿',
    wild_draw_four: '晨星打出变色 +4；惩罚累计至 +6，余烬可继续叠加或接牌',
    take_penalty: '晨星接下累计惩罚，摸 6 张并跳过',
    catch_uno: '晨星抓到余烬漏喊 UNO；后者摸 2 张',
    play: '晨星打出湛蓝 5，并宣告 UNO',
  }
  const counts: Record<string, number> = { draw_two: 2, wild_draw_four: 4, take_penalty: 6, catch_uno: 2 }
  const stackTotals: Record<string, number> = { draw_two: 6, wild_draw_four: 6, take_penalty: 6 }
  const event: UnoEvent = {
    sequence: eventSequence.value,
    type,
    playerId: 'p1',
    targetPlayerId: ['skip', 'draw_two', 'wild_draw_four', 'catch_uno'].includes(type) ? targetId : null,
    card: eventCard(type),
    color: type === 'wild' ? 'green' : type === 'wild_draw_four' ? 'blue' : eventCard(type)?.color ?? null,
    count: counts[type] ?? 0,
    stackTotal: stackTotals[type] ?? 0,
    stacked: type === 'draw_two' || type === 'wild_draw_four',
    calledUno: type === 'play',
    message: messages[type],
  }
  const isStack = type === 'draw_two' || type === 'wild_draw_four'
  const takesPenalty = type === 'take_penalty'
  const historyItem = { type, playerId: 'p1', targetPlayerId: event.targetPlayerId, count: event.count, message: event.message }
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: {
      ...current,
      direction: type === 'reverse' ? -current.direction as 1 | -1 : current.direction,
      activeColor: event.color ?? current.activeColor,
      currentPlayerId: takesPenalty ? targetId : 'p1',
      playableCardIds: isStack ? [cards.redDrawTwo.id, cards.wildFour.id] : current.playableCardIds,
      pendingDrawTotal: isStack ? 6 : 0,
      pendingDrawTargetPlayerId: isStack ? 'p1' : null,
      pendingDrawSourcePlayerId: isStack ? targetId : null,
      canTakePenalty: isStack,
      canDraw: !isStack && !takesPenalty,
      latestEvent: event,
      history: [...current.history, historyItem].slice(-18),
    },
  }
}

function showFinished(): void {
  const current = gameState()
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    phase: 'finished',
    winnerPlayerIds: ['p1'],
    actions: { ...snapshot.value.actions, canAct: false, canRestart: true },
    game: { ...current, winnerPlayerIds: ['p1'], currentPlayerId: null },
  }
}

setDevPluginActions({
  async action(action) {
    if (action === 'take_penalty') triggerEffect('take_penalty')
    return true
  },
  async rapidAction() { return false },
  async restart() {
    snapshot.value = makeSnapshot(playerCount.value)
    return true
  },
  publishSpectatorFrame() { return false },
})
</script>

<template>
  <main class="dev-shell">
    <header class="dev-toolbar" aria-label="UNO 验收工具栏">
      <strong>真实 GameView 验收</strong>
      <label>玩家
        <select v-model.number="playerCount" aria-label="玩家人数">
          <option v-for="count in [3, 4, 5, 6, 7, 8]" :key="count" :value="count">{{ count }} 人</option>
        </select>
      </label>
      <div class="effect-controls">
        <button type="button" @click="triggerEffect('skip')">跳过</button>
        <button type="button" @click="triggerEffect('reverse')">反转</button>
        <button type="button" @click="triggerEffect('draw_two')">叠加 +2</button>
        <button type="button" @click="triggerEffect('wild')">变色</button>
        <button type="button" @click="triggerEffect('wild_draw_four')">叠加 +4</button>
        <button type="button" @click="triggerEffect('take_penalty')">接下惩罚</button>
        <button type="button" @click="triggerEffect('catch_uno')">抓漏喊</button>
        <button type="button" @click="triggerEffect('play')">UNO!</button>
        <button type="button" @click="showFinished">结算</button>
      </div>
    </header>
    <GameView :snapshot="snapshot" />
  </main>
</template>

<style scoped>
.dev-shell { width: 100%; min-height: 100vh; padding: 8px; background: radial-gradient(circle at 50% 0, #15223a, #02040a 42%); }
.dev-toolbar { width: min(100%, 1440px); min-width: 0; display: flex; align-items: center; gap: 8px; margin: 0 auto 8px; border: 1px solid rgb(255 255 255 / .12); border-radius: 14px; padding: 8px 10px; color: #dfeaff; background: rgb(7 10 17 / .94); }
.dev-toolbar > strong { flex: 0 0 auto; font-size: 10px; }
.dev-toolbar label { flex: 0 0 auto; display: flex; align-items: center; gap: 5px; color: #95a8c7; font-size: 8px; }
.dev-toolbar select, .dev-toolbar button { min-height: 30px; border: 1px solid rgb(255 255 255 / .14); border-radius: 8px; color: #e9f0ff; background: #101725; font-size: 8px; cursor: pointer; }
.dev-toolbar select { padding: 0 7px; }
.effect-controls { min-width: 0; display: flex; flex: 1; gap: 5px; overflow-x: auto; scrollbar-width: thin; }
.effect-controls button { flex: 0 0 auto; padding: 0 10px; white-space: nowrap; }
.effect-controls button:hover { border-color: #6e9eeb; background: #182948; }
@media (max-width: 620px) {
  .dev-shell { padding: 5px; }
  .dev-toolbar { display: grid; grid-template-columns: 1fr auto; padding: 6px; }
  .effect-controls { grid-column: 1 / -1; width: 100%; }
}
</style>
