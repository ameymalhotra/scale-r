/**
 * Loads the Flood What-If files (D-199, D-200). Private admin data (D-095):
 * - development (`npm run dev`): served by the dev-only Vite middleware at /__admin_data/ from the git-ignored
 *   "Modelling Data from Web/outputs/admin_data/" folder; this route does not exist in a build;
 * - production: downloaded from the private Supabase Storage bucket "admin-data" with the signed-in admin's
 *   session; the bucket's read policy allows admins only (public.is_admin()).
 * The files are never imported, so no build contains them.
 */
import { ADMIN_BUCKET, fetchAdminBlob } from '../adminData.js';
import { readTile } from './whatIfEngine.js';

export { ADMIN_BUCKET };
const PREFIX = 'what_if/';
const fetchBlob = (name, opts) => fetchAdminBlob(PREFIX + name, opts);

export async function loadJson(name, opts) {
  return JSON.parse(await (await fetchBlob(name, opts)).text());
}

export async function loadGz(name, opts) {
  const blob = await fetchBlob(name, opts);
  const stream = blob.stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}

/** Tile cache: each 2 km square is downloaded once. */
export function tileStore(man, opts, list = man.tiles) {
  const tiles = new Map();
  const pending = new Map();
  const byKey = new Map((list || []).map((t) => [`${t.ix}_${t.iy}`, t]));
  async function ensure(keys) {
    const jobs = [];
    for (const k of keys) {
      if (tiles.has(k) || !byKey.has(k)) continue;
      if (!pending.has(k)) {
        pending.set(k, loadGz(byKey.get(k).file, opts).then((buf) => { tiles.set(k, readTile(buf)); pending.delete(k); }));
      }
      jobs.push(pending.get(k));
    }
    await Promise.all(jobs);
  }
  return { tiles, ensure, byKey };
}
