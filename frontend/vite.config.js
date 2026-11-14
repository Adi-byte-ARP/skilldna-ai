import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiTarget = process.env.SKILLDNA_API_URL || 'http://127.0.0.1:8001'

export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
    proxy: Object.fromEntries(
      // Every backend route prefix. A missing prefix sends the request to the Vite server,
      // which answers with index.html, so the page shows a JSON parse error instead of data.
      ['/health', '/auth', '/users', '/resume', '/github', '/ocr', '/report', '/mock', '/plan', '/daily', '/reminders', '/interview', '/assistant', '/profile']
        .map((prefix) => [prefix, apiTarget]),
    ),
  },
})
