<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type { LoveEvent, LoveLetterView } from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

type Report = { playerCount: number; actionCount: number; roundCount: number; winnerPlayerIds: string[]; sealedCardRevealed: boolean }
const snapshot = ref<ArcadeSnapshot | null>(null)
const report = ref<Report | null>(null)
const running = ref(false)
const error = ref('')

setDevPluginActions({
  action: async () => false,
  rapidAction: async () => false,
  restart: async () => { await loadPreview(4); return true },
  publishSpectatorFrame: () => false,
})

async function request(url: string, init?: RequestInit): Promise<Record<string, unknown>> {
  const response = await fetch(url, init)
  if (!response.ok) throw new Error(await response.text())
  return await response.json()
}

async function loadPreview(count: number): Promise<void> {
  running.value = true; error.value = ''; report.value = null
  try { snapshot.value = (await request(`/api/preview?count=${count}`)).snapshot as ArcadeSnapshot }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function autoplay(count: number): Promise<void> {
  running.value = true; error.value = ''
  try {
    const payload = await request(`/api/autoplay?count=${count}`, { method: 'POST' })
    snapshot.value = payload.snapshot as ArcadeSnapshot
    report.value = payload.report as Report
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function loadScenario(name: 'guard' | 'chancellor' | 'sealed'): Promise<void> {
  running.value = true; error.value = ''; report.value = null
  try { snapshot.value = (await request(`/api/scenario?name=${name}`)).snapshot as ArcadeSnapshot }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

function playMotion(kind: string): void {
  if (!snapshot.value) return
  const game = snapshot.value.game as unknown as LoveLetterView
  const seq = (game.events.at(-1)?.seq ?? 0) + 1
  const event: LoveEvent = {
    seq, kind, actorPlayerId: 'p1', targetPlayerIds: game.players[1] ? ['p2'] : [],
    messageZh: `${kind} · 动画轨迹、遮罩与层级验收`, data: {},
  }
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: { ...game, events: [...game.events, event], latestEvent: event },
  } as ArcadeSnapshot
}

onMounted(() => loadPreview(4))
</script>

<template>
  <main class="harness">
    <nav aria-label="情书本地完整对局测试控制台">
      <strong>情书 · 真实引擎与界面</strong>
      <button v-for="count in [2,3,4]" :key="`preview-${count}`" :data-preview-count="count" :disabled="running" @click="loadPreview(count)">{{ count }} 人桌面</button>
      <button v-for="count in [2,3,4]" :key="`auto-${count}`" :data-autoplay-count="count" :disabled="running" @click="autoplay(count)">跑完 {{ count }} 人局</button>
      <button data-scenario="guard" @click="loadScenario('guard')">卫兵猜测</button>
      <button data-scenario="chancellor" @click="loadScenario('chancellor')">大臣私密选择</button>
      <button data-scenario="sealed" @click="loadScenario('sealed')">封存牌结算</button>
      <span v-if="running" data-test-status="running">运行中…</span>
      <span v-else-if="report" data-test-status="passed">{{ report.playerCount }} 人通过 · {{ report.actionCount }} 动作 · {{ report.roundCount }} 轮 · 封存牌公开={{ report.sealedCardRevealed }}</span>
      <span v-if="error" data-test-status="failed">{{ error }}</span>
    </nav>
    <aside class="motion-controls" aria-label="全部卡牌与结算动画测试">
      <button v-for="kind in ['round_deal','draw_card','play_card','spy_mark','guess_miss','guess_hit','peek_hand','compare_hands','gain_protection','protection_expired','force_redraw','prince_princess','chancellor_draw','chancellor_no_draw','bottom_cards','trade_hands','queen_escape','princess_discard','no_legal_target','round_end','forfeit']" :key="kind" :data-motion-kind="kind" @click="playMotion(kind)">{{ kind }}</button>
    </aside>
    <GameView v-if="snapshot" :snapshot="snapshot" />
  </main>
</template>

<style>
:root{color-scheme:dark;background:#14070d}*{box-sizing:border-box}body{margin:0;min-width:0;min-height:100vh;background:#14070d}.harness{display:grid;grid-template-rows:auto auto minmax(0,1fr);min-width:0;height:100dvh;overflow:hidden}.harness>nav,.motion-controls{display:flex;align-items:center;gap:6px;min-width:0;min-height:40px;overflow-x:auto;padding:5px 9px;color:#eadfc8;background:#24101a;font:10px/1.2 system-ui,sans-serif}.harness>nav{border-bottom:1px solid #896737}.harness>nav strong{flex:0 0 auto;color:#f0cb70}.harness>nav span{margin-left:auto;white-space:nowrap;color:#8de1c9}.harness button{flex:0 0 auto;padding:5px 8px;border:1px solid #84663d;border-radius:6px;color:#f2e4c9;background:#4b1e2d;cursor:pointer}.motion-controls{min-height:34px;background:#311421}.motion-controls button{font-size:8px}.harness>.love-letter-game{height:100%;min-height:0}[data-test-status="failed"]{color:#ff9d94!important}
</style>
