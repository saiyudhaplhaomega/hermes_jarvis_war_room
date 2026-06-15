import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Token injection is done by scripts/inject_runtime_config.py after build.
// See vite.config.ts comment for the simpler alternative.

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8502',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 8503,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8502',
        changeOrigin: true,
      },
    },
  },
})
