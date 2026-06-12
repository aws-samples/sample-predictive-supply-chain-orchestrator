import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Vite dev server configuration for Procurement UI.
 *
 * Proxy routes:
 *   /api/*          → Procurement backend (port 5001) — optimization, suppliers, graph
 *   /health         → Procurement backend health check
 *   /forecast-api/* → Demand forecasting server (port 8888) — ML forecast predictions
 *
 * The forecast-api proxy rewrites the path so the React app can call
 * /forecast-api/forecast and it reaches http://localhost:8888/api/forecast.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://localhost:5001',
      '/health': 'http://localhost:5001',
      '/forecast-api': {
        target: 'http://localhost:8888',
        rewrite: (path) => path.replace(/^\/forecast-api/, '/api'),
      },
    }
  }
})
