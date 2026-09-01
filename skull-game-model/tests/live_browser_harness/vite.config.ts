import vue from '../../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'
import { fileURLToPath, URL } from 'node:url'

const fromConfig = (relativePath: string) => fileURLToPath(
  new URL(relativePath, import.meta.url),
)

export default {
  root: fromConfig('.'),
  cacheDir: fromConfig('../../../../frontend/node_modules/.vite/skull-live-browser'),
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fromConfig('../../../../frontend/src/plugin-sdk/index.ts'),
      '@lucide/vue': fromConfig('../../../../frontend/node_modules/@lucide/vue'),
      pinia: fromConfig('../../../../frontend/node_modules/pinia'),
      vue: fromConfig('../../../../frontend/node_modules/vue'),
    },
    dedupe: ['vue'],
  },
  server: {
    host: '127.0.0.1',
    port: 4182,
    strictPort: true,
    fs: { allow: [fromConfig('../../../..')] },
    proxy: {
      '/api': 'http://127.0.0.1:8019',
    },
  },
}
