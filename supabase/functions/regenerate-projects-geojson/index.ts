// Supabase Edge Function: fetch all rows from projects_merged_conf1, build GeoJSON, upload to Storage.
// Invoke after insert/update/delete on projects_merged_conf1 so visitors get fresh data from Storage
// without the map querying the table directly.
//
// Requires: Storage bucket "project-data" (public). Secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Output path matches Dashboard.jsx → projects_merged_conf1.geojson

import { createClient } from 'npm:@supabase/supabase-js@2';

const BUCKET = 'project-data';
const FILE = 'projects_merged_conf1.geojson';
const TABLE = 'projects_merged_conf1';

const COLS =
  'id, project_na, name, city, latitude, longitude, infrastruc, categories, disaster_f, new_15_25_, project_st, project_en, project_status, estimated_cost, implementa, link_to_da, additional, tract_geoid';
const PAGE_SIZE = 1000;

function rowToFeature(row: Record<string, unknown>) {
  const lat = Number(row.latitude);
  const lng = Number(row.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return {
    type: 'Feature' as const,
    id: row.id,
    geometry: { type: 'Point' as const, coordinates: [lng, lat] as [number, number] },
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
      TRACT_GEOID: row.tract_geoid ?? '',
    },
  };
}

Deno.serve(async (req: Request) => {
  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    if (!supabaseUrl || !serviceRoleKey) {
      return new Response(JSON.stringify({ error: 'Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const rows: Record<string, unknown>[] = [];
    let offset = 0;
    let hasMore = true;

    while (hasMore) {
      const { data: chunk, error: selectError } = await supabase
        .from(TABLE)
        .select(COLS)
        .order('id', { ascending: true })
        .range(offset, offset + PAGE_SIZE - 1);

      if (selectError) {
        return new Response(JSON.stringify({ error: selectError.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (!chunk?.length) break;
      rows.push(...chunk);
      hasMore = chunk.length === PAGE_SIZE;
      offset += PAGE_SIZE;
    }

    const features = rows.map(rowToFeature).filter(Boolean);
    const geojson = { type: 'FeatureCollection' as const, features };
    const body = new TextEncoder().encode(JSON.stringify(geojson));

    const { error: uploadError } = await supabase.storage.from(BUCKET).upload(FILE, body, {
      contentType: 'application/geo+json',
      upsert: true,
    });

    if (uploadError) {
      return new Response(JSON.stringify({ error: uploadError.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ ok: true, features: features.length }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
