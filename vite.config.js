import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: 'public',
  base: '/',
  build: {
    rollupOptions: {
      output: {
        // Split the vendor libraries out of the single 2.35 MB entry chunk.
        // This changes only how the same code is packaged, never what runs:
        // mapbox-gl and recharts are dashboard-only, so keeping them in their
        // own chunks lets the browser parse and cache them independently.
        manualChunks(id) {
          // Rollup's CommonJS interop helper is a virtual module shared by
          // react, recharts and mapbox-gl alike. It has no node_modules in its
          // id, so without this it lands in whichever vendor chunk claims it
          // first and the other chunks import *that* chunk to reach it —
          // producing a cycle in which React evaluates after its consumers and
          // reads as undefined. Isolating it keeps the vendor chunks acyclic.
          if (id.includes('commonjsHelpers')) return 'vendor-cjs';
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('mapbox-gl')) return 'mapbox';
          // recharts pulls in the d3-* scale/shape/array packages and the
          // victory-vendor shim; they are only ever reached through recharts.
          if (id.includes('recharts') || id.includes('victory-vendor') || /node_modules\/d3-/.test(id)) {
            return 'charts';
          }
          // React, ReactDOM, the scheduler and the router must share a chunk:
          // splitting them risks evaluating ReactDOM before React is ready.
          if (/node_modules\/(react|react-dom|scheduler|react-router|react-router-dom)\//.test(id)) {
            return 'react';
          }
          return undefined;
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
    testTimeout: 30000,
  }
})
