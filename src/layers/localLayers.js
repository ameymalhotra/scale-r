/**
 * Local test mode for map layers (VITE_LOCAL_LAYERS=true in .env.local).
 *
 * /admin/layers keeps its draft, published versions and history in this
 * browser's localStorage, and uploaded GeoJSON in IndexedDB (too large for
 * localStorage). The local /dashboard reads the "live" layers from there.
 * Nothing is written to Supabase.
 */

export const LOCAL_LAYERS = import.meta.env.VITE_LOCAL_LAYERS === 'true';

export const LOCAL_LAYERS_KEY = 'scaler-local-layers';

const FILES_DB = 'scaler-local-layer-files';
const FILES_STORE = 'files';

/** { draft, versions } or null when local testing has not started. */
export function readLocalLayerState() {
  try {
    const raw = window.localStorage.getItem(LOCAL_LAYERS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function writeLocalLayerState(state) {
  window.localStorage.setItem(LOCAL_LAYERS_KEY, JSON.stringify(state));
}

/** The config the local map should use, or null when nothing was published locally. */
export function readLocalLiveLayerConfig() {
  return readLocalLayerState()?.versions?.find((v) => v.is_current)?.config ?? null;
}

function openFilesDb() {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(FILES_DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(FILES_STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function filesRequest(mode, run) {
  const db = await openFilesDb();
  try {
    return await new Promise((resolve, reject) => {
      const request = run(db.transaction(FILES_STORE, mode).objectStore(FILES_STORE));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export const putLocalLayerFile = (path, geojson) => filesRequest('readwrite', (store) => store.put(geojson, path));

/** The GeoJSON uploaded in local mode for `path`, or null. */
export async function getLocalLayerFile(path) {
  try {
    return (await filesRequest('readonly', (store) => store.get(path))) ?? null;
  } catch {
    return null;
  }
}

export async function clearLocalLayerState() {
  window.localStorage.removeItem(LOCAL_LAYERS_KEY);
  await filesRequest('readwrite', (store) => store.clear()).catch(() => {});
}
