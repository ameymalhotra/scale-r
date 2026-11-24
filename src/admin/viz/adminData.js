/**
 * Private admin data (D-095). Never imported, so no build contains it:
 * - development (`npm run dev`): served by the dev-only Vite middleware at /__admin_data/ from the git-ignored
 *   "Modelling Data from Web/outputs/admin_data/" folder; this route does not exist in a build;
 * - production: downloaded from the private Supabase Storage bucket "admin-data" with the signed-in admin's
 *   session; the bucket's read policy allows admins only (public.is_admin()).
 */
import { supabase } from '../../lib/supabaseClient.js';

export const ADMIN_BUCKET = 'admin-data';

/** One file from the private admin data, by its path in the bucket (for example "scenario/models.json"). */
export async function fetchAdminBlob(path, { client = supabase, dev = import.meta.env.DEV } = {}) {
  if (dev) {
    const r = await fetch(`/__admin_data/${path}`);
    if (!r.ok) throw new Error(`Could not load ${path} (${r.status}). Build the admin data first.`);
    return r.blob();
  }
  if (!client) throw new Error('Supabase is not configured');
  const { data, error } = await client.storage.from(ADMIN_BUCKET).download(path);
  if (error || !data) throw new Error(`Could not load ${path}: ${error?.message ?? 'no data'}`);
  return data;
}

export async function loadAdminJson(path, opts) {
  return JSON.parse(await (await fetchAdminBlob(path, opts)).text());
}
