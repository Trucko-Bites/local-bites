import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the React app calls "/api/...", and Vite forwards those
// requests to Django. That keeps the browser on one origin, so no CORS
// setup is needed (in production, Caddy does the same forwarding).
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// changeOrigin: false keeps the browser's Host header (localhost:5173).
// Django's CSRF check compares the request's Origin to its Host, so the
// owner login would be rejected if the proxy rewrote Host to backend:8000.
const djangoProxy = { target: apiProxyTarget, changeOrigin: false }

// Inside Docker on Windows (and sometimes macOS), edits made on the host
// don't always reach the container as file-change events, so hot reload
// silently stops working. Polling checks for changes on a timer instead.
// docker-compose.yml turns this on; running Vite directly on a laptop leaves it off.
const useFilePolling = process.env.VITE_WATCH_USE_POLLING === 'true'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // listen inside the Docker container
    port: 5173,
    // 500 ms between checks: fast enough to feel instant, light on CPU
    watch: useFilePolling ? { usePolling: true, interval: 500 } : undefined,
    proxy: {
      '/api': djangoProxy,
      '/admin': djangoProxy,
      '/django-static': djangoProxy,
    },
  },
})
