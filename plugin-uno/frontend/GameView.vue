<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  usePluginFullscreen,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import PrismCard from './components/PrismCard.vue'
import EffectOverlay from './components/EffectOverlay.vue'
import type { UnoCardModel, UnoColor, UnoGameView } from './types'
import './animations/effects.css'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const gameRoot = ref<HTMLElement | null>(null)
const { isFullscreen, isSupported: fullscreenSupported, toggle: toggleFullscreen } = usePluginFullscreen(gameRoot)

const selectedCardId = ref<string | null>(null)
const chosenColor = ref<UnoColor | null>(null)
const callUno = ref(false)
const effectVisible = ref(false)
let effectTimer: ReturnType<typeof setTimeout> | null = null

const emptyGame: UnoGameView = {
  colors: [],
  turnOrder: [],
  currentPlayerId: null,
  direction: 1,
  activeColor: null,
  stage: 'turn',
  topCard: null,
  hand: [],
  cardCounts: {},
  drawPileCount: 0,
  discardPileCount: 0,
  drawnCardId: null,
  playableCardIds: [],
  pendingDrawTotal: 0,
  pendingDrawTargetPlayerId: null,
  pendingDrawSourcePlayerId: null,
  canTakePenalty: false,
  canDraw: false,
  canKeepDrawn: false,
  canCatchUno: false,
  unoVulnerablePlayerId: null,
  forfeitedPlayerIds: [],
  winnerPlayerIds: [],
  latestEvent: null,
  history: [],
}

const game = computed<UnoGameView>(() => (
  (props.snapshot.game as unknown as UnoGameView | undefined) ?? emptyGame
))
const selfId = computed(() => props.snapshot.self.id)
const isSpectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const selectedCard = computed(() => (
  game.value.hand.find((card) => card.id === selectedCardId.value) ?? null
))
const selectedNeedsColor = computed(() => selectedCard.value?.color === null)
const willLeaveOne = computed(() => Boolean(
  selectedCard.value && game.value.hand.length === 2,
))
const canPlaySelected = computed(() => Boolean(
  selectedCard.value
  && game.value.playableCardIds.includes(selectedCard.value.id)
  && (!selectedNeedsColor.value || chosenColor.value),
))
const opponents = computed(() => (
  props.snapshot.players.filter((player) => player.id !== selfId.value)
))
const currentPlayerName = computed(() => playerName(game.value.currentPlayerId))
const activeColorLabel = computed(() => (
  game.value.colors.find((color) => color.id === game.value.activeColor)?.label ?? '未指定'
))
const directionLabel = computed(() => game.value.direction === 1 ? '顺时针' : '逆时针')
const statusText = computed(() => {
  if (props.snapshot.phase === 'finished') return '本局已经完成，棱镜牌桌等待再次点亮。'
  if (isSpectator.value) return `观战中 · 当前由 ${currentPlayerName.value} 行动`
  if (game.value.currentPlayerId !== selfId.value) {
    return game.value.pendingDrawTotal > 0
      ? `惩罚链 +${game.value.pendingDrawTotal} · 等待 ${currentPlayerName.value} 叠加或接牌`
      : `等待 ${currentPlayerName.value} 出牌`
  }
  if (game.value.canTakePenalty) {
    return `累计 +${game.value.pendingDrawTotal} · 打出 +2 / +4 继续叠加，或接下惩罚`
  }
  if (game.value.canKeepDrawn) return '刚摸到的牌可以打出，也可以保留并结束回合'
  return '你的回合 · 选择发光卡牌，或从能量牌库摸一张'
})
const effectEvent = computed(() => game.value.latestEvent)

watch(
  () => game.value.latestEvent?.sequence,
  () => {
    const event = game.value.latestEvent
    if (!event) return
    const cinematicTypes = new Set([
      'skip',
      'reverse',
      'draw_two',
      'wild',
      'wild_draw_four',
      'take_penalty',
      'catch_uno',
    ])
    if (!cinematicTypes.has(event.type) && !event.calledUno) return
    if (effectTimer) clearTimeout(effectTimer)
    effectVisible.value = true
    effectTimer = setTimeout(() => {
      effectVisible.value = false
    }, 1580)
  },
)

watch(
  () => game.value.hand.map((card) => card.id).join('|'),
  () => {
    if (selectedCardId.value && !game.value.hand.some((card) => card.id === selectedCardId.value)) {
      resetSelection()
    }
  },
)

onUnmounted(() => {
  if (effectTimer) clearTimeout(effectTimer)
})

function playerName(playerId: string | null | undefined): string {
  if (!playerId) return '未知玩家'
  return props.snapshot.players.find((player) => player.id === playerId)?.name ?? '未知玩家'
}

function cardCount(playerId: string): number {
  return game.value.cardCounts[playerId] ?? 0
}

function isPlayable(card: UnoCardModel): boolean {
  return game.value.playableCardIds.includes(card.id)
}

function selectCard(card: UnoCardModel): void {
  if (!isPlayable(card) || isSpectator.value) return
  if (selectedCardId.value === card.id) {
    resetSelection()
    return
  }
  selectedCardId.value = card.id
  chosenColor.value = card.color
  callUno.value = false
}

function chooseColor(color: UnoColor): void {
  chosenColor.value = color
}

function resetSelection(): void {
  selectedCardId.value = null
  chosenColor.value = null
  callUno.value = false
}

async function playSelected(): Promise<void> {
  if (!selectedCard.value || !canPlaySelected.value) return
  const card = selectedCard.value
  const payload = {
    cardId: card.id,
    chosenColor: card.color === null ? chosenColor.value : card.color,
    callUno: willLeaveOne.value && callUno.value,
  }
  resetSelection()
  await actions.action('play_card', payload)
}

async function drawCard(): Promise<void> {
  resetSelection()
  await actions.action('draw_card')
}

async function keepDrawn(): Promise<void> {
  resetSelection()
  await actions.action('keep_drawn')
}

async function takePenalty(): Promise<void> {
  resetSelection()
  await actions.action('take_penalty')
}

async function catchUno(): Promise<void> {
  await actions.action('catch_uno')
}
</script>

<template>
  <section ref="gameRoot" class="uno-game" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="arena-shell">
      <header class="game-hud">
        <div class="brand-lockup">
          <span class="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <span>
            <small>PRISM CARD ARENA</small>
            <h2>UNO <em>光域对决</em></h2>
          </span>
        </div>

        <div class="round-status" :class="{ mine: game.currentPlayerId === selfId }">
          <i :class="`color-${game.activeColor ?? 'wild'}`" />
          <span>
            <small>{{ game.currentPlayerId === selfId ? 'YOUR TURN' : 'MATCH STATUS' }}</small>
            <b>{{ statusText }}</b>
          </span>
        </div>

        <div class="hud-actions">
          <span v-if="game.pendingDrawTotal" class="hud-chip penalty-chip">
            <small>累计惩罚</small><b>+{{ game.pendingDrawTotal }}</b>
          </span>
          <span class="hud-chip"><small>当前光谱</small><b>{{ activeColorLabel }}</b></span>
          <span class="hud-chip"><small>行动方向</small><b>{{ directionLabel }}</b></span>
          <button
            v-if="fullscreenSupported"
            type="button"
            class="icon-button"
            :aria-label="isFullscreen ? '退出全屏' : '进入全屏'"
            @click="toggleFullscreen"
          >
            {{ isFullscreen ? '⊙' : '⛶' }}
          </button>
        </div>
      </header>

      <div class="opponent-rail" :class="`seats-${opponents.length}`">
        <article
          v-for="(player, index) in opponents"
          :key="player.id"
          class="player-seat"
          :class="{
            current: game.currentPlayerId === player.id,
            uno: cardCount(player.id) === 1,
            out: game.forfeitedPlayerIds.includes(player.id),
          }"
          :style="{ '--seat-index': index }"
        >
          <span class="player-avatar">{{ player.name.slice(0, 1).toUpperCase() }}</span>
          <span class="player-copy">
            <b>{{ player.name }}</b>
            <small v-if="game.currentPlayerId === player.id">正在行动</small>
            <small v-else-if="cardCount(player.id) === 1">UNO 警戒</small>
            <small v-else>{{ cardCount(player.id) }} 张手牌</small>
          </span>
          <span class="mini-stack" aria-hidden="true">
            <i v-for="cardIndex in Math.min(cardCount(player.id), 5)" :key="cardIndex" />
          </span>
          <strong>{{ cardCount(player.id) }}</strong>
        </article>
      </div>

      <main class="arena-stage">
        <div class="stage-vignette" />
        <div class="turn-orbit" :class="{ reverse: game.direction === -1 }" aria-hidden="true">
          <i v-for="index in 12" :key="index" :style="{ '--orbit-index': index }" />
        </div>

        <div class="table-core">
          <div class="active-spectrum" :class="`color-${game.activeColor ?? 'wild'}`">
            <i /><i /><i /><i />
          </div>

          <section class="deck-zone" aria-label="摸牌堆">
            <span class="zone-label">ENERGY DECK</span>
            <div class="card-stack">
              <i /><i /><i />
              <PrismCard
                face-down
                compact
                :disabled="!game.canDraw || isSpectator"
                @activate="drawCard"
              />
            </div>
            <small>{{ game.drawPileCount }} 张</small>
          </section>

          <section class="discard-zone" aria-label="弃牌堆">
            <span class="zone-label">PRISM CORE</span>
            <div class="discard-glow" :class="`color-${game.activeColor ?? 'wild'}`" />
            <PrismCard v-if="game.topCard" :card="game.topCard" compact disabled />
            <small>{{ game.discardPileCount }} 张</small>
          </section>

          <div class="direction-readout" :class="{ reverse: game.direction === -1 }">
            <span>↻</span>
            <small>{{ directionLabel }}</small>
          </div>

        </div>

        <div v-if="game.pendingDrawTotal" class="penalty-reactor" role="status">
          <small>DRAW CHAIN</small>
          <strong>+{{ game.pendingDrawTotal }}</strong>
          <span>锁定 {{ playerName(game.pendingDrawTargetPlayerId) }}</span>
        </div>

        <EffectOverlay
          v-if="effectVisible && effectEvent"
          :key="effectEvent.sequence"
          :event="effectEvent"
        />
      </main>

      <section class="self-zone">
        <header class="hand-header">
          <div class="self-identity">
            <span class="player-avatar self-avatar">{{ snapshot.self.name.slice(0, 1).toUpperCase() }}</span>
            <span>
              <small>{{ isSpectator ? 'FIXED VIEW' : 'YOUR HAND' }}</small>
              <b>{{ snapshot.self.name }}</b>
            </span>
          </div>
          <div class="hand-state">
            <b>{{ game.hand.length }}</b>
            <small>张手牌</small>
          </div>
        </header>

        <div class="hand-scroller" aria-label="你的手牌">
          <div v-if="game.hand.length" class="hand-fan">
            <PrismCard
              v-for="(card, index) in game.hand"
              :key="card.id"
              :card="card"
              :selected="selectedCardId === card.id"
              :playable="isPlayable(card)"
              :disabled="!isPlayable(card) || isSpectator"
              :drawn="game.drawnCardId === card.id"
              :style="{
                '--hand-index': index,
                '--hand-center': (game.hand.length - 1) / 2,
              }"
              @activate="selectCard(card)"
            />
          </div>
          <p v-else class="empty-hand">牌面已清空，光域归你所有。</p>
        </div>

        <div v-if="!isSpectator && snapshot.phase === 'playing'" class="control-dock">
          <div class="selection-readout">
            <small>SELECTED CARD</small>
            <b>{{ selectedCard?.label ?? '请选择一张发光的可出牌' }}</b>
          </div>

          <div v-if="selectedNeedsColor" class="color-picker" aria-label="选择万能牌颜色">
            <button
              v-for="color in game.colors"
              :key="color.id"
              type="button"
              :class="[`color-${color.id}`, { selected: chosenColor === color.id }]"
              :aria-label="`指定${color.label}`"
              :aria-pressed="chosenColor === color.id"
              @click="chooseColor(color.id)"
            >
              <i />{{ color.label }}
            </button>
          </div>

          <button
            v-if="willLeaveOne"
            type="button"
            class="uno-call-button"
            :class="{ active: callUno }"
            :aria-pressed="callUno"
            @click="callUno = !callUno"
          >
            <span>UNO!</span>
            <small>{{ callUno ? '已准备宣告' : '剩一张前必须点亮' }}</small>
          </button>

          <button
            type="button"
            class="primary-action"
            :disabled="!canPlaySelected"
            @click="playSelected"
          >
            <span>打出卡牌</span>
            <small v-if="selectedNeedsColor && !chosenColor">先选择下一种颜色</small>
            <small v-else>释放棱镜效果</small>
          </button>

          <button
            v-if="game.canTakePenalty"
            type="button"
            class="penalty-action"
            @click="takePenalty"
          >
            <span>接下累计 +{{ game.pendingDrawTotal }}</span>
            <small>摸牌并跳过本回合</small>
          </button>
          <button
            v-else-if="game.canKeepDrawn"
            type="button"
            class="secondary-action"
            @click="keepDrawn"
          >
            保留摸牌
          </button>
          <button
            v-else
            type="button"
            class="secondary-action"
            :disabled="!game.canDraw"
            @click="drawCard"
          >
            摸一张
          </button>

          <button
            v-if="game.canCatchUno"
            type="button"
            class="catch-action"
            @click="catchUno"
          >
            抓漏喊 · +2
          </button>
        </div>
      </section>

      <div class="info-grid">
        <section class="history-panel">
          <header><span><small>LIVE FEED</small><b>光域记录</b></span><em>{{ game.history.length }}</em></header>
          <ol>
            <li v-for="(item, index) in [...game.history].reverse()" :key="`${index}-${item.message}`" :class="item.type">
              <i />
              <span>{{ item.message }}</span>
            </li>
          </ol>
        </section>

        <section class="quick-rules">
          <header><small>QUICK RULES</small><b>三十秒上桌</b></header>
          <div class="rule-cards">
            <article><strong>01</strong><span><b>匹配</b><small>同色、同数字或同功能</small></span></article>
            <article><strong>02</strong><span><b>累计惩罚</b><small>+2 / +4 可连续混合叠加</small></span></article>
            <article><strong>03</strong><span><b>数字收尾</b><small>最后打出的牌必须是数字牌</small></span></article>
            <article><strong>04</strong><span><b>UNO</b><small>剩 1 张前宣告，否则被抓摸 2</small></span></article>
          </div>
        </section>
      </div>

      <div v-if="snapshot.phase === 'finished'" class="result-overlay">
        <div class="result-card">
          <span class="result-prism"><i /><i /><i /><i /></span>
          <small>PRISM ARENA COMPLETE</small>
          <h3>{{ game.winnerPlayerIds.includes(selfId) ? '光域由你点亮' : '本局光谱已归位' }}</h3>
          <p>{{ game.winnerPlayerIds.includes(selfId) ? '你率先清空所有手牌，成为本局胜者。' : '查看牌桌记录，准备下一次逆转。' }}</p>
          <button
            type="button"
            class="primary-action restart-action"
            :disabled="!snapshot.actions.canRestart"
            @click="actions.restart()"
          >
            再来一局
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.uno-game {
  --uno-red: #ff4d62;
  --uno-yellow: #ffc83d;
  --uno-green: #35d78b;
  --uno-blue: #438fff;
  --uno-ink: #070910;
  --uno-panel: rgb(8 11 18 / 0.84);
  --uno-line: rgb(255 255 255 / 0.12);
  --uno-text: #f5f8ff;
  --uno-muted: rgb(225 232 248 / 0.58);
  width: 100%;
  min-width: 0;
  max-width: none;
  min-height: calc(100dvh - 8px);
  margin: 0 auto;
  color: var(--uno-text);
  font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  container-type: inline-size;
}

.uno-game.is-fullscreen { width: 100vw; max-width: none; height: 100vh; overflow: auto; background: #03050a; }
.uno-game.is-fullscreen .arena-shell { min-height: 100vh; border-radius: 0; }

.arena-shell {
  position: relative;
  min-height: inherit;
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto minmax(390px, 1fr) auto auto;
  gap: 13px;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: clamp(18px, 2.4vw, 30px);
  padding: clamp(12px, 2vw, 24px);
  background:
    linear-gradient(180deg, rgb(3 5 10 / 0.24), rgb(3 5 10 / 0.9)),
    url('./assets/scenes/prism-arena.png') top center / 100% auto no-repeat,
    #03050a;
  box-shadow: 0 28px 70px rgb(0 0 0 / 0.38), 0 1px 0 rgb(255 255 255 / 0.08) inset;
  isolation: isolate;
}

.arena-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: radial-gradient(circle at 50% 30%, transparent 0 24%, rgb(2 4 8 / 0.2) 58%, rgb(2 4 8 / 0.88) 100%);
  pointer-events: none;
}

button { font: inherit; }
button:focus-visible { outline: 2px solid white; outline-offset: 3px; }

.game-hud {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(220px, .9fr) minmax(300px, 1.25fr) minmax(240px, .85fr);
  align-items: center;
  gap: 14px;
  border: 1px solid var(--uno-line);
  border-radius: 18px;
  padding: 12px 14px;
  background: linear-gradient(180deg, rgb(14 18 28 / 0.84), rgb(6 8 14 / 0.74));
  box-shadow: 0 14px 34px rgb(0 0 0 / 0.28), 0 1px 0 rgb(255 255 255 / 0.07) inset;
  backdrop-filter: blur(16px) saturate(1.2);
}

.brand-lockup,
.self-identity {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 11px;
}

.brand-mark,
.result-prism {
  position: relative;
  width: 42px;
  aspect-ratio: 1;
  flex: 0 0 auto;
  display: block;
  transform: rotate(45deg);
  filter: drop-shadow(0 0 12px rgb(92 145 255 / 0.4));
}

.brand-mark i,
.result-prism i {
  position: absolute;
  width: 48%;
  height: 48%;
  border: 1px solid rgb(255 255 255 / 0.42);
  border-radius: 4px;
}
.brand-mark i:nth-child(1), .result-prism i:nth-child(1) { top: 0; left: 0; background: var(--uno-red); }
.brand-mark i:nth-child(2), .result-prism i:nth-child(2) { top: 0; right: 0; background: var(--uno-yellow); }
.brand-mark i:nth-child(3), .result-prism i:nth-child(3) { bottom: 0; left: 0; background: var(--uno-green); }
.brand-mark i:nth-child(4), .result-prism i:nth-child(4) { right: 0; bottom: 0; background: var(--uno-blue); }

.brand-lockup > span:last-child,
.self-identity > span:last-child,
.round-status > span { min-width: 0; display: grid; gap: 2px; }
.brand-lockup small,
.round-status small,
.self-identity small,
.selection-readout small,
.quick-rules header small,
.history-panel header small {
  color: #93a6c9;
  font-size: 8px;
  font-weight: 900;
  letter-spacing: .18em;
}
.brand-lockup h2 { margin: 0; font-size: clamp(18px, 2.4vw, 28px); font-weight: 950; letter-spacing: -.04em; line-height: 1; }
.brand-lockup h2 em { color: #b7c6e1; font-size: .55em; font-style: normal; font-weight: 750; letter-spacing: .08em; }

.round-status {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--uno-line);
  border-radius: 13px;
  padding: 10px 12px;
  background: rgb(255 255 255 / 0.035);
}
.round-status.mine { border-color: rgb(120 174 255 / 0.48); background: rgb(70 133 255 / 0.09); box-shadow: 0 0 22px rgb(62 134 255 / 0.12) inset; }
.round-status > i { width: 9px; height: 32px; flex: 0 0 auto; border-radius: 99px; background: var(--uno-blue); box-shadow: 0 0 16px currentColor; }
.round-status b { overflow: hidden; color: #e6edfa; font-size: 11px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }

.hud-actions { min-width: 0; display: flex; justify-content: flex-end; align-items: center; gap: 7px; }
.hud-chip { min-width: 0; display: grid; gap: 2px; border: 1px solid var(--uno-line); border-radius: 11px; padding: 8px 10px; background: rgb(255 255 255 / 0.035); }
.hud-chip small { color: var(--uno-muted); font-size: 7px; white-space: nowrap; }
.hud-chip b { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.penalty-chip { border-color: rgb(255 190 61 / 0.5); color: #ffe29a; background: rgb(255 180 42 / 0.1); box-shadow: 0 0 18px rgb(255 177 39 / 0.12) inset; }
.penalty-chip b { font-size: 14px; letter-spacing: -.04em; }
.icon-button { width: 37px; aspect-ratio: 1; flex: 0 0 auto; border: 1px solid var(--uno-line); border-radius: 11px; color: white; background: rgb(255 255 255 / 0.05); cursor: pointer; }

.color-red { color: var(--uno-red) !important; background-color: var(--uno-red) !important; }
.color-yellow { color: var(--uno-yellow) !important; background-color: var(--uno-yellow) !important; }
.color-green { color: var(--uno-green) !important; background-color: var(--uno-green) !important; }
.color-blue { color: var(--uno-blue) !important; background-color: var(--uno-blue) !important; }
.color-wild { color: white !important; background: conic-gradient(var(--uno-red), var(--uno-yellow), var(--uno-green), var(--uno-blue), var(--uno-red)) !important; }

.opponent-rail {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: 8px;
}

.player-seat {
  min-width: 0;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--uno-line);
  border-radius: 14px;
  padding: 8px 9px;
  background: linear-gradient(180deg, rgb(12 16 25 / 0.76), rgb(6 8 14 / 0.68));
  backdrop-filter: blur(10px);
  transition: border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease;
}
.player-seat.current { border-color: rgb(114 173 255 / 0.62); box-shadow: 0 0 20px rgb(57 126 255 / 0.16); transform: translateY(2px); }
.player-seat.uno { border-color: rgb(255 70 95 / 0.64); }
.player-seat.out { opacity: .42; filter: grayscale(1); }

.player-avatar {
  width: 34px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 11px;
  color: #dce7ff;
  background: linear-gradient(145deg, #273149, #0d111b);
  font-size: 12px;
  font-weight: 900;
  box-shadow: 0 4px 10px rgb(0 0 0 / 0.26);
}
.player-copy { min-width: 0; display: grid; gap: 2px; }
.player-copy b { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.player-copy small { overflow: hidden; color: var(--uno-muted); font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }
.player-seat > strong { color: white; font-size: 14px; }

.mini-stack { position: relative; width: 23px; height: 30px; display: block; }
.mini-stack i { position: absolute; inset: 1px 4px; border: 1px solid rgb(255 255 255 / 0.26); border-radius: 3px; background: linear-gradient(145deg, #27314a, #070910); transform: translateX(calc((var(--seat-index, 0) + 1) * 0px)); }
.mini-stack i:nth-child(2) { transform: translateX(2px) rotate(3deg); }
.mini-stack i:nth-child(3) { transform: translateX(4px) rotate(6deg); }
.mini-stack i:nth-child(4) { transform: translateX(6px) rotate(9deg); }
.mini-stack i:nth-child(5) { transform: translateX(8px) rotate(12deg); }

.arena-stage {
  position: relative;
  min-width: 0;
  min-height: clamp(390px, 45vw, 680px);
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: clamp(20px, 2.7vw, 32px);
  background:
    radial-gradient(ellipse at 50% 52%, rgb(5 8 13 / 0.12) 0 28%, rgb(2 4 8 / 0.54) 70%),
    linear-gradient(180deg, rgb(2 4 8 / 0.08), rgb(2 4 8 / 0.5));
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.32) inset;
}

.stage-vignette { position: absolute; inset: 0; background: radial-gradient(ellipse, transparent 25%, rgb(0 0 0 / 0.56) 92%); pointer-events: none; }

.turn-orbit {
  position: absolute;
  width: min(72%, 760px);
  aspect-ratio: 1.9 / 1;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 50%;
  animation: orbit-turn 26s linear infinite;
}
.turn-orbit.reverse { animation-direction: reverse; }
.turn-orbit::before, .turn-orbit::after { content: ''; position: absolute; inset: 8%; border: 1px solid rgb(91 147 255 / 0.11); border-radius: inherit; }
.turn-orbit::after { inset: 18%; }
.turn-orbit i {
  --angle: calc(var(--orbit-index) * 30deg);
  position: absolute;
  top: 50%;
  left: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #91baff;
  box-shadow: 0 0 10px #4a8fff;
  transform: rotate(var(--angle)) translateX(min(34vw, 350px));
  transform-origin: left center;
}

.table-core {
  position: relative;
  width: min(82%, 840px);
  aspect-ratio: 2 / 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  place-items: center;
  gap: clamp(24px, 7vw, 84px);
  border: 1px solid rgb(207 222 250 / 0.2);
  border-radius: 50%;
  padding: 7% 17%;
  background:
    radial-gradient(circle at 50% 44%, rgb(55 83 127 / 0.13), transparent 54%),
    linear-gradient(160deg, rgb(25 31 42 / 0.86), rgb(5 7 11 / 0.96));
  box-shadow:
    0 0 0 8px rgb(0 0 0 / 0.22),
    0 0 0 10px rgb(255 255 255 / 0.06),
    0 28px 44px rgb(0 0 0 / 0.52),
    0 0 48px rgb(57 105 188 / 0.12) inset;
}
.table-core::before { content: ''; position: absolute; inset: 7%; border: 1px solid rgb(255 255 255 / 0.08); border-radius: 50%; }

.active-spectrum {
  position: absolute;
  inset: -6%;
  z-index: -1;
  border-radius: 50%;
  opacity: .42;
  filter: blur(16px);
}
.active-spectrum i { position: absolute; width: 13%; height: 8%; border-radius: 50%; background: currentColor; }
.active-spectrum i:nth-child(1) { top: 5%; left: 12%; }
.active-spectrum i:nth-child(2) { top: 5%; right: 12%; }
.active-spectrum i:nth-child(3) { bottom: 5%; left: 12%; }
.active-spectrum i:nth-child(4) { right: 12%; bottom: 5%; }

.deck-zone,
.discard-zone { position: relative; z-index: 2; width: clamp(80px, 9vw, 126px); display: grid; justify-items: center; gap: 7px; }
.zone-label { color: rgb(199 214 239 / 0.52); font-size: 7px; font-weight: 950; letter-spacing: .16em; white-space: nowrap; }
.deck-zone > small, .discard-zone > small { color: var(--uno-muted); font-size: 8px; }
.card-stack { position: relative; width: 100%; }
.card-stack > i { position: absolute; inset: 1% 0; border: 1px solid rgb(255 255 255 / 0.2); border-radius: 13.5%; background: #0a0d14; }
.card-stack > i:nth-child(1) { transform: translate(-7px, 5px) rotate(-4deg); }
.card-stack > i:nth-child(2) { transform: translate(6px, 5px) rotate(4deg); }
.card-stack > i:nth-child(3) { transform: translate(1px, 3px); }
.discard-glow { position: absolute; inset: 17% -18%; z-index: -1; border-radius: 50%; opacity: .3; filter: blur(20px); }

.direction-readout { position: absolute; top: 50%; left: 50%; z-index: 3; display: grid; justify-items: center; gap: 2px; transform: translate(-50%, -50%); }
.direction-readout span { width: 42px; aspect-ratio: 1; display: grid; place-items: center; border: 1px solid rgb(255 255 255 / 0.18); border-radius: 50%; color: #a8c3ef; background: rgb(3 5 9 / 0.72); font-size: 27px; box-shadow: 0 0 22px rgb(82 135 225 / 0.14); animation: direction-spin 9s linear infinite; }
.direction-readout.reverse span { animation-direction: reverse; }
.direction-readout small { color: var(--uno-muted); font-size: 7px; white-space: nowrap; }

.penalty-reactor {
  position: absolute;
  bottom: clamp(8px, 2vw, 24px);
  left: 50%;
  z-index: 5;
  min-width: 112px;
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  gap: 0 7px;
  border: 1px solid rgb(255 221 137 / 0.46);
  border-radius: 13px;
  padding: 7px 11px;
  color: #fff4ce;
  background: linear-gradient(135deg, rgb(77 40 8 / 0.92), rgb(12 12 19 / 0.94));
  box-shadow: 0 0 24px rgb(255 175 39 / 0.24), 0 1px 0 rgb(255 255 255 / 0.14) inset;
  transform: translateX(-50%);
  animation: penalty-reactor-pulse 720ms ease-in-out infinite alternate;
}
.penalty-reactor small { color: #e8be61; font-size: 6px; font-weight: 950; letter-spacing: .18em; }
.penalty-reactor strong { grid-row: 1 / 3; grid-column: 2; font-size: 28px; line-height: 1; letter-spacing: -.08em; }
.penalty-reactor span { max-width: 92px; overflow: hidden; color: rgb(255 255 255 / .62); font-size: 6px; text-overflow: ellipsis; white-space: nowrap; }

.self-zone {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(150px, .25fr) minmax(0, 1.5fr) minmax(250px, .55fr);
  align-items: stretch;
  gap: 10px;
  border: 1px solid var(--uno-line);
  border-radius: 19px;
  padding: 10px;
  background: linear-gradient(180deg, rgb(11 15 24 / 0.94), rgb(5 7 12 / 0.94));
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.32), 0 1px 0 rgb(255 255 255 / 0.06) inset;
}

.hand-header { display: grid; align-content: space-between; gap: 12px; border-right: 1px solid var(--uno-line); padding: 7px 12px 7px 5px; }
.self-avatar { width: 42px; border-color: rgb(92 148 255 / 0.48); box-shadow: 0 0 20px rgb(68 134 255 / 0.16); }
.self-identity b { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.hand-state { display: flex; align-items: baseline; gap: 6px; }
.hand-state b { color: #b9d4ff; font-size: 32px; letter-spacing: -.08em; }
.hand-state small { color: var(--uno-muted); font-size: 8px; }

.hand-scroller { min-width: 0; min-height: 164px; overflow-x: auto; overflow-y: hidden; scrollbar-width: thin; scrollbar-color: rgb(87 128 196 / .5) transparent; }
.hand-fan { min-width: min-content; height: 100%; display: flex; align-items: end; justify-content: center; gap: clamp(2px, .35vw, 6px); padding: 19px 10px 5px; }
.hand-fan :deep(.prism-card) { width: clamp(72px, 7.25vw, 116px); transform-origin: 50% 120%; }
.empty-hand { height: 100%; display: grid; place-items: center; margin: 0; color: var(--uno-muted); font-size: 10px; }

.control-dock {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-content: center;
  gap: 7px;
  border-left: 1px solid var(--uno-line);
  padding: 4px 4px 4px 12px;
}
.selection-readout { grid-column: 1 / -1; min-width: 0; display: grid; gap: 3px; }
.selection-readout b { overflow: hidden; color: #dce7f9; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }

.color-picker { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
.color-picker button { min-width: 0; display: flex; align-items: center; justify-content: center; gap: 4px; border: 1px solid transparent; border-radius: 8px; padding: 7px 4px; color: white !important; background: rgb(255 255 255 / 0.05) !important; font-size: 7px; cursor: pointer; }
.color-picker button i { width: 8px; aspect-ratio: 1; border-radius: 3px; background: currentColor; box-shadow: 0 0 8px currentColor; }
.color-picker button.selected { border-color: currentColor; background: rgb(255 255 255 / 0.11) !important; }

.uno-call-button,
.primary-action,
.secondary-action,
.penalty-action,
.catch-action {
  border-radius: 11px;
  padding: 9px 11px;
  cursor: pointer;
  transition: transform 160ms ease, filter 160ms ease, opacity 160ms ease;
}
.uno-call-button:disabled, .primary-action:disabled, .secondary-action:disabled, .penalty-action:disabled, .catch-action:disabled { opacity: .36; cursor: not-allowed; }
.uno-call-button { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; border: 1px solid rgb(255 78 99 / 0.42); color: #ff8997; background: rgb(255 55 82 / 0.08); }
.uno-call-button span { font-size: 18px; font-weight: 1000; font-style: italic; letter-spacing: -.07em; }
.uno-call-button small { color: var(--uno-muted); font-size: 7px; }
.uno-call-button.active { color: white; background: linear-gradient(135deg, #ff3858, #b9153b); box-shadow: 0 0 24px rgb(255 48 82 / 0.34); animation: uno-ready 900ms ease-in-out infinite alternate; }

.primary-action { min-width: 0; display: grid; border: 1px solid rgb(149 191 255 / 0.42); color: white; background: linear-gradient(135deg, #367de8, #244ca8); box-shadow: 0 8px 18px rgb(28 76 163 / 0.28); }
.primary-action span { font-size: 10px; font-weight: 900; }
.primary-action small { color: rgb(228 238 255 / 0.66); font-size: 7px; }
.secondary-action { border: 1px solid var(--uno-line); color: #c8d5eb; background: rgb(255 255 255 / 0.045); font-size: 8px; font-weight: 800; }
.penalty-action { min-width: 0; display: grid; border: 1px solid rgb(255 204 95 / 0.56); color: #fff7dc; background: linear-gradient(135deg, #b36318, #66320e); box-shadow: 0 0 22px rgb(255 168 42 / 0.2); }
.penalty-action span { font-size: 9px; font-weight: 950; }
.penalty-action small { color: rgb(255 239 200 / .66); font-size: 6.5px; }
.catch-action { grid-column: 1 / -1; border: 1px solid rgb(255 73 102 / 0.58); color: white; background: linear-gradient(135deg, #d72e51, #7e1530); font-size: 9px; font-weight: 950; box-shadow: 0 0 24px rgb(255 49 83 / 0.22); animation: catch-pulse 700ms ease-in-out infinite alternate; }

.info-grid { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(310px, .72fr); gap: 10px; }
.history-panel, .quick-rules { min-width: 0; border: 1px solid var(--uno-line); border-radius: 16px; padding: 12px; background: var(--uno-panel); backdrop-filter: blur(10px); }
.history-panel header, .quick-rules header { display: flex; align-items: center; justify-content: space-between; gap: 10px; border-bottom: 1px solid var(--uno-line); padding-bottom: 9px; }
.history-panel header > span, .quick-rules header { min-width: 0; }
.history-panel header span { display: grid; gap: 2px; }
.history-panel header b, .quick-rules header b { font-size: 10px; }
.history-panel header em { min-width: 24px; display: grid; place-items: center; border-radius: 99px; padding: 4px 6px; color: #aec8f4; background: rgb(84 137 226 / 0.12); font-size: 8px; font-style: normal; }
.history-panel ol { max-height: 118px; display: grid; gap: 6px; margin: 9px 0 0; padding: 0; overflow-y: auto; list-style: none; }
.history-panel li { min-width: 0; display: grid; grid-template-columns: 5px minmax(0, 1fr); align-items: center; gap: 7px; color: var(--uno-muted); font-size: 8px; line-height: 1.4; }
.history-panel li i { width: 5px; aspect-ratio: 1; border-radius: 50%; background: #6f89b5; }
.history-panel li.skip i, .history-panel li.catch_uno i { background: var(--uno-red); box-shadow: 0 0 8px var(--uno-red); }
.history-panel li.reverse i, .history-panel li.wild i { background: var(--uno-blue); box-shadow: 0 0 8px var(--uno-blue); }
.history-panel li.draw_two i, .history-panel li.wild_draw_four i { background: var(--uno-yellow); box-shadow: 0 0 8px var(--uno-yellow); }

.rule-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; padding-top: 9px; }
.rule-cards article { min-width: 0; display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 7px; border: 1px solid var(--uno-line); border-radius: 10px; padding: 8px; background: rgb(255 255 255 / 0.025); }
.rule-cards article > strong { color: #769cda; font-size: 13px; }
.rule-cards article > span { min-width: 0; display: grid; gap: 2px; }
.rule-cards b { font-size: 8px; }
.rule-cards small { overflow: hidden; color: var(--uno-muted); font-size: 6.5px; text-overflow: ellipsis; white-space: nowrap; }

.result-overlay { position: absolute; inset: 0; z-index: 60; display: grid; place-items: center; padding: 18px; background: rgb(1 3 7 / 0.76); backdrop-filter: blur(16px); }
.result-card { width: min(100%, 480px); display: grid; justify-items: center; gap: 10px; border: 1px solid rgb(255 255 255 / 0.18); border-radius: 24px; padding: clamp(28px, 6vw, 52px); text-align: center; background: radial-gradient(circle at 50% 0, rgb(88 137 222 / 0.2), transparent 42%), linear-gradient(160deg, #141a28, #070910); box-shadow: 0 28px 80px rgb(0 0 0 / 0.58); }
.result-prism { width: 72px; margin-bottom: 7px; }
.result-card > small { color: #9fb6db; font-size: 8px; font-weight: 900; letter-spacing: .2em; }
.result-card h3 { margin: 0; font-size: clamp(27px, 6vw, 44px); letter-spacing: -.06em; }
.result-card p { margin: 0 0 8px; color: var(--uno-muted); font-size: 10px; }
.restart-action { min-width: 180px; padding: 13px 18px; font-size: 11px; font-weight: 900; }

@media (hover: hover) {
  .icon-button:hover, .secondary-action:hover:not(:disabled) { background: rgb(255 255 255 / 0.1); }
  .primary-action:hover:not(:disabled), .penalty-action:hover:not(:disabled), .uno-call-button:hover, .catch-action:hover { transform: translateY(-2px); filter: brightness(1.1); }
}

@keyframes orbit-turn { to { transform: rotate(360deg); } }
@keyframes direction-spin { to { transform: rotate(360deg); } }
@keyframes uno-ready { to { box-shadow: 0 0 34px rgb(255 48 82 / 0.58); } }
@keyframes catch-pulse { to { filter: brightness(1.18); transform: translateY(-1px); } }
@keyframes penalty-reactor-pulse { to { border-color: rgb(255 229 164 / 0.82); box-shadow: 0 0 34px rgb(255 168 42 / 0.38), 0 1px 0 rgb(255 255 255 / 0.18) inset; } }

@container (max-width: 960px) {
  .game-hud { grid-template-columns: 1fr 1.15fr; }
  .hud-actions { grid-column: 1 / -1; justify-content: stretch; }
  .hud-chip { flex: 1; }
  .self-zone { grid-template-columns: 120px minmax(0, 1fr); }
  .control-dock { grid-column: 1 / -1; grid-template-columns: minmax(0, 1fr) auto auto; border-top: 1px solid var(--uno-line); border-left: 0; padding: 10px 4px 2px; }
  .selection-readout { grid-column: auto; }
  .color-picker { grid-column: 1 / -1; }
  .uno-call-button, .catch-action { grid-column: 1 / -1; }
  .info-grid { grid-template-columns: 1fr; }
  .rule-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@container (max-width: 680px) {
  .uno-game { min-height: 100dvh; }
  .arena-shell { grid-template-rows: auto auto auto auto auto; }
  .arena-shell { gap: 9px; padding: 9px; border-radius: 18px; background-size: auto 520px; }
  .game-hud { grid-template-columns: 1fr auto; align-items: start; gap: 9px; padding: 10px; }
  .round-status { grid-column: 1 / -1; grid-row: 2; }
  .hud-actions { grid-column: 2; grid-row: 1; }
  .hud-chip { display: none; }
  .brand-mark { width: 34px; }
  .opponent-rail { display: flex; overflow-x: auto; padding-bottom: 2px; }
  .player-seat { min-width: 138px; grid-template-columns: 30px minmax(0, 1fr) auto; }
  .player-avatar { width: 30px; }
  .mini-stack { display: none; }
  .arena-stage { min-height: 315px; }
  .table-core { width: 94%; padding-inline: 16%; gap: 50px; }
  .turn-orbit { width: 92%; }
  .turn-orbit i { transform: rotate(var(--angle)) translateX(42vw); }
  .self-zone { grid-template-columns: 1fr; padding: 8px; }
  .hand-header { grid-template-columns: 1fr auto; align-items: center; border-right: 0; border-bottom: 1px solid var(--uno-line); padding: 4px 4px 8px; }
  .hand-state { justify-content: end; }
  .hand-scroller { min-height: 145px; }
  .hand-fan { justify-content: flex-start; padding-inline: 7px; }
  .hand-fan :deep(.prism-card) { width: 74px; }
  .control-dock { grid-template-columns: 1fr 1fr; }
  .selection-readout { grid-column: 1 / -1; }
  .primary-action, .secondary-action, .penalty-action { min-height: 46px; }
  .rule-cards { grid-template-columns: 1fr; }
  .rule-cards small { white-space: normal; }
}

@container (max-width: 390px) {
  .brand-lockup h2 em { display: none; }
  .round-status b { font-size: 9px; }
  .arena-stage { min-height: 320px; }
  .table-core { width: 100%; gap: 38px; }
  .deck-zone, .discard-zone { width: 68px; }
  .direction-readout span { width: 34px; font-size: 22px; }
  .direction-readout small, .zone-label { display: none; }
  .hand-fan :deep(.prism-card) { width: 66px; }
  .history-panel ol { max-height: 96px; }
}

@media (prefers-reduced-motion: reduce) {
  .turn-orbit, .direction-readout span, .penalty-reactor, .uno-call-button.active, .catch-action { animation: none; }
  .player-seat, .primary-action, .secondary-action, .penalty-action, .uno-call-button, .catch-action { transition: none; }
}
</style>
