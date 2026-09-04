import { fileURLToPath, URL } from 'node:url'
import vue from '../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'

const fromConfig = (relativePath) => fileURLToPath(new URL(relativePath, import.meta.url))

export default {
  root: fromConfig('.'),
  cacheDir: fromConfig('../../../frontend/node_modules/.vite/love-letter-live'),
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fromConfig('./local-sdk.ts'),
      pinia: fromConfig('../../../frontend/node_modules/pinia'),
      vue: fromConfig('../../../frontend/node_modules/vue'),
    },
    dedupe: ['vue'],
  },
  server: {
    host: '127.0.0.1', port: 4190, strictPort: true,
    fs: { allow: [fromConfig('../../..')] },
    proxy: { '/api': 'http://127.0.0.1:8030' },
  },
}
