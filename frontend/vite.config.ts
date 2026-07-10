import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy is only used in LOCAL DEV (npm run dev).
    // In production (Vercel), the frontend calls the Render backend directly
    // via the hardcoded BASE_URL in videoApi.ts — no proxy needed.
    proxy: {
      '/api':      { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads':  { target: 'http://localhost:8000', changeOrigin: true },
      '/outputs':  { target: 'http://localhost:8000', changeOrigin: true },
      '/previews': { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})