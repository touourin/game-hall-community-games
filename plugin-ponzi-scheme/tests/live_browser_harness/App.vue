<script setup lang="ts">
import { ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../../frontend/GameView.vue'

type Scenario = 'funding' | 'trade' | 'crash' | 'finished'

const scenario = ref<Scenario>('funding')
const playerCount = ref(5)

const industryCatalog = [
  { id: 'transportation', name: '交通运输', shortName: '交通', supply: 15, remaining: 10, color: '#6d91aa', icon: 'rail' },
  { id: 'grain', name: '粮食农业', shortName: '粮食', supply: 15, remaining: 9, color: '#c5a15a', icon: 'grain' },
  { id: 'media', name: '新闻媒体', shortName: '媒体', supply: 15, remaining: 11, color: '#8d9b72', icon: 'signal' },
  { id: 'real_estate', name: '地产开发', shortName: '地产', supply: 15, remaining: 12, color: '#9a6574', icon: 'building' },
] as const

const luxuryMarket = [
  { id: 'watch', name: '典藏腕表', cost: 30, points: 1, icon: 'watch' },
  { id: 'roadster', name: '古董跑车', cost: 56, points: 2, icon: 'car' },
  { id: 'yacht', name: '私人游艇', cost: 78, points: 3, icon: 'yacht' },
  { id: 'club', name: '城市会所', cost: 96, points: 4, icon: 'column' },
]

function card(amount: number, row: number) {
  const isBear = amount >= 63
  return {
    id: `F${String(amount).padStart(3, '0')}`,
    amount,
    period: row === 1 ? 5 : row === 2 ? 4 : 3,
    interest: Math.max(8, Math.round(amount * (isBear ? 1.8 : .92))),
    averageBurden: Math.round(amount / 2),
    yieldPercent: isBear ? 59 : 28,
    kind: isBear ? 'bear' : amount < 18 ? 'starting' : 'regular',
    isBear,
  }
}

function buildLedger(playerId: string, index: number, reveal = false) {
  const amounts = [9 + index, 21 + index, 33 + index].slice(0, index % 3 + 1)
  return {
    playerId,
    cash: reveal || playerId === 'p1' ? 44 + index * 7 : null,
    cashHidden: !reveal && playerId !== 'p1',
    industries: {
      transportation: index % 4,
      grain: (index + 2) % 4,
      media: (index + 1) % 3,
      real_estate: index % 2,
    },
    industryTotal: 0,
    funds: amounts.map((amount, fundIndex) => ({ ...card(amount, fundIndex + 1), dueIn: fundIndex + 1 })),
    fundCount: amounts.length,
    luxuries: index === 1 ? [luxuryMarket[0]] : [],
    interestDueNext: index === 0 ? 8 : 0,
    cycleInterest: amounts.reduce((total, amount) => total + Math.round(amount * .92), 0),
    bankrupt: false,
    forfeited: false,
    finalScore: null,
  }
}

function buildSnapshot(count: number, nextScenario: Scenario): ArcadeSnapshot {
  const players = Array.from({ length: count }, (_, index) => ({
    id: `p${index + 1}`,
    name: `玩家${index + 1}`,
    seat: index,
    connected: true,
  }))
  const finished = nextScenario === 'finished'
  const ledgers = players.map((player, index) => buildLedger(player.id, index, finished))
  if (finished) {
    ledgers[0].finalScore = 14
    ledgers[1].finalScore = 11
    ledgers[count - 1].bankrupt = true
  }
  const marketAmounts = nextScenario === 'crash'
    ? [45, 53, 61, 62, 63, 64, 65, 66, 67]
    : [18, 21, 25, 29, 33, 37, 45, 53, 63]
  const marketRows = [0, 1, 2].map(row => marketAmounts.slice(row * 3, row * 3 + 3).map(amount => card(amount, row + 1)))
  const stage = finished ? 'finished' : nextScenario === 'trade' ? 'trade_response' : nextScenario === 'crash' ? 'crash_discard' : 'funding'
  const stageLabels = { funding: '募集资金', trade: '回应暗盘报价', crash: '市场崩盘', finished: '破产结算' }
  const settlementRows = players.map((player, index) => ({
    playerId: player.id,
    rank: index === count - 1 ? null : index + 1,
    winner: index === 0,
    bankrupt: index === count - 1,
    industryScore: Math.max(0, 11 - index),
    luxuryScore: index === 0 ? 3 : index === 1 ? 1 : 0,
    wealthScore: null,
    highestFund: 53 - index,
    total: Math.max(0, 11 - index) + (index === 0 ? 3 : index === 1 ? 1 : 0),
  }))
  return {
    revision: Date.now(),
    roomCode: 'PONZ',
    gameKey: 'plugin-ponzi-scheme',
    gameName: '庞氏骗局',
    phase: finished ? 'finished' : 'playing',
    options: { luxuries: true, skipFirstTrade: true },
    hostId: 'p1',
    self: { id: 'p1', name: '玩家1', seat: 0 },
    players,
    requiredPlayers: 5,
    minimumPlayers: 3,
    roundNumber: 4,
    winner: finished ? 'capital' : null,
    winnerPlayerIds: finished ? ['p1'] : [],
    winReason: finished ? '骗局崩解；玩家1 以 14 分胜出' : null,
    actions: {
      canStart: false, canRestart: false, canAct: !finished, canKickPlayers: false,
      canDissolve: false, canEditRules: false, canRequestUndo: false,
      canRequestDraw: false, canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 300, messages: [] },
    game: {
      version: '1.1.0', ruleset: 'bright-eye-standard', round: 4, stage,
      stageLabel: stageLabels[nextScenario], currentPlayerId: finished ? null : 'p1',
      starterPlayerId: 'p1', turnOrder: players.map(player => player.id), marketRows,
      bearCount: nextScenario === 'crash' ? 5 : 1, playerCount: count,
      deckCounts: { draw: 38, discard: 7, removedStarting: 2 },
      industryCatalog, luxuryMarket, luxuriesEnabled: true,
      scoringMode: 'industry_and_luxury', wheelPosition: nextScenario === 'crash' ? 3 : 1,
      wheelAdvance: nextScenario === 'crash' ? 2 : 1, ledgers,
      pendingTrade: nextScenario === 'trade' ? {
        proposerId: 'p2', targetId: 'p1', industryId: 'grain', industryName: '粮食农业',
        offer: 17, offerKnown: true,
      } : null,
      legalActions: finished ? {} : nextScenario === 'funding' ? {
        canResign: true,
        fundingOptions: industryCatalog.map(industry => ({
          industryId: industry.id, industryName: industry.name, row: 1,
          cardIds: marketRows[0].map(item => item.id),
        })),
        canPassFunding: true,
      } : nextScenario === 'trade' ? {
        canResign: true, canAcceptOffer: true, canCounterOffer: true,
      } : {
        canResign: true, discardIndustryIds: ['transportation', 'grain'],
      },
      events: [{ seq: 1, type: 'game_start', message: '视觉回归场景已加载', data: {} }],
      bankruptPlayerIds: finished ? [`p${count}`] : [],
      rankings: finished ? players.slice(0, -1).map(player => player.id) : [],
      settlement: finished ? {
        mode: 'industry_and_luxury', winnerPlayerIds: ['p1'],
        bankruptPlayerIds: [`p${count}`], reason: '骗局崩解；玩家1 以 14 分胜出',
        rows: settlementRows,
      } : null,
      privacy: { cash: finished ? 'revealed-at-finish' : 'self-only', tradeOffer: 'participants-only', fundsAndIndustries: 'public' },
    },
  } as unknown as ArcadeSnapshot
}

const snapshot = ref<ArcadeSnapshot>(buildSnapshot(playerCount.value, scenario.value))

function selectScenario(next: Scenario, count: number) {
  scenario.value = next
  playerCount.value = count
  snapshot.value = buildSnapshot(count, next)
}

function playMotion(type: string) {
  const game = snapshot.value.game as Record<string, any>
  const seq = (game.events[game.events.length - 1]?.seq ?? 0) + 1
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: {
      ...game,
      wheelPosition: type === 'wheel' ? (game.wheelPosition + 1) % 5 : game.wheelPosition,
      events: [...game.events, { seq, type, message: `视觉测试：${type}`, data: {} }],
    },
  } as ArcadeSnapshot
}
</script>

<template>
  <main class="harness">
    <nav aria-label="视觉回归控制台">
      <strong>庞氏骗局 · 全幅回归</strong>
      <button data-scenario="funding" @click="selectScenario('funding', 3)">3 人募集</button>
      <button data-scenario="trade" @click="selectScenario('trade', 4)">4 人暗盘</button>
      <button data-scenario="crash" @click="selectScenario('crash', 5)">5 人崩盘</button>
      <button data-scenario="finished" @click="selectScenario('finished', 5)">5 人结算</button>
      <span>{{ playerCount }} 人 / {{ scenario }}</span>
    </nav>
    <aside class="motion-controls" aria-label="动画测试">
      <button v-for="type in ['fund', 'trade_offer', 'trade_accept', 'luxury', 'market_discard', 'market_crash', 'crash_discard', 'interest_paid', 'wheel', 'bankruptcy', 'marker_pass']" :key="type" :data-motion="type" @click="playMotion(type)">{{ type }}</button>
    </aside>
    <GameView :snapshot="snapshot" />
  </main>
</template>

<style>
:root { color-scheme: dark; background: #071411; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; background: #071411; }
.harness { min-height: 100vh; }
.harness > nav, .motion-controls { display: flex; align-items: center; gap: 6px; overflow-x: auto; padding: 6px 10px; color: #e7ddc8; background: #101b1a; font: 11px/1.2 system-ui, sans-serif; }
.harness > nav { min-height: 42px; border-bottom: 1px solid #604f32; }
.harness > nav strong { flex: 0 0 auto; color: #d0b573; }
.harness > nav span { margin-left: auto; white-space: nowrap; color: #9bbd91; }
.harness button { flex: 0 0 auto; border: 1px solid #725f3c; border-radius: 4px; padding: 5px 8px; color: #eee4cf; background: #263633; cursor: pointer; }
.motion-controls { min-height: 38px; background: #182522; }
.motion-controls button { font-size: 9px; }
.harness > .ponzi-table { min-height: calc(100dvh - 80px); }
@media (max-width: 680px) {
  .harness > nav span { display: none; }
  .harness > nav, .motion-controls { padding: 5px 6px; }
}
</style>
