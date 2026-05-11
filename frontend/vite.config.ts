import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load *all* env (including non-VITE_* vars) so we can keep secrets
  // like ELEVENLABS_API_KEY out of the client bundle. The proxy injects
  // the key as a request header — the browser never sees it.
  const env = loadEnv(mode, process.cwd(), '')
  const elKey = env.ELEVENLABS_API_KEY ?? ''

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        // Server-side proxy to ElevenLabs. Frontend hits /api/elevenlabs/*
        // and Vite forwards it to api.elevenlabs.io/v1/* with xi-api-key
        // injected. Used for the agent interview screen's auto-pull of
        // past conversations + transcripts.
        '/api/elevenlabs': {
          target: 'https://api.elevenlabs.io',
          changeOrigin: true,
          secure: true,
          rewrite: (p) => p.replace(/^\/api\/elevenlabs/, '/v1'),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (elKey) proxyReq.setHeader('xi-api-key', elKey)
            })
          },
        },
      },
    },
  }
})
