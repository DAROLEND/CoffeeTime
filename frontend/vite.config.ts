/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import scopePages from './postcss-scope-pages.ts';

// In dev, the SPA and the API share one origin through this proxy, exactly
// like production does through Render's rewrite rules (see render.yaml).
// Same origin means the session cookie stays first-party with
// SameSite=Lax, and there is no CORS to configure.
const API_TARGET = process.env.API_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/static': { target: API_TARGET, changeOrigin: true },
    },
  },
  css: {
    postcss: { plugins: [scopePages()] },
  },
  build: {
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
