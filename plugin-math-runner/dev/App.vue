<script setup lang="ts">
import { ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type { RunnerAction, RunnerOption } from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

const questionSets: Array<{
  correct: RunnerAction
  options: RunnerOption[]
}> = [
  {
    correct: 'jump',
    options: [
      { action: 'left', lane: 'left', obstacle: null, equation: '4 + 4 = 11 - 2' },
      { action: 'jump', lane: 'center', obstacle: 'ground', equation: '3 + 5 = 10 - 2' },
    ],
  },
  {
    correct: 'right',
    options: [
      { action: 'slide', lane: 'center', obstacle: 'overhead', equation: '18 ÷ 3 = 2 + 5' },
      { action: 'right', lane: 'right', obstacle: null, equation: '4 × 5 = 13 + 7' },
    ],
  },
  {
    correct: 'left',
    options: [
      { action: 'left', lane: 'left', obstacle: null, equation: '(4 + 3) × 5 = 40 - 5' },
      { action: 'slide', lane: 'center', obstacle: 'overhead', equation: '32 ÷ 4 + 9 = 20 - 2' },
      { action: 'right', lane: 'right', obstacle: null, equation: '8 × 4 + 3 = 42 - 6' },
    ],
  },
  {
    correct: 'slide',
    options: [
      { action: 'left', lane: 'left', obstacle: null, equation: '24 ÷ 4 = 9 - 2' },
      { action: 'slide', lane: 'center', obstacle: 'overhead', equation: '6 × 3 = 25 - 7' },
      { action: 'right', lane: 'right', obstacle: null, equation: '7 + 8 = 18 - 2' },
    ],
  },
]

function makeSnapshot(questionIndex = 0): ArcadeSnapshot {
  const set = questionSets[questionIndex % questionSets.length]
  const correctAnswers = questionIndex
  const level = Math.min(10, Math.floor(correctAnswers / 10) + 1)
  const availableActions = new Set(set.options.map((option) => option.action))
  return {
    revision: questionIndex + 1,
    roomCode: 'DEMO',
    gameKey: 'plugin-math-runner',
    gameName: '算途疾行',
    phase: 'playing',
    options: {},
    hostId: 'p1',
    self: { id: 'p1', name: '逐光者', seat: 0 },
    players: [{ id: 'p1', name: '逐光者', seat: 0, online: true }],
    requiredPlayers: 1,
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
    game: {
      level,
      maxLevel: 10,
      correctAnswers,
      totalQuestions: 100,
      streakInLevel: correctAnswers % 10,
      questionsPerLevel: 10,
      questionsToNextLevel: 10 - correctAnswers % 10,
      score: correctAnswers * 340,
      distanceMeters: correctAnswers * 24,
      questionId: questionIndex + 1,
      timeLimitMs: 6500 - (level - 1) * 360,
      remainingMs: 6200,
      options: set.options,
      branchCount: set.options.length,
      blockedActions: ['jump', 'left', 'slide', 'right'].filter(
        (action) => !availableActions.has(action as RunnerAction),
      ),
      lastAction: questionIndex
        ? questionSets[(questionIndex - 1) % questionSets.length].correct
        : null,
      lastPoints: questionIndex ? 340 : 0,
      levelUp: questionIndex > 0 && questionIndex % 10 === 0,
      endReason: null,
      correctAction: null,
      elapsedMs: questionIndex * 2100,
      averageResponseMs: questionIndex ? 1850 : null,
      speed: {
        trackPeriodMs: 1500 - (level - 1) * 90,
        runCycleMs: 720 - (level - 1) * 30,
      },
      won: false,
      result: null,
    },
  } as unknown as ArcadeSnapshot
}

const activeQuestion = ref(0)
const snapshot = ref(makeSnapshot())
const showGame = ref(true)

setDevPluginActions({
  async action(action, payload = {}) {
    if (snapshot.value.phase !== 'playing') return false
    const current = questionSets[activeQuestion.value % questionSets.length]
    if (action === 'timeout') {
      snapshot.value = {
        ...snapshot.value,
        phase: 'finished',
        winner: 'failed',
        winReason: '本地验收：超时',
        actions: { ...snapshot.value.actions, canAct: false, canRestart: true },
        game: {
          ...snapshot.value.game,
          remainingMs: 0,
          endReason: 'timeout',
          correctAction: current.correct,
          result: 'failed',
        },
      }
      return true
    }
    if (action !== 'choose' || payload.runnerAction !== current.correct) {
      snapshot.value = {
        ...snapshot.value,
        phase: 'finished',
        winner: 'failed',
        winReason: '本地验收：错答',
        actions: { ...snapshot.value.actions, canAct: false, canRestart: true },
        game: {
          ...snapshot.value.game,
          remainingMs: 0,
          lastAction: payload.runnerAction,
          endReason: 'wrong',
          correctAction: current.correct,
          result: 'failed',
        },
      }
      return true
    }
    activeQuestion.value += 1
    snapshot.value = makeSnapshot(activeQuestion.value)
    return true
  },
  async rapidAction() { return false },
  async restart() {
    activeQuestion.value = 0
    snapshot.value = makeSnapshot()
    return true
  },
  publishSpectatorFrame() { return false },
})
</script>

<template>
  <main class="demo-shell">
    <header class="demo-host-header">
      <button v-if="showGame" type="button" @click="showGame = false">← 返回主界面</button>
      <strong>第三方插件独立验收壳</strong>
    </header>
    <GameView v-if="showGame" :snapshot="snapshot" />
    <section v-else class="demo-menu" aria-label="游戏大厅主界面">
      <p>已安全离开本局</p>
      <h1>游戏大厅主界面</h1>
      <button type="button" @click="showGame = true">重新进入算途疾行</button>
    </section>
  </main>
</template>

<style scoped>
.demo-shell { width: 100%; min-height: 100%; padding: 10px; background: #0c1725; }
.demo-host-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 54px;
  padding: 0 12px;
  color: #dcecf2;
}
.demo-menu {
  min-height: 560px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 14px;
  color: #f7ead8;
}
.demo-menu p { margin: 0; color: #7fe3ef; letter-spacing: .12em; }
.demo-menu h1 { margin: 0; }
.demo-menu button { padding: 10px 18px; border-radius: 12px; cursor: pointer; }
.demo-host-header button {
  min-height: 38px;
  border: 1px solid #486476;
  border-radius: 10px;
  padding: 0 13px;
  color: #e8f7fb;
  background: #172b3c;
}
</style>
