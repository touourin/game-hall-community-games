<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type { BullCard, BullCardTier, BullheadGameView } from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

type Scenario = 'deal' | 'select' | 'waiting' | 'place' | 'take_full' | 'take_low' | 'summary' | 'finished'

const scenarios: Array<{ id: Scenario; label: string }> = [
  { id: 'deal', label: '发牌' },
  { id: 'select', label: '暗选' },
  { id: 'waiting', label: '等待' },
  { id: 'place', label: '升序落牌' },
  { id: 'take_full', label: '第六张收牌' },
  { id: 'take_low', label: '自动收牌' },
  { id: 'summary', label: '轮末' },
  { id: 'finished', label: '终局' },
]
const activeScenario = ref<Scenario>('select')
const playerCount = ref(4)
const playerNames = ['青角', '赤角', '金角', '紫角', '银角', '墨角', '苍角', '白角']
const totalScores = [18, 41, 27, 70, 33, 12, 58, 24]
const roundScores = [3, 12, 5, 17, 8, 2, 14, 6]

function penalty(number: number): 1 | 2 | 3 | 5 | 7 {
  if (number === 55) return 7
  if (number % 11 === 0) return 5
  if (number % 10 === 0) return 3
  if (number % 5 === 0) return 2
  return 1
}

function card(number: number): BullCard {
  const bullheads = penalty(number)
  const tiers: Record<number, BullCardTier> = {
    1: 'single', 2: 'double', 3: 'triple', 5: 'quintuple', 7: 'royal',
  }
  return { id: `card-${String(number).padStart(3, '0')}`, number, bullheads, tier: tiers[bullheads]! }
}

function playersFor(scenario: Scenario) {
  const includedScores = totalScores.slice(0, playerCount.value)
  return Array.from({ length: playerCount.value }, (_, index) => {
    const id = `p${index + 1}`
    const hasSelected = scenario === 'waiting'
      ? index !== 1
      : scenario === 'select' && index >= Math.max(2, playerCount.value - 2)
    const rank = scenario === 'finished'
      ? 1 + includedScores.filter(score => score < includedScores[index]!).length
      : null
    return {
      id,
      name: playerNames[index]!,
      seat: index,
      status: 'active' as const,
      handCount: scenario === 'summary' || scenario === 'finished' ? 0 : 7,
      hasSelected,
      roundPenalty: roundScores[index]!,
      totalPenalty: includedScores[index]!,
      capturedCount: Math.max(0, Math.round(roundScores[index]! / 2)),
      rank,
    }
  })
}

function resolveFixture(
  startingRows: number[][],
  revealed: Array<{ playerId: string; card: BullCard }>,
) {
  const rows = startingRows
    .map(row => row.map(card))
    .sort((left, right) => left[0]!.number - right[0]!.number)
  const steps = revealed.map((play, index) => {
    const eligible = rows
      .map((row, rowIndex) => ({ head: row[0]!.number, rowIndex }))
      .filter(candidate => candidate.head <= play.card.number)
    let rowIndex = eligible.at(-1)?.rowIndex ?? 0
    const mustReplace = play.card.number < rows[rowIndex]!.at(-1)!.number
    const isSixth = !mustReplace && rows[rowIndex]!.length === 5
    const takenCards = mustReplace || isSixth ? [...rows[rowIndex]!] : []
    const type = mustReplace ? 'take_low' as const : isSixth ? 'take_full' as const : 'place' as const
    if (takenCards.length) {
      const replacement = [play.card]
      rows[rowIndex] = replacement
      rows.sort((left, right) => left[0]!.number - right[0]!.number)
      rowIndex = rows.indexOf(replacement)
    }
    else {
      rows[rowIndex] = [...rows[rowIndex]!, play.card]
    }
    return {
      id: `fixture-${activeScenario.value}-${index}-${play.card.number}`,
      type,
      playerId: play.playerId,
      card: play.card,
      rowIndex,
      takenCards,
      penalty: takenCards.reduce((sum, item) => sum + item.bullheads, 0),
    }
  })
  return { rows, steps }
}

function gameFor(scenario: Scenario): BullheadGameView {
  const players = playersFor(scenario)
  const committedPlayerIds = players.filter(player => player.hasSelected).map(player => player.id)
  const base: BullheadGameView = {
    schemaVersion: 1,
    sceneId: 'turn.select',
    stage: 'select',
    roundNumber: 2,
    turnNumber: 4,
    rules: { cardMinimum: 1, cardMaximum: 104, handSize: 10, rowCount: 4, rowLimit: 5, targetPenalty: 66 },
    players,
    activePlayerIds: players.map(player => player.id),
    rows: [
      [card(12), card(14), card(15), card(21), card(26)],
      [card(37), card(41)],
      [card(43), card(44), card(55)],
      [card(58), card(61), card(68), card(83)],
    ],
    hand: [3, 5, 10, 11, 30, 55, 104].map(card),
    committedCard: null,
    committedPlayerIds,
    waitingForPlayerIds: players.filter(player => !player.hasSelected).map(player => player.id),
    revealed: [],
    pendingLowCard: null,
    rowChoices: [],
    actions: ['select_card'],
    animation: null,
    roundSummary: null,
    history: [
      { type: 'place', message: '紫角将 83 接到第 4 行' },
      { type: 'take_full', message: '赤角成为第六张，收走第 1 行' },
      { type: 'reveal', message: '第 3 手同时翻开：21、44、61、83' },
    ],
    rankings: [],
    canSelect: true,
    canChooseRow: false,
    canStartNextRound: false,
  }
  if (scenario === 'deal') {
    return {
      ...base,
      sceneId: 'turn.select',
      animation: {
        id: 6_000 + playerCount.value,
        kind: 'round_deal',
        roundNumber: 2,
        turnNumber: 1,
        revealed: [],
        steps: [],
        pendingChoice: null,
        complete: true,
      },
    }
  }
  if (scenario === 'waiting') {
    return {
      ...base,
      sceneId: 'turn.waiting',
      hand: base.hand.filter(item => item.number !== 30),
      committedCard: card(30),
      committedPlayerIds,
      waitingForPlayerIds: players.filter(player => !player.hasSelected).map(player => player.id),
      actions: [], canSelect: false,
    }
  }
  if (scenario === 'place') {
    const revealed = [5, 11, 22, 30, 55, 62, 70, 104]
      .slice(0, playerCount.value)
      .map((number, index) => ({ playerId: players[index]!.id, card: card(number) }))
    const fixture = resolveFixture([[1], [20], [40], [60]], revealed)
    return {
      ...base,
      sceneId: 'turn.resolve', stage: 'resolving', actions: [], canSelect: false,
      rows: fixture.rows,
      revealed,
      animation: {
        id: 7_000 + playerCount.value, kind: 'turn_resolution', roundNumber: 2, turnNumber: 4,
        revealed,
        steps: fixture.steps,
        pendingChoice: null, complete: true,
      },
    }
  }
  if (scenario === 'take_full') {
    const playerOrder = [players.at(-1)!, ...players.slice(0, -1)]
    const revealed = [30, 40, 50, 65, 75, 92, 98, 104]
      .slice(0, playerCount.value)
      .map((number, index) => ({ playerId: playerOrder[index]!.id, card: card(number) }))
    const fixture = resolveFixture(
      [[12, 14, 15, 21, 26], [37], [60], [90]],
      revealed,
    )
    return {
      ...base,
      sceneId: 'turn.resolve', stage: 'resolving', actions: [], canSelect: false,
      rows: fixture.rows,
      revealed,
      animation: {
        id: 8_000 + playerCount.value, kind: 'turn_resolution', roundNumber: 2, turnNumber: 4,
        revealed,
        steps: fixture.steps,
        pendingChoice: null, complete: true,
      },
    }
  }
  if (scenario === 'take_low') {
    const lowPlayer = players.at(-1)!
    const otherPlayers = players.slice(0, -1)
    const revealed = [
      { playerId: lowPlayer.id, card: card(3) },
      ...[20, 40, 60, 70, 85, 95, 104]
        .slice(0, playerCount.value - 1)
        .map((number, index) => ({ playerId: otherPlayers[index]!.id, card: card(number) })),
    ]
    const fixture = resolveFixture([[12], [37], [43, 44, 55], [83]], revealed)
    return {
      ...base,
      sceneId: 'turn.resolve', stage: 'resolving', actions: [], canSelect: false,
      rows: fixture.rows,
      revealed,
      animation: {
        id: 9_000 + playerCount.value, kind: 'turn_resolution', roundNumber: 2, turnNumber: 4,
        revealed,
        steps: fixture.steps,
        pendingChoice: null, complete: true,
      },
    }
  }
  if (scenario === 'summary') {
    const penalties = Object.fromEntries(players.map(player => [player.id, player.roundPenalty]))
    const totals = Object.fromEntries(players.map(player => [player.id, player.totalPenalty]))
    const lowest = Math.min(...players.map(player => player.totalPenalty))
    return {
      ...base,
      sceneId: 'round.summary', stage: 'round_summary', hand: [], actions: ['next_round'], canSelect: false, canStartNextRound: true,
      roundSummary: {
        roundNumber: 2,
        penalties,
        totals,
        leaderIds: players.filter(player => player.totalPenalty === lowest).map(player => player.id),
        thresholdReached: false,
      },
    }
  }
  if (scenario === 'finished') {
    return {
      ...base,
      sceneId: 'game.finished', stage: 'finished', hand: [], actions: [], canSelect: false,
      rankings: [...players]
        .sort((left, right) => left.totalPenalty - right.totalPenalty || left.seat - right.seat)
        .map(player => player.id),
    }
  }
  return base
}

const snapshot = computed(() => {
  const game = gameFor(activeScenario.value)
  const finished = activeScenario.value === 'finished'
  const lowest = Math.min(...game.players.map(player => player.totalPenalty))
  const winnerPlayerIds = finished
    ? game.players.filter(player => player.totalPenalty === lowest).map(player => player.id)
    : []
  const winnerNames = game.players
    .filter(player => winnerPlayerIds.includes(player.id))
    .map(player => player.name)
    .join('、')
  return {
    revision: playerCount.value * 100 + scenarios.findIndex(item => item.id === activeScenario.value),
    roomCode: 'MODEL',
    gameKey: 'plugin-bullhead-king',
    gameName: '谁是牛头王',
    phase: finished ? 'finished' : 'playing',
    statsEligible: true,
    hostId: 'p1',
    self: { id: 'p1', name: '青角', seat: 0 },
    viewer: { mode: 'player', id: 'p1', name: '青角', targetPlayerId: 'p1' },
    players: game.players.map(player => ({ id: player.id, name: player.name, seat: player.seat, connected: true })),
    requiredPlayers: playerCount.value,
    minimumPlayers: 2,
    roundNumber: 2,
    winner: finished ? '最低牛头分' : null,
    winnerPlayerIds,
    winReason: finished ? `有人达到 66 牛头分；${winnerNames} 以 ${lowest} 分获胜` : null,
    actions: { canAct: !finished, canRestart: finished },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] },
    game,
  } as unknown as ArcadeSnapshot
})

setDevPluginActions({
  async action(action) {
    if (action === 'select_card') activeScenario.value = 'waiting'
    if (action === 'next_round') activeScenario.value = 'select'
    return true
  },
  async rapidAction() { return false },
  async restart() { activeScenario.value = 'select'; return true },
  publishSpectatorFrame() { return false },
})
</script>

<template>
  <div class="lab-shell">
    <header class="lab-toolbar">
      <span><b>场景实验台</b><small>仅本地模型数据</small></span>
      <div class="lab-controls">
        <label>
          <span>玩家</span>
          <select v-model.number="playerCount" aria-label="玩家数量">
            <option v-for="count in [4, 5, 6, 7, 8]" :key="count" :value="count">{{ count }} 人</option>
          </select>
        </label>
        <nav aria-label="场景切换">
          <button
            v-for="scenario in scenarios"
            :key="scenario.id"
            type="button"
            :class="{ active: activeScenario === scenario.id }"
            @click="activeScenario = scenario.id"
          >{{ scenario.label }}</button>
        </nav>
      </div>
    </header>
    <GameView :snapshot="snapshot" />
  </div>
</template>

<style scoped>
.lab-shell { width: 100%; min-height: 100vh; background: #071315; }
.lab-toolbar { position: sticky; z-index: 50; top: 0; min-height: 54px; display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid rgb(214 164 71 / .22); padding: 8px 14px; background: rgb(7 19 21 / .94); backdrop-filter: blur(12px); }
.lab-toolbar > span { display: grid; gap: 2px; }
.lab-toolbar b { color: #f0d39b; font-size: 11px; }
.lab-toolbar small { color: #78938f; font-size: 7px; }
.lab-controls { min-width: 0; display: flex; align-items: center; gap: 8px; }
.lab-controls label { display: flex; align-items: center; gap: 5px; color: #78938f; font-size: 8px; }
.lab-controls select { min-height: 34px; border: 1px solid #29474a; border-radius: 9px; padding: 0 8px; color: #f7e5c0; background: #0c2427; }
.lab-toolbar nav { min-width: 0; display: flex; gap: 5px; overflow-x: auto; }
.lab-toolbar button { min-height: 34px; border: 1px solid #29474a; border-radius: 9px; padding: 0 10px; color: #abc0bc; background: #0c2427; cursor: pointer; white-space: nowrap; }
.lab-toolbar button.active { border-color: #d6a447; color: #f7e5c0; background: #49391d; }
@media (max-width: 760px) { .lab-toolbar { align-items: flex-start; flex-direction: column; } .lab-controls, .lab-toolbar nav { width: 100%; } .lab-controls { align-items: flex-start; flex-direction: column; } }
</style>
