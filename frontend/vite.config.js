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
  define: {
    // Define environment variables for the frontend
    __DEV__: JSON.stringify(process.env.NODE_ENV === 'development'),
  },
})
