<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type { AnimationCue, HalliGalliEvent, HalliGalliView } from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

type Report = { playerCount: number; actionCount: number; winnerPlayerIds: string[]; ending: string; actionMix: Record<string, number> }
type Scenario = 'exact-five' | 'wrong-bell' | 'last-chance' | 'final-duel' | 'final-wrong' | 'last-player' | 'resignation' | 'shared-win' | 'no-progress'

const snapshot = ref<ArcadeSnapshot | null>(null)
const report = ref<Report | null>(null)
const running = ref(false)
const error = ref('')
const currentCount = ref(4)
const cleanMode = ref(false)

async function request(url: string, init?: RequestInit): Promise<Record<string, unknown>> {
  const response = await fetch(url, init)
  if (!response.ok) throw new Error(await response.text())
  return await response.json()
}

async function loadPreview(count: number): Promise<void> {
  running.value = true; error.value = ''; report.value = null; currentCount.value = count
  try { snapshot.value = (await request(`/api/preview?count=${count}`)).snapshot as ArcadeSnapshot }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function loadScenario(name: Scenario): Promise<void> {
  running.value = true; error.value = ''; report.value = null
  try {
    const payload = await request(`/api/scenario?name=${name}`)
    snapshot.value = payload.snapshot as ArcadeSnapshot
    currentCount.value = (snapshot.value.game as unknown as HalliGalliView).players.length
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function autoplay(count: number): Promise<void> {
  running.value = true; error.value = ''; currentCount.value = count
  try {
    const payload = await request(`/api/autoplay?count=${count}`, { method: 'POST' })
    snapshot.value = payload.snapshot as ArcadeSnapshot
    report.value = payload.report as Report
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function autoStep(): Promise<void> {
  try { snapshot.value = (await request('/api/step', { method: 'POST' })).snapshot as ArcadeSnapshot }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
}

setDevPluginActions({
  action: async (action, payload) => {
    const response = await request('/api/action', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, payload }),
    })
    snapshot.value = response.snapshot as ArcadeSnapshot
    return true
  },
  rapidAction: async () => false,
  restart: async () => { await loadPreview(currentCount.value); return true },
  publishSpectatorFrame: () => false,
})

const cues: AnimationCue[] = [
  'round_deal', 'card_flip', 'bell_press_local', 'bell_confirmed',
  'collect_piles', 'penalty_transfer', 'player_eliminated',
  'final_duel_armed', 'result_enter',
]

function playMotion(cue: AnimationCue): void {
  if (!snapshot.value) return
  const game = snapshot.value.game as unknown as HalliGalliView
  const seq = (game.events.at(-1)?.seq ?? 0) + 1
  const sampleCard = game.cardCatalog.find(item => item.faceId === 'face-banana-3') ?? game.cardCatalog[0]
  const motionEvent: HalliGalliEvent = {
    seq, type: cue, cue, actorPlayerId: 'p1', targetPlayerIds: game.players[1] ? ['p2'] : [],
    messageZh: `${cue} · 动画轨迹与层级验收`, boardEpoch: game.boardEpoch,
    data: {
      card: sampleCard, winnerPlayerId: game.players[1]?.id ?? 'p1', capturedCount: 8,
      sourceCounts: Object.fromEntries(game.players.map(player => [player.id, 2])),
      penalties: game.players.slice(1, 4).map(player => ({ toPlayerId: player.id, count: 1 })),
    },
  }
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: { ...game, events: [...game.events, motionEvent], latestEvent: motionEvent },
  } as ArcadeSnapshot
}

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  cleanMode.value = params.get('clean') === '1'
  const scenario = params.get('scenario') as Scenario | null
  const count = Math.min(6, Math.max(2, Number(params.get('players') ?? 4)))
  if (scenario) void loadScenario(scenario)
  else void loadPreview(count)
})
</script>

<template>
  <main class="harness" :class="{ clean: cleanMode }">
    <nav v-if="!cleanMode" aria-label="德国心脏病本地测试控制台">
      <strong>德国心脏病 · 真实引擎</strong>
      <button v-for="count in [2,3,4,5,6]" :key="`preview-${count}`" :data-preview-count="count" :disabled="running" @click="loadPreview(count)">{{ count }} 人桌面</button>
      <button v-for="count in [2,3,4,5,6]" :key="`auto-${count}`" :data-autoplay-count="count" :disabled="running" @click="autoplay(count)">跑完 {{ count }} 人</button>
      <button data-action="auto-step" :disabled="running" @click="autoStep">自动一步</button>
      <span v-if="running" data-test-status="running">运行中…</span>
      <span v-else-if="report" data-test-status="passed">{{ report.playerCount }} 人通过 · {{ report.actionCount }} 动作 · {{ report.ending }}</span>
      <span v-if="error" data-test-status="failed">{{ error }}</span>
    </nav>
    <aside v-if="!cleanMode" class="scenario-controls" aria-label="结算场景测试">
      <button v-for="name in ['exact-five','wrong-bell','last-chance','final-duel','final-wrong','last-player','resignation','shared-win','no-progress'] as Scenario[]" :key="name" :data-scenario="name" @click="loadScenario(name)">{{ name }}</button>
      <button v-for="cue in cues" :key="cue" :data-motion-cue="cue" @click="playMotion(cue)">{{ cue }}</button>
    </aside>
    <GameView v-if="snapshot" :snapshot="snapshot" />
  </main>
</template>

<style>
:root{color-scheme:dark;background:#101817}*{box-sizing:border-box}html,body,#app{width:100%;min-width:0;min-height:100%;margin:0;background:#101817}.harness{display:grid;height:100dvh;grid-template-rows:auto auto minmax(0,1fr);min-width:0;overflow:hidden}.harness>nav,.scenario-controls{display:flex;align-items:center;gap:5px;min-width:0;min-height:38px;overflow-x:auto;padding:5px 8px;color:#dce7e2;background:#0d2926;font:9px/1.2 system-ui,sans-serif}.harness>nav{border-bottom:1px solid #87673b}.harness>nav strong{flex:0 0 auto;color:#f1cf77}.harness>nav span{margin-left:auto;white-space:nowrap;color:#80dba2}.harness button{flex:0 0 auto;padding:5px 8px;border:1px solid #5c776f;border-radius:6px;color:#e9f0eb;background:#1d4942;cursor:pointer}.scenario-controls{min-height:34px;background:#143731}.scenario-controls button{font-size:8px}.harness>.halli-galli-game{height:100%;min-height:0;border-radius:0}.harness.clean{display:block}.harness.clean>.halli-galli-game{width:100vw;height:100dvh;border-radius:0}[data-test-status="failed"]{color:#ff9da6!important}
</style>
