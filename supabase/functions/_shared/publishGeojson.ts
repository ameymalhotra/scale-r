import type { SupabaseClient } from 'npm:@supabase/supabase-js@2';
import { PROJECT_SELECT, projectsToFeatureCollection } from './projectToFeature.ts';

export const BUCKET = 'project-data';
export const PUBLISHED_FILE = 'projects_merged_conf1.geojson';
export const versionFile = (versionNo: number) => `versions/projects_merged_conf1_v${versionNo}.geojson`;

const TABLE = 'projects_merged_conf1';
const PAGE_SIZE = 1000;

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

export function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

/** Reads projects_merged_conf1 with the service-role client and writes the public GeoJSON. */
export async function writePublishedGeojson(admin: SupabaseClient, versionNo?: number) {
  const rows: Record<string, unknown>[] = [];
  for (let offset = 0; ; offset += PAGE_SIZE) {
    const { data, error } = await admin
      .from(TABLE)
      .select(PROJECT_SELECT)
      .order('id', { ascending: true })
      .range(offset, offset + PAGE_SIZE - 1);
    if (error) throw new Error(`Reading ${TABLE}: ${error.message}`);
    if (!data?.length) break;
    rows.push(...data);
    if (data.length < PAGE_SIZE) break;
  }

  const geojson = projectsToFeatureCollection(rows);
  const body = new TextEncoder().encode(JSON.stringify(geojson));

  const { error: liveError } = await admin.storage.from(BUCKET).upload(PUBLISHED_FILE, body, {
    contentType: 'application/geo+json',
    cacheControl: '0',
    upsert: true,
  });
  if (liveError) throw new Error(`Uploading ${PUBLISHED_FILE}: ${liveError.message}`);

  if (versionNo != null) {
    const { error: archiveError } = await admin.storage.from(BUCKET).upload(versionFile(versionNo), body, {
      contentType: 'application/geo+json',
      cacheControl: '31536000',
      upsert: true,
    });
    if (archiveError) throw new Error(`Uploading ${versionFile(versionNo)}: ${archiveError.message}`);
  }

  return { features: geojson.features.length };
}
