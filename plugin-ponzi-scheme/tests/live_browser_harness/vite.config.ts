import vue from '../../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'
import { fileURLToPath, URL } from 'node:url'

const fromConfig = (relativePath: string) => fileURLToPath(
  new URL(relativePath, import.meta.url),
)

export default {
  root: fromConfig('.'),
  cacheDir: fromConfig('../../../../frontend/node_modules/.vite/ponzi-live-browser'),
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fromConfig('../../../../frontend/src/plugin-sdk/index.ts'),
      pinia: fromConfig('../../../../frontend/node_modules/pinia'),
      vue: fromConfig('../../../../frontend/node_modules/vue'),
    },
    dedupe: ['vue'],
  },
  server: {
    host: '127.0.0.1',
    port: 4183,
    strictPort: true,
    fs: { allow: [fromConfig('../../../..')] },
  },
}
