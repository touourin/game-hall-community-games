import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import viewSource from './GameView.vue?raw'

const actionMock = vi.hoisted(() => vi.fn().mockResolvedValue({ ok: true }))

vi.mock('@game-hall/plugin-sdk', () => ({
  usePluginGameActions: () => ({
    action: actionMock,
    rapidAction: vi.fn(),
    restart: vi.fn(),
  }),
}))

const commodityDefinitions = [
  { id: 'ginseng', label: '人参', labelEn: 'Ginseng', code: 'GS', profit: 18, costs: [1, 2, 3], color: '#B4862C', pattern: 'diagonal-root' },
  { id: 'nutmeg', label: '肉豆蔻', labelEn: 'Nutmeg', code: 'NM', profit: 24, costs: [2, 3, 4], color: '#9A5C3A', pattern: 'seed-dots' },
  { id: 'silk', label: '丝绸', labelEn: 'Silk', code: 'SK', profit: 30, costs: [3, 4, 5], color: '#456F9E', pattern: 'woven-lines' },
  { id: 'jade', label: '玉石', labelEn: 'Jade', code: 'JD', profit: 36, costs: [3, 4, 5, 5], color: '#3F806E', pattern: 'faceted-diamonds' },
] as const

function worker(workerId: string, playerId: string, color = '#d6a341') {
  return { workerId, playerId, role: 'accomplice', slotIndex: 0, colorId: 'amber', color, ink: '#332817' }
}

function snapshot(): ArcadeSnapshot {
  const players = [1, 2, 3].map((number, index) => ({
    id: `p${number}`,
    name: `玩家${number}`,
    seat: index,
    connected: true,
  }))
  const market = commodityDefinitions.map((item, index) => ({
    ...item,
    value: [5, 10, 20, 0][index],
    trackIndex: [1, 2, 3, 0][index],
    supplyCount: 3,
  }))
  const shareCards = commodityDefinitions.slice(0, 2).map((item, index) => ({
    id: `share-${item.id}-0${index + 1}`,
    commodityId: item.id,
    label: item.label,
    labelEn: item.labelEn,
    code: item.code,
    color: item.color,
    pattern: item.pattern,
    marketValue: market[index].value,
    mortgaged: index === 1,
  }))
  const gamePlayers = players.map((player, index) => ({
    ...player,
    avatarUrl: null,
    forfeited: false,
    cash: 29 + index,
    colorId: ['amber', 'coral', 'teal'][index],
    color: ['#d6a341', '#cb6252', '#4c9a91'][index],
    ink: '#281f17',
    workerCount: 4,
    availableWorkerCount: 3,
    shareCount: 2,
    mortgagedShareCount: index === 0 ? 1 : 0,
    passedPlacement: false,
    isHarborMaster: index === 0,
    isCurrent: index === 0,
    finalWealth: null,
    rank: null,
    ...(index === 0 ? { shareCards } : {}),
  }))
  const punts = commodityDefinitions.slice(0, 3).map((commodity, index) => ({
    id: `punt-${index + 1}`,
    number: index + 1,
    cargoId: commodity.id,
    cargo: commodity,
    laneId: `lane-${index + 1}`,
    position: [2, 6, 12][index],
    status: 'sailing',
    lastDie: index + 2,
    destinationSlot: null,
    plundered: false,
    displacedPlayerIds: [],
    occupants: index === 0 ? [worker('w1', 'p2', '#cb6252')] : [],
    cargoSlots: commodity.costs.map((cost, slotIndex) => ({
      index: slotIndex,
      cost,
      occupant: index === 0 && slotIndex === 0 ? worker('w1', 'p2', '#cb6252') : null,
    })),
  }))
  const destinations = (kind: 'port' | 'shipyard') => ['A', 'B', 'C'].map((slot, index) => ({
    id: `${kind}-${slot}`,
    slot,
    kind,
    cost: [4, 3, 2][index],
    payout: [6, 8, 15][index],
    bettor: null,
    puntId: null,
  }))
  return {
    revision: 1,
    roomCode: 'MNL1',
    gameKey: 'plugin-manila',
    gameName: '马尼拉',
    phase: 'playing',
    options: {},
    hostId: 'p1',
    self: { id: 'p1', name: '玩家1', seat: 0 },
    players,
    requiredPlayers: 5,
    minimumPlayers: 3,
    roundNumber: 1,
    winner: null,
    winnerPlayerIds: [],
    winReason: null,
    actions: {
      canStart: false,
      canRestart: false,
      canAct: true,
      canKickPlayers: false,
      canDissolve: false,
      canEditRules: false,
      canRequestUndo: false,
      canRequestDraw: false,
      canResolveRequest: false,
    },
    rematchReadyPlayerIds: [],
    request: null,
    chat: { maxLength: 300, messages: [] },
    game: {
      schemaVersion: 1,
      modelVersion: '1.0.0',
      ruleset: 'zoch-2005-base',
      rulesVariant: 'base',
      enhancedPirates: false,
      sceneId: 'placement.choose',
      stage: 'placement',
      stageLabel: '部署助手',
      voyageNumber: 1,
      roomPhase: 'playing',
      currentPlayerId: 'p1',
      harborMasterId: 'p1',
      turnOrder: players.map(player => player.id),
      players: gamePlayers,
      market,
      marketTrack: [0, 5, 10, 20, 30],
      lanes: [1, 2, 3].map(number => ({ id: `lane-${number}`, number, marks: Array.from({ length: 14 }, (_, index) => index), puntId: `punt-${number}` })),
      punts,
      destinations: { port: destinations('port'), shipyard: destinations('shipyard') },
      specialPositions: [
        { id: 'pirate-captain', kind: 'pirate', label: '海盗船长', cost: 5, occupant: null },
        { id: 'pirate-crew', kind: 'pirate', label: '海盗船员', cost: 5, occupant: null },
        { id: 'pilot-small', kind: 'pilot', label: '小引航员', cost: 2, occupant: null },
        { id: 'pilot-large', kind: 'pilot', label: '大引航员', cost: 5, occupant: null },
        { id: 'insurance', kind: 'insurance', label: '保险代理', cost: 0, occupant: null },
      ],
      auction: null,
      schedule: [
        { index: 0, token: 'placement', state: 'current' },
        { index: 1, token: 'placement', state: 'upcoming' },
        { index: 2, token: 'movement', state: 'upcoming' },
      ],
      placementRound: 1,
      movementRound: 0,
      dice: {},
      lastMoveOrder: [],
      pirateBoardQueue: [],
      pirateRouteQueue: [],
      legalActions: {
        canResign: true,
        loanableShareIds: [shareCards[0].id],
        repayableShareIds: [shareCards[1].id],
        placementTargets: [
          { targetId: 'punt-1', kind: 'punt', label: '人参货船', cost: 2, slotIndex: 1, affordable: true, blindAllowed: false, payable: 2 },
          { targetId: 'port-A', kind: 'port', label: '港口 A', cost: 4, slotIndex: 0, payout: 6, affordable: true, blindAllowed: false, payable: 4 },
          { targetId: 'pirate-captain', kind: 'pirate', label: '海盗船长', cost: 5, affordable: true, blindAllowed: false, payable: 5 },
        ],
        canPassPlacement: true,
      },
      animation: null,
      events: [{ id: 1, type: 'game_start', message: '三位玩家进入港口', details: {} }],
      settlement: null,
      rankings: [],
      winnerPlayerIds: [],
      winReason: null,
      own: { playerId: 'p1', cash: 29, availableWorkerIds: ['w1', 'w2', 'w3'], shareCards },
      rules: {},
    },
  } as unknown as ArcadeSnapshot
}

describe('Manila immersive tabletop', () => {
  beforeEach(() => actionMock.mockClear())
  afterEach(() => vi.useRealTimers())

  it('renders every stable modeled zone without moving them between stages', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    expect(wrapper.findAll('.player-ledger')).toHaveLength(3)
    expect(wrapper.findAll('.market-row')).toHaveLength(4)
    expect(wrapper.findAll('.shipping-lane')).toHaveLength(3)
    expect(wrapper.findAll('.track-ticks span')).toHaveLength(42)
    expect(wrapper.findAll('.punt-model')).toHaveLength(3)
    expect(wrapper.findAll('.destination-slot')).toHaveLength(6)
    expect(wrapper.findAll('.special-position')).toHaveLength(5)
    expect(wrapper.findAll('.share-card')).toHaveLength(2)
  })

  it('submits visual placement targets with the current voyage stale guard', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    await wrapper.get('.place-on-punt').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('place_accomplice', {
      voyageNumber: 1,
      targetId: 'punt-1',
    })
  })

  it('models strict auction bidding and pass as separate actions', async () => {
    const value = snapshot()
    const game = value.game as Record<string, any>
    game.stage = 'auction'
    game.stageLabel = '港务长拍卖'
    game.sceneId = 'auction.bid'
    game.auction = { openerId: 'p1', currentPlayerId: 'p1', activePlayerIds: ['p1', 'p2', 'p3'], passedPlayerIds: [], leaderId: null, currentBid: 0 }
    game.legalActions = { canBid: true, minimumBid: 1, maximumBid: 53, canPassAuction: true, loanableShareIds: [], repayableShareIds: [] }
    const wrapper = mount(GameView, { props: { snapshot: value } })
    await wrapper.get('.auction-action input').setValue('7')
    await wrapper.get('.auction-action .primary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('bid', { voyageNumber: 1, amount: 7 })
    actionMock.mockClear()
    await wrapper.get('.auction-action .secondary-action').trigger('click')
    await flushPromises()
    expect(actionMock).toHaveBeenCalledWith('pass_auction', { voyageNumber: 1 })
  })

  it('keeps opponent share identities out of the player ledgers and models mortgage state', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    expect(wrapper.findAll('.player-ledger .share-card')).toHaveLength(0)
    expect(wrapper.findAll('.mortgage-band')).toHaveLength(1)
    expect(wrapper.text()).toContain('已抵押 12')
    expect(viewSource).toContain('legal.loanableShareIds')
    expect(viewSource).toContain('legal.repayableShareIds')
  })

  it('opens an accessible base-rule drawer that explicitly excludes displacement pirates', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    await wrapper.get('[aria-label="打开规则摘要"]').trigger('click')
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(dialog.text()).toContain('不启用满船逐客增强变体')
    expect(dialog.text()).toContain('现金 + 所有份额市值')
  })

  it.each([
    ['dice_roll', '.motion-dice'],
    ['punt_move', '.motion-punt'],
    ['worker_move', '.motion-worker'],
    ['pirate_board', '.motion-pirate'],
    ['pilot_move', '.motion-compass'],
    ['share_deal', '.motion-share'],
    ['settlement', '.motion-coins'],
  ])('maps %s server snapshots to a bounded visual cue', async (kind, selector) => {
    vi.useFakeTimers()
    const first = snapshot()
    const wrapper = mount(GameView, { props: { snapshot: first } })
    const next = snapshot()
    ;(next.game as Record<string, any>).animation = { id: 2, kind }
    await wrapper.setProps({ snapshot: next })
    expect(wrapper.find(selector).exists()).toBe(true)
    vi.advanceTimersByTime(1300)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.motion-layer').exists()).toBe(false)
  })

  it('renders atomic settlement entries including bank coverage', () => {
    const value = snapshot()
    const game = value.game as Record<string, any>
    game.stage = 'voyage_summary'
    game.stageLabel = '航行结算'
    game.sceneId = 'voyage.summary'
    game.settlement = {
      voyageNumber: 1,
      entries: [{ entryId: 'V1-E01', fromId: 'p1', toId: 'p2', amount: 15, reason: 'insured_repair', puntId: 'punt-1', slotId: 'shipyard-C', bankCoverage: 3, payerAmount: 12, selfInsurance: false }],
      deliveredCommodityIds: ['ginseng'], damagedPuntIds: ['punt-1'], plunderedPuntIds: [], cashBefore: {}, cashAfter: {}, marketBefore: {}, marketAfter: {},
    }
    game.legalActions = { canStartNextVoyage: true, loanableShareIds: [], repayableShareIds: [] }
    const wrapper = mount(GameView, { props: { snapshot: value } })
    expect(wrapper.get('.settlement-entries').text()).toContain('银行补 3')
    expect(wrapper.get('.settlement-action').text()).toContain('人参')
  })

  it('defines near-viewport desktop geometry, narrow-screen containment and reduced motion', () => {
    expect(viewSource).toContain("import './layout.css'")
    expect(viewSource).toContain("import './models.css'")
    expect(viewSource).toContain("import './responsive.css'")
    expect(viewSource).toContain("import './motion.css'")
    expect(viewSource).toContain('class="motion-layer"')
    expect(viewSource).toContain('class="scene-grid"')
  })
})
