<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import { setDevPluginActions } from './local-sdk'


const fruitNames = ['苹果', '梨', '橙子', '桃子', '李子', '杏', '番石榴', '火龙果', '香蕉', '杨桃', '百香果', '柠檬', '青柠', '西柚', '葡萄', '蓝莓', '黑莓', '草莓', '樱桃', '覆盆子', '西瓜', '哈密瓜', '椰子', '菠萝', '猕猴桃', '无花果', '荔枝', '龙眼', '芒果', '红毛丹']
const effectByIndex = ['harvest', 'harvest', 'harvest', 'harvest', 'harvest', 'harvest', 'harvest', 'harvest', 'shake_basket', 'shake_basket', 'shake_basket', 'sour_skip', 'sour_skip', 'sour_skip', 'peek_hand', 'peek_hand', 'peek_hand', 'sweet_share', 'sweet_share', 'sweet_share', 'half_exchange', 'half_exchange', 'shell_guard', 'shell_guard', 'careful_stocking', 'careful_stocking', 'extra_pick', 'extra_pick', 'market_conveyor', 'market_conveyor']
const labelByEffect: Record<string, string> = {
  harvest: '好收成', shake_basket: '摇匀果篮', sour_skip: '酸住了', peek_hand: '偷瞄一串',
  sweet_share: '甜蜜分享', half_exchange: '对半交换', shell_guard: '硬壳保护',
  careful_stocking: '精心理货', extra_pick: '顺手再摘', market_conveyor: '流水果摊', old_maid: '坏果老鳖',
}
const query = new URLSearchParams(window.location.search)
const initialPlayers = Math.min(8, Math.max(4, Number(query.get('players')) || 8))
const panelVisible = ref(query.get('panel') !== '0')
const playerCount = ref(initialPlayers)
let sequence = 4

function fruitCard(index: number, instance = `self-${index}`) {
  const code = String(index).padStart(2, '0')
  const effectId = effectByIndex[index - 1]
  return {
    instanceId: instance,
    catalogId: `fruit-${code}`,
    cardCode: code,
    sortIndex: index,
    kind: 'normal',
    nameZh: fruitNames[index - 1],
    effectId,
    effectLabelZh: labelByEffect[effectId],
  }
}

function oldMaidCard(index: number) {
  const names = ['发霉榴莲', '黑斑木瓜', '酸败石榴', '腐坏山竹']
  return {
    instanceId: `old-${index}`,
    catalogId: `old-maid-0${index}`,
    cardCode: `B0${index}`,
    sortIndex: 100 + index,
    kind: 'old_maid',
    nameZh: names[index - 1],
    effectId: 'old_maid',
    effectLabelZh: '坏果老鳖',
  }
}

function makeSnapshot(count: number): ArcadeSnapshot {
  const players = Array.from({ length: count }, (_, index) => ({
    id: `p${index + 1}`, name: `果客${index + 1}`, seat: index, online: true,
  }))
  const selfCards = [fruitCard(9), fruitCard(18), fruitCard(23), oldMaidCard(Math.min(4, Math.floor(count / 2))), fruitCard(5), fruitCard(15), fruitCard(27)]
  const boards = players.map((player, seatIndex) => {
    const cards = player.id === 'p1'
      ? selfCards
      : Array.from({ length: Math.max(4, 10 - seatIndex % 4) }, (_, index) => fruitCard((seatIndex * 4 + index) % 30 + 1, `${player.id}-${index}`))
    return {
      playerId: player.id,
      seatIndex,
      handCount: cards.length,
      handSlots: cards.map((card, index) => ({
        slotId: `${player.id}:${sequence}:${index}`,
        index,
        card: player.id === 'p1' ? card : null,
        protected: player.id === 'p2' && index === 3,
        selectable: player.id === 'p2' && index !== 3,
      })),
      safe: false,
      pendingEmpty: false,
      protectedSlotIndex: player.id === 'p2' ? 3 : null,
      harvestPairIds: Array.from({ length: seatIndex % 4 }, (_, index) => `fruit-0${index + 1}`),
      harvestCount: seatIndex % 4,
    }
  })
  return {
    revision: sequence,
    roomCode: 'FRUT',
    gameKey: 'plugin-spoiled-fruit',
    gameName: '坏果别留手！',
    phase: 'playing',
    options: { mode: 'standard' },
    hostId: 'p1',
    self: players[0],
    players,
    requiredPlayers: 4,
    roundNumber: 1,
    winner: null,
    winnerPlayerIds: [],
    winReason: null,
    actions: {
      canStart: false, canRestart: false, canAct: true, canKickPlayers: false, canDissolve: true,
      canEditRules: false, canRequestUndo: false, canRequestDraw: false, canResolveRequest: false,
    },
    rematchReadyPlayerIds: [], request: null, chat: { maxLength: 200, messages: [] },
    game: {
      schemaVersion: 1, gameKey: 'spoiled-fruit', mode: 'standard', phase: 'turn_draw',
      sceneId: 'turn.normal-draw', firstPlayerId: 'p1', currentPlayerId: 'p1', playerCount: count,
      oldMaidCount: Math.floor(count / 2), totalCardCount: 60 + Math.floor(count / 2),
      removedPairCount: 11, initialRemovedPairCount: 7, normalDrawCount: 8, effectTransferCount: 5,
      players: boards, drawSourcePlayerId: 'p2', effectQueue: [], activeEffect: null, skipCount: 0,
      pendingChoice: null, privateChoice: null, privatePeek: null, legalActions: ['draw_card'],
      events: [
        { sequence: 1, type: 'deal', message: `${60 + Math.floor(count / 2)} 张牌按固定顺序发完` },
        { sequence: 2, type: 'initial_sweep', message: '开局收走 7 对水果；不发动技能' },
        { sequence: 3, type: 'turn', message: '轮到果客1从果客2按序暗抽' },
        { sequence: 4, type: 'draw', message: '顺时暗抽完成；新牌固定追加到最右侧' },
      ],
      eventSequence: sequence, safeOrder: [], finished: null, won: false, result: null,
    },
  } as unknown as ArcadeSnapshot
}

const snapshot = ref(makeSnapshot(playerCount.value))
const gameState = computed(() => snapshot.value.game as any)

function replaceGame(patch: Record<string, unknown>) {
  snapshot.value = {
    ...snapshot.value,
    revision: ++sequence,
    game: { ...gameState.value, ...patch, eventSequence: sequence },
  }
}

function choosePlayers(count: number) {
  playerCount.value = count
  sequence += 1
  snapshot.value = makeSnapshot(count)
}

function trigger(type: string) {
  const messages: Record<string, string> = {
    draw: '顺时暗抽完成；新牌固定追加到最右侧', pair: '香蕉成对离场，摇匀果篮进入队尾',
    shuffle: '果客1的整篮手牌已由服务端随机洗序', skip: '酸味累积：交接时额外跳过 1 人',
    peek: '果客1查看了果客3的完整固定牌序', sweet_share: '甜蜜分享完成，2 张牌按所选插槽落位',
    half_exchange: '对半交换完成，6 张牌按所选插槽落位', protect: '果客1给固定牌序中的一张牌加上硬壳',
    move: '果客1用精心理货移动了一张牌', extra_draw: '顺手再摘完成；新牌固定追加到最右侧',
    market_conveyor: '流水果摊完成，所有传牌按所选插槽落位', safe: '果客4效果队列清空后空篮，安全离场',
  }
  const nextSequence = sequence + 1
  const event = {
    sequence: nextSequence,
    type,
    message: messages[type] ?? type,
    pairCatalogId: type === 'pair' ? 'fruit-09' : undefined,
    effectId: type === 'pair' || type === 'shuffle' ? 'shake_basket' : undefined,
  }
  replaceGame({ events: [...gameState.value.events, event] })
}

function showChoice(type: 'half' | 'insert' | 'peek') {
  if (type === 'half') {
    replaceGame({
      phase: 'effect_choice', drawSourcePlayerId: null, legalActions: ['select_exchange_cards'],
      privateChoice: {
        type: 'half_select', queueId: 'demo-half', effectId: 'half_exchange', effectLabelZh: '对半交换',
        selectionCount: 4, handCount: 7, otherPlayerId: 'p3',
        availableCardIds: gameState.value.players[0].handSlots.map((slot: any) => slot.card.instanceId),
      },
      pendingChoice: { type: 'half_select', effectId: 'half_exchange', requiredPlayerIds: ['p1', 'p3'], completedPlayerIds: [] },
      activeEffect: { queueId: 'demo-half', batchId: 'demo', pairCatalogId: 'fruit-21', effectId: 'half_exchange', effectLabelZh: '对半交换', ownerPlayerId: 'p1' },
      effectQueue: [{ queueId: 'demo-half', batchId: 'demo', pairCatalogId: 'fruit-21', effectId: 'half_exchange', effectLabelZh: '对半交换', ownerPlayerId: 'p1' }],
    })
  } else if (type === 'insert') {
    replaceGame({
      phase: 'effect_insert', drawSourcePlayerId: null, legalActions: ['place_received'],
      privateChoice: {
        type: 'insert', queueId: 'demo-insert', effectId: 'half_exchange', effectLabelZh: '对半交换',
        transferType: 'half_exchange', baseHandCount: 7,
        incomingCards: [fruitCard(2, 'incoming-1'), oldMaidCard(2), fruitCard(30, 'incoming-3')],
      },
      pendingChoice: { type: 'insert', effectId: 'half_exchange', requiredPlayerIds: ['p1', 'p3'], completedPlayerIds: ['p3'] },
      activeEffect: { queueId: 'demo-insert', batchId: 'demo', pairCatalogId: 'fruit-21', effectId: 'half_exchange', effectLabelZh: '对半交换', ownerPlayerId: 'p1' },
      effectQueue: [{ queueId: 'demo-insert', batchId: 'demo', pairCatalogId: 'fruit-21', effectId: 'half_exchange', effectLabelZh: '对半交换', ownerPlayerId: 'p1' }],
    })
  } else {
    replaceGame({
      phase: 'effect_choice', drawSourcePlayerId: null, legalActions: ['resolve_optional'],
      privateChoice: { type: 'optional', queueId: 'demo-peek', effectId: 'peek_hand', effectLabelZh: '偷瞄一串', targetPlayerIds: snapshot.value.players.slice(1).map((player) => player.id) },
      pendingChoice: { type: 'optional', effectId: 'peek_hand', requiredPlayerIds: ['p1'], completedPlayerIds: [] },
      activeEffect: { queueId: 'demo-peek', batchId: 'demo', pairCatalogId: 'fruit-15', effectId: 'peek_hand', effectLabelZh: '偷瞄一串', ownerPlayerId: 'p1' },
      effectQueue: [{ queueId: 'demo-peek', batchId: 'demo', pairCatalogId: 'fruit-15', effectId: 'peek_hand', effectLabelZh: '偷瞄一串', ownerPlayerId: 'p1' }],
    })
  }
}

function finishDemo() {
  const holders = [
    { playerId: 'p1', cards: [oldMaidCard(4)] },
    { playerId: 'p5', cards: [oldMaidCard(1), oldMaidCard(2), oldMaidCard(3)].slice(0, Math.max(1, Math.floor(playerCount.value / 2) - 1)) },
  ]
  snapshot.value = {
    ...snapshot.value,
    phase: 'finished',
    winner: 'fruit_market',
    winnerPlayerIds: snapshot.value.players.filter((player) => !holders.some((holder) => holder.playerId === player.id)).map((player) => player.id),
    actions: { ...snapshot.value.actions, canAct: false, canRestart: true },
    game: {
      ...gameState.value,
      phase: 'finished', currentPlayerId: null, drawSourcePlayerId: null, legalActions: [], effectQueue: [], activeEffect: null,
      privateChoice: null, pendingChoice: null, removedPairCount: 30, won: false, result: 'fruit_market',
      finished: {
        winnerIds: snapshot.value.players.filter((player) => !holders.some((holder) => holder.playerId === player.id)).map((player) => player.id),
        loserIds: holders.map((holder) => holder.playerId), oldMaidHolders: holders,
      },
      eventSequence: ++sequence,
      events: [...gameState.value.events, { sequence, type: 'finish', message: '坏果揭晓：果客1与果客5仍持有老鳖' }],
    },
  } as ArcadeSnapshot
}

setDevPluginActions({
  async action(action, payload = {}) {
    if (action === 'draw_card' || action === 'draw_extra') trigger(action === 'draw_card' ? 'draw' : 'extra_draw')
    else if (action === 'select_exchange_cards') showChoice('insert')
    else if (action === 'place_received') {
      trigger('half_exchange')
      replaceGame({ privateChoice: null, pendingChoice: null, effectQueue: [], activeEffect: null, phase: 'turn_draw', drawSourcePlayerId: 'p2', legalActions: ['draw_card'] })
    } else if (action === 'resolve_optional') {
      if (payload.use) trigger('peek')
      replaceGame({ privateChoice: null, pendingChoice: null, effectQueue: [], activeEffect: null, phase: 'turn_draw', drawSourcePlayerId: 'p2', legalActions: ['draw_card'] })
    }
    return true
  },
  async rapidAction() { return false },
  async restart() { choosePlayers(playerCount.value); return true },
  publishSpectatorFrame() { return false },
})
</script>

<template>
  <main class="dev-shell">
    <GameView :snapshot="snapshot" />
    <button v-if="!panelVisible" class="show-panel" type="button" @click="panelVisible = true">验收面板</button>
    <aside v-else class="dev-panel">
      <header><b>本地验收</b><button type="button" @click="panelVisible = false">×</button></header>
      <div><button v-for="count in [4, 5, 6, 7, 8]" :key="count" type="button" :class="{ active: playerCount === count }" @click="choosePlayers(count)">{{ count }} 人</button></div>
      <div><button v-for="type in ['draw', 'pair', 'shuffle', 'skip', 'peek', 'sweet_share', 'half_exchange', 'protect', 'move', 'extra_draw', 'market_conveyor', 'safe']" :key="type" type="button" @click="trigger(type)">{{ type }}</button></div>
      <div><button type="button" @click="showChoice('peek')">偷瞄选择</button><button type="button" @click="showChoice('half')">对半锁牌</button><button type="button" @click="showChoice('insert')">交换插入</button><button type="button" @click="finishDemo">结算</button></div>
    </aside>
  </main>
</template>

<style>
* { box-sizing: border-box; }
html,body,#app { width: 100%; min-width: 320px; height: 100%; margin: 0; overflow: hidden; background: #160d1f; }
button,input,select { font: inherit; }
.dev-shell { width: 100%; height: 100%; overflow: hidden; }
.dev-panel { position: fixed; z-index: 500; top: 84px; right: 9px; width: min(380px, 44vw); display: grid; gap: 7px; border: 1px solid #f6e9cf44; border-radius: 13px; padding: 9px; color: #f6e9cf; background: #211429e8; box-shadow: 0 12px 30px #100813; backdrop-filter: blur(12px); }.dev-panel header { display: flex; justify-content: space-between; align-items: center; font-size: 9px; }.dev-panel header button { font-size: 18px; }.dev-panel > div { display: flex; flex-wrap: wrap; gap: 4px; }.dev-panel button,.show-panel { border: 1px solid #f6e9cf35; border-radius: 7px; padding: 5px 7px; color: #f6e9cf; background: #382142; font-size: 7px; cursor: pointer; }.dev-panel button.active { color: #281b32; background: #e9a33a; }.show-panel { position: fixed; z-index: 500; top: 84px; right: 9px; }
@media (max-width: 620px) { .dev-panel { top: 70px; width: calc(100vw - 18px); max-height: 150px; overflow: auto; } }
</style>
