/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

// CesiumJS loads workers, assets and widget CSS at runtime from this public path.
const CESIUM_BASE_URL = '/cesium';
const cesiumSource = 'node_modules/cesium/Build/Cesium';

// Where `npm run dev` forwards /api requests (the FastAPI backend).
const apiProxyTarget = process.env.SATTRACK_API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: ['Workers', 'ThirdParty', 'Assets', 'Widgets'].map((dir) => ({
        src: `${cesiumSource}/${dir}`,
        dest: CESIUM_BASE_URL.slice(1),
        // Drop "node_modules/cesium/Build/Cesium" so files land in /cesium/<dir>/...
        rename: { stripBase: cesiumSource.split('/').length },
      })),
    }),
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify(CESIUM_BASE_URL),
  },
  worker: {
    // The worker is loaded with { type: 'module' }; satellite.js uses top-level await.
    format: 'es',
  },
  server: {
    proxy: {
      '/api': apiProxyTarget,
    },
  },
  build: {
    // CesiumJS alone is about 4 MB minified (1.2 MB gzipped); that is expected for a 3D globe.
    chunkSizeWarningLimit: 6000,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: {
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.test.ts', 'src/**/*.worker.ts'],
    },
  },
});
