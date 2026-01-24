import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static-v2/',  // Match FastAPI mount path
  build: {
    outDir: '../src/dashboard/static-v2',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:9000',
      '/ws': {
        target: 'ws://localhost:9000',
        ws: true,
      },
    },
  },
})
