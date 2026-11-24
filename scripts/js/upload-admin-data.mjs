/**
 * Upload the private admin data (D-095) to the Supabase Storage bucket "admin-data".
 *   npm run upload-admin-data            upload everything
 *   npm run upload-admin-data -- --dry   list what would be uploaded
 *   npm run upload-admin-data -- --only what_if/examples.json   upload only the named files
 * Source: the git-ignored staging folder "Modelling Data from Web/outputs/admin_data/":
 *   gap/       the resilience gap map (scripts/python/build_viz_tracts.py)
 *   scenario/  the Scenario view (build_scenario_data.py)
 *   what_if/   the Flood What-If view (export_what_if.py); test-only files are skipped
 * Uses SUPABASE_SERVICE_ROLE_KEY from .env: never printed, never shipped to the browser.
 * Refuses to upload if the bucket is public.
 */
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { createClient } from '@supabase/supabase-js';

const url = process.env.VITE_SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) {
  console.error('Set VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env');
  process.exit(1);
}
const BUCKET = 'admin-data';
const STAGING = path.resolve('Modelling Data from Web/outputs/admin_data');
const FOLDERS = ['gap', 'scenario', 'what_if'];
const SKIP = new Set(['what_if/parity_fixture.json', 'what_if/parity_result.json', 'what_if/reason_parity.json', 'what_if/export_summary.json']);
const TYPES = { '.json': 'application/json', '.geojson': 'application/geo+json', '.gz': 'application/octet-stream' };
const dry = process.argv.includes('--dry');
const only = process.argv.flatMap((a, i, all) => (all[i - 1] === '--only' ? [a] : []));

async function list(dir) {
  const out = [];
  for (const e of await readdir(path.join(STAGING, dir), { withFileTypes: true })) {
    const rel = `${dir}/${e.name}`;
    if (e.isDirectory()) out.push(...(await list(rel)));
    else if (TYPES[path.extname(e.name)] && !SKIP.has(rel)) out.push(rel);
  }
  return out;
}

const supabase = createClient(url, key, { auth: { persistSession: false } });
const { data: bucket, error: bucketError } = await supabase.storage.getBucket(BUCKET);
if (bucketError || !bucket) throw new Error(`bucket ${BUCKET} not found: run the SQL in supabase/sql/admin_dashboard.sql first`);
if (bucket.public) throw new Error(`bucket ${BUCKET} is PUBLIC; refusing to upload admin data`);

const all = (await Promise.all(FOLDERS.map(list))).flat();
const missing = only.filter((n) => !all.includes(n));
if (missing.length) throw new Error(`not in the staging folder (or skipped): ${missing.join(', ')}`);
const files = only.length ? all.filter((n) => only.includes(n)) : all;
let bytes = 0;
let done = 0;
const queue = [...files];
async function worker() {
  while (queue.length) {
    const name = queue.shift();
    const body = await readFile(path.join(STAGING, name));
    if (!name.endsWith('.gz')) JSON.parse(body.toString()); // fail early on a broken file
    bytes += body.length;
    if (!dry) {
      const { error } = await supabase.storage.from(BUCKET).upload(name, body, {
        contentType: TYPES[path.extname(name)], upsert: true, cacheControl: 'no-cache',
      });
      if (error) throw new Error(`${name}: ${error.message}`);
    }
    done += 1;
    if (done % 100 === 0) console.log(`${done} of ${files.length}`);
  }
}
await Promise.all(Array.from({ length: 6 }, worker));
console.log(`${dry ? 'would upload' : 'uploaded'} ${files.length} files, ${(bytes / 1e6).toFixed(1)} MB`);
for (const f of FOLDERS) console.log(`  ${f}/: ${files.filter((n) => n.startsWith(`${f}/`)).length} files`);
