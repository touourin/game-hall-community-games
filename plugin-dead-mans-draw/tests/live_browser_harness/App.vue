<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../../frontend/GameView.vue'
import type { CardView, DeadMansDrawView, SuitId } from '../../frontend/types'

type Report = { playerCount: number; actionCount: number; turnCount: number; winnerPlayerIds: string[] }
const snapshot = ref<ArcadeSnapshot | null>(null)
const report = ref<Report | null>(null)
const running = ref(false)
const error = ref('')

async function loadPreview(count: number) {
  running.value = true; error.value = ''; report.value = null
  try {
    const response = await fetch(`/api/preview?count=${count}`)
    if (!response.ok) throw new Error(await response.text())
    snapshot.value = (await response.json()).snapshot
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function autoplay(count: number) {
  running.value = true; error.value = ''
  try {
    const response = await fetch(`/api/autoplay?count=${count}`, { method: 'POST' })
    if (!response.ok) throw new Error(await response.text())
    const payload = await response.json()
    snapshot.value = payload.snapshot
    report.value = payload.report
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

async function loadScenario(name: string) {
  running.value = true; error.value = ''; report.value = null
  try {
    const response = await fetch(`/api/scenario?name=${name}`)
    if (!response.ok) throw new Error(await response.text())
    snapshot.value = (await response.json()).snapshot
  } catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { running.value = false }
}

function playSuit(suit: SuitId) {
  if (!snapshot.value) return
  const game = snapshot.value.game as unknown as DeadMansDrawView
  const spec = game.suitCatalog.find(item => item.id === suit)!
  const card: CardView = { ...spec, suit, id: `loot-${suit}-${suit === 'mermaid' ? 9 : 7}`, value: suit === 'mermaid' ? 9 : 7 }
  const seq = (game.events.at(-1)?.seq ?? 0) + 1
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: { ...game, revision: game.revision + 1, events: [...game.events, { seq, type: 'card_entered', textZh: `${spec.nameZh}进入航道并发动能力`, data: { card, suit } }] },
  } as ArcadeSnapshot
}

function playSettlement(type: string) {
  if (!snapshot.value) return
  const game = snapshot.value.game as unknown as DeadMansDrawView
  const seq = (game.events.at(-1)?.seq ?? 0) + 1
  const text: Record<string, string> = {
    bust_detected: '美人鱼花色重复，发生爆牌', protected_split: '三张受保护牌飞入银行',
    key_chest_bonus: '钥匙与宝箱带来四张奖励牌', card_transferred: '航道战利品进入银行',
  }
  snapshot.value = {
    ...snapshot.value,
    revision: snapshot.value.revision + 1,
    game: { ...game, revision: game.revision + 1, events: [...game.events, { seq, type, textZh: text[type], data: type === 'bust_detected' ? { card: { ...game.suitCatalog.find(item => item.id === 'mermaid'), suit: 'mermaid', id: 'loot-mermaid-9', value: 9 } } : { count: 3 } }] },
  } as ArcadeSnapshot
}

onMounted(() => loadPreview(4))
</script>

<template>
  <main class="harness">
    <nav aria-label="本地完整对局测试控制台">
      <strong>亡命神抽 · 真实引擎与界面</strong>
      <button v-for="count in [2,3,4]" :key="`preview-${count}`" :data-preview-count="count" :disabled="running" @click="loadPreview(count)">{{ count }} 人桌面</button>
      <button v-for="count in [2,3,4]" :key="`auto-${count}`" :data-autoplay-count="count" :disabled="running" @click="autoplay(count)">跑完 {{ count }} 人局</button>
      <button data-scenario="trait" :disabled="running" @click="loadScenario('trait')">特性选择场景</button>
      <button data-scenario="effect" :disabled="running" @click="loadScenario('effect')">强制爆牌选择</button>
      <button data-scenario="shared" :disabled="running" @click="loadScenario('shared')">共享胜利结算</button>
      <span v-if="running" data-test-status="running">运行中…</span>
      <span v-else-if="report" data-test-status="passed">{{ report.playerCount }} 人通过 · {{ report.actionCount }} 动作 · {{ report.turnCount }} 回合 · 胜者 {{ report.winnerPlayerIds.join(', ') }}</span>
      <span v-if="error" data-test-status="failed">{{ error }}</span>
    </nav>
    <aside class="motion-controls" aria-label="全部花色与结算动画测试">
      <button v-for="suit in ['anchor','hook','cannon','key','chest','map','oracle','sword','kraken','mermaid'] as SuitId[]" :key="suit" :data-motion-suit="suit" @click="playSuit(suit)">{{ suit }}</button>
      <button v-for="type in ['bust_detected','protected_split','key_chest_bonus','card_transferred']" :key="type" :data-motion-type="type" @click="playSettlement(type)">{{ type }}</button>
    </aside>
    <GameView v-if="snapshot" :snapshot="snapshot" />
  </main>
</template>

<style>
:root { color-scheme: dark; background: #071817; }
* { box-sizing: border-box; }
body { margin: 0; min-width: 0; min-height: 100vh; background: #071817; }
.harness { min-width: 0; min-height: 100vh; overflow-x: hidden; }
.harness > nav, .motion-controls { min-width: 0; display: flex; align-items: center; gap: 6px; overflow-x: auto; padding: 6px 10px; color: #e7ddc8; background: #101f1e; font: 11px/1.2 system-ui, sans-serif; }
.harness > nav { min-height: 42px; border-bottom: 1px solid #6f4f32; }
.harness > nav strong { flex: 0 0 auto; color: #f2c96d; }
.harness > nav span { margin-left: auto; white-space: nowrap; color: #9bc8b9; }
.harness button { flex: 0 0 auto; padding: 5px 8px; border: 1px solid #725f3c; border-radius: 6px; color: #eee4cf; background: #263f3c; cursor: pointer; }
.motion-controls { min-height: 38px; background: #182c2a; }.motion-controls button { font-size: 9px; }
.harness > .dmd-game { min-height: calc(100dvh - 80px); }
[data-test-status="failed"] { color: #ff9d94 !important; }
</style>
