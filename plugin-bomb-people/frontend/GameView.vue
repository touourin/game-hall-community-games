<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  BookOpen,
  Check,
  Expand,
  Gamepad2,
  Map as MapIcon,
  Minimize,
  Skull,
  Trophy,
  Zap,
} from '@lucide/vue'
import {
  PluginButton,
  PluginIconButton,
  PluginModal,
  usePluginFullscreen,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import GameBoard from './GameBoard.vue'
import { ITEM_ART, MAP_ART, PLAYER_ART } from './catalog'
import { createBombPeopleSound } from './sound'
import type { BombGame, BombMap, BombPlayer } from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const sound = createBombPeopleSound()
const gameRoot = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported, toggle } = usePluginFullscreen(gameRoot)

const showRules = ref(false)
const showMaps = ref(props.snapshot.phase === 'lobby')
const keyboardMask = ref(0)
const touchMask = ref(0)
const joystickX = ref(0)
const joystickY = ref(0)
const joystickActive = ref(false)
const SNAPSHOT_CLOCK_MS = 50
const BACKUP_CLOCK_STALE_MS = 180
const RELEASE_RETRY_DELAYS_MS = [45, 120] as const
let inputSequence = 0
let heartbeatSequence = 0
let heartbeatTimer: ReturnType<typeof setInterval> | null = null
let heartbeatInFlight = false
let lastSnapshotAt = performance.now()
let disposed = false
let joystickPointerId: number | null = null
let soundEffectsInitialized = false
let soundRound = props.snapshot.roundNumber
const seenSoundEffectIds = new Set<number>()
const inputRetryTimers = new Set<ReturnType<typeof setTimeout>>()

const game = computed(() => props.snapshot.game as unknown as BombGame)
const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const selfActor = computed(() => game.value.players.find(player => player.id === props.snapshot.self.id) ?? null)
const isCarryingBomb = computed(() => selfActor.value?.carriedBombId != null)
const canControl = computed(() => (
  props.snapshot.phase === 'playing'
  && !isSpectator.value
  && Boolean(selfActor.value?.alive)
  && !game.value.frozen
))
const isMapCatalogPhase = computed(() => ['lobby', 'finished'].includes(props.snapshot.phase))
const selectedMap = computed(() => game.value.mapCatalog.find(map => map.key === game.value.selectedMap) ?? game.value.currentMap)
const winner = computed(() => game.value.players.find(player => player.id === game.value.winnerId) ?? null)

const roster = computed(() => {
  if (game.value.players.length) return game.value.players
  return props.snapshot.players.map((player, index): BombPlayer => ({
    id: player.id,
    name: player.name,
    seat: player.seat,
    color: ['#ff5a55', '#4f8cff', '#ffd44f', '#50c878', '#ff914d', '#45d6dd', '#a970ff', '#d7b25b'][index % 8]!,
    character: index % 8,
    x: 0,
    y: 0,
    facingX: 0,
    facingY: 1,
    moving: false,
    carriedBombId: null,
    alive: true,
    eliminatedBy: null,
    eliminationReason: null,
    kills: 0,
    stats: { kills: 0, championships: 0, matches: 0, winRate: 0 },
    equipment: {
      bombCapacity: 1, blastRange: 2, speedLevel: 0,
      kick: false, punch: false, throw: false, timer: false, chain: false,
      magnet: false, ice: false, shieldCharges: 0,
      ghost: false, invincibleTicks: 0, cursedTicks: 0,
    },
  }))
})

const inventory = computed(() => {
  const equipment = selfActor.value?.equipment
  if (!equipment) return []
  const result: { key: string; label: string; value?: string; active?: boolean }[] = [
    { key: 'bomb_up', label: '炸弹', value: `×${equipment.bombCapacity}`, active: true },
    { key: 'flame_up', label: '火焰', value: `${equipment.blastRange} 格`, active: true },
  ]
  if (equipment.speedLevel) result.push({ key: 'speed', label: '速度', value: `Lv.${equipment.speedLevel}`, active: true })
  for (const [key, enabled] of [
    ['kick', equipment.kick], ['punch', equipment.punch], ['throw', equipment.throw],
    ['timer', equipment.timer], ['chain', equipment.chain], ['magnet', equipment.magnet], ['ice', equipment.ice],
  ] as const) if (enabled) result.push({
    key,
    label: game.value.itemLabels[key] ?? key,
    value: key === 'timer' ? '遥控 ×1' : undefined,
    active: true,
  })
  if (equipment.shieldCharges) result.push({ key: 'shield', label: '护盾', value: `×${equipment.shieldCharges}`, active: true })
  if (equipment.ghost) result.push({ key: 'ghost', label: '幽灵', value: '永久', active: true })
  if (equipment.invincibleTicks) result.push({ key: 'star', label: '无敌', value: seconds(equipment.invincibleTicks), active: true })
  if (equipment.cursedTicks) result.push({ key: 'skull', label: '禁雷', value: seconds(equipment.cursedTicks), active: true })
  return result
})

const stageLabel = computed(() => ({
  lobby: '等待开局', countdown: '准备', active: '对抗中', collapse: '落石决胜', finished: '本局结束',
}[game.value.stage] ?? game.value.stage))

const stageTime = computed(() => {
  if (game.value.stage === 'collapse') return `落石 ${game.value.collapsePlaced}/${game.value.collapseTotal}`
  if (game.value.stage === 'finished') return '00:00'
  const ticks = game.value.stage === 'countdown' ? game.value.stageTicksRemaining : game.value.roundTicksRemaining
  const total = Math.max(0, Math.ceil(ticks / Math.max(1, game.value.tickRate)))
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
})

function seconds(ticks: number) {
  return `${Math.ceil(ticks / Math.max(1, game.value.tickRate))}s`
}

function mapArt(map: BombMap) {
  return MAP_ART[map.key] ?? MAP_ART.magma_crucible
}

const KEY_BITS: Record<string, number> = {
  KeyW: 1,
  ArrowUp: 1,
  KeyS: 2,
  ArrowDown: 2,
  KeyA: 4,
  ArrowLeft: 4,
  KeyD: 8,
  ArrowRight: 8,
  Space: 16,
  KeyZ: 32,
  KeyX: 64,
  KeyC: 128,
}
const DIRECTION_MASK = 1 | 2 | 4 | 8
const JOYSTICK_RADIUS = 38
const JOYSTICK_DEAD_ZONE = 10

const joystickStyle = computed(() => ({
  transform: `translate(-50%, -50%) translate3d(${joystickX.value}px, ${joystickY.value}px, 0)`,
}))

function isEditableTarget(target: EventTarget | null) {
  return target instanceof Element
    && Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

function combinedMask() {
  return keyboardMask.value | touchMask.value
}

function unlockSound() {
  sound.unlock()
}

function canTransmitInput(nextMask: number) {
  if (nextMask !== 0) return canControl.value
  return props.snapshot.phase === 'playing' && !isSpectator.value
}

function scheduleInputRetry(nextMask: number, delay: number, retryOnFailure = false) {
  if (disposed) return
  const timer = setTimeout(() => {
    inputRetryTimers.delete(timer)
    if (disposed || combinedMask() !== nextMask || !canTransmitInput(nextMask)) return
    transmitInput(nextMask, retryOnFailure)
  }, delay)
  inputRetryTimers.add(timer)
}

function transmitInput(nextMask: number, retryOnFailure = true) {
  if (disposed || !canTransmitInput(nextMask)) return
  inputSequence = Math.max(inputSequence, game.value.selfInputSequence) + 1
  const request = actions.rapidAction('input', {
    sequence: inputSequence,
    inputMask: nextMask,
  })
  void request.then(
    accepted => {
      if (!accepted && retryOnFailure && combinedMask() === nextMask) {
        scheduleInputRetry(nextMask, 70)
      }
    },
    () => {
      if (retryOnFailure && combinedMask() === nextMask) {
        scheduleInputRetry(nextMask, 70)
      }
    },
  )
}

function sendInput(nextMask = combinedMask(), released = false) {
  transmitInput(nextMask)
  if (!released) return
  for (const delay of RELEASE_RETRY_DELAYS_MS) {
    scheduleInputRetry(nextMask, delay)
  }
}

function updateKeyboard(bit: number, pressed: boolean) {
  const previous = combinedMask()
  keyboardMask.value = pressed ? keyboardMask.value | bit : keyboardMask.value & ~bit
  const next = combinedMask()
  if (next !== previous) sendInput(next, Boolean(previous & ~next))
}

function keydown(event: KeyboardEvent) {
  const bit = KEY_BITS[event.code]
  if (!bit || isEditableTarget(event.target) || !canControl.value) return
  event.preventDefault()
  unlockSound()
  updateKeyboard(bit, true)
}

function keyup(event: KeyboardEvent) {
  const bit = KEY_BITS[event.code]
  if (!bit) return
  if (canControl.value) event.preventDefault()
  updateKeyboard(bit, false)
}

function touchDown(bit: number, event: PointerEvent) {
  if (!canControl.value) return
  event.preventDefault()
  unlockSound()
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
  const previous = combinedMask()
  touchMask.value |= bit
  if (combinedMask() !== previous) sendInput()
}

function touchUp(bit: number, event: PointerEvent) {
  event.preventDefault()
  const previous = combinedMask()
  touchMask.value &= ~bit
  if (combinedMask() !== previous) sendInput(combinedMask(), true)
}

function setTouchDirection(bit: number) {
  const previous = combinedMask()
  touchMask.value = (touchMask.value & ~DIRECTION_MASK) | bit
  const next = combinedMask()
  if (next !== previous) sendInput(next, Boolean(previous & ~next))
}

function moveJoystick(event: PointerEvent) {
  if (event.pointerId !== joystickPointerId) return
  event.preventDefault()
  const target = event.currentTarget as HTMLElement
  const bounds = target.getBoundingClientRect()
  let x = event.clientX - (bounds.left + bounds.width / 2)
  let y = event.clientY - (bounds.top + bounds.height / 2)
  const distance = Math.hypot(x, y)
  if (distance > JOYSTICK_RADIUS) {
    x = x / distance * JOYSTICK_RADIUS
    y = y / distance * JOYSTICK_RADIUS
  }
  joystickX.value = Math.round(x)
  joystickY.value = Math.round(y)

  if (distance < JOYSTICK_DEAD_ZONE) {
    setTouchDirection(0)
  } else if (Math.abs(x) > Math.abs(y)) {
    setTouchDirection(x < 0 ? 4 : 8)
  } else {
    setTouchDirection(y < 0 ? 1 : 2)
  }
}

function startJoystick(event: PointerEvent) {
  if (!canControl.value || joystickPointerId !== null) return
  unlockSound()
  joystickPointerId = event.pointerId
  joystickActive.value = true
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
  moveJoystick(event)
}

function stopJoystick(event: PointerEvent) {
  if (event.pointerId !== joystickPointerId) return
  event.preventDefault()
  joystickPointerId = null
  joystickActive.value = false
  joystickX.value = 0
  joystickY.value = 0
  setTouchDirection(0)
}

function clearInput(notify = true) {
  const hadInput = combinedMask() !== 0
  keyboardMask.value = 0
  touchMask.value = 0
  joystickPointerId = null
  joystickActive.value = false
  joystickX.value = 0
  joystickY.value = 0
  if (notify && hadInput && props.snapshot.phase === 'playing' && !isSpectator.value) {
    sendInput(0, true)
  }
}

function blur() {
  clearInput(true)
}

function visibilityChange() {
  if (document.hidden) clearInput(true)
}

async function heartbeat() {
  const isLeader = game.value.clockLeaderId === props.snapshot.self.id
  const backupDelay = BACKUP_CLOCK_STALE_MS + Math.max(0, props.snapshot.self.seat) * 15
  if (
    heartbeatInFlight
    || props.snapshot.phase !== 'playing'
    || isSpectator.value
    || (!isLeader && performance.now() - lastSnapshotAt < backupDelay)
  ) return
  heartbeatInFlight = true
  heartbeatSequence += 1
  try {
    await actions.rapidAction('heartbeat', { sequence: heartbeatSequence })
  } catch {
    // The next clock slot retries naturally; never build an in-flight queue.
  } finally {
    heartbeatInFlight = false
  }
}

watch(canControl, active => { if (!active) clearInput(true) })
watch(() => props.snapshot.phase, phase => {
  showMaps.value = phase === 'lobby'
})
watch(() => game.value.tick, () => {
  lastSnapshotAt = performance.now()
})
watch(() => game.value.effects ?? [], nextEffects => {
  if (soundRound !== props.snapshot.roundNumber) {
    soundRound = props.snapshot.roundNumber
    seenSoundEffectIds.clear()
  }
  for (const effect of nextEffects) {
    if (seenSoundEffectIds.has(effect.id)) continue
    seenSoundEffectIds.add(effect.id)
    if (soundEffectsInitialized) sound.play(effect.kind)
  }
  soundEffectsInitialized = true
}, { immediate: true })

onMounted(() => {
  inputSequence = Math.max(0, game.value.selfInputSequence)
  window.addEventListener('keydown', keydown, { passive: false })
  window.addEventListener('keyup', keyup, { passive: false })
  window.addEventListener('pointerdown', unlockSound, { passive: true, once: true })
  window.addEventListener('blur', blur)
  window.addEventListener('pagehide', blur)
  document.addEventListener('visibilitychange', visibilityChange)
  heartbeatTimer = setInterval(() => { void heartbeat() }, SNAPSHOT_CLOCK_MS)
})

onBeforeUnmount(() => {
  clearInput(true)
  disposed = true
  window.removeEventListener('keydown', keydown)
  window.removeEventListener('keyup', keyup)
  window.removeEventListener('pointerdown', unlockSound)
  window.removeEventListener('blur', blur)
  window.removeEventListener('pagehide', blur)
  document.removeEventListener('visibilitychange', visibilityChange)
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  for (const timer of inputRetryTimers) clearTimeout(timer)
  inputRetryTimers.clear()
  sound.destroy()
})
</script>

<template>
  <section ref="gameRoot" class="bomb-people" :class="[`stage-${game.stage}`, { fullscreen: isFullscreen }]">
    <header class="game-header">
      <div class="title-lockup">
        <span class="brand-bomb"><i /></span>
        <div><p>BOMB PEOPLE · 20 × 20</p><h2>炸弹超人</h2></div>
      </div>
      <div class="match-status" :class="game.stage">
        <span>{{ stageLabel }}</span><strong>{{ stageTime }}</strong><small>{{ selectedMap?.name }}</small>
      </div>
      <div class="header-actions">
        <PluginIconButton label="玩法说明" @click="showRules = true"><BookOpen :size="18" /></PluginIconButton>
        <PluginIconButton v-if="isMapCatalogPhase" label="随机地图池" @click="showMaps = !showMaps"><MapIcon :size="18" /></PluginIconButton>
        <PluginIconButton v-if="isSupported" :label="isFullscreen ? '退出全屏' : '全屏游戏'" @click="toggle">
          <Minimize v-if="isFullscreen" :size="18" /><Expand v-else :size="18" />
        </PluginIconButton>
      </div>
    </header>

    <section v-if="isMapCatalogPhase && showMaps" class="map-negotiation" aria-label="随机地图池">
      <div class="negotiation-heading">
        <div><p class="eyebrow">RANDOM MAP ROTATION</p><h3>每局随机抽取，连续两局不会重复</h3></div>
        <p class="proposal-status">{{ snapshot.phase === 'finished' ? '本局地图' : '当前展示' }}：<strong>{{ selectedMap?.name }}</strong><span>下一局开局时重新抽取</span></p>
      </div>

      <div class="map-grid">
        <button
          v-for="map in game.mapCatalog"
          :key="map.key"
          type="button"
          class="map-card"
          :class="{ selected: map.key === game.selectedMap }"
          disabled
          :aria-label="`${map.name}，${map.pace}，${map.density}${map.key === game.selectedMap ? '，当前展示地图' : ''}`"
        >
          <img :src="mapArt(map)" :alt="`${map.name}预览`" draggable="false" />
          <span class="map-shade" />
          <span class="map-badges"><i>{{ map.pace }}</i><i>{{ map.density }}</i></span>
          <span class="map-copy"><strong>{{ map.name }}</strong><small>{{ map.subtitle }}</small></span>
          <span v-if="map.startingItems.length" class="starter-icons" title="本图带初始装备">
            <img v-for="item in map.startingItems" :key="item" :src="ITEM_ART[item]" :alt="game.itemLabels[item]" />
          </span>
          <span v-if="map.key === game.selectedMap" class="selected-mark"><Check :size="13" />{{ snapshot.phase === 'finished' ? '本局' : '展示' }}</span>
        </button>
      </div>
      <p class="map-help">房主开始新一局时，由服务端从全部 {{ game.mapCatalog.length }} 张地图中随机抽取；上一局地图会暂时排除。</p>
    </section>

    <section v-if="snapshot.phase === 'lobby'" class="lobby-overview">
      <div class="lobby-copy">
        <p class="eyebrow">READY ROOM</p>
        <h3>下一局随机地图</h3>
        <p>开局时从全部 {{ game.mapCatalog.length }} 张地图中随机抽取，连续两局不会重复。每局先对抗 90 秒，随后从左上角开始沿边缘顺时针一圈圈落石，最后生还者夺冠。</p>
        <div class="rule-chips"><span>2–8 人</span><span>随机换图</span><span>炸弹 2 秒</span><span>自动拾取</span><span>落石可淘汰</span></div>
        <small>玩家准备完毕后，由房主使用房间顶部的“开始游戏”。</small>
      </div>
      <div class="lobby-roster" aria-label="本房间玩家">
        <article v-for="player in roster" :key="player.id" :style="{ '--player-color': player.color }">
          <img :src="PLAYER_ART[player.character]" :alt="player.name" /><div><strong>{{ player.name }}</strong><small>玩家 {{ player.seat + 1 }}{{ player.id === snapshot.hostId ? ' · 房主' : '' }}</small></div>
        </article>
        <div v-for="seat in Math.max(0, 2 - roster.length)" :key="`empty:${seat}`" class="empty-seat">等待玩家加入</div>
      </div>
    </section>

    <div v-else class="play-layout">
      <aside class="scoreboard panel" aria-label="玩家战绩">
        <div class="panel-heading"><div><p class="eyebrow">LIVE RECORDS</p><h3>玩家战绩</h3></div><Trophy :size="19" /></div>
        <div class="player-list">
          <article
            v-for="player in game.players"
            :key="player.id"
            class="player-card"
            :class="{ self: player.id === snapshot.self.id, eliminated: !player.alive }"
            :style="{ '--player-color': player.color }"
          >
            <div class="player-avatar"><img :src="PLAYER_ART[player.character]" :alt="player.name" /><span>{{ player.seat + 1 }}</span></div>
            <div class="player-info"><strong>{{ player.name }}</strong><small>{{ player.alive ? (player.id === snapshot.self.id ? '你 · 生还' : '生还') : '已阵亡' }}</small></div>
            <div class="kill-count"><b>{{ player.kills }}</b><small>本局击杀</small></div>
            <div class="career-row"><span><Trophy :size="11" />{{ player.stats.championships }} 冠</span><span>{{ player.stats.winRate }}% 胜率</span><span>{{ player.stats.kills }} 总击杀</span></div>
          </article>
        </div>
        <p class="records-note">当前房间连续对局统计；每局结果和击杀明细同时写入大厅战绩。</p>
      </aside>

      <main class="arena-column">
        <GameBoard :game="game" :self-id="snapshot.self.id" :self-input-mask="combinedMask()" />

        <div v-if="!isSpectator && snapshot.phase === 'playing'" class="touch-controls" :class="{ disabled: !canControl }" aria-label="移动端触屏操作">
          <div
            class="joystick"
            :class="{ active: joystickActive }"
            role="application"
            aria-label="移动摇杆，按住并向一个方向滑动"
            @pointerdown="startJoystick"
            @pointermove="moveJoystick"
            @pointerup="stopJoystick"
            @pointercancel="stopJoystick"
            @lostpointercapture="stopJoystick"
          >
            <span class="joystick-compass" aria-hidden="true">▲</span>
            <span class="joystick-knob" :style="joystickStyle" aria-hidden="true"><i /></span>
            <small>滑动移动</small>
          </div>
          <div class="action-pad">
            <button class="punch-action" type="button" aria-label="拳击手套打雷" @pointerdown="touchDown(32, $event)" @pointerup="touchUp(32, $event)" @pointercancel="touchUp(32, $event)" @lostpointercapture="touchUp(32, $event)"><b>拳</b><small>打雷</small></button>
            <button class="bomb-action" type="button" aria-label="放置普通炸弹或部署遥控定时炸弹" @pointerdown="touchDown(16, $event)" @pointerup="touchUp(16, $event)" @pointercancel="touchUp(16, $event)" @lostpointercapture="touchUp(16, $event)"><b>●</b><small>放雷</small></button>
            <button v-if="selfActor?.equipment.timer" class="timer-action" type="button" :disabled="isCarryingBomb" aria-label="引爆自己的遥控定时炸弹" @pointerdown="touchDown(128, $event)" @pointerup="touchUp(128, $event)" @pointercancel="touchUp(128, $event)" @lostpointercapture="touchUp(128, $event)"><b>C</b><small>引爆</small></button>
            <button class="throw-action" type="button" :aria-label="isCarryingBomb ? '扔出手中炸弹' : '拿起面前炸弹'" @pointerdown="touchDown(64, $event)" @pointerup="touchUp(64, $event)" @pointercancel="touchUp(64, $event)" @lostpointercapture="touchUp(64, $event)"><b>{{ isCarryingBomb ? '投' : '拿' }}</b><small>{{ isCarryingBomb ? '扔出' : '抱雷' }}</small></button>
          </div>
        </div>
      </main>

      <aside class="battle-hud">
        <section v-if="snapshot.phase === 'finished'" class="result-card panel">
          <Trophy v-if="winner" :size="28" /><Skull v-else :size="28" />
          <p class="eyebrow">MATCH RESULT</p>
          <h3>{{ winner ? `${winner.name} 夺冠` : '本局平局' }}</h3>
          <p>{{ snapshot.winReason }}</p>
          <PluginButton block :disabled="!snapshot.actions.canRestart" @click="actions.restart()">
            {{ snapshot.actions.canRestart ? '同意再来一局' : '等待其他玩家确认' }}
          </PluginButton>
          <PluginButton variant="secondary" block @click="showMaps = !showMaps"><MapIcon :size="16" />查看随机地图池</PluginButton>
        </section>

        <section class="inventory panel">
          <div class="panel-heading"><div><p class="eyebrow">AUTO PICKUP</p><h3>{{ isSpectator ? '观察装备' : '我的装备' }}</h3></div><Zap :size="19" /></div>
          <div v-if="inventory.length" class="inventory-grid">
            <div v-for="entry in inventory" :key="entry.key" class="inventory-item" :class="entry.key">
              <img :src="ITEM_ART[entry.key]" :alt="entry.label" /><span><strong>{{ entry.label }}</strong><small>{{ entry.value ?? '已装备' }}</small></span>
            </div>
          </div>
          <p v-else class="empty-inventory">破坏箱子并走过道具即可自动拾取。</p>
          <p v-if="selfActor?.equipment.cursedTicks" class="curse-warning"><Skull :size="16" />骷髅诅咒：装备已清空，{{ seconds(selfActor.equipment.cursedTicks) }} 内不能放炸弹。</p>
        </section>

        <section class="controls panel">
          <div class="panel-heading"><div><p class="eyebrow">CONTROLS</p><h3>操作</h3></div><Gamepad2 :size="19" /></div>
          <div class="key-guide"><span><kbd>WASD / ↑↓←→</kbd>移动</span><span><kbd>Space</kbd>放雷 / 部署遥控雷</span><span><kbd>C</kbd>引爆遥控雷</span><span><kbd>Z</kbd>拳套即时打雷</span><span><kbd>X</kbd>先拿雷，再按投出</span></div>
          <p>普通炸弹达到容量后再按空格，会用额外槽部署一枚遥控定时炸弹；它不会倒计时或被火焰、连锁引爆，只有所有者按 C 才会爆炸。扔雷分两步：第一次拿起面前炸弹，可抱着继续移动；第二次按当前朝向投出最多四格。抱雷期间不能放雷或遥控引爆，普通炸弹的剩余引信暂停，投出或落地后继续倒计时。幽灵相位获得后本局永久生效，可穿过箱墙并在箱墙格内放雷，但不能穿固定石块或决胜落石。</p>
        </section>

        <section class="event-panel panel" aria-label="对局动态">
          <div class="panel-heading"><div><p class="eyebrow">BATTLE FEED</p><h3>对局动态</h3></div></div>
          <div class="event-list"><p v-for="event in [...game.events].reverse().slice(0, 7)" :key="event.id">{{ event.message }}</p><p v-if="!game.events.length">等待对局事件……</p></div>
        </section>
      </aside>
    </div>

    <PluginModal v-if="showRules" title="炸弹超人 · 完整玩法" size="large" mobile-sheet @close="showRules = false">
      <div class="rulebook">
        <section><h3>目标与时间</h3><p>支持 2–8 人。每张地图固定为 20×20 格；一个方块只占一格。最后生还者夺冠。开局倒计时后对抗 90 秒，随后从左上角起沿外圈顺时针放置落石，再一圈圈向中心收缩。爆炸和落石都能淘汰玩家。</p></section>
        <section><h3>炸弹与通用交互</h3><p>普通炸弹放下后最多 2 秒爆炸，火焰按十字方向传播，固定石块和落石会阻挡，可破坏箱墙被摧毁后有 38% 概率掉落道具。幽灵相位获得后本局永久生效，可穿箱墙并在墙内放雷；墙内炸弹爆炸时会同时摧毁所在箱墙，但幽灵不能穿固定石块或决胜落石。火焰和连锁引线只会引爆普通炸弹；遥控定时炸弹只响应所有者的 C 键。</p></section>
        <section><h3>电脑键盘与手机触屏</h3><ul><li><kbd>W A S D</kbd> 或方向键：逐格移动。</li><li><kbd>Space</kbd>：先放普通炸弹；普通容量已满且拥有遥控定时炸弹时，再部署一枚不占普通容量的遥控雷。</li><li><kbd>C</kbd>：引爆自己的遥控定时炸弹；引爆后额外槽永久保留，可再次部署。</li><li><kbd>Z</kbd>：用拳击手套即时把面前炸弹打出三格。</li><li><kbd>X</kbd>：第一次拿起面前炸弹，之后可继续移动；第二次按当前朝向把手中炸弹越过障碍投到前方最多四格。若没有可用落点则继续抱着。</li><li>抱雷会占用双手，不能放雷、遥控引爆或使用拳套；普通炸弹被拿起时冻结剩余引信，成功投出，或因退出、阵亡、失去手套而落地后，才继续倒计时。</li><li>脚踢雷无需单独按键，朝炸弹移动即可让它持续滚动。</li><li>手机端拖动左侧摇杆移动，右手点击拳击、放雷、遥控引爆和拿雷/投雷按钮。</li></ul></section>
        <section><h3>道具</h3><div class="rules-items"><article v-for="(label, key) in game.itemLabels" :key="key"><img :src="ITEM_ART[key]" :alt="label" /><strong>{{ label }}</strong></article></div><p>道具自动拾取。落地道具没有消失倒计时，也不会被爆炸清除，会保留到被拾取、所在格被决胜落石覆盖或本局结束。骷髅诅咒会立即清空其他装备，并使玩家 5 秒不能放炸弹；地图还会每 10 秒进行一次 24% 的随机装备刷新判定。</p></section>
        <section><h3>地图类型</h3><p>云顶激斗场、风暴船坞等激斗图让玩家近距离出生并自带装备；丛林金字塔、发条铸造厂和水晶裂隙使用高密箱墙或分区固定墙，给予玩家更安全的发展期。其他地图在障碍密度和开阔程度之间变化。</p></section>
        <section><h3>随机地图与战绩</h3><p>每次新一局开始时，服务端从全部地图中随机抽取，并排除上一局地图以避免连续重复。每名玩家记录本局击杀、房间累计击杀、夺冠数和胜率；结算后还会把胜负及击杀明细写入大厅战绩。</p></section>
      </div>
    </PluginModal>
  </section>
</template>

<style scoped>
.bomb-people { --ink: #f2f5f6; --muted: #98a4aa; --panel: #12181de8; --panel-strong: #0d1216f2; --line: #ffffff18; --accent: #f0a63a; width: 100%; min-width: 0; max-width: none; min-height: min(860px, calc(100vh - 110px)); padding: 10px; color: var(--ink); background: radial-gradient(circle at 50% -20%, #303a42 0, #11171b 46%, #080b0e 100%); border: 1px solid #ffffff12; border-radius: 20px; box-sizing: border-box; overflow: hidden; }
.bomb-people * { box-sizing: border-box; }
.bomb-people.fullscreen { width: 100vw; height: 100vh; min-height: 100vh; padding: 12px; border: 0; border-radius: 0; overflow: auto; }
.game-header { min-width: 0; min-height: 76px; display: grid; grid-template-columns: minmax(190px, 1fr) auto minmax(190px, 1fr); align-items: center; gap: 14px; padding: 8px 12px 12px; }
.title-lockup, .header-actions, .match-status, .panel-heading, .negotiation-heading { display: flex; align-items: center; }
.title-lockup { gap: 12px; min-width: 0; }.title-lockup p, .eyebrow { margin: 0 0 3px; color: var(--muted); font-size: 9px; font-weight: 800; letter-spacing: .16em; }.title-lockup h2 { margin: 0; font-size: clamp(24px, 2.5vw, 36px); letter-spacing: .07em; }
.brand-bomb { position: relative; width: 42px; height: 42px; flex: 0 0 auto; border-radius: 50%; background: radial-gradient(circle at 30% 25%, #808b90 0 7%, #282f34 25%, #07090b 73%); border: 1px solid #8d9699; box-shadow: inset -5px -6px 8px #000, 0 4px 10px #0008; }.brand-bomb::before { content: ''; position: absolute; width: 16px; height: 12px; right: 0; top: -7px; border: 4px solid #b98647; border-bottom: 0; border-radius: 50%; transform: rotate(34deg); }.brand-bomb i { position: absolute; right: -6px; top: -8px; width: 8px; height: 8px; border-radius: 50%; background: #fff4a3; box-shadow: 0 0 8px 3px #ff7918; }
.match-status { justify-self: center; flex-direction: column; min-width: 160px; padding: 7px 26px; border: 1px solid var(--line); border-radius: 14px; background: #080c0f99; box-shadow: inset 0 1px #ffffff12; }.match-status span { color: #ffcd73; font-size: 9px; font-weight: 800; letter-spacing: .18em; }.match-status strong { font: 800 25px/1.15 ui-monospace, monospace; font-variant-numeric: tabular-nums; }.match-status small { max-width: 180px; overflow: hidden; color: var(--muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }.match-status.collapse { border-color: #d64f48; background: #3a0d0dcc; }.match-status.finished { border-color: #d6a84966; }
.header-actions { justify-self: end; gap: 7px; }.header-actions > * { min-width: 44px; min-height: 44px; }
.panel, .map-negotiation, .lobby-overview { min-width: 0; border: 1px solid var(--line); border-radius: 15px; background: var(--panel); box-shadow: inset 0 1px #ffffff0d, 0 10px 24px #0002; }
.map-negotiation { margin: 0 4px 12px; padding: 14px; }.negotiation-heading { justify-content: space-between; gap: 16px; margin-bottom: 12px; }.negotiation-heading h3, .panel-heading h3, .lobby-copy h3, .result-card h3 { margin: 0; }.proposal-status { display: grid; justify-items: end; gap: 2px; margin: 0; color: var(--muted); font-size: 11px; }.proposal-status strong { color: var(--ink); font-size: 14px; }.proposal-status span { color: #f2bb5b; }
.map-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 9px; }.map-card { position: relative; min-width: 0; aspect-ratio: 1.18; overflow: hidden; padding: 0; border: 1px solid #ffffff1f; border-radius: 11px; background: #0c1114; color: white; font: inherit; text-align: left; cursor: default; }.map-card > img:first-child { width: 100%; height: 100%; object-fit: cover; }.map-card.selected { border-color: #f1b84f; box-shadow: 0 0 0 1px #f1b84f, 0 0 16px #f1a93d33; }.map-shade { position: absolute; inset: 0; background: linear-gradient(transparent 25%, #080b0eda 70%, #080b0ef7); }.map-badges { position: absolute; left: 7px; top: 7px; display: flex; gap: 4px; }.map-badges i { padding: 2px 5px; border: 1px solid #ffffff33; border-radius: 999px; background: #091015c7; font-size: 8px; font-style: normal; }.map-copy { position: absolute; left: 8px; right: 8px; bottom: 7px; display: grid; gap: 2px; }.map-copy strong { font-size: 12px; }.map-copy small { overflow: hidden; color: #c7d0d4; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.starter-icons { position: absolute; right: 6px; top: 6px; display: flex; max-width: 60%; }.starter-icons img { width: 22px; height: 22px; margin-left: -5px; object-fit: contain; filter: drop-shadow(0 1px 2px #000); }.selected-mark { position: absolute; right: 6px; bottom: 6px; display: flex; align-items: center; gap: 2px; padding: 2px 5px; border-radius: 999px; color: #241806; background: #f0b74e; font-size: 8px; font-weight: 800; }.map-help { margin: 10px 1px 0; color: var(--muted); font-size: 10px; text-align: center; }
.lobby-overview { margin: 0 4px 4px; min-height: 430px; display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(300px, .8fr); gap: 30px; align-items: center; padding: clamp(24px, 5vw, 64px); background: radial-gradient(circle at 18% 18%, #e1912b20, transparent 30%), var(--panel); }.lobby-copy h3 { font-size: clamp(30px, 4vw, 54px); }.lobby-copy > p:not(.eyebrow) { max-width: 700px; color: #bdc7cb; font-size: 14px; line-height: 1.9; }.lobby-copy > small { color: #f0bd68; }.rule-chips { display: flex; flex-wrap: wrap; gap: 7px; margin: 18px 0; }.rule-chips span { padding: 6px 10px; border: 1px solid #ffffff1c; border-radius: 999px; color: #d9e0e2; background: #ffffff0a; font-size: 11px; }.lobby-roster { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }.lobby-roster article, .empty-seat { min-height: 82px; display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid color-mix(in srgb, var(--player-color, #fff) 38%, #ffffff18); border-radius: 11px; background: #080c0f99; }.lobby-roster img { width: 62px; height: 62px; object-fit: contain; }.lobby-roster article div { min-width: 0; display: grid; gap: 3px; }.lobby-roster strong { overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.lobby-roster small { color: var(--muted); font-size: 9px; }.empty-seat { justify-content: center; border-style: dashed; color: var(--muted); font-size: 10px; }
.play-layout { min-height: calc(100vh - 112px); display: grid; grid-template-columns: minmax(184px, 238px) minmax(420px, 1fr) minmax(210px, 284px); align-items: start; gap: 10px; padding: 0 4px 4px; }.scoreboard, .battle-hud { max-height: calc(100vh - 112px); overflow: auto; scrollbar-width: thin; }.scoreboard { padding: 12px; }.panel-heading { justify-content: space-between; gap: 9px; margin-bottom: 10px; }.panel-heading svg { color: #e9b14b; }.panel-heading h3 { font-size: 15px; }.player-list { display: grid; gap: 7px; }.player-card { --player-color: #fff; display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; align-items: center; gap: 7px; padding: 7px; border: 1px solid #ffffff12; border-left: 3px solid var(--player-color); border-radius: 10px; background: #080d10b8; }.player-card.self { background: color-mix(in srgb, var(--player-color) 9%, #080d10); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--player-color) 35%, transparent); }.player-card.eliminated { opacity: .48; filter: grayscale(.75); }.player-avatar { position: relative; width: 42px; height: 48px; }.player-avatar img { width: 100%; height: 100%; object-fit: contain; }.player-avatar span { position: absolute; left: -3px; bottom: -1px; width: 16px; height: 16px; display: grid; place-items: center; border-radius: 50%; color: #111; background: var(--player-color); font-size: 8px; font-weight: 900; }.player-info { min-width: 0; display: grid; gap: 2px; }.player-info strong { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }.player-info small, .kill-count small, .career-row, .records-note { color: var(--muted); font-size: 8px; }.kill-count { display: grid; justify-items: end; }.kill-count b { font: 800 20px/1 ui-monospace, monospace; }.career-row { grid-column: 1 / -1; display: flex; gap: 7px; padding-top: 5px; border-top: 1px solid #ffffff0c; }.career-row span { display: flex; align-items: center; gap: 2px; }.records-note { margin: 10px 2px 0; line-height: 1.6; }
.arena-column { position: relative; min-width: 0; display: grid; gap: 8px; }.touch-controls { display: none; justify-content: space-between; align-items: end; gap: 20px; min-height: 132px; padding: 8px 12px; }.touch-controls.disabled { opacity: .45; pointer-events: none; }.joystick { position: relative; width: 116px; height: 116px; flex: 0 0 auto; border: 1px solid #ffffff2c; border-radius: 50%; background: radial-gradient(circle, #ffffff12 0 18%, #1b252bb8 19% 48%, #071015a6 49% 100%); box-shadow: inset 0 0 0 8px #ffffff08, 0 8px 24px #0008; touch-action: none; user-select: none; }.joystick::before, .joystick::after { content: ''; position: absolute; inset: 13%; border: solid #ffffff18; border-width: 1px 0; border-radius: 50%; }.joystick::after { transform: rotate(90deg); }.joystick-compass { position: absolute; inset: 7px 0 auto; color: #ffffff52; font-size: 10px; text-align: center; }.joystick-knob { position: absolute; left: 50%; top: 50%; width: 54px; height: 54px; display: grid; place-items: center; border: 1px solid #e9f2f477; border-radius: 50%; background: radial-gradient(circle at 32% 28%, #69777e, #263238 55%, #11191d); box-shadow: inset 0 2px #ffffff35, 0 5px 14px #000a; transition: transform .08s ease-out; will-change: transform; }.joystick.active .joystick-knob { border-color: #f5ba52; box-shadow: inset 0 2px #ffffff35, 0 0 18px #e9a83d80; transition: none; }.joystick-knob i { width: 16px; height: 16px; border-radius: 50%; background: #eab14c; box-shadow: 0 0 10px #f0a536; }.joystick > small { position: absolute; left: 50%; bottom: 8px; transform: translateX(-50%); color: #c5d0d4; font-size: 8px; white-space: nowrap; }.action-pad { display: flex; align-items: end; gap: 8px; }.action-pad button { width: 58px; height: 58px; display: grid; place-items: center; align-content: center; gap: 0; border: 1px solid #ffffff37; border-radius: 50%; color: white; background: linear-gradient(#3b474d, #171e22); box-shadow: inset 0 2px #ffffff27, 0 6px 14px #0009; font: 800 12px system-ui; touch-action: none; user-select: none; }.action-pad button:active { transform: scale(.93); filter: brightness(1.18); }.action-pad button b { font-size: 17px; }.action-pad button small { font-size: 8px; }.action-pad .punch-action { margin-bottom: 24px; border-color: #77c8e277; }.action-pad .throw-action { margin-bottom: 24px; border-color: #a78be477; }.action-pad .bomb-action { width: 72px; height: 72px; border-color: #e5a747; background: radial-gradient(circle at 32% 28%, #727b80, #171d21 45%, #07090b 75%); }.action-pad .bomb-action b { color: #ffbd56; font-size: 24px; }
.action-pad .timer-action { border-color: #55dfef; background: radial-gradient(circle at 32% 28%, #297582, #102b31 48%, #071114 78%); box-shadow: inset 0 1px #d5fbff55, 0 0 10px #24c8db44; }.action-pad .timer-action b { color: #83f4ff; }
.battle-hud { display: grid; gap: 8px; }.battle-hud .panel { padding: 12px; }.result-card { border-color: #e1ad4f66; text-align: center; }.result-card > svg { color: #f1ba54; }.result-card h3 { font-size: 21px; }.result-card > p:not(.eyebrow) { color: #c1c9cc; font-size: 10px; line-height: 1.6; }.result-card > button { margin-top: 7px; }.inventory-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }.inventory-item { min-width: 0; display: flex; align-items: center; gap: 5px; padding: 5px; border: 1px solid #ffffff12; border-radius: 8px; background: #080c0fa8; }.inventory-item img { width: 30px; height: 30px; object-fit: contain; }.inventory-item span { min-width: 0; display: grid; }.inventory-item strong { overflow: hidden; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.inventory-item small { color: #d8ab5c; font-size: 8px; }.inventory-item.skull { border-color: #79cf4659; background: #1a3213cc; }.empty-inventory, .controls p, .curse-warning { margin: 4px 0 0; color: var(--muted); font-size: 9px; line-height: 1.65; }.curse-warning { display: flex; align-items: flex-start; gap: 6px; padding: 7px; color: #b9f28d; border: 1px solid #85d14f55; border-radius: 8px; background: #193014b8; }.key-guide { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }.key-guide span { display: flex; align-items: center; gap: 5px; color: #cbd3d6; font-size: 9px; }kbd { min-width: 31px; display: inline-grid; place-items: center; padding: 3px 5px; border: 1px solid #ffffff2b; border-bottom-width: 3px; border-radius: 5px; color: #f3c36d; background: #20282d; font: 800 8px ui-monospace, monospace; }.event-list { max-height: 150px; overflow: auto; }.event-list p { margin: 0; padding: 6px 0; border-bottom: 1px solid #ffffff0c; color: #b8c2c6; font-size: 9px; line-height: 1.45; }
.rulebook { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; color: #dce2e4; font-size: 12px; line-height: 1.8; }.rulebook section { padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: #ffffff06; }.rulebook h3 { margin: 0 0 6px; color: white; font-size: 15px; }.rulebook p, .rulebook ul { margin: 0; }.rulebook ul { padding-left: 20px; }.rules-items { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 5px; margin-bottom: 8px; }.rules-items article { min-width: 0; display: grid; justify-items: center; gap: 2px; }.rules-items img { width: 42px; height: 42px; object-fit: contain; }.rules-items strong { max-width: 100%; overflow: hidden; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.bomb-people :focus-visible { outline: 2px solid #f2bc5a; outline-offset: 2px; }
@media (max-width: 1180px) { .play-layout { grid-template-columns: minmax(170px, 220px) minmax(400px, 1fr); }.battle-hud { grid-column: 1 / -1; grid-template-columns: repeat(3, minmax(0, 1fr)); max-height: none; }.event-panel { display: none; }.map-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (hover: none) and (pointer: coarse) { :global(html:has(.bomb-people:not(.stage-lobby))), :global(body:has(.bomb-people:not(.stage-lobby))) { width: 100%; height: 100%; overflow: hidden; overscroll-behavior: none; }.bomb-people { min-height: 0; padding: 6px; border-radius: 13px; }.bomb-people:not(.stage-lobby) { position: fixed; inset: 0; z-index: 900; width: 100vw; height: 100dvh; max-height: 100dvh; padding: max(4px, env(safe-area-inset-top)) max(4px, env(safe-area-inset-right)) max(4px, env(safe-area-inset-bottom)) max(4px, env(safe-area-inset-left)); overflow: clip; border: 0; border-radius: 0; overscroll-behavior: none; touch-action: none; }.bomb-people.fullscreen { height: 100dvh; min-height: 0; padding: max(4px, env(safe-area-inset-top)) max(4px, env(safe-area-inset-right)) max(4px, env(safe-area-inset-bottom)) max(4px, env(safe-area-inset-left)); overflow: clip; }.bomb-people.stage-lobby.fullscreen { overflow: auto; touch-action: pan-y; }.game-header { min-height: 62px; grid-template-columns: 1fr auto; gap: 5px; padding: 3px 4px 6px; }.title-lockup p, .brand-bomb { display: none; }.title-lockup h2 { font-size: 20px; }.match-status { min-width: 0; padding: 3px 8px; grid-column: 1 / -1; grid-row: 2; width: 100%; flex-direction: row; justify-content: space-between; border-radius: 9px; }.match-status strong { font-size: 17px; }.match-status small { max-width: 115px; }.header-actions { grid-column: 2; grid-row: 1; gap: 4px; }.header-actions > * { min-width: 36px; min-height: 36px; }.play-layout { height: calc(100dvh - 90px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); min-height: 0; grid-template-columns: minmax(0, 1fr); align-items: start; padding: 0; overflow: clip; }.arena-column { grid-row: 1; height: 100%; align-content: start; overflow: clip; }.scoreboard, .battle-hud { display: none; }.stage-finished .battle-hud { position: absolute; inset: 90px 8px 8px; z-index: 70; display: grid; place-items: center; max-height: none; overflow: auto; background: #030608c7; backdrop-filter: blur(6px); }.stage-finished .battle-hud > :not(.result-card) { display: none; }.stage-finished .result-card { width: min(100%, 380px); padding: 20px; }.touch-controls { position: absolute; z-index: 50; left: 0; right: 0; bottom: max(5px, env(safe-area-inset-bottom)); display: flex; align-items: end; min-height: 128px; padding: 5px 10px; border: 0; background: transparent; pointer-events: none; }.touch-controls > * { pointer-events: auto; }.touch-controls.disabled > * { pointer-events: none; }.map-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.negotiation-heading { align-items: flex-start; flex-direction: column; }.proposal-status { justify-items: start; }.lobby-overview { grid-template-columns: minmax(0, 1fr); padding: 24px 16px; }.rulebook { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 430px) { .map-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }.map-card { aspect-ratio: 1; }.map-copy small, .map-badges { display: none; }.lobby-roster { grid-template-columns: minmax(0, 1fr); }.touch-controls { min-height: 112px; padding: 4px 7px; }.joystick { width: 102px; height: 102px; }.joystick-knob { width: 48px; height: 48px; }.joystick > small { bottom: 6px; }.action-pad { gap: 3px; }.action-pad button { width: 47px; height: 47px; }.action-pad button b { font-size: 15px; }.action-pad .punch-action, .action-pad .throw-action { margin-bottom: 19px; }.action-pad .bomb-action { width: 59px; height: 59px; }.inventory-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }.inventory-item { display: grid; justify-items: center; }.inventory-item span { justify-items: center; }.rules-items { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (prefers-reduced-motion: reduce) { .bomb-people * { scroll-behavior: auto; transition: none !important; } }
</style>
