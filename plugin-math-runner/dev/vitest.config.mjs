import { fileURLToPath, URL } from 'node:url'
import vue from '../../../frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs'


const pluginFrontend = fileURLToPath(new URL('../frontend/', import.meta.url))

export default {
  root: pluginFrontend,
  plugins: [vue()],
  resolve: {
    alias: {
      '@game-hall/plugin-sdk': fileURLToPath(new URL('../../../frontend/src/plugin-sdk/index.ts', import.meta.url)),
      '@lucide/vue': fileURLToPath(new URL('../../../frontend/node_modules/@lucide/vue', import.meta.url)),
      '@vue/test-utils': fileURLToPath(new URL('../../../frontend/node_modules/@vue/test-utils', import.meta.url)),
      pinia: fileURLToPath(new URL('../../../frontend/node_modules/pinia', import.meta.url)),
      vue: fileURLToPath(new URL('../../../frontend/node_modules/vue', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['**/*.test.ts'],
  },
}
