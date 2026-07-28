import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Vite config -- https://vitejs.dev/config/
//
// This started as a Figma Make export, which wired several plugins to
// Figma's own preview/deploy infrastructure (a `.figma/make/site.json`
// config file that only exists inside Figma Make, a dev-only "kit" route
// for Figma's design surface, HMR error-overlay replay, etc). None of that
// exists once the export runs standalone, so those plugins have been
// removed rather than stubbed out -- this is a plain React + Tailwind app.
export default defineConfig({
  build: {
    sourcemap: false,
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.PORT || '5173'),
  },
  preview: {
    host: '0.0.0.0',
    port: parseInt(process.env.PORT || '5173'),
  },
})
