import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Inline the entry stylesheet into index.html and preload the navbar font.
 *
 * The 9 KiB app CSS is same-origin and already cheap, but a <link rel=
 * "stylesheet"> is still a render-blocking request in Lighthouse. Inlining
 * removes that request without deferring styles (which would flash unstyled
 * content). Mapbox CSS is not inlined: it is a dynamic import that only loads
 * with the map.
 *
 * Manrope is the navbar face on every route, including /dashboard whose LCP
 * is text. Preloading the latin woff2 lets the browser start the font file
 * before it finishes parsing the inlined @font-face.
 */
function inlineEntryCssAndPreloadFonts() {
  return {
    name: 'inline-entry-css-and-preload-fonts',
    apply: 'build',
    enforce: 'post',
    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        const bundle = ctx.bundle
        if (!bundle) return html

        let nextHtml = html.replace(
          /<link\b[^>]*\brel=["']stylesheet["'][^>]*>/gi,
          (match) => {
            const hrefMatch = match.match(/\bhref=["']([^"']+)["']/i)
            if (!hrefMatch) return match
            const fileName = hrefMatch[1].replace(/^\//, '').split('?')[0]
            const assetKey = Object.keys(bundle).find(
              (key) => bundle[key].type === 'asset' && bundle[key].fileName === fileName,
            )
            const asset = assetKey ? bundle[assetKey] : null
            if (!asset || asset.source == null) return match
            const css =
              typeof asset.source === 'string'
                ? asset.source
                : Buffer.from(asset.source).toString('utf8')
            delete bundle[assetKey]
            return `<style>${css}</style>`
          },
        )

        const manrope = Object.values(bundle).find(
          (asset) =>
            asset.type === 'asset' &&
            typeof asset.fileName === 'string' &&
            asset.fileName.endsWith('.woff2') &&
            asset.fileName.includes('manrope-latin'),
        )
        if (manrope) {
          const preload =
            `    <link rel="preload" href="/${manrope.fileName}" as="font" type="font/woff2" crossorigin>\n`
          const marker = '    <link rel="preconnect" href="https://api.mapbox.com"'
          nextHtml = nextHtml.includes(marker)
            ? nextHtml.replace(marker, `${preload}${marker}`)
            : nextHtml.replace('<head>', `<head>\n${preload}`)
        }

        return nextHtml
      },
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), inlineEntryCssAndPreloadFonts()],
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
