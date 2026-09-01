import { fileURLToPath, URL } from 'node:url'
import vue from '../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'


const devRoot = fileURLToPath(new URL('.', import.meta.url))
const pluginRoot = fileURLToPath(new URL('..', import.meta.url))
const hallRoot = fileURLToPath(new URL('../../..', import.meta.url))
const frontendModules = fileURLToPath(new URL('../../../frontend/node_modules', import.meta.url))
const apiPort = process.env.BOMB_PEOPLE_API_PORT ?? '10619'

export default {
  root: devRoot,
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fileURLToPath(new URL('./local-sdk.ts', import.meta.url)),
      '@lucide/vue': fileURLToPath(new URL('../../../frontend/node_modules/@lucide/vue', import.meta.url)),
      '@vue/test-utils': fileURLToPath(new URL('../../../frontend/node_modules/@vue/test-utils', import.meta.url)),
      pinia: fileURLToPath(new URL('../../../frontend/node_modules/pinia', import.meta.url)),
      vue: fileURLToPath(new URL('../../../frontend/node_modules/vue', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    fs: { allow: [pluginRoot, hallRoot, frontendModules] },
    proxy: {
      '/api': `http://127.0.0.1:${apiPort}`,
    },
  },
  build: {
    outDir: fileURLToPath(new URL('../.local-test/dist', import.meta.url)),
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    include: ['../frontend/**/*.test.ts'],
  },
}
