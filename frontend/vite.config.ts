import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend port - should match APP_PORT in .env (default 8000)
const BACKEND_PORT = process.env.BACKEND_PORT || '8000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to the Python backend
      '/chatkit': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/api': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      // Proxy static files (logo, branding assets)
      '/static': {
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
  },
})
