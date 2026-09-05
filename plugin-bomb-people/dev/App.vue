<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  installLocalGameActions,
  type ArcadeSnapshot,
} from './local-sdk'

const GameView = defineAsyncComponent(() => import('../frontend/GameView.vue'))


interface ApiResult {
  ok: boolean
  error?: string
  snapshot?: ArcadeSnapshot
  test?: { paused: boolean }
}

const snapshot = ref<ArcadeSnapshot | null>(null)
const viewerId = ref('local-p1')
const playerCount = ref(2)
const selectedItem = ref('bomb_up')
const paused = ref(false)
const busy = ref(false)
const errorMessage = ref('')
const notice = ref('正在连接本地规则服务……')
const mountVersion = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollRunning = false

const PHASE_LABELS: Record<string, string> = { lobby: '等待开局', playing: '游戏中', finished: '本局结束' }
const STAGE_LABELS: Record<string, string> = { countdown: '倒计时', active: '对抗', collapse: '落石', finished: '结束', lobby: '大厅' }
const game = computed(() => snapshot.value?.game as Record<string, any> | undefined)
const itemLabels = computed<Record<string, string>>(() => game.value?.itemLabels ?? {})
const canConfigure = computed(() => Boolean(snapshot.value && snapshot.value.phase !== 'playing'))
const phaseLabel = computed(() => PHASE_LABELS[snapshot.value?.phase ?? ''] ?? snapshot.value?.phase ?? '未连接')
const stageLabel = computed(() => STAGE_LABELS[game.value?.stage ?? ''] ?? game.value?.stage ?? '—')

async function api(path: string, body?: Record<string, unknown>, force = false): Promise<ApiResult> {
  const response = await fetch(path, body ? {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  } : undefined)
  const result = await response.json() as ApiResult
  if (!response.ok || !result.ok) throw new Error(result.error || `请求失败：${response.status}`)
  if (result.snapshot && (force || !snapshot.value || result.snapshot.revision >= snapshot.value.revision)) {
    snapshot.value = result.snapshot
  }
  if (result.test) paused.value = result.test.paused
  return result
}

async function run(label: string, operation: () => Promise<ApiResult>, force = false) {
  if (busy.value) return false
  busy.value = true
  errorMessage.value = ''
  try {
    const result = await operation()
    if (result.snapshot && force) snapshot.value = result.snapshot
    notice.value = label
    return true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
    return false
  } finally {
    busy.value = false
  }
}

async function poll() {
  if (pollRunning) return
  pollRunning = true
  try {
    const query = new URLSearchParams({ viewerId: viewerId.value })
    await api(`/api/snapshot?${query}`)
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    pollRunning = false
  }
}

async function resetRoom() {
  const ok = await run('测试房已重置', () => api('/api/reset', {
    playerCount: playerCount.value,
  }, true), true)
  if (ok) {
    viewerId.value = 'local-p1'
    mountVersion.value += 1
  }
}

async function startGame() {
  await run('游戏已开始', () => api('/api/start', { viewerId: viewerId.value }))
}

async function togglePause() {
  await run(paused.value ? '游戏已继续' : '游戏已暂停', () => api('/api/debug/pause', {
    viewerId: viewerId.value,
    paused: !paused.value,
  }))
}

async function jumpToCollapse() {
  await run('已进入落石阶段', () => api('/api/debug/collapse', { viewerId: viewerId.value }))
}

async function finishMatch() {
  await run('已生成结算画面', () => api('/api/debug/finish', { viewerId: viewerId.value }))
}

async function spawnItem() {
  await run(`已在附近投放${itemLabels.value[selectedItem.value] ?? selectedItem.value}`, () => api('/api/debug/spawn-item', {
    viewerId: viewerId.value,
    kind: selectedItem.value,
  }))
}

async function grantItem() {
  await run(`已授予${itemLabels.value[selectedItem.value] ?? selectedItem.value}`, () => api('/api/debug/grant-item', {
    viewerId: viewerId.value,
    kind: selectedItem.value,
  }))
}

async function sendGameAction(action: string, payload?: Record<string, unknown>) {
  try {
    await api('/api/action', { viewerId: viewerId.value, action, payload: payload ?? {} })
    return true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
    return false
  }
}

installLocalGameActions({
  action: sendGameAction,
  rapidAction: sendGameAction,
  restart: async () => run('新一局已开始', () => api('/api/restart', { viewerId: viewerId.value })),
  publishSpectatorFrame: () => false,
})

watch(viewerId, () => {
  mountVersion.value += 1
  void poll()
})

onMounted(async () => {
  await poll()
  notice.value = '本地测试已就绪；房主可协商下一局地图，未协商时仍会随机换图。'
  pollTimer = setInterval(poll, 33)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="local-test-shell">
    <section class="local-test-toolbar" aria-label="本地测试控制台">
      <div class="toolbar-title">
        <strong>炸弹超人 · 本地测试台</strong>
        <span>{{ phaseLabel }} · {{ stageLabel }} · Tick {{ game?.tick ?? 0 }}</span>
      </div>

      <label>
        玩家数
        <select v-model.number="playerCount" :disabled="busy || !canConfigure">
          <option v-for="count in 7" :key="count + 1" :value="count + 1">{{ count + 1 }} 人</option>
        </select>
      </label>
      <button type="button" :disabled="busy || !canConfigure" @click="resetRoom">按配置重置</button>
      <button class="primary" type="button" :disabled="busy || snapshot?.phase !== 'lobby'" @click="startGame">开始游戏</button>

      <label>
        当前操控
        <select v-model="viewerId" :disabled="busy">
          <option v-for="player in snapshot?.players ?? []" :key="player.id" :value="player.id">
            {{ player.name }}{{ player.isHost ? '（房主）' : '' }}
          </option>
        </select>
      </label>
      <button type="button" :disabled="busy || snapshot?.phase !== 'playing'" @click="togglePause">{{ paused ? '继续' : '暂停' }}</button>
      <button type="button" :disabled="busy || snapshot?.phase !== 'playing'" @click="jumpToCollapse">跳到落石</button>
      <button type="button" :disabled="busy || snapshot?.phase !== 'playing'" @click="finishMatch">让当前玩家夺冠</button>

      <label>
        调试道具
        <select v-model="selectedItem" :disabled="busy">
          <option v-for="(label, key) in itemLabels" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <button type="button" :disabled="busy || snapshot?.phase !== 'playing'" @click="spawnItem">投放到附近</button>
      <button type="button" :disabled="busy || snapshot?.phase !== 'playing'" @click="grantItem">直接授予</button>

      <div class="toolbar-status" :class="{ error: errorMessage }">
        {{ errorMessage || notice }}
      </div>
    </section>

    <section v-if="!snapshot" class="local-loading">正在加载真实游戏引擎……</section>
    <GameView
      v-else
      :key="`${viewerId}:${mountVersion}`"
      :snapshot="snapshot"
    />
  </main>
</template>
