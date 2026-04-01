import path from 'path';
import { defineConfig, loadEnv } from 'vite';


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
          '/ws': {
            target: apiUrl,
            changeOrigin: true,
            secure: false,
            ws: true,
          },
        },
      },
      plugins: [],
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
