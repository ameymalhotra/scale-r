/**
 * Build GeoJSON from Supabase `projects_merged` and upload to Storage.
 * Run after seeding projects_merged (e.g. npm run seed-merged).
 * Requires: Storage bucket "project-data" (public). Uses SUPABASE_SERVICE_ROLE_KEY.
 *
 * Run: npm run upload-geojson-merged
 * Output: project-data/projects_merged.geojson (use this URL in the app to show merged data)
 */

import { createClient } from '@supabase/supabase-js';

const BUCKET = 'project-data';
const FILE = 'projects_merged.geojson';

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

const INFRA_CANONICAL = {
  blue: 'Blue Infrastructure',
  'blue infrastructure': 'Blue Infrastructure',
  green: 'Green Infrastructure',
  'green infrastructure': 'Green Infrastructure',
  grey: 'Grey Infrastructure',
  'grey infrastructure': 'Grey Infrastructure',
  hybrid: 'Hybrid',
};

function normalizeInfrastruc(val) {
  if (!val) return '';
  const key = String(val).trim().toLowerCase();
  return INFRA_CANONICAL[key] ?? val;
}

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
      Infrastruc: normalizeInfrastruc(row.infrastruc),
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

const COLS =
  'id, project_na, name, city, latitude, longitude, infrastruc, categories, disaster_f, new_15_25_, project_st, project_en, project_status, estimated_cost, implementa, link_to_da, additional';
const PAGE_SIZE = 1000;

async function upload() {
  const rows = [];
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const { data: chunk, error: selectError } = await supabase
      .from('projects_merged')
      .select(COLS)
      .range(offset, offset + PAGE_SIZE - 1);

    if (selectError) {
      console.error('Select error:', selectError);
      process.exit(1);
    }
    if (!chunk?.length) break;
    rows.push(...chunk);
    hasMore = chunk.length === PAGE_SIZE;
    offset += PAGE_SIZE;
  }

  const features = rows.map(rowToFeature).filter(Boolean);
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

  console.log(`Uploaded ${BUCKET}/${FILE} (${features.length} features).`);
  console.log(
    `URL: ${supabaseUrl}/storage/v1/object/public/${BUCKET}/${FILE}`
  );
}

upload().catch((e) => {
  console.error(e);
  process.exit(1);
});
