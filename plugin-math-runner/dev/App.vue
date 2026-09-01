<script setup lang="ts">
import { ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import { setDevPluginActions } from './local-sdk'

type Direction = 'up' | 'left' | 'down' | 'right'

const questionSets: Array<{
  correct: Direction
  options: Array<{ direction: Direction; equation: string }>
}> = [
  {
    correct: 'up',
    options: [
      { direction: 'up', equation: '3 + 5 = 10 - 2' },
      { direction: 'left', equation: '4 + 4 = 11 - 2' },
      { direction: 'right', equation: '2 × 6 = 7 + 4' },
    ],
  },
  {
    correct: 'right',
    options: [
      { direction: 'up', equation: '5 × 4 = 13 + 8' },
      { direction: 'down', equation: '18 ÷ 3 = 2 + 5' },
      { direction: 'right', equation: '4 × 5 = 13 + 7' },
    ],
  },
  {
    correct: 'left',
    options: [
      { direction: 'up', equation: '7 × 6 - 5 = 39 - 1' },
      { direction: 'left', equation: '(4 + 3) × 5 = 40 - 5' },
      { direction: 'down', equation: '32 ÷ 4 + 9 = 20 - 2' },
      { direction: 'right', equation: '8 × 4 + 3 = 42 - 6' },
    ],
  },
]

function makeSnapshot(questionIndex = 0): ArcadeSnapshot {
  const set = questionSets[questionIndex % questionSets.length]
  const correctAnswers = questionIndex
  const level = Math.min(10, Math.floor(correctAnswers / 10) + 1)
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
      blockedDirections: ['up', 'left', 'down', 'right'].filter(
        (direction) => !set.options.some((option) => option.direction === direction),
      ),
      lastDirection: questionIndex ? questionSets[(questionIndex - 1) % questionSets.length].correct : null,
      lastPoints: questionIndex ? 340 : 0,
      levelUp: questionIndex > 0 && questionIndex % 10 === 0,
      endReason: null,
      correctDirection: null,
      elapsedMs: questionIndex * 2100,
      averageResponseMs: questionIndex ? 1850 : null,
      speed: {
        trackPeriodMs: 1500 - (level - 1) * 90,
        runCycleMs: 720 - (level - 1) * 30,
        speedLines: Math.min(12, 4 + level - 1),
      },
      won: false,
      result: null,
    },
  } as unknown as ArcadeSnapshot
}

const activeQuestion = ref(0)
const snapshot = ref(makeSnapshot())

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
          correctDirection: current.correct,
          result: 'failed',
        },
      }
      return true
    }
    if (action !== 'choose' || payload.direction !== current.correct) {
      snapshot.value = {
        ...snapshot.value,
        phase: 'finished',
        winner: 'failed',
        winReason: '本地验收：错答',
        actions: { ...snapshot.value.actions, canAct: false, canRestart: true },
        game: {
          ...snapshot.value.game,
          remainingMs: 0,
          lastDirection: payload.direction,
          endReason: 'wrong',
          correctDirection: current.correct,
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
    <GameView :snapshot="snapshot" />
  </main>
</template>

<style scoped>
.demo-shell { width: 100%; height: 100%; overflow: hidden; }
</style>
