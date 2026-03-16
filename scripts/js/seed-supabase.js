/**
 * One-time seed: load public/Cities_FeaturesToJSON.geojson into Supabase `projects` table.
 *
 * RLS requires authenticated users to INSERT. For seeding, use the service role key
 * (bypasses RLS). In Supabase: Project Settings → API → service_role (secret).
 * Set in .env: SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
 * Do not commit the service role key. Run this script only locally.
 */

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
const supabaseKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.VITE_SUPABASE_ANON_KEY ||
  process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    'Set VITE_SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY (for seed) or VITE_SUPABASE_ANON_KEY'
  );
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

function mapFeatureToRow(feature) {
  const p = feature.properties || {};
  const coords = feature.geometry?.coordinates;
  if (!coords || coords.length < 2) return null;

  const lat = parseFloat(p.Latitude ?? coords[1]);
  const lng = parseFloat(p.Longitude ?? coords[0]);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;

  const projectEn = p.Project_En?.trim();
  const estimated = parseFloat(p.Estimated_);
  return {
    project_na: (p.Project_Na || '').trim() || null,
    name: (p.NAME || p.City || '').trim() || null,
    latitude: lat,
    longitude: lng,
    infrastruc: (p.Infrastruc || '').trim() || null,
    city: (p.City || '').trim() || null,
    categories: (p.Categories || '').trim() || null,
    disaster_f: (p.Disaster_F || '').trim() || null,
    new_15_25_: (p['New_15_25_'] || '').trim() || null,
    project_st: (p.Project_St || '').trim() || null,
    project_en: projectEn === 'Null' || projectEn === '' ? null : projectEn,
    project_status: (p['Project__1'] || '').trim() || null,
    estimated_cost: Number.isFinite(estimated) ? estimated : null,
    implementa: (p.Implementa || '').trim() || null,
    link_to_da: (p.Link_to_Da || '').trim() || null,
    additional: (p.Additional || '').trim() || null,
  };
}

async function seed() {
  const geojsonPath = join(__dirname, '..', '..', 'public', 'Cities_FeaturesToJSON.geojson');
  const raw = readFileSync(geojsonPath, 'utf8');
  const geojson = JSON.parse(raw);
  const features = geojson.features || [];

  const rows = features.map(mapFeatureToRow).filter(Boolean);
  console.log(`Mapped ${rows.length} projects from ${features.length} features.`);

  const BATCH = 50;
  for (let i = 0; i < rows.length; i += BATCH) {
    const chunk = rows.slice(i, i + BATCH);
    const { error } = await supabase.from('projects').insert(chunk);
    if (error) {
      console.error('Insert error at batch', i, error);
      throw error;
    }
    console.log(`Inserted ${i + chunk.length}/${rows.length}`);
  }
  console.log('Seed done.');
}

seed().catch((e) => {
  console.error(e);
  process.exit(1);
});
