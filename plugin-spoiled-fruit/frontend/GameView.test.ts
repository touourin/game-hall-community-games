import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'


function card(index: number) {
  const code = String(index).padStart(2, '0')
  return {
    instanceId: `card-${code}`,
    catalogId: `fruit-${code}`,
    cardCode: code,
    sortIndex: index,
    kind: 'normal',
    nameZh: `水果${code}`,
    effectId: index <= 8 ? 'harvest' : 'shake_basket',
    effectLabelZh: index <= 8 ? '好收成' : '摇匀果篮',
  }
}

function makeSnapshot(playerCount = 8): ArcadeSnapshot {
  const players = Array.from({ length: playerCount }, (_, index) => ({
    id: `p${index + 1}`,
    name: `果客${index + 1}`,
    seat: index,
    online: true,
  }))
  const boards = players.map((player, playerIndex) => {
    const cards = Array.from({ length: 8 }, (_, index) => card((index + playerIndex) % 30 + 1))
    return {
      playerId: player.id,
      seatIndex: playerIndex,
      handCount: cards.length,
      handSlots: cards.map((item, index) => ({
        slotId: `${player.id}:1:${index}`,
        index,
        card: player.id === 'p1' ? item : null,
        protected: player.id === 'p2' && index === 3,
        selectable: player.id === 'p2' && index !== 3,
      })),
      safe: false,
      pendingEmpty: false,
      protectedSlotIndex: player.id === 'p2' ? 3 : null,
      harvestPairIds: [],
      harvestCount: playerIndex,
    }
  })
  return {
    revision: 1,
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
      canStart: false,
      canRestart: false,
      canAct: true,
      canKickPlayers: false,
      canDissolve: true,
      canEditRules: false,
      canRequestUndo: false,
      canRequestDraw: false,
      canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 200, messages: [] },
    game: {
      schemaVersion: 1,
      gameKey: 'spoiled-fruit',
      mode: 'standard',
      phase: 'turn_draw',
      sceneId: 'turn.normal-draw',
      firstPlayerId: 'p1',
      currentPlayerId: 'p1',
      playerCount,
      oldMaidCount: Math.floor(playerCount / 2),
      totalCardCount: 60 + Math.floor(playerCount / 2),
      removedPairCount: 6,
      initialRemovedPairCount: 5,
      normalDrawCount: 1,
      effectTransferCount: 0,
      players: boards,
      drawSourcePlayerId: 'p2',
      effectQueue: [],
      activeEffect: null,
      skipCount: 0,
      pendingChoice: null,
      privateChoice: null,
      privatePeek: null,
      legalActions: ['draw_card'],
      events: [{ sequence: 1, type: 'turn', message: '轮到果客1' }],
      eventSequence: 1,
      safeOrder: [],
      finished: null,
      won: false,
      result: null,
    },
  } as unknown as ArcadeSnapshot
}

function mountGame(snapshot: ArcadeSnapshot) {
  return mount(GameView, {
    props: { snapshot },
    global: { plugins: [createPinia()] },
  })
}

describe('spoiled fruit immersive table', () => {
  it.each([4, 5, 6, 7, 8])('lays out %i players without duplicate seat coordinates', (playerCount) => {
    const wrapper = mountGame(makeSnapshot(playerCount))
    const seats = wrapper.findAll('.seat')
    expect(seats).toHaveLength(playerCount - 1)
    const coordinates = seats.map((seat) => seat.attributes('style'))
    expect(new Set(coordinates).size).toBe(coordinates.length)
    for (const style of coordinates) {
      const values = [...style.matchAll(/([\d.]+)%/g)].map((match) => Number(match[1]))
      expect(values).toHaveLength(2)
      expect(values[0]).toBeGreaterThanOrEqual(7)
      expect(values[0]).toBeLessThanOrEqual(93)
      expect(values[1]).toBeGreaterThanOrEqual(9)
      expect(values[1]).toBeLessThanOrEqual(79)
    }
  })

  it('shows the exact fixed source sequence and disables the protected slot', () => {
    const wrapper = mountGame(makeSnapshot(8))
    expect(wrapper.findAll('.draw-sequence .fruit-card')).toHaveLength(8)
    const sourceCards = wrapper.findAll('.draw-sequence .fruit-card')
    expect(sourceCards[3].attributes('disabled')).toBeDefined()
    expect(sourceCards[3].attributes('aria-label')).toContain('受保护')
    expect(wrapper.findAll('.hand-slot')).toHaveLength(8)
    expect(wrapper.text()).toContain('正常新牌落点')
  })

  it('renders half-exchange as a private exact-count lock', async () => {
    const snapshot = makeSnapshot(6)
    snapshot.game = {
      ...(snapshot.game as object),
      phase: 'effect_choice',
      drawSourcePlayerId: null,
      legalActions: ['select_exchange_cards'],
      privateChoice: {
        type: 'half_select',
        queueId: 'effect-1',
        effectId: 'half_exchange',
        effectLabelZh: '对半交换',
        selectionCount: 4,
        handCount: 8,
        otherPlayerId: 'p3',
        availableCardIds: Array.from({ length: 8 }, (_, index) => `card-${String(index + 1).padStart(2, '0')}`),
      },
    }
    const wrapper = mountGame(snapshot)
    expect(wrapper.text()).toContain('秘密选 4 / 8 张')
    const cards = wrapper.findAll('.choice-cards.wide .fruit-card')
    await cards[0].trigger('click')
    await cards[1].trigger('click')
    await cards[2].trigger('click')
    await cards[3].trigger('click')
    expect(wrapper.findAll('.choice-cards.wide .fruit-card.selected')).toHaveLength(4)
    expect(wrapper.get('.choice-panel .primary').attributes('disabled')).toBeUndefined()
  })

  it('queues visual events into the isolated animation plane', async () => {
    vi.useFakeTimers()
    const snapshot = makeSnapshot(4)
    const wrapper = mountGame(snapshot)
    const next = {
      ...snapshot,
      game: {
        ...(snapshot.game as object),
        eventSequence: 2,
        events: [
          ...((snapshot.game as any).events),
          { sequence: 2, type: 'pair', message: '香蕉成对离场', pairCatalogId: 'fruit-09' },
        ],
      },
    } as unknown as ArcadeSnapshot
    await wrapper.setProps({ snapshot: next })
    await nextTick()
    expect(wrapper.get('.animation-layer').classes()).toContain('animation-pair')
    expect(wrapper.findAll('.pair-card')).toHaveLength(2)
    expect(getComputedStyle(wrapper.get('.animation-layer').element).pointerEvents).toBe('none')
    vi.runAllTimers()
    vi.useRealTimers()
  })

  it('reveals every old maid holder only after settlement', () => {
    const snapshot = makeSnapshot(8)
    const oldMaid = {
      instanceId: 'old-4', catalogId: 'old-maid-04', cardCode: 'B04', sortIndex: 104,
      kind: 'old_maid', nameZh: '腐坏山竹', effectId: 'old_maid', effectLabelZh: '坏果老鳖',
    }
    snapshot.phase = 'finished'
    snapshot.game = {
      ...(snapshot.game as object),
      phase: 'finished',
      currentPlayerId: null,
      won: false,
      result: 'fruit_market',
      finished: {
        winnerIds: ['p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8'],
        loserIds: ['p1'],
        oldMaidHolders: [{ playerId: 'p1', cards: [oldMaid] }],
      },
    }
    const wrapper = mountGame(snapshot)
    expect(wrapper.get('.result-overlay').text()).toContain('坏果留在你的果篮里')
    expect(wrapper.get('.result-overlay').text()).toContain('腐坏山竹')
  })
})
