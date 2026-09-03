import { flushPromises, mount } from '@vue/test-utils'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'
import type { EuropeGameView, EuropePlayerView, TrainCardModel } from './types'

const pluginActions = vi.hoisted(() => ({
  action: vi.fn(async () => true),
  rapidAction: vi.fn(async () => true),
  restart: vi.fn(async () => true),
  publishSpectatorFrame: vi.fn(() => true),
}))

vi.mock('@game-hall/plugin-sdk', async (importOriginal) => ({
  ...await importOriginal<typeof import('@game-hall/plugin-sdk')>(),
  usePluginGameActions: () => pluginActions,
}))

const accents: Record<string, string> = {
  white: '#e6e1d5', blue: '#3985c3', red: '#c4544d', green: '#549263',
  black: '#454b52', yellow: '#d8b22d', orange: '#dc812e', purple: '#8562a9', locomotive: '#9e799e',
}

function card(id: string, color: TrainCardModel['color']): TrainCardModel {
  return {
    id,
    typeId: `train-${color}`,
    color,
    label: color === 'locomotive' ? '彩虹机车' : `${color} 车票`,
    visual: { accent: accents[color], pattern: color === 'locomotive' ? 'spectrum' : 'grid', accessibilityCode: color.slice(0, 2).toUpperCase() },
  }
}

function player(index: number): EuropePlayerView {
  const colors: EuropePlayerView['color'][] = ['ruby', 'sapphire', 'jade', 'amber', 'violet']
  return {
    id: `p${index}`,
    name: `玩家${index}`,
    seat: index - 1,
    color: colors[index - 1],
    status: 'active',
    score: index * 3,
    trainsRemaining: 45 - index,
    stationsRemaining: 3,
    trainHandCount: 4,
    destinationTicketCount: 2,
    initialTicketChoiceSubmitted: true,
    finalStationAssignmentSubmitted: false,
  }
}

function baseGame(count = 3, overrides: Partial<EuropeGameView> = {}): EuropeGameView {
  const players = Array.from({ length: count }, (_, index) => player(index + 1))
  return {
    schemaVersion: 1,
    gameKey: 'ticket-to-ride-europe-base',
    sceneId: 'turn.choose-action',
    phase: 'turn_idle',
    rules: {
      playerCount: count,
      startingTrains: 45,
      startingStations: 3,
      europeanExpressPoints: 10,
      unusedStationPoints: 4,
      doubleRoutesRestricted: count <= 3,
    },
    turnOrder: players.map(item => item.id),
    currentPlayerId: 'p1',
    turnNumber: 7,
    players,
    market: [card('market-blue', 'blue'), card('market-red', 'red'), card('market-green', 'green'), card('market-loco', 'locomotive'), card('market-yellow', 'yellow')],
    trainDeckCount: 70,
    trainDiscardCount: 4,
    destinationDeckCount: 35,
    claimedRoutes: [{ routeId: 'route-bruxelles-paris-a', ownerPlayerId: 'p2' }],
    stationPlacements: [],
    hand: [card('white-1', 'white'), card('white-2', 'white'), card('blue-1', 'blue'), card('loco-1', 'locomotive')],
    destinationTickets: [{
      id: 'ticket-london-wien', category: 'regular', fromCityId: 'london', toCityId: 'wien',
      fromLabel: '伦敦', toLabel: '维也纳', points: 10, completed: false,
    }],
    initialTicketOptions: [],
    pendingTicketChoice: null,
    pendingTunnel: null,
    ownTunnelPayment: null,
    legalClaimRouteIds: ['route-amsterdam-frankfurt'],
    stationEligibleCityIds: ['amsterdam', 'berlin'],
    finalRound: null,
    actions: ['draw_train_card', 'claim_route', 'draw_destination_tickets', 'build_station'],
    latestEvent: null,
    history: [{ sequence: 1, type: 'setup_complete', playerId: 'p1', message: '游戏开始' }],
    result: null,
    ...overrides,
  }
}

function snapshot(game: EuropeGameView, viewer: 'player' | 'spectator' = 'player', phase: 'playing' | 'finished' = 'playing'): ArcadeSnapshot {
  return {
    revision: 1,
    phase,
    roundNumber: game.turnNumber,
    self: { id: 'p1', name: '玩家1' },
    viewer: { mode: viewer },
    players: game.players.map(item => ({ id: item.id, name: item.name })),
    actions: { canAct: true, canRestart: false },
    game,
  } as unknown as ArcadeSnapshot
}

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll('button').find(item => item.text().includes(text))
  if (!button) throw new Error(`Button not found: ${text}`)
  return button
}

describe('Europe rail immersive game view', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.useRealTimers())

  it.each([3, 4, 5])('renders the full 47-city/101-route board for %i players', (count) => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot(baseGame(count)) }, attachTo: document.body })
    expect(wrapper.findAll('g.city')).toHaveLength(47)
    expect(wrapper.findAll('g.route')).toHaveLength(101)
    expect(wrapper.findAll('.player-token')).toHaveLength(count)
    expect(wrapper.findAll('.market-cards .train-card')).toHaveLength(5)
    expect(wrapper.findAll('.hand-cards .train-card')).toHaveLength(4)
    wrapper.unmount()
  })

  it('submits the exact initial ticket selection payload', async () => {
    const options = [
      { id: 'long-1', category: 'long' as const, fromCityId: 'lisboa', toCityId: 'moskva', fromLabel: '里斯本', toLabel: '莫斯科', points: 20, completed: false },
      { id: 'regular-1', category: 'regular' as const, fromCityId: 'paris', toCityId: 'wien', fromLabel: '巴黎', toLabel: '维也纳', points: 8, completed: false },
      { id: 'regular-2', category: 'regular' as const, fromCityId: 'roma', toCityId: 'berlin', fromLabel: '罗马', toLabel: '柏林', points: 9, completed: false },
      { id: 'regular-3', category: 'regular' as const, fromCityId: 'madrid', toCityId: 'zurich', fromLabel: '马德里', toLabel: '苏黎世', points: 7, completed: false },
    ]
    const game = baseGame(3, { phase: 'setup_ticket_selection', initialTicketOptions: options, actions: ['keep_initial_tickets'] })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game) }, global: { stubs: { teleport: true } } })
    expect(wrapper.findAll('[data-testid="ticket-choice"] .is-selected')).toHaveLength(2)
    await buttonByText(wrapper, '确认保留').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('keep_initial_tickets', { ticketIds: ['long-1', 'regular-1'] })
    wrapper.unmount()
  })

  it('draws blind and public train cards with server-compatible payloads', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot(baseGame()) } })
    await buttonByText(wrapper, '盲抽车票').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('draw_train_card', { source: 'deck' })
    await wrapper.find('.market-cards .train-card').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenLastCalledWith('draw_train_card', { source: 'market', cardId: 'market-blue' })
    wrapper.unmount()
  })

  it('selects a route and pays the exact matching cards', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot(baseGame()) } })
    await buttonByText(wrapper, '占用轨道').trigger('click')
    await wrapper.get('[data-route-id="route-amsterdam-frankfurt"]').trigger('click')
    const hand = wrapper.findAll('.hand-cards .train-card')
    await hand[0].trigger('click')
    await hand[1].trigger('click')
    await buttonByText(wrapper, '确认占用轨道').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('claim_route', {
      routeId: 'route-amsterdam-frankfurt', cardIds: ['white-1', 'white-2'], declaredColor: 'white',
    })
    wrapper.unmount()
  })

  it('builds the first station with one same-color card', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot(baseGame()) } })
    await buttonByText(wrapper, '建火车站').trigger('click')
    await wrapper.get('[data-city-id="amsterdam"]').trigger('click')
    await wrapper.find('.hand-cards .train-card').trigger('click')
    await buttonByText(wrapper, '确认建造车站').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('build_station', { cityId: 'amsterdam', cardIds: ['white-1'] })
    wrapper.unmount()
  })

  it('handles tunnel extra payment and decline controls', async () => {
    const tunnel = {
      actorPlayerId: 'p1', routeId: 'route-paris-zurich', declaredColor: 'blue' as const,
      revealedCards: [card('risk-blue', 'blue'), card('risk-red', 'red'), card('risk-loco', 'locomotive')], extraCost: 2, status: 'awaiting_payment',
    }
    const ownTunnelPayment = {
      routeId: tunnel.routeId, declaredColor: 'blue' as const, initialCards: [card('spent-blue', 'blue')],
      extraCost: 2, paymentMode: 'declared-color' as const,
    }
    const game = baseGame(3, { phase: 'tunnel_payment', hand: [card('blue-a', 'blue'), card('red-a', 'red'), card('loco-a', 'locomotive')], pendingTunnel: tunnel, ownTunnelPayment, actions: ['pay_tunnel_extra', 'decline_tunnel'] })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game) }, global: { stubs: { teleport: true } } })
    const hand = wrapper.findAll('.hand-cards .train-card')
    expect(hand[1].attributes('disabled')).toBeDefined()
    await hand[0].trigger('click')
    await hand[2].trigger('click')
    await buttonByText(wrapper, '补付并通车').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('pay_tunnel_extra', { cardIds: ['blue-a', 'loco-a'] })
    vi.clearAllMocks()
    await buttonByText(wrapper, '放弃并收回初始牌').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('decline_tunnel', undefined)
    wrapper.unmount()
  })

  it('submits all station borrow decisions, including a deliberate no-borrow', async () => {
    const game = baseGame(4, {
      phase: 'final_station_assignment', actions: ['assign_station_routes'],
      stationPlacements: [{ cityId: 'paris', ownerPlayerId: 'p1', borrowedRouteId: null }],
      claimedRoutes: [{ routeId: 'route-bruxelles-paris-a', ownerPlayerId: 'p2' }],
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game) }, global: { stubs: { teleport: true } } })
    const select = wrapper.get('[data-testid="station-assignments"] select')
    await select.setValue('route-bruxelles-paris-a')
    await buttonByText(wrapper, '确认并进入结算').trigger('click')
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('assign_station_routes', { assignments: { paris: 'route-bruxelles-paris-a' } })
    wrapper.unmount()
  })

  it('renders co-winner settlement and every scoring component', () => {
    const game = baseGame(3)
    const resultPlayers = game.players.map((item, index) => ({
      playerId: item.id, status: 'active', routePoints: 30 - index, destinationPoints: 12, stationPoints: 8,
      longestPathPoints: index < 2 ? 10 : 0, total: index < 2 ? 60 : 45, completedTicketCount: 2,
      completedTicketIds: ['t1'], failedTicketIds: [], stationsUsed: 1, longestPathLength: index < 2 ? 21 : 14,
      europeanExpress: index < 2, rank: index < 2 ? 1 : 3,
    }))
    Object.assign(game, {
      phase: 'finished', actions: [], result: {
        reason: 'score', winnerPlayerIds: ['p1', 'p2'], ranking: ['p1', 'p2', 'p3'],
        europeanExpressPlayerIds: ['p1', 'p2'], longestPathLength: 21, players: resultPlayers,
      },
    })
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game, 'player', 'finished') } })
    expect(wrapper.get('[data-testid="result-overlay"]').text()).toContain('并列冠军')
    expect(wrapper.text()).toContain('线路 30 · 任务 12 · 车站 8')
    expect(wrapper.text()).toContain('欧洲快车 +10')
    wrapper.unmount()
  })

  it('keeps spectator mode read-only and hides all private information', () => {
    const game = baseGame()
    game.hand = []
    game.destinationTickets = []
    game.actions = []
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game, 'spectator') } })
    expect(wrapper.find('[data-testid="hand-tray"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('私密手牌和任务已隐藏')
    expect(wrapper.findAll('[data-testid="action-dock"] button').every(button => button.attributes('disabled') !== undefined)).toBe(true)
    wrapper.unmount()
  })

  it.each([
    ['train_card_drawn', '盲抽车票'], ['route_claimed', '铁路贯通'], ['tunnel_cards_revealed', '隧道勘探'],
    ['station_built', '中央车站落成'], ['destination_tickets_drawn', '新任务抵达'],
    ['final_round_triggered', '最后一轮'], ['game_scored', '欧洲快车结算'],
  ])('plays the dedicated %s visual effect', async (type, title) => {
    vi.useFakeTimers()
    const game = baseGame()
    const wrapper = mount(GameView, { props: { snapshot: snapshot(game) } })
    const next = baseGame(3, { latestEvent: {
      sequence: 9, type, playerId: 'p1', source: 'deck', message: '动画测试', points: 4, extraCost: 1,
      count: 3, revealedCards: [card('risk-a', 'blue'), card('risk-b', 'red'), card('risk-c', 'locomotive')],
    } })
    await wrapper.setProps({ snapshot: snapshot(next) })
    await vi.advanceTimersByTimeAsync(20)
    expect(wrapper.get(`[data-effect="${type}"]`).text()).toContain(title)
    wrapper.unmount()
  })
})
