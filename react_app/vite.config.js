import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // No base path - dev server serves from root
  // The FastAPI proxy handles /{username}/app -> localhost:3000/
  // React Router's basename handles client-side routing at /app
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    // Disable HMR - doesn't work well behind reverse proxies
    hmr: false
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Only set base for production builds
    // Dev mode serves from root
  }
})
