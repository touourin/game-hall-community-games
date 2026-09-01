import { flushPromises, mount } from '@vue/test-utils'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from './GameView.vue'

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

function snapshot(
  phase: 'playing' | 'finished' = 'playing',
  gameOverrides: Record<string, unknown> = {},
): ArcadeSnapshot {
  return {
    revision: 1,
    phase,
    roundNumber: 1,
    actions: {
      canAct: phase === 'playing',
      canRestart: phase === 'finished',
    },
    game: {
      level: 1,
      maxLevel: 10,
      correctAnswers: 0,
      totalQuestions: 100,
      streakInLevel: 0,
      questionsPerLevel: 10,
      questionsToNextLevel: 10,
      score: 0,
      distanceMeters: 0,
      questionId: 1,
      timeLimitMs: 6500,
      remainingMs: phase === 'playing' ? 6000 : 0,
      options: [
        { direction: 'up', equation: '3 + 5 = 10 - 2' },
        { direction: 'left', equation: '4 + 4 = 11 - 2' },
      ],
      blockedDirections: ['down', 'right'],
      lastDirection: null,
      lastPoints: 0,
      levelUp: false,
      endReason: null,
      correctDirection: null,
      elapsedMs: 500,
      averageResponseMs: null,
      speed: {
        trackPeriodMs: 1500,
        runCycleMs: 720,
        speedLines: 4,
      },
      won: false,
      result: null,
      ...gameOverrides,
    },
  } as unknown as ArcadeSnapshot
}

describe('math runner plugin view', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders four stable direction slots and only enables open routes', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.findAll('.question-gate')).toHaveLength(4)
    expect(wrapper.findAll('.direction-button')).toHaveLength(4)
    expect(wrapper.get('[data-direction="up"]').text()).toContain('3 + 5 = 10 - 2')
    expect(wrapper.get('[data-direction="left"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-direction="down"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-control="right"]').classes()).toContain('direction-button--blocked')

    wrapper.unmount()
  })

  it('submits only the question id and clicked direction', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('[data-direction="up"]').trigger('click')
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledWith('choose', {
      questionId: 1,
      direction: 'up',
    })
    wrapper.unmount()
  })

  it('maps WASD to open routes and ignores a blocked key', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }))
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('choose', {
      questionId: 1,
      direction: 'left',
    })

    pluginActions.action.mockClear()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's' }))
    await flushPromises()
    expect(pluginActions.action).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('sends one timeout action when the local display reaches zero', async () => {
    vi.useFakeTimers()
    const wrapper = mount(GameView, {
      props: {
        snapshot: snapshot('playing', { remainingMs: 40 }),
      },
    })

    await vi.advanceTimersByTimeAsync(150)
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledTimes(1)
    expect(pluginActions.action).toHaveBeenCalledWith('timeout', { questionId: 1 })
    wrapper.unmount()
  })

  it('plays a confirmed turn only after the server advances the question', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })
    expect(wrapper.find('.runner-model--turn-left').exists()).toBe(false)

    await wrapper.setProps({
      snapshot: snapshot('playing', {
        questionId: 2,
        correctAnswers: 1,
        streakInLevel: 1,
        distanceMeters: 24,
        lastDirection: 'left',
        lastPoints: 375,
      }),
    })

    expect(wrapper.get('.runner-model').classes()).toContain('runner-model--turn-left')
    expect(wrapper.get('.track-world').classes()).toContain('track-world--turn-left')
    wrapper.unmount()
  })

  it('reveals the correct route after failure and restarts from the result card', async () => {
    const failed = snapshot('finished', {
      score: 1480,
      correctAnswers: 6,
      distanceMeters: 144,
      lastDirection: 'left',
      endReason: 'wrong',
      correctDirection: 'up',
      elapsedMs: 12_400,
      averageResponseMs: 1_620,
      result: 'failed',
    })
    const wrapper = mount(GameView, { props: { snapshot: failed } })

    expect(wrapper.get('[data-direction="up"]').classes()).toContain('question-gate--correct')
    expect(wrapper.get('[data-direction="left"]').classes()).toContain('question-gate--wrong')
    expect(wrapper.get('.runner-result').text()).toContain('这次方向算错了')
    expect(wrapper.get('.solo-result-score').text()).toContain('144 米')
    expect(wrapper.get('.runner-result').text()).toContain('技巧得分')
    expect(wrapper.get('.runner-result').text()).toContain('1,480')
    expect(wrapper.get('.leaderboard-note').text()).toContain('路程')

    await wrapper.get('.runner-result .solo-result-restart').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('opens the complete in-game rule guide', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('[aria-label="查看算途疾行规则"]').trigger('click')

    expect(document.body.textContent).toContain('连续 10 题升一级')
    expect(document.body.textContent).toContain('WASD')
    expect(document.body.textContent).toContain('排行榜主值')
    wrapper.unmount()
  })

  it('locks the browser viewport while the game is mounted', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(document.documentElement.classList.contains('math-runner-viewport-lock')).toBe(true)
    expect(document.body.classList.contains('math-runner-viewport-lock')).toBe(true)

    wrapper.unmount()
    expect(document.documentElement.classList.contains('math-runner-viewport-lock')).toBe(false)
    expect(document.body.classList.contains('math-runner-viewport-lock')).toBe(false)
  })

  it('settles a completed run with 2400 metres as the leaderboard value', () => {
    const completed = snapshot('finished', {
      level: 10,
      correctAnswers: 100,
      streakInLevel: 0,
      questionsToNextLevel: 0,
      score: 68_420,
      distanceMeters: 2400,
      endReason: 'completed',
      elapsedMs: 228_400,
      averageResponseMs: 1_684,
      result: 'completed',
      won: true,
    })
    const wrapper = mount(GameView, { props: { snapshot: completed } })

    expect(wrapper.get('.solo-result-score').text()).toContain('2,400 米')
    expect(wrapper.get('.runner-result').text()).toContain('十级赛道通关')
    expect(wrapper.get('.runner-result').text()).toContain('100 / 100')
    expect(wrapper.get('.runner-result').text()).toContain('68,420 分')
    expect(wrapper.get('.leaderboard-note').text()).toContain('历史最大值')
    wrapper.unmount()
  })
})
