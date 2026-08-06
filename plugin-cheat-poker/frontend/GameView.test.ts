import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import GameView from './GameView.vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'

const snapshot = {
  phase: 'playing',
  self: { id: 'p1' },
  players: [
    { id: 'p1', name: '玩家一' },
    { id: 'p2', name: '玩家二' },
    { id: 'p3', name: '玩家三' },
    { id: 'p4', name: '玩家四' },
  ],
  game: {
    dealerPlayerId: 'p1',
    currentPlayerId: 'p1',
    stage: 'play',
    requiredRank: null,
    requiredRankLabel: null,
    rankOptions: ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2'].map((rank) => ({ rank, label: rank })),
    hand: [
      { id: 'spades-Q', rank: 'Q', suit: 'spades', suitLabel: '♠', label: 'Q', isJoker: false },
      { id: 'hearts-K', rank: 'K', suit: 'hearts', suitLabel: '♥', label: 'K', isJoker: false },
      { id: 'joker-small', rank: 'joker', suit: 'joker', suitLabel: '★', label: '小王', isJoker: true },
    ],
    cardCounts: { p1: 3, p2: 14, p3: 13, p4: 13 },
    activePlayerIds: ['p1', 'p2', 'p3', 'p4'],
    forfeitedPlayerIds: [],
    pileCount: 0,
    pileLimit: 15,
    pileLocked: false,
    archivedCount: 0,
    lastPlay: null,
    winnerTarget: 1,
    rankings: [],
    scores: {},
    history: [],
    canPlay: true,
    canAccept: false,
    canChallenge: false,
    isOpening: true,
    myRank: null,
  },
} as unknown as ArcadeSnapshot

describe('cheat poker plugin view', () => {
  it('selects up to three hidden cards and an opening claim', async () => {
    const wrapper = mount(GameView, {
      props: { snapshot },
      global: { plugins: [createPinia()] },
    })

    const dealerRow = wrapper.findAll('.players-panel li')[0]
    expect(dealerRow.findAll('.player-name small').map((item) => item.text())).toEqual([
      '3 张手牌',
      '庄家',
    ])
    expect(wrapper.findAll('.hand-card')).toHaveLength(3)
    const rankButtons = wrapper.findAll('.rank-grid button')
    expect(rankButtons).toHaveLength(13)
    expect(rankButtons.map((button) => button.text())).toEqual([
      '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2',
    ])
    await rankButtons[12].trigger('click')
    expect(rankButtons[12].attributes('aria-pressed')).toBe('true')
    expect(rankButtons[12].classes()).toContain('selected')
    await wrapper.findAll('.hand-card')[0].trigger('click')
    await wrapper.findAll('.hand-card')[1].trigger('click')

    expect(wrapper.findAll('.hand-card.selected')).toHaveLength(2)
    expect(wrapper.get('.play-button').text()).toContain('背面打出 2 张')
  })

  it('shows challenge and accept choices during the response window', () => {
    const challengeSnapshot = {
      ...snapshot,
      game: {
        ...(snapshot.game as object),
        currentPlayerId: 'p1',
        stage: 'challenge',
        requiredRank: 'K',
        requiredRankLabel: 'K',
        pileCount: 3,
        lastPlay: {
          playerId: 'p3',
          playerName: '玩家三',
          claimedRank: 'Q',
          claimedLabel: 'Q',
          count: 2,
        },
        canPlay: false,
        canAccept: true,
        canChallenge: true,
        isOpening: false,
      },
    } as unknown as ArcadeSnapshot
    const wrapper = mount(GameView, {
      props: { snapshot: challengeSnapshot },
      global: { plugins: [createPinia()] },
    })

    expect(wrapper.get('.challenge-button').text()).toContain('立即质疑')
    expect(wrapper.get('.accept-button').text()).toContain('相信并继续')
    expect(wrapper.text()).toContain('玩家三 声称打出 2 张 Q')
  })
})
