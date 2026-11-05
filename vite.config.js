import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// IMPORTANT: This must match the GitHub repository name.
export default defineConfig({
  plugins: [react()],
  base: '/roadmap-studio/'
})
