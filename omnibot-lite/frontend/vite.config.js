import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev : l'API/WS du hub tournent sur 8080 (OMNIBOT_PORT). En prod (Docker) le
// même serveur sert le build — pas de proxy nécessaire.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8080', ws: true },
    },
  },
})
