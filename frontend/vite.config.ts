import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// When running inside the dev Docker stack, VITE_API_BASE is set to the
// backend container's internal URL (e.g. http://orbit-backend-dev:5000).
// When running directly on the host, it falls back to localhost:5000.
const apiBase = process.env.VITE_API_BASE || 'http://127.0.0.1:5000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',   // Needed for Docker dev container exposure
    port: 5173,
    proxy: {
      '/api': {
        target: apiBase,
        changeOrigin: true,
      },
      '/rest': {
        target: apiBase,
        changeOrigin: true,
      }
    }
  }
})

