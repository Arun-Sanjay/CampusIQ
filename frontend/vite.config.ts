import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/apple-touch-icon.png'],
      manifest: {
        name: 'CampusIQ — AI companion for engineering students',
        short_name: 'CampusIQ',
        description:
          'Adaptive learning, AI quizzes, in-browser coding practice, and a four-pillar readiness score for engineering students.',
        theme_color: '#06070A',
        background_color: '#06070A',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          { src: '/icons/pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/pwa-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Precache the app shell only. The backend API (different origin),
        // Pyodide (~10MB CDN) and MediaPipe (CDN) are cross-origin and never
        // precached; oversized local chunks (e.g. Monaco) are skipped by size.
        globPatterns: ['**/*.{js,css,html,svg}'],
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
        cleanupOutdatedCaches: true,
        // This app is useless offline (always needs the backend), so serve the
        // HTML shell NETWORK-FIRST: a returning visitor always gets the freshest
        // index.html → freshest JS chunks. Without this, a stale precached shell
        // could reference an old bundle (e.g. pointing at a retired backend URL)
        // for one load after a redeploy. Cache is only the offline fallback.
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/, /^\/audio/],
        runtimeCaching: [
          {
            urlPattern: ({ request }: { request: Request }) => request.mode === 'navigate',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'app-shell',
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 4 },
            },
          },
          {
            urlPattern: ({ url }: { url: URL }) =>
              url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com',
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'google-fonts', expiration: { maxEntries: 20 } },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
