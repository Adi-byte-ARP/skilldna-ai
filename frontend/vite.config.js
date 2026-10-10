import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/resume': 'http://localhost:8000',
      '/github': 'http://localhost:8000',
      '/ocr': 'http://localhost:8000',
      '/report': 'http://localhost:8000',
    },
  },
})
