<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  PluginButton,
  usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import EffectChoice from './components/EffectChoice.vue'
import LootCard from './components/LootCard.vue'
import PlayerBank from './components/PlayerBank.vue'
import ScoreBreakdown from './components/ScoreBreakdown.vue'
import SuitIcon from './components/SuitIcon.vue'
import type { DeadMansDrawView, PublicEventView, SuitId } from './types'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const busy = ref(false)
const game = computed(() => props.snapshot.game as unknown as DeadMansDrawView)
const selfPlayer = computed(() => game.value.players.find(player => player.id === props.snapshot.self.id) ?? null)
const opponents = computed(() => game.value.players.filter(player => player.id !== props.snapshot.self.id))
const currentPlayer = computed(() => game.value.players.find(player => player.id === game.value.currentPlayerId) ?? null)
const pendingChoice = computed(() => game.value.turn?.pendingChoice ?? null)
const latestEvent = computed(() => game.value.events.at(-1) ?? null)
const phaseLabel = computed(() => ({
  trait_selection: '选择特性', turn: '翻牌抉择', effect_choice: '结算能力', finished: '终局结算', waiting: '等待开局',
})[game.value.phase] ?? game.value.phase)
const instruction = computed(() => {
  if (game.value.phase === 'trait_selection') return game.value.actions.canChooseTrait ? '从两项候选中秘密选择一项' : game.value.actions.canChooseLockerTarget ? '为戴维·琼斯的魔柜指定对手' : '等待其他玩家完成选择'
  if (game.value.phase === 'effect_choice') return pendingChoice.value?.promptZh ?? '正在解决花色能力'
  if (game.value.phase === 'finished') return game.value.result?.summaryZh ?? '牌局已经结算'
  if (game.value.turn?.krakenDebt) return `海怪仍要求 ${game.value.turn.krakenDebt} 张牌成功进入航道`
  if (!game.value.playArea.length) return game.value.actions.canDraw ? '翻开本回合第一张战利品' : '等待当前玩家翻牌'
  return game.value.actions.canDraw || game.value.actions.canCollect ? '继续冒险，或把航道战利品收入银行' : '等待当前玩家决定'
})

async function send(action: string, payload: Record<string, unknown> = {}) {
  if (busy.value) return
  busy.value = true
  try {
    await actions.action(action, { ...payload, revision: game.value.revision })
  } finally {
    busy.value = false
  }
}

function chooseTrait(traitId: string) { return send('choose_trait', { traitId }) }
function chooseLockerTarget(playerId: string) { return send('choose_locker_target', { playerId }) }
function draw() { return send('draw') }
function collect() { return send('collect') }
function resolveEffect(optionId: string) {
  if (!pendingChoice.value?.choiceId) return
  return send('resolve_effect', { choiceId: pendingChoice.value.choiceId, optionId })
}
function playerName(playerId: string | null) {
  return game.value.players.find(player => player.id === playerId)?.displayName ?? '未知玩家'
}

const motion = ref<PublicEventView | null>(null)
const motionQueue = ref<PublicEventView[]>([])
const lastEventSeq = ref(0)
let motionTimer: ReturnType<typeof setTimeout> | null = null

function playNextMotion() {
  if (motion.value || !motionQueue.value.length) return
  motion.value = motionQueue.value.shift() ?? null
  motionTimer = setTimeout(() => {
    motion.value = null
    motionTimer = null
    setTimeout(playNextMotion, 30)
  }, motion.value?.type === 'bust_detected' ? 820 : 660)
}

watch(
  () => game.value.events.map(event => event.seq).join(','),
  () => {
    const events = game.value.events
    if (!lastEventSeq.value) {
      lastEventSeq.value = events.at(-1)?.seq ?? 0
      return
    }
    const incoming = events.filter(event => event.seq > lastEventSeq.value)
    if (incoming.length) {
      lastEventSeq.value = incoming.at(-1)!.seq
      motionQueue.value.push(...incoming.filter(event => event.type !== 'trait_locked'))
      playNextMotion()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (motionTimer) clearTimeout(motionTimer)
})

const motionSuit = computed<SuitId | null>(() => {
  const data = motion.value?.data
  return (data?.card?.suit ?? data?.suit ?? null) as SuitId | null
})
const motionClasses = computed(() => {
  if (!motion.value) return []
  const typeClass: Record<string, string> = {
    card_drawn: 'cue-card-drawn', card_entered: 'cue-card-entered', effect_targeted: 'cue-effect',
    oracle_revealed: 'cue-oracle', kraken_debt_changed: 'cue-kraken', bust_detected: 'cue-bust',
    protected_split: 'cue-protected', key_chest_bonus: 'cue-bonus', card_transferred: 'cue-transfer',
    turn_changed: 'cue-turn', score_resolved: 'cue-score', traits_revealed: 'cue-traits', game_finished: 'cue-score',
    map_revealed: 'cue-map', player_forfeit: 'cue-bust',
  }
  return [typeClass[motion.value.type] ?? 'cue-effect', motionSuit.value ? `cue-${motionSuit.value}` : '']
})
</script>

<template>
  <section
    class="dmd-game"
    :class="`phase-${game.phase}`"
    :data-phase="game.phase"
    :data-player-count="game.players.length"
  >
    <header class="status-rail">
      <div><small>亡命神抽 · {{ game.rules.profileNameZh }}</small><strong>第 {{ game.turnNumber }} 回合</strong></div>
      <div class="status-center"><b>{{ currentPlayer?.displayName || '牌局结束' }}</b><span>{{ phaseLabel }} · {{ instruction }}</span></div>
      <div class="deck-metric"><small>抽牌堆</small><strong>{{ game.drawCount }}</strong></div>
    </header>

    <div class="table-surface">
      <div class="opponent-rail" :class="`count-${opponents.length}`">
        <PlayerBank v-for="player in opponents" :key="player.id" :player="player" :suits="game.suitCatalog" compact />
      </div>

      <main class="center-board">
        <section class="pile-zone discard-zone" aria-label="弃牌堆">
          <span>弃牌堆 · 公开</span>
          <div class="discard-card" :class="{ empty: !game.discard.count }">
            <LootCard v-if="game.discard.cards[0]" :card="game.discard.cards[0]" compact />
            <b v-else>空</b>
          </div>
          <strong>{{ game.discard.count }}</strong>
        </section>

        <section class="play-lane" aria-label="本回合航道">
          <header>
            <div><strong>本回合航道</strong><small>{{ game.playArea.length ? `${game.playArea.length} 张已入场` : '等待第一张牌' }}</small></div>
            <div class="risk-pills">
              <span v-for="suit in game.turn?.presentBustKeys ?? []" :key="suit" :style="{ '--pill': game.suitCatalog.find(item => item.id === suit)?.color }">{{ game.suitCatalog.find(item => item.id === suit)?.symbol }}</span>
            </div>
          </header>
          <div class="lane-cards">
            <div v-if="!game.playArea.length" class="lane-empty"><span>翻牌</span><b>每种花色只能出现一次</b></div>
            <div v-for="(entry, index) in game.playArea" :key="entry.entryId" class="lane-entry" :class="{ protected: entry.protected }">
              <LootCard class="lane-card" :card="entry.card" :protected="entry.protected" />
              <span>{{ index + 1 }}</span><small>{{ entry.protected ? entry.protectionLabelsZh.join(' · ') : entry.sourceLabelZh }}</small>
            </div>
          </div>
          <footer class="risk-meter" :class="{ danger: (game.turn?.krakenDebt ?? 0) > 0 }">
            <span>爆牌依据：花色重复</span>
            <strong v-if="game.turn?.krakenDebt"><SuitIcon suit="kraken" :size="21" label="海怪"/> 海怪 {{ game.turn.krakenDebt }}</strong>
            <b v-else>可安全收牌</b>
          </footer>
          <aside v-if="game.turn?.oraclePeekCards.length" class="oracle-peek" aria-label="水晶球公开预览">
            <span><SuitIcon suit="oracle" :size="22" label="水晶球"/> 下一张</span>
            <LootCard v-for="card in game.turn.oraclePeekCards" :key="card.id" :card="card" compact />
          </aside>
        </section>

        <button class="pile-zone draw-zone" type="button" :disabled="!game.actions.canDraw || busy" aria-label="从抽牌堆翻一张牌" @click="draw">
          <span>抽牌堆 · 隐藏</span>
          <div class="card-back"><i/><b>亡命<br>神抽</b></div>
          <strong>{{ game.drawCount }}</strong>
        </button>
      </main>

      <PlayerBank v-if="selfPlayer" class="self-bank" :player="selfPlayer" :suits="game.suitCatalog" self />

      <footer class="action-dock">
        <div><small>{{ latestEvent?.textZh || '常规规则已加载' }}</small><strong>{{ game.actions.disabledReasonZh || instruction }}</strong></div>
        <PluginButton class="draw-action" variant="primary" :disabled="!game.actions.canDraw || busy" @click="draw">
          {{ game.playArea.length ? '继续翻牌' : '翻第一张牌' }}
        </PluginButton>
        <PluginButton class="collect-action" :disabled="!game.actions.canCollect || busy" @click="collect">
          收牌{{ game.turn?.krakenDebt ? `（海怪 ${game.turn.krakenDebt}）` : '' }}
        </PluginButton>
        <details class="rule-tip"><summary>规则</summary><p>重复花色立即爆牌；收牌时每个花色只计算最高牌。抓钩、弯刀和藏宝图的强制选择可能导致爆牌。</p></details>
      </footer>
    </div>

    <aside v-if="game.phase === 'trait_selection'" class="trait-sheet" role="dialog" aria-modal="true" aria-labelledby="trait-title">
      <small>开局准备 · 私密选择</small><h2 id="trait-title">选择你的船长特性</h2>
      <div v-if="game.actions.canChooseTrait" class="trait-options">
        <button v-for="trait in game.self?.traitOffer ?? []" :key="trait.id" type="button" :disabled="busy" @click="chooseTrait(trait.id)">
          <span>{{ trait.nameEn }}</span><strong>{{ trait.nameZh }}</strong><p>{{ trait.summaryZh }}</p>
        </button>
      </div>
      <div v-else-if="game.actions.canChooseLockerTarget" class="locker-options">
        <p>选择一名对手；该玩家爆牌时，未受保护的牌将进入你的银行。</p>
        <button v-for="player in opponents.filter(item => !item.forfeited)" :key="player.id" type="button" @click="chooseLockerTarget(player.id)">{{ player.displayName }}</button>
      </div>
      <p v-else class="waiting">你的选择已锁定，等待其他玩家完成。</p>
    </aside>

    <EffectChoice v-if="pendingChoice" :choice="pendingChoice" :player-name="playerName" @select="resolveEffect" />
    <ScoreBreakdown v-if="game.result" :result="game.result" :players="game.players" :suits="game.suitCatalog" :can-restart="snapshot.actions.canRestart" @restart="actions.restart()" />

    <div v-if="motion" class="motion-layer" :class="motionClasses" aria-hidden="true">
      <div class="motion-object">
        <SuitIcon v-if="motionSuit" :suit="motionSuit" :size="74" :label="motionSuit" />
        <b v-else>{{ motion.type === 'bust_detected' ? '爆' : '✦' }}</b>
      </div>
      <p>{{ motion.textZh }}</p>
    </div>
    <p class="sr-live" :aria-live="motion?.type === 'bust_detected' || motion?.type === 'game_finished' ? 'assertive' : 'polite'">{{ latestEvent?.textZh }}</p>
  </section>
</template>

<style scoped>
.dmd-game {
  --table: #173b3a; --table-edge: #6f4f32; --paper: #efe2c4; --ink: #1e2928;
  --paper-shadow: #b7a47d; --muted-ink: #5e6965; --brass: #b28a4a; --danger: #a3473d;
  --protected: #4f7f78; --focus: #f2c96d; --panel: #203f3e; --white: #fff9ea;
  position: relative; isolation: isolate; width: 100%; min-width: 0; max-width: 100%; min-height: min(900px, calc(100dvh - 30px));
  overflow: hidden; color: #fff9ea; background: #0d2526; font-family: Inter, "Microsoft YaHei", system-ui, sans-serif;
}
* { box-sizing: border-box; }
.status-rail { min-width: 0; display: grid; grid-template-columns: 1fr minmax(280px, 1.4fr) 1fr; align-items: center; gap: 16px; min-height: 68px; padding: 11px clamp(14px, 2.5vw, 38px); border-bottom: 1px solid #3e6562; background: #203f3e; box-shadow: 0 8px 30px #07191870; }
.status-rail > div { min-width: 0; display: grid; }
.status-rail small { color: #afc0b9; font-size: 10px; letter-spacing: .08em; }
.status-rail strong { overflow: hidden; color: #fff9ea; font-size: 18px; text-overflow: ellipsis; white-space: nowrap; }
.status-center { text-align: center; }
.status-center b { color: var(--focus); font-size: 17px; }
.status-center span { overflow: hidden; color: #c9d5cf; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.deck-metric { justify-items: end; }.deck-metric strong { color: var(--focus); font-size: 27px; }
.table-surface { min-width: 0; display: grid; grid-template-columns: minmax(190px, .22fr) minmax(0, 1fr) minmax(190px, .22fr); grid-template-rows: auto minmax(340px, 1fr) auto auto; grid-template-areas: ". north ." "west center east" ". self ." ". dock ."; gap: 10px; min-height: calc(100dvh - 98px); padding: 12px clamp(10px, 2vw, 26px) 14px; border: clamp(8px, 1vw, 16px) solid var(--table-edge); border-top: 0; border-radius: 0 0 38px 38px; background: radial-gradient(circle at 50% 38%, #214c49, var(--table) 52%, #123332); box-shadow: inset 0 0 0 3px #365c58, inset 0 25px 60px #061b1a55; }
.opponent-rail { display: contents; }
.opponent-rail :deep(.player-bank) { align-self: center; }
.opponent-rail.count-1 :deep(.player-bank:nth-child(1)) { grid-area: north; }
.opponent-rail.count-2 :deep(.player-bank:nth-child(1)), .opponent-rail.count-3 :deep(.player-bank:nth-child(1)) { grid-area: west; }
.opponent-rail.count-2 :deep(.player-bank:nth-child(2)) { grid-area: east; }
.opponent-rail.count-3 :deep(.player-bank:nth-child(2)) { grid-area: north; }
.opponent-rail.count-3 :deep(.player-bank:nth-child(3)) { grid-area: east; }
.center-board { grid-area: center; min-width: 0; display: grid; grid-template-columns: 104px minmax(0, 1fr) 104px; gap: 10px; align-items: stretch; }
.pile-zone { min-width: 0; display: grid; place-items: center; align-content: center; gap: 7px; padding: 8px; border: 1px solid #557370; border-radius: 15px; color: #c9d5cf; background: #153332cc; }
.pile-zone > span { font-size: 9px; text-align: center; }.pile-zone > strong { color: var(--focus); font-size: 21px; }
.draw-zone { font: inherit; cursor: pointer; }.draw-zone:disabled { cursor: default; opacity: .62; }
.draw-zone:not(:disabled):hover, .draw-zone:not(:disabled):focus-visible { border-color: var(--focus); outline: 2px solid #f2c96d66; }
.card-back { position: relative; display: grid; width: 70px; aspect-ratio: 5/7; place-items: center; overflow: hidden; border: 2px solid #b28a4a; border-radius: 11px; color: #f2c96d; background: linear-gradient(145deg, #173e3d, #0f2828); box-shadow: 4px 5px 0 #214947, 8px 10px 0 #132f2e, 0 12px 20px #05181780; }
.card-back::before, .card-back::after { content: ''; position: absolute; inset: 9px; border: 1px solid #67837c; border-radius: 9px; transform: rotate(34deg); }.card-back::after { transform: rotate(-34deg); }.card-back b { z-index: 1; text-align: center; font-size: 12px; letter-spacing: .1em; }
.discard-card { display: grid; min-height: 82px; place-items: center; transform: rotate(-2deg); }.discard-card.empty { width: 58px; border: 1px dashed #557370; border-radius: 8px; }
.play-lane { position: relative; min-width: 0; display: grid; grid-template-rows: auto minmax(150px, 1fr) auto; padding: 12px; border: 1px dashed #3e6562; border-radius: 24px; background: #0d2d2cbd; box-shadow: inset 0 14px 30px #05191880; }
.play-lane > header { min-width: 0; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 0 4px 8px; }.play-lane > header div:first-child { display: grid; }.play-lane > header strong { font-size: 13px; }.play-lane > header small { color: #afc0b9; font-size: 9px; }
.risk-pills { display: flex; gap: 3px; }.risk-pills span { display: grid; width: 21px; height: 21px; place-items: center; border: 1px solid var(--pill); border-radius: 50%; color: #fff9ea; background: color-mix(in srgb, var(--pill) 65%, #123332); font-size: 9px; font-weight: 900; }
.lane-cards { min-width: 0; display: flex; align-items: center; gap: clamp(8px, 1vw, 14px); overflow-x: auto; overflow-y: hidden; padding: 8px 7px 16px; scrollbar-color: #557370 transparent; }
.lane-entry { display: grid; justify-items: center; gap: 2px; flex: 0 0 auto; }.lane-entry > span { color: #c9d5cf; font-size: 9px; }.lane-entry > small { max-width: 100px; overflow: hidden; color: #74aaa2; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.lane-entry.protected > span { color: var(--focus); }
.lane-empty { width: 100%; min-height: 130px; display: grid; place-items: center; align-content: center; gap: 5px; color: #678b87; }.lane-empty span { display: grid; width: 54px; height: 70px; place-items: center; border: 1px dashed #557370; border-radius: 10px; }.lane-empty b { font-size: 10px; font-weight: 500; }
.risk-meter { display: flex; align-items: center; justify-content: center; gap: 20px; min-height: 40px; padding: 7px 14px; border: 1px solid #557370; border-radius: 14px; color: #c9d5cf; background: #203f3e; font-size: 11px; }.risk-meter strong { display: flex; align-items: center; gap: 4px; color: #ffb1a8; }.risk-meter b { color: #8fc2a8; }.risk-meter.danger { border-color: var(--danger); box-shadow: 0 0 20px #a3473d33; }
.oracle-peek { position: absolute; top: 50px; right: 8px; z-index: 4; display: flex; align-items: center; gap: 5px; padding: 6px; border: 1px solid #8f7cca; border-radius: 11px; background: #1e2540ed; box-shadow: 0 8px 22px #071015aa; }.oracle-peek > span { display: flex; align-items: center; gap: 4px; color: #d6ccff; font-size: 9px; }
.self-bank { grid-area: self; width: 100%; }
.action-dock { grid-area: dock; min-width: 0; display: grid; grid-template-columns: minmax(180px, 1fr) auto auto auto; gap: 8px; align-items: center; padding: 10px 12px; border: 1px solid #557370; border-radius: 16px; background: #203f3eef; box-shadow: 0 -8px 26px #06181755; }.action-dock > div { min-width: 0; display: grid; }.action-dock small, .action-dock strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.action-dock small { color: #8fa9a3; font-size: 9px; }.action-dock strong { font-size: 11px; }
.action-dock :deep(button) { min-width: 128px; }.action-dock .collect-action:deep(button), .action-dock :deep(.collect-action) { background: #4f7f78; }
.rule-tip { position: relative; }.rule-tip summary { padding: 8px; cursor: pointer; color: #c9d5cf; font-size: 11px; }.rule-tip p { position: absolute; z-index: 12; right: 0; bottom: 36px; width: min(330px, 80vw); margin: 0; padding: 12px; border: 1px solid #557370; border-radius: 10px; color: #dbe4df; background: #102a29f5; font-size: 11px; line-height: 1.55; box-shadow: 0 16px 40px #031211b8; }
.trait-sheet { position: absolute; z-index: 25; inset: 50% auto auto 50%; width: min(760px, calc(100% - 28px)); transform: translate(-50%, -50%); padding: clamp(18px, 3vw, 30px); border: 1px solid var(--focus); border-radius: 23px; color: #fff9ea; background: #102c2bf2; box-shadow: 0 30px 80px #020d0cdb; backdrop-filter: blur(18px); }.trait-sheet > small { color: var(--focus); font-size: 10px; letter-spacing: .16em; }.trait-sheet h2 { margin: 5px 0 16px; font-size: clamp(22px, 4vw, 35px); }
.trait-options { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.trait-options button { display: grid; gap: 5px; min-height: 170px; padding: 20px; border: 1px solid #557370; border-radius: 16px; color: #fff9ea; text-align: left; background: linear-gradient(145deg, #1d4643, #163735); cursor: pointer; }.trait-options button:hover, .trait-options button:focus-visible { transform: translateY(-3px); border-color: var(--focus); outline: none; box-shadow: 0 12px 30px #020d0c88; }.trait-options span { color: #afc0b9; font-size: 11px; }.trait-options strong { color: var(--focus); font-size: 24px; }.trait-options p, .locker-options p { margin: 0; color: #d4ded8; font-size: 13px; line-height: 1.55; }
.locker-options { display: flex; flex-wrap: wrap; gap: 9px; }.locker-options p { flex-basis: 100%; }.locker-options button { padding: 10px 16px; border: 1px solid #b28a4a; border-radius: 10px; color: #fff9ea; background: #234743; cursor: pointer; }.waiting { color: #afc0b9; }
.motion-layer { position: absolute; z-index: 40; inset: 0; display: grid; place-items: center; align-content: center; gap: 16px; overflow: hidden; pointer-events: none; background: radial-gradient(circle, #173b3a30, transparent 58%); }.motion-object { display: grid; width: 132px; height: 132px; place-items: center; border: 2px solid var(--focus); border-radius: 50%; color: var(--focus); background: #102b2be8; box-shadow: 0 0 70px #f2c96d50; }.motion-object > b { font-size: 70px; }.motion-layer p { max-width: min(620px, 88vw); margin: 0; padding: 9px 16px; border-radius: 999px; color: #fff9ea; text-align: center; background: #071c1bdc; font-size: clamp(13px, 2vw, 18px); font-weight: 800; }
.cue-card-drawn .motion-object { animation: card-flight .66s cubic-bezier(.2,.8,.2,1) both; }.cue-card-entered .motion-object, .cue-effect .motion-object { animation: card-arrive .66s ease both; }.cue-anchor .motion-object { animation: anchor-lock .66s ease both; color: #62a8b4; }.cue-hook .motion-object { animation: hook-swing .66s ease both; color: #b68c72; }.cue-cannon .motion-object { animation: cannon-recoil .66s ease both; color: #d87868; }.cue-key .motion-object { animation: key-turn .66s ease both; color: #e0ae45; }.cue-chest .motion-object, .cue-bonus .motion-object { animation: chest-open .66s ease both; color: #d0a45a; }.cue-map .motion-object { animation: map-unfold .66s ease both; color: #84ad7e; }.cue-oracle .motion-object { animation: oracle-focus .66s ease both; color: #a58fdf; }.cue-sword .motion-object { animation: sword-slash .66s ease both; color: #a6b3ba; }.cue-kraken .motion-object { animation: kraken-rise .66s ease both; color: #6fa49f; }.cue-mermaid .motion-object { animation: mermaid-wave .66s ease both; color: #d886af; }.cue-bust { background: radial-gradient(circle, #a3473d55, transparent 62%); animation: bust-flash .82s ease both; }.cue-bust .motion-object { color: #ffb1a8; border-color: #d65e52; animation: bust-shake .82s ease both; }.cue-protected .motion-object { color: #8fc9bf; border-color: #4f7f78; animation: shield-split .66s ease both; }.cue-transfer .motion-object { animation: bank-drop .66s ease both; }.cue-turn .motion-object { animation: turn-pulse .66s ease both; }.cue-score .motion-object { animation: score-rise .66s ease both; }
.sr-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
@keyframes card-flight { from { opacity: 0; transform: translate(32vw,-28vh) rotate(16deg) scale(.45); } 70% { opacity: 1; transform: translate(0) rotate(-3deg) scale(1.08); } to { transform: none; } }
@keyframes card-arrive { from { opacity: 0; transform: translateY(70px) scale(.65); } 60% { transform: translateY(-8px) scale(1.08); } to { opacity: 1; transform: none; } }
@keyframes anchor-lock { 0% { transform: scale(.45) rotate(-18deg); opacity: 0; } 55% { transform: scale(1.16); } 75% { box-shadow: 0 0 0 28px #4f7f7825, 0 0 70px #4f7f7860; } 100% { transform: none; opacity: 1; } }
@keyframes hook-swing { 0% { transform: translateY(-90px) rotate(-38deg); opacity: 0; } 55% { transform: translateY(8px) rotate(20deg); opacity: 1; } 100% { transform: none; } }
@keyframes cannon-recoil { 0% { transform: translateX(-30px); opacity: .4; } 35% { transform: translateX(18px) scale(1.12); box-shadow: 50px 0 70px #d8786870; } 100% { transform: none; opacity: 1; } }
@keyframes key-turn { 0% { transform: rotate(-100deg) scale(.5); opacity: 0; } 70% { transform: rotate(14deg) scale(1.12); } 100% { transform: none; opacity: 1; } }
@keyframes chest-open { 0% { clip-path: inset(48% 0 48%); transform: scale(.75); } 60% { clip-path: inset(0); transform: scale(1.14); box-shadow: 0 -28px 70px #f2c96d70; } 100% { transform: none; } }
@keyframes map-unfold { 0% { transform: scaleX(.08) rotate(-7deg); opacity: .4; } 70% { transform: scaleX(1.08) rotate(2deg); } 100% { transform: none; opacity: 1; } }
@keyframes oracle-focus { 0% { filter: blur(9px); transform: scale(.5); opacity: 0; } 55% { filter: blur(0); transform: scale(1.15); box-shadow: 0 0 80px #a58fdf80; } 100% { transform: none; opacity: 1; } }
@keyframes sword-slash { 0% { clip-path: inset(0 100% 0 0); transform: translate(-60px,40px) rotate(-28deg); } 55% { clip-path: inset(0); transform: translate(14px,-8px) rotate(8deg); } 100% { transform: none; } }
@keyframes kraken-rise { 0% { transform: translateY(100px) scaleY(.45); opacity: 0; } 55% { transform: translateY(-10px) scaleY(1.12); } 100% { transform: none; opacity: 1; } }
@keyframes mermaid-wave { 0% { transform: translate(-50px,35px) rotate(-12deg); opacity: 0; } 45% { transform: translate(16px,-9px) rotate(8deg) scale(1.12); } 100% { transform: none; opacity: 1; } }
@keyframes bust-flash { 0%,100% { opacity: 1; } 30% { opacity: .82; background-color: #a3473d33; } }
@keyframes bust-shake { 0%,100% { transform: translateX(0); } 20% { transform: translateX(-24px) rotate(-7deg); } 40% { transform: translateX(22px) rotate(6deg); } 60% { transform: translateX(-13px); } 80% { transform: translateX(8px); } }
@keyframes shield-split { 0% { transform: scale(.55); opacity: 0; } 55% { box-shadow: -60px 0 50px #4f7f7860, 60px 0 50px #a3473d45; transform: scale(1.12); } 100% { transform: none; opacity: 1; } }
@keyframes bank-drop { from { transform: translateY(-80px) scale(.7); opacity: 0; } 70% { transform: translateY(8px) scale(1.08); } to { transform: none; opacity: 1; } }
@keyframes turn-pulse { 0% { transform: scale(.7); opacity: 0; } 60% { transform: scale(1.16); } 100% { transform: none; opacity: 1; } }
@keyframes score-rise { from { transform: translateY(50px) scale(.7); opacity: 0; } 60% { transform: translateY(-8px) scale(1.12); } to { transform: none; opacity: 1; } }
@media (max-width: 1179px) {
  .status-rail { grid-template-columns: 1fr 1.5fr auto; }
  .table-surface { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(280px, 1fr) auto auto; grid-template-areas: "opponents" "center" "self" "dock"; }
  .center-board { grid-template-columns: 92px minmax(0, 1fr) 92px; gap: 8px; }.card-back { width: 58px; }
  .opponent-rail { grid-area: opponents; min-width: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
  .opponent-rail.count-1 { grid-template-columns: minmax(280px, 560px); justify-content: center; }.opponent-rail.count-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .opponent-rail.count-1 :deep(.player-bank), .opponent-rail.count-2 :deep(.player-bank), .opponent-rail.count-3 :deep(.player-bank) { grid-area: auto; align-self: stretch; }
  .action-dock { grid-template-columns: minmax(140px,1fr) auto auto; }.rule-tip { display: none; }
}
@media (max-width: 759px) {
  .dmd-game { min-height: 100dvh; }
  .status-rail { grid-template-columns: 1fr auto; min-height: 60px; padding: 8px 10px; }.status-center { grid-column: 1 / -1; grid-row: 2; text-align: left; }.status-center b { display: none; }.status-center span { white-space: normal; }.deck-metric { grid-column: 2; grid-row: 1; }
  .table-surface { grid-template-rows: auto auto auto auto; padding: 8px 6px 90px; border-width: 7px; border-radius: 0; }
  .opponent-rail, .opponent-rail.count-1, .opponent-rail.count-2 { display: flex; justify-content: flex-start; overflow-x: auto; }.opponent-rail :deep(.player-bank) { min-width: min(280px, 82vw); }
  .center-board { grid-template-columns: 1fr 1fr; }.play-lane { grid-column: 1 / -1; grid-row: 1; grid-template-rows: auto auto minmax(150px, 1fr) auto; min-height: 285px; }.discard-zone, .draw-zone { min-height: 112px; }.pile-zone { grid-row: 2; grid-template-columns: auto auto auto; align-content: center; }.discard-card, .card-back { width: 45px; min-height: 62px; }.pile-zone > span { text-align: left; }
  .play-lane > header { grid-row: 1; }.oracle-peek { position: static; grid-row: 2; max-width: 100%; margin: 0 0 4px; justify-self: end; }.lane-cards { grid-row: 3; min-height: 158px; }.risk-meter { grid-row: 4; gap: 9px; justify-content: space-between; }
  .action-dock { position: fixed; z-index: 18; right: 0; bottom: 0; left: 0; grid-template-columns: 1fr 1fr; padding: 8px; border-radius: 14px 14px 0 0; }.action-dock > div { grid-column: 1 / -1; }.action-dock :deep(button) { min-width: 0; width: 100%; }.rule-tip { display: none; }
  .trait-sheet { position: fixed; inset: 8px; width: auto; max-height: none; overflow: auto; transform: none; }
  .trait-options { grid-template-columns: 1fr; }.trait-options button { min-height: 130px; }
}
@media (max-width: 390px) {
  .status-rail strong { font-size: 15px; }.table-surface { border-left-width: 4px; border-right-width: 4px; }.play-lane { padding: 8px; }.lane-entry > small { display: none; }.loot-card { width: 76px; }.risk-meter > span { display: none; }
  .trait-sheet { width: auto; padding: 16px; }.trait-sheet h2 { font-size: 21px; }.trait-options button { padding: 14px; }.trait-options strong { font-size: 20px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
  .motion-layer { background: #102b2bd9; }.motion-object { transform: none !important; box-shadow: 0 0 0 4px currentColor !important; }
}
</style>
