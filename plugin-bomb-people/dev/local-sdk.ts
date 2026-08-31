import {
  defineComponent,
  h,
  onBeforeUnmount,
  onMounted,
  ref,
  type Ref,
} from 'vue'


export type ArcadePhase = 'lobby' | 'playing' | 'finished' | string

export interface ArcadeSnapshot {
  revision: number
  roomCode: string
  gameKey: string
  gameName: string
  phase: ArcadePhase
  hostId: string
  self: { id: string; name: string; seat: number }
  viewer?: { mode: 'player' | 'spectator'; id: string; name: string; targetPlayerId: string }
  players: Array<{ id: string; name: string; seat: number; connected: boolean; isHost: boolean }>
  roundNumber: number
  winner: string | null
  winnerPlayerIds: string[]
  winReason: string | null
  actions: {
    canStart: boolean
    canRestart: boolean
    canAct: boolean
    [key: string]: boolean | undefined
  }
  game: Record<string, unknown>
  [key: string]: unknown
}

export interface PluginGameActions {
  action: (actionName: string, payload?: Record<string, unknown>) => Promise<boolean>
  rapidAction: (actionName: string, payload?: Record<string, unknown>) => Promise<boolean>
  restart: () => Promise<boolean>
  publishSpectatorFrame: (sequence: number, state: Record<string, unknown>) => boolean
}

let installedActions: PluginGameActions | null = null

export function installLocalGameActions(actions: PluginGameActions) {
  installedActions = actions
}

export function usePluginGameActions(): PluginGameActions {
  if (!installedActions) throw new Error('本地测试动作尚未初始化')
  return installedActions
}

export const PluginButton = defineComponent({
  name: 'PluginButton',
  inheritAttrs: false,
  props: {
    variant: { type: String, default: 'secondary' },
    type: { type: String, default: 'button' },
    block: { type: Boolean, default: false },
    compact: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  setup(props, { attrs, slots }) {
    return () => h('button', {
      ...attrs,
      type: props.type as 'button' | 'submit' | 'reset',
      disabled: props.disabled,
      class: [
        'local-plugin-button',
        `local-plugin-button--${props.variant}`,
        { block: props.block, compact: props.compact },
        attrs.class,
      ],
    }, slots.default?.())
  },
})

export const PluginIconButton = defineComponent({
  name: 'PluginIconButton',
  inheritAttrs: false,
  props: {
    label: { type: String, required: true },
    type: { type: String, default: 'button' },
    compact: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  setup(props, { attrs, slots }) {
    return () => h('button', {
      ...attrs,
      type: props.type as 'button' | 'submit' | 'reset',
      disabled: props.disabled,
      'aria-label': props.label,
      title: props.label,
      class: ['local-plugin-icon-button', { compact: props.compact }, attrs.class],
    }, slots.default?.())
  },
})

export const PluginModal = defineComponent({
  name: 'PluginModal',
  props: {
    title: { type: String, default: '' },
    description: { type: String, default: '' },
    size: { type: String, default: 'small' },
    closeOnBackdrop: { type: Boolean, default: true },
  },
  emits: ['close'],
  setup(props, { emit, slots }) {
    function backdrop(event: MouseEvent) {
      if (props.closeOnBackdrop && event.target === event.currentTarget) emit('close')
    }
    return () => h('div', {
      class: 'local-modal-backdrop',
      role: 'presentation',
      onClick: backdrop,
    }, [
      h('article', {
        class: ['local-modal-card', `local-modal-card--${props.size}`],
        role: 'dialog',
        'aria-modal': 'true',
        'aria-label': props.title || '弹窗',
      }, [
        h('header', { class: 'local-modal-header' }, [
          h('div', [
            h('h2', props.title),
            props.description ? h('p', props.description) : null,
          ]),
          h('button', {
            type: 'button',
            class: 'local-modal-close',
            'aria-label': '关闭弹窗',
            onClick: () => emit('close'),
          }, '×'),
        ]),
        h('div', { class: 'local-modal-content' }, slots.default?.()),
      ]),
    ])
  },
})

export function usePluginFullscreen(target: Ref<HTMLElement | null>) {
  const isFullscreen = ref(false)
  const isSupported = ref(false)

  function sync() {
    isFullscreen.value = document.fullscreenElement === target.value
  }

  async function toggle() {
    if (!target.value || !isSupported.value) return
    if (document.fullscreenElement === target.value) await document.exitFullscreen()
    else await target.value.requestFullscreen()
  }

  onMounted(() => {
    isSupported.value = Boolean(document.fullscreenEnabled && target.value?.requestFullscreen)
    document.addEventListener('fullscreenchange', sync)
    sync()
  })
  onBeforeUnmount(() => document.removeEventListener('fullscreenchange', sync))

  return { isFullscreen, isSupported, toggle }
}
