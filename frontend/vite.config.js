import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections
    port: 5173,
    // Removed HTTPS configuration - using HTTP for development
  },
  build: {
    // Production optimizations
    minify: 'esbuild',
    sourcemap: false,
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // React vendor chunk
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'react-vendor'
          }
          // Router chunk
          if (id.includes('node_modules/react-router')) {
            return 'router-vendor'
          }
          // Axios chunk
          if (id.includes('node_modules/axios')) {
            return 'axios-vendor'
          }
          // Lucide icons chunk (can be large)
          if (id.includes('node_modules/lucide-react')) {
            return 'icons-vendor'
          }
          // Large page components
          if (id.includes('/pages/Dashboard')) {
            return 'dashboard'
          }
          if (id.includes('/pages/ProjectDetail')) {
            return 'project-detail'
          }
          if (id.includes('/pages/Recommendations')) {
            return 'recommendations'
          }
        },
        // Optimize chunk file names
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    chunkSizeWarningLimit: 1000,
    // Enable tree shaking
    treeshake: {
      moduleSideEffects: false,
    },
  },
  define: {
    // Define environment variables for the frontend
    __DEV__: JSON.stringify(process.env.NODE_ENV === 'development'),
  },
})
