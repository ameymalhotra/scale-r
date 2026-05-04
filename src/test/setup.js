import '@testing-library/jest-dom'

if (typeof process !== 'undefined' && !process.env.VITE_SUPABASE_URL) {
  process.env.VITE_SUPABASE_URL = 'https://test.supabase.co'
}

if (typeof process !== 'undefined' && !process.env.VITE_MAPBOX_ACCESS_TOKEN) {
  process.env.VITE_MAPBOX_ACCESS_TOKEN = 'test-mapbox-token'
}

if (typeof window !== 'undefined' && !window.ResizeObserver) {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

if (typeof globalThis !== 'undefined' && !globalThis.IntersectionObserver) {
  globalThis.IntersectionObserver = class IntersectionObserver {
    constructor() {}
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  };
}

if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = () => ({
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
    media: '',
    onchange: null,
  })
}
