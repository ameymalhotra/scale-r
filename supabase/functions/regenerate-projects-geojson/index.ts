// Supabase Edge Function: fetch all projects from DB, build GeoJSON, upload to Storage.
// Invoke after insert/update/delete on projects so visitors get fresh data from Storage without hitting the DB.
// Requires: Storage bucket "project-data" (public). Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in function secrets.

import { createClient } from 'npm:@supabase/supabase-js@2';

const BUCKET = 'project-data';
const FILE = 'projects.geojson';

function rowToFeature(row: Record<string, unknown>) {
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

Deno.serve(async (req: Request) => {
  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    if (!supabaseUrl || !serviceRoleKey) {
      return new Response(
        JSON.stringify({ error: 'Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    const { data: rows, error: selectError } = await supabase
      .from('projects')
      .select('id, project_na, name, city, latitude, longitude, infrastruc, categories, disaster_f, new_15_25_, project_st, project_en, project_status, estimated_cost, implementa, link_to_da, additional');

    if (selectError) {
      return new Response(
        JSON.stringify({ error: selectError.message }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const features = (rows || []).map(rowToFeature).filter(Boolean);
    const geojson = { type: 'FeatureCollection', features };
    const body = new TextEncoder().encode(JSON.stringify(geojson));

    const { error: uploadError } = await supabase.storage
      .from(BUCKET)
      .upload(FILE, body, {
        contentType: 'application/geo+json',
        upsert: true,
      });

    if (uploadError) {
      return new Response(
        JSON.stringify({ error: uploadError.message }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({ ok: true, features: features.length }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ error: String(e) }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
});
