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
        {
          action: 'jump',
          lane: 'center',
          obstacle: 'ground',
          equation: '3 + 5 = 10 - 2',
        },
        {
          action: 'left',
          lane: 'left',
          obstacle: null,
          equation: '4 + 4 = 11 - 2',
        },
      ],
      branchCount: 2,
      blockedActions: ['slide', 'right'],
      lastAction: null,
      lastPoints: 0,
      levelUp: false,
      endReason: null,
      correctAction: null,
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

  it('renders three bridge lanes, a two-way fork and four stable controls', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(wrapper.findAll('.route-lane')).toHaveLength(3)
    expect(wrapper.findAll('.lane-gate')).toHaveLength(2)
    expect(wrapper.findAll('.direction-button')).toHaveLength(4)
    expect(wrapper.get('[data-lane="center"]').text()).toContain('3 + 5 = 10 - 2')
    expect(wrapper.get('[data-action="left"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-control="slide"]').classes()).toContain('direction-button--blocked')
    expect(wrapper.find('[data-obstacle="ground"]').exists()).toBe(true)

    wrapper.unmount()
  })

  it('renders all three branches when the server publishes a three-way section', () => {
    const wrapper = mount(GameView, {
      props: {
        snapshot: snapshot('playing', {
          branchCount: 3,
          options: [
            { action: 'left', lane: 'left', obstacle: null, equation: '2 + 2 = 7 - 3' },
            { action: 'slide', lane: 'center', obstacle: 'overhead', equation: '3 + 4 = 10 - 2' },
            { action: 'right', lane: 'right', obstacle: null, equation: '5 + 5 = 12 - 2' },
          ],
          blockedActions: ['jump'],
        }),
      },
    })

    expect(wrapper.findAll('.lane-gate')).toHaveLength(3)
    expect(wrapper.get('.section-radar').text()).toContain('3 路分叉')
    expect(wrapper.find('[data-obstacle="overhead"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('submits only the question id and runner action', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('[data-action="jump"]').trigger('click')
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledWith('choose', {
      questionId: 1,
      runnerAction: 'jump',
    })
    wrapper.unmount()
  })

  it('maps WASD and arrow keys to available actions and ignores a blocked key', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w' }))
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('choose', {
      questionId: 1,
      runnerAction: 'jump',
    })

    pluginActions.action.mockClear()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }))
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledWith('choose', {
      questionId: 1,
      runnerAction: 'left',
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
      props: { snapshot: snapshot('playing', { remainingMs: 40 }) },
    })

    await vi.advanceTimersByTimeAsync(150)
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledTimes(1)
    expect(pluginActions.action).toHaveBeenCalledWith('timeout', { questionId: 1 })
    wrapper.unmount()
  })

  it('sends timeout again when a restarted run reuses question id one', async () => {
    vi.useFakeTimers()
    const wrapper = mount(GameView, {
      props: { snapshot: snapshot('playing', { remainingMs: 40 }) },
    })

    await vi.advanceTimersByTimeAsync(150)
    await flushPromises()
    expect(pluginActions.action).toHaveBeenCalledTimes(1)

    await wrapper.setProps({
      snapshot: snapshot('finished', {
        remainingMs: 0,
        endReason: 'timeout',
        correctAction: 'jump',
        result: 'failed',
      }),
    })
    await wrapper.get('.runner-result .solo-result-restart').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()

    await wrapper.setProps({
      snapshot: snapshot('playing', { questionId: 1, remainingMs: 40 }),
    })
    await vi.advanceTimersByTimeAsync(150)
    await flushPromises()

    expect(pluginActions.action).toHaveBeenCalledTimes(2)
    expect(pluginActions.action).toHaveBeenLastCalledWith('timeout', { questionId: 1 })
    wrapper.unmount()
  })

  it.each([
    ['left', 'runner-model--left', 'bridge-world--left'],
    ['jump', 'runner-model--jump', 'bridge-world--jump'],
    ['slide', 'runner-model--slide', 'bridge-world--slide'],
    ['right', 'runner-model--right', 'bridge-world--right'],
  ] as const)('plays the confirmed %s animation after the server advances', async (
    action,
    runnerClass,
    worldClass,
  ) => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.setProps({
      snapshot: snapshot('playing', {
        questionId: 2,
        correctAnswers: 1,
        streakInLevel: 1,
        distanceMeters: 24,
        lastAction: action,
        lastPoints: 375,
      }),
    })

    expect(wrapper.get('.runner-model').classes()).toContain(runnerClass)
    expect(wrapper.get('.bridge-world').classes()).toContain(worldClass)
    wrapper.unmount()
  })

  it('reveals the correct action after failure and restarts from the result card', async () => {
    const failed = snapshot('finished', {
      score: 1480,
      correctAnswers: 6,
      distanceMeters: 144,
      lastAction: 'left',
      endReason: 'wrong',
      correctAction: 'jump',
      elapsedMs: 12_400,
      averageResponseMs: 1_620,
      result: 'failed',
    })
    const wrapper = mount(GameView, { props: { snapshot: failed } })

    expect(wrapper.get('[data-action="jump"]').classes()).toContain('lane-gate--correct')
    expect(wrapper.get('[data-action="left"]').classes()).toContain('lane-gate--wrong')
    expect(wrapper.get('.runner-result').text()).toContain('这次路线算错了')
    expect(wrapper.get('.solo-result-score').text()).toContain('144 米')
    expect(wrapper.get('.runner-result').text()).toContain('技巧得分')

    await wrapper.get('.runner-result .solo-result-restart').trigger('click')
    await flushPromises()
    expect(pluginActions.restart).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('keeps the host viewport and standard return control available', () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    expect(document.documentElement.classList.contains('math-runner-viewport-lock')).toBe(false)
    expect(document.body.classList.contains('math-runner-viewport-lock')).toBe(false)
    expect(wrapper.get('.math-runner').element.parentElement).not.toBe(document.body)
    wrapper.unmount()
  })

  it('opens the complete in-game rule guide', async () => {
    const wrapper = mount(GameView, { props: { snapshot: snapshot() } })

    await wrapper.get('[aria-label="查看算途疾行规则"]').trigger('click')

    expect(document.body.textContent).toContain('连续 10 题升一级')
    expect(document.body.textContent).toContain('W 跳跃')
    expect(document.body.textContent).toContain('排行榜主值')
    wrapper.unmount()
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
    wrapper.unmount()
  })
})
