// Changes what is live on the public map, then rebuilds the file the map reads.
//
//   { "note": string }       publish the /admin draft as a new version
//                            (publish_draft(): snapshot + replace projects_merged_conf1)
//   { "versionId": number }  put an existing version back on the map
//                            (make_version_live(): no new version is created)
//   { "rebuild": true }      only rewrite the GeoJSON from projects_merged_conf1
//
//   { "filters": { "note": string, "name"?: string } }
//                            publish the saved map filter draft (publish_filters())
//   { "filtersVersionId": number }
//                            put an existing filter version back on the map
//                            (make_filters_version_live())
//   Both filter calls then rewrite filters_config.json.
//
// Called from /admin with the signed-in user's JWT; the database functions
// re-check admin membership.
// Secrets: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY (provided by Supabase).

import { createClient } from 'npm:@supabase/supabase-js@2';
import { corsHeaders, json, writeFiltersConfig, writePublishedGeojson } from '../_shared/publishGeojson.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders });
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const anonKey = Deno.env.get('SUPABASE_ANON_KEY');
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if (!supabaseUrl || !anonKey || !serviceRoleKey) {
    return json({ error: 'Function is missing Supabase environment variables' }, 500);
  }

  const authorization = req.headers.get('Authorization');
  if (!authorization) return json({ error: 'Sign in required' }, 401);

  let note = '';
  let versionId: number | null = null;
  let rebuild = false;
  let filters: { note: string; name: string | null } | null = null;
  let filtersVersionId: number | null = null;
  try {
    const body = await req.json();
    note = typeof body?.note === 'string' ? body.note.trim() : '';
    versionId = Number.isInteger(body?.versionId) ? body.versionId : null;
    rebuild = body?.rebuild === true;
    if (body?.filters && typeof body.filters === 'object') {
      filters = {
        note: typeof body.filters.note === 'string' ? body.filters.note.trim() : '',
        name: typeof body.filters.name === 'string' ? body.filters.name : null,
      };
    }
    filtersVersionId = Number.isInteger(body?.filtersVersionId) ? body.filtersVersionId : null;
  } catch {
    return json({ error: 'Expected a JSON body' }, 400);
  }

  // Runs as the caller so the database functions can check is_admin() against their JWT.
  const asUser = createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authorization } },
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const admin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  if (filters || filtersVersionId != null) {
    if (filters && !filters.note) return json({ error: 'A publish note is required' }, 400);
    const { data: published, error: filtersError } = filters
      ? await asUser.rpc('publish_filters', { p_note: filters.note, p_name: filters.name })
      : await asUser.rpc('make_filters_version_live', { p_version_id: filtersVersionId });
    if (filtersError) {
      const status = filtersError.code === '42501' ? 403 : 400;
      return json({ error: filtersError.message }, status);
    }
    try {
      await writeFiltersConfig(admin, published.config, published.version_no);
      return json({ ok: true, version_id: published.version_id, version_no: published.version_no });
    } catch (e) {
      return json(
        {
          error: `Filter version ${published.version_no} is live in the database, but updating the map's filter file failed: ${String(e)}`,
          version_no: published.version_no,
          filtersFileFailed: true,
        },
        502,
      );
    }
  }

  if (!rebuild && versionId == null && !note) return json({ error: 'A publish note is required' }, 400);

  if (rebuild) {
    const { data: isAdmin, error: adminError } = await asUser.rpc('is_admin');
    if (adminError) return json({ error: adminError.message }, 400);
    if (!isAdmin) return json({ error: 'Only admins can rebuild the map file' }, 403);
    try {
      const { features } = await writePublishedGeojson(admin);
      return json({ ok: true, features });
    } catch (e) {
      return json({ error: `Rebuilding the map file failed: ${String(e)}` }, 502);
    }
  }

  const { data: published, error: publishError } =
    versionId == null
      ? await asUser.rpc('publish_draft', { p_note: note })
      : await asUser.rpc('make_version_live', { p_version_id: versionId });
  if (publishError) {
    const status = publishError.code === '42501' ? 403 : 400;
    return json({ error: publishError.message }, status);
  }

  try {
    // Only a new publish gets an archive copy; a re-activated version already had one.
    const { features } = await writePublishedGeojson(admin, versionId == null ? published.version_no : undefined);
    return json({ ok: true, ...published, features });
  } catch (e) {
    // The database is already updated; the map will catch up on the next
    // successful rebuild (regenerate-projects-geojson, npm run
    // upload-geojson-merged-conf1, or another publish).
    return json(
      {
        error: `Version ${published.version_no} is live in the database, but updating the map file failed: ${String(e)}`,
        ...published,
        geojsonFailed: true,
      },
      502,
    );
  }
});
