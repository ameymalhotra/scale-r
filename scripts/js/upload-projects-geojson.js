/**
 * One-time (or re-run) upload: read projects from Supabase, build GeoJSON, upload to Storage.
 * Run after seeding the DB so the app can fetch projects.geojson from Storage instead of hitting the DB.
 * Requires: Storage bucket "project-data" (public). Create in Supabase Dashboard → Storage.
 * Uses SUPABASE_SERVICE_ROLE_KEY so the bucket can be written. Do not commit that key.
 */

import { createClient } from '@supabase/supabase-js';

const BUCKET = 'project-data';
const FILE = 'projects.geojson';

const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
const supabaseKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.VITE_SUPABASE_ANON_KEY ||
  process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    'Set VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or VITE_SUPABASE_ANON_KEY)'
  );
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

function rowToFeature(row) {
  const lat = Number(row.latitude);
  const lng = Number(row.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return {
    type: 'Feature',
    id: row.id,
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: {
      Project_Na: row.project_na ?? '',
      NAME: row.name ?? '',
      City: row.city ?? '',
      Infrastruc: row.infrastruc ?? '',
      Categories: row.categories ?? '',
      Disaster_F: row.disaster_f ?? '',
      New_15_25_: row.new_15_25_ ?? '',
      Project_St: row.project_st ?? '',
      Project_En: row.project_en ?? '',
      Project__1: row.project_status ?? '',
      Estimated_: row.estimated_cost != null ? String(row.estimated_cost) : '',
      Implementa: row.implementa ?? '',
      Link_to_Da: row.link_to_da ?? '',
      Additional: row.additional ?? '',
    },
  };
}

async function upload() {
  const { data: rows, error: selectError } = await supabase
    .from('projects')
    .select(
      'id, project_na, name, city, latitude, longitude, infrastruc, categories, disaster_f, new_15_25_, project_st, project_en, project_status, estimated_cost, implementa, link_to_da, additional'
    );

  if (selectError) {
    console.error('Select error:', selectError);
    process.exit(1);
  }

  const features = (rows || []).map(rowToFeature).filter(Boolean);
  const geojson = { type: 'FeatureCollection', features };
  const body = JSON.stringify(geojson);

  const { error: uploadError } = await supabase.storage.from(BUCKET).upload(FILE, body, {
    contentType: 'application/geo+json',
    upsert: true,
  });

  if (uploadError) {
    console.error('Upload error:', uploadError);
    process.exit(1);
  }

  console.log(`Uploaded projects.geojson to ${BUCKET}/${FILE} (${features.length} features).`);
}

upload().catch((e) => {
  console.error(e);
  process.exit(1);
});
