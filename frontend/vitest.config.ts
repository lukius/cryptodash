import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const repoRoot = path.resolve(__dirname, '..')

export default defineConfig({
  plugins: [vue()],
  server: {
    fs: {
      allow: [__dirname, repoRoot],
    },
  },
  test: {
    environment: 'happy-dom',
    setupFiles: [path.resolve(repoRoot, 'tests/frontend/setup.ts')],
    globals: true,
    include: [path.resolve(repoRoot, 'tests/frontend/**/*.test.ts')],
    deps: {
      moduleDirectories: ['node_modules', path.resolve(__dirname, 'node_modules')],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      // Ensure packages resolve from frontend/node_modules for files outside frontend/
      '@vue/test-utils': path.resolve(__dirname, 'node_modules/@vue/test-utils'),
      'vue-router': path.resolve(__dirname, 'node_modules/vue-router'),
      'pinia': path.resolve(__dirname, 'node_modules/pinia'),
      'vue': path.resolve(__dirname, 'node_modules/vue'),
    },
  },
})
