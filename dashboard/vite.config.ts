import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';


export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    const apiUrl = env.VITE_API_URL || 'http://192.168.0.104:8001';
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          '/api': {
            target: `${apiUrl}/api`,
            changeOrigin: true,
            secure: false,
          },
          '/static': {
            target: apiUrl,
            changeOrigin: true,
            secure: false,
          },
        },
      },
      plugins: [
        VitePWA({
          registerType: 'autoUpdate',
          includeAssets: ['icons/*.png'],
          manifest: {
            name: 'LuzApp - Automercados Luz',
            short_name: 'LuzApp',
            description: 'Dashboard de monitoreo',
            start_url: '/',
            display: 'standalone',
            background_color: '#09090b',
            theme_color: '#22d3ee',
            lang: 'es',
            orientation: 'portrait-primary',
            icons: [
              {
                src: 'icons/pwa-192x192.png',
                sizes: '192x192',
                type: 'image/png',
                purpose: 'any',
              },
              {
                src: 'icons/pwa-512x512.png',
                sizes: '512x512',
                type: 'image/png',
                purpose: 'any maskable',
              },
            ],
          },
          workbox: {
            globPatterns: ['**/*.{js,css,html,png,ico,svg}'],
            runtimeCaching: [
              {
                urlPattern: /^https?:\/\/.*\/api\/.*/i,
                handler: 'NetworkFirst',
                options: {
                  cacheName: 'api-cache',
                  expiration: {
                    maxEntries: 50,
                    maxAgeSeconds: 60 * 60,
                  },
                  networkTimeoutSeconds: 10,
                },
              },
              {
                urlPattern: /\.(?:png|jpg|jpeg|svg|gif|ico)$/,
                handler: 'CacheFirst',
                options: {
                  cacheName: 'image-cache',
                  expiration: {
                    maxEntries: 100,
                    maxAgeSeconds: 60 * 60 * 24 * 30,
                  },
                },
              },
            ],
          },
        }),
      ],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
