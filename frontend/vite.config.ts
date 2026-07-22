import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { demoApiPlugin } from './demo/api'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const demo = env.T2D_DEMO === '1'
  return {
    plugins: [vue(), ...(demo ? [demoApiPlugin()] : [])],
    server: {
      port: 5173,
      proxy: demo ? undefined : { '/api': 'http://127.0.0.1:8001' },
    },
  }
})
