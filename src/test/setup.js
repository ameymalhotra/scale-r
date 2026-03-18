import '@testing-library/jest-dom'

if (typeof process !== 'undefined' && !process.env.VITE_SUPABASE_URL) {
  process.env.VITE_SUPABASE_URL = 'https://test.supabase.co'
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
