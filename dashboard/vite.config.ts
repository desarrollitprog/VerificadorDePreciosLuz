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
          includeAssets: ['logoluz.png'],
          manifest: {
            name: 'LuzApp - Automercados Luz',
            short_name: 'LuzApp',
            description: 'Dashboard de monitoreo',
            start_url: '/',
            display: 'standalone',
            background_color: '#09090b',
            theme_color: '#22d3ee',
            icons: [
              {
                src: 'logoluz.png',
                sizes: '192x192',
                type: 'image/png',
              },
              {
                src: 'logoluz.png',
                sizes: '512x512',
                type: 'image/png',
              },
            ],
          },
          workbox: {
            globPatterns: ['**/*.{js,css,html,png,svg}'],
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
