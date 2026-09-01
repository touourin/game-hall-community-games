<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../../frontend/GameView.vue'

type RunReport = {
  playerCount: number
  actionCount: number
  phaseTrace: string[]
  resultReason: string
  winnerPlayerIds: string[]
  settlement: Array<{ playerId: string; role: string; won: boolean }>
}

const snapshot = ref<ArcadeSnapshot | null>(null)
const report = ref<RunReport | null>(null)
const running = ref(false)
const error = ref('')

async function runGame(count: number) {
  running.value = true
  error.value = ''
  try {
    const response = await fetch(`/api/autoplay?count=${count}`, { method: 'POST' })
    if (!response.ok) throw new Error(await response.text())
    const payload = await response.json()
    snapshot.value = payload.snapshot as ArcadeSnapshot
    report.value = payload.report as RunReport
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    running.value = false
  }
}

onMounted(() => runGame(3))
</script>

<template>
  <main class="harness">
    <nav aria-label="浏览器完整对局测试控制台">
      <strong>Skull 真实引擎 × 真实界面</strong>
      <button
        v-for="count in [3, 4, 5, 6]"
        :key="count"
        :data-player-count="count"
        :disabled="running"
        @click="runGame(count)"
      >
        测试 {{ count }} 人
      </button>
      <span v-if="running" data-test-status="running">正在运行完整对局…</span>
      <span v-else-if="report" data-test-status="passed">
        {{ report.playerCount }} 人通过 · {{ report.actionCount }} 动作 ·
        {{ report.resultReason }} · 胜者 {{ report.winnerPlayerIds.join(', ') }}
      </span>
      <span v-if="error" data-test-status="failed">{{ error }}</span>
    </nav>
    <GameView v-if="snapshot" :snapshot="snapshot" />
  </main>
</template>

<style>
:root { color-scheme: dark; background: #090b0a; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; background: #090b0a; }
.harness { min-height: 100vh; }
.harness > .skull-game { min-height: calc(100dvh - 45px); border-radius: 0; }
nav { min-height: 44px; display: flex; align-items: center; gap: 8px; padding: 6px 12px; color: #dcd4c4; background: #151916; font: 12px/1.2 system-ui, sans-serif; }
nav strong { color: #d1b470; }
nav button { border: 1px solid #5b5140; border-radius: 7px; padding: 6px 10px; color: #e5dccb; background: #242a25; cursor: pointer; }
nav button:disabled { opacity: .5; }
nav span { margin-left: auto; color: #a9c6a5; }
nav [data-test-status="failed"] { color: #e69b96; }
</style>
