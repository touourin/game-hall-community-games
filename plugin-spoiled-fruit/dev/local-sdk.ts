export {
  usePluginFullscreen,
  usePluginTheme,
} from '../../../frontend/src/plugin-sdk/index'
export type { ArcadeSnapshot } from '../../../frontend/src/plugin-sdk/index'
import type { PluginGameActions } from '../../../frontend/src/plugin-sdk/index'


let devActions: PluginGameActions = {
  action: async () => false,
  rapidAction: async () => false,
  restart: async () => false,
  publishSpectatorFrame: () => false,
}

export function setDevPluginActions(actions: PluginGameActions) {
  devActions = actions
}

export function usePluginGameActions(): PluginGameActions {
  return devActions
}
