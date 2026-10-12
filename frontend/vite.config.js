import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import { sentryVitePlugin } from "@sentry/vite-plugin"

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'inject-sw-version',
      writeBundle() {
        const hash = Date.now().toString(36);
        const swPath = './dist/sw.js';
        try {
          const content = fs.readFileSync(swPath, 'utf8');
          fs.writeFileSync(swPath, content.replace('__BUILD_HASH__', hash));
          console.log(`✅ Service worker version injected: ${hash}`);
        } catch (err) {
          console.warn('⚠️ Failed to inject SW version:', err.message);
        }
      }
    },
    // Sentry plugin for source map uploads
    sentryVitePlugin({
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      authToken: process.env.SENTRY_AUTH_TOKEN,
      disable: !process.env.SENTRY_AUTH_TOKEN, // Disable if no token
    }),
  ],
  resolve: {
    // One React for the whole app. Two copies make every hook throw "Invalid hook call"
    // ("Cannot read properties of null (reading 'useState')").
    dedupe: ['react', 'react-dom'],
  },
  optimizeDeps: {
    // Pre-bundle these up front. Left to discovery, the dev server re-optimizes the first time a
    // page imports one of them, and a tab loaded before that keeps the old React next to the new.
    include: ['react', 'react-dom', 'react-dom/client', 'react/jsx-runtime', 'react/jsx-dev-runtime', 'react-router', 'axios'],
  },
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
          // Match whole package directories: 'node_modules/react' alone also matches react-router.
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) {
            return 'react-vendor'
          }
          // Router chunk
          if (id.includes('node_modules/react-router/')) {
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
