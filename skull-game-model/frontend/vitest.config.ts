import vue from '../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'
import { fileURLToPath, URL } from 'node:url'

const fromConfig = (relativePath: string) => fileURLToPath(
  new URL(relativePath, import.meta.url),
)

export default {
  root: fromConfig('.'),
  cacheDir: fromConfig('../../../frontend/node_modules/.vite/skull-game-model'),
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fromConfig('../../../frontend/src/plugin-sdk/index.ts'),
      '@lucide/vue': fromConfig('../../../frontend/node_modules/@lucide/vue'),
      '@vue/test-utils': fromConfig('../../../frontend/node_modules/@vue/test-utils'),
      vue: fromConfig('../../../frontend/node_modules/vue'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['GameView.test.ts'],
  },
  server: {
    fs: {
      allow: [fromConfig('../../..')],
    },
  },
}
