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

if (typeof globalThis !== 'undefined' && !globalThis.URL.createObjectURL) {
  // The parser hands large collections to mapbox as blob: URLs. jsdom has no
  // object-URL support, and the mocked map ignores source data anyway, so a
  // stable fake URL is enough.
  let blobUrlCounter = 0;
  globalThis.URL.createObjectURL = () => `blob:test-object-url/${++blobUrlCounter}`;
  globalThis.URL.revokeObjectURL = () => {};
}

if (typeof globalThis !== 'undefined' && !globalThis.Worker) {
  // jsdom has no Worker, but the dashboard's data loading genuinely depends on
  // one, so stubbing it out with a no-op would silently empty the dashboard
  // under test. This stub speaks the same message protocol and runs the real
  // parsing code in-process, so the tests still exercise the actual transforms
  // rather than a mock of them.
  globalThis.Worker = class Worker {
    constructor() {
      this.listeners = new Set();
    }

    addEventListener(type, fn) {
      if (type === 'message') this.listeners.add(fn);
    }

    removeEventListener(type, fn) {
      if (type === 'message') this.listeners.delete(fn);
    }

    async postMessage({ id, task, payload }) {
      const { runTask } = await import('../workers/dataParser.core.js');
      let message;
      try {
        message = { id, ok: true, result: await runTask(task, payload) };
      } catch (err) {
        message = { id, ok: false, error: err?.message ?? String(err) };
      }
      for (const fn of [...this.listeners]) fn({ data: message });
    }

    terminate() {
      this.listeners.clear();
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
