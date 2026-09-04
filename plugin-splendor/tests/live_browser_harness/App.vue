<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../../frontend/GameView.vue'
import type { EventView, SplendorGameView } from '../../frontend/types'

type Report = { playerCount: number, actionCount: number, turnCount: number, winnerPlayerIds: string[], summaryZh: string }
const snapshot = ref<ArcadeSnapshot | null>(null)
const report = ref<Report | null>(null)
const running = ref(false)
const error = ref('')

async function load(url: string, method = 'GET') {
  running.value = true; error.value = ''; report.value = null
  try {
    const response = await fetch(url, { method })
    if (!response.ok) throw new Error(await response.text())
    const payload = await response.json()
    snapshot.value = payload.snapshot
    report.value = payload.report ?? null
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    running.value = false
  }
}

function playMotion(type: string) {
  if (!snapshot.value) return
  const game = snapshot.value.game as unknown as SplendorGameView
  const event: EventView = {
    seq: (game.events.at(-1)?.seq ?? 0) + 1,
    type,
    message: `动画验收：${type}`,
    data: { level: 2, card: game.tiers[1].slots[0].card },
  }
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: { ...game, revision: game.revision + 1, events: [...game.events, event] },
  } as ArcadeSnapshot
}

onMounted(() => load('/api/preview?count=4'))
</script>

<template>
  <main class="harness">
    <nav aria-label="璀璨宝石本地验收控制台">
      <strong>璀璨宝石 · 真实引擎</strong>
      <button v-for="count in [2,3,4]" :key="`preview-${count}`" :data-preview-count="count" :disabled="running" @click="load(`/api/preview?count=${count}`)">{{ count }} 人桌面</button>
      <button v-for="count in [2,3,4]" :key="`auto-${count}`" :data-autoplay-count="count" :disabled="running" @click="load(`/api/autoplay?count=${count}`, 'POST')">跑完 {{ count }} 人局</button>
      <button v-for="name in ['payment','return','noble','final-round','shared']" :key="name" :data-scenario="name" :disabled="running" @click="load(`/api/scenario?name=${name}`)">{{ name }}</button>
      <span v-if="running" data-test-status="running">运行中…</span>
      <span v-else-if="report" data-test-status="passed">{{ report.playerCount }} 人通过 · {{ report.actionCount }} 次提交 · {{ report.summaryZh }}</span>
      <span v-if="error" data-test-status="failed">{{ error }}</span>
    </nav>
    <aside class="motion-controls" aria-label="全部动画测试">
      <button v-for="type in ['pieces_taken','pieces_returned','card_reserved_public','card_reserved_blind','card_purchased','market_refilled','noble_acquired','final_round_triggered','turn_advanced','game_finished']" :key="type" :data-motion-type="type" @click="playMotion(type)">{{ type }}</button>
    </aside>
    <GameView v-if="snapshot" :snapshot="snapshot" />
  </main>
</template>

<style>
:root { color-scheme: dark; background: #071817; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 0; min-height: 100vh; overflow-x: hidden; background: #071817; }
.harness { min-width: 0; min-height: 100vh; overflow-x: hidden; }
.harness > nav, .motion-controls { display: flex; min-width: 0; min-height: 39px; align-items: center; gap: 5px; padding: 5px 8px; overflow-x: auto; color: #e7ddc8; background: #101f1e; font: 10px/1.2 system-ui, sans-serif; }
.harness > nav { border-bottom: 1px solid #6f4f32; }.harness > nav strong { flex: 0 0 auto; color: #f2c96d; }.harness > nav span { margin-left: auto; white-space: nowrap; color: #9bc8b9; }
.harness button { flex: 0 0 auto; min-height: 28px; padding: 4px 7px; border: 1px solid #725f3c; border-radius: 5px; color: #eee4cf; background: #263f3c; cursor: pointer; }
.motion-controls { background: #182c2a; }.motion-controls button { font-size: 8px; }
.harness > .splendor-game { height: calc(100dvh - 78px); min-height: 642px; }
[data-test-status="failed"] { color: #ff9d94 !important; }
@media (max-width: 900px) { .harness > .splendor-game { height: auto; min-height: calc(100dvh - 78px); } }
</style>
