/**
 * Local test mode for the map filters (VITE_LOCAL_FILTERS=true in .env.local).
 *
 * /admin/live-tool keeps its draft, published versions and history in this
 * browser's localStorage instead of Supabase, and the local /dashboard reads
 * the "live" filters from there. Nothing is written to Supabase.
 */

export const LOCAL_FILTERS = import.meta.env.VITE_LOCAL_FILTERS === 'true';

export const LOCAL_FILTERS_KEY = 'scaler-local-filters';

/** { draft, versions } or null when local testing has not started. */
export function readLocalFilterState() {
  try {
    const raw = window.localStorage.getItem(LOCAL_FILTERS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function writeLocalFilterState(state) {
  window.localStorage.setItem(LOCAL_FILTERS_KEY, JSON.stringify(state));
}

export function clearLocalFilterState() {
  window.localStorage.removeItem(LOCAL_FILTERS_KEY);
}

/** The config the local map should use, or null to fall back to the real file. */
export function readLocalLiveConfig() {
  return readLocalFilterState()?.versions?.find((v) => v.is_current)?.config ?? null;
}
