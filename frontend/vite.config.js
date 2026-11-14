import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: the frontend calls /api on its own origin; forward it to the FastAPI backend (run_backend.py, port 8000).
export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1800 },
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/static': 'http://127.0.0.1:8000' } },
})
