import { DRAFT_SELECT, EDITABLE_KEYS, ROW_KEYS } from './fieldSchema.js';

const PAGE_SIZE = 1000;

function raise(error, context) {
  if (error) throw new Error(`${context}: ${error.message}`);
}

async function fetchAllRows(source, label) {
  const rows = [];
  for (let offset = 0; ; offset += PAGE_SIZE) {
    const { data, error } = await source()
      .select(DRAFT_SELECT)
      .order('id', { ascending: true })
      .range(offset, offset + PAGE_SIZE - 1);
    raise(error, `Loading ${label}`);
    rows.push(...data);
    if (data.length < PAGE_SIZE) break;
  }
  return rows;
}

export const fetchDraftRows = (client) => fetchAllRows(() => client.from('projects_draft'), 'the draft');
export const fetchPublishedRows = (client) =>
  fetchAllRows(() => client.rpc('admin_published_rows'), 'the live rows');

const VERSION_COLUMNS = 'id, version_no, name, created_at, created_by, note, row_count, is_current';

export async function fetchVersions(client) {
  const { data, error } = await client
    .from('projects_versions')
    .select(VERSION_COLUMNS)
    .order('version_no', { ascending: false });
  raise(error, 'Loading versions');
  return data;
}

export async function fetchVersionSnapshot(client, versionId) {
  const { data, error } = await client
    .from('projects_versions')
    .select('snapshot')
    .eq('id', versionId)
    .single();
  raise(error, 'Loading version');
  return data.snapshot ?? [];
}

function pick(row, keys) {
  return Object.fromEntries(keys.map((k) => [k, row[k] ?? null]));
}

/**
 * Persists local edits to projects_draft in one transaction (save_draft_changes).
 *   updates: full rows (existing ids)
 *   inserts: new rows (the database assigns ids)
 *   deletes: ids to remove
 */
export async function saveDraftChanges(client, { updates, inserts, deletes }) {
  const { data, error } = await client.rpc('save_draft_changes', {
    p_updates: updates.map((row) => pick(row, ROW_KEYS)),
    p_inserts: inserts.map((row) => pick(row, [...EDITABLE_KEYS, 'tract_geoid'])),
    p_deletes: deletes,
  });
  raise(error, 'Saving draft');
  return data;
}

async function invokePublishFunction(client, body) {
  const { data, error } = await client.functions.invoke('publish-projects', { body });
  if (error) {
    if (error.name === 'FunctionsFetchError') {
      throw new Error(
        'Could not reach the publish-projects edge function, so nothing was published. ' +
          'Check that it is deployed (supabase functions deploy publish-projects) and that you are online.',
      );
    }
    let message = error.message;
    try {
      const body = await error.context?.json?.();
      if (body?.error) message = body.error;
    } catch {
      // keep the generic message
    }
    throw new Error(message);
  }
  return data;
}

/** Publishes the draft as a new version. Resolves to { version_no, row_count, features }. */
export const publishDraft = (client, note) => invokePublishFunction(client, { note });

/** Puts an existing version back on the map without creating a new one. */
export const makeVersionLive = (client, versionId) => invokePublishFunction(client, { versionId });

/** Rewrites the public map file from the live table; no data changes. */
export const rebuildMapFile = (client) => invokePublishFunction(client, { rebuild: true });

export async function renameVersion(client, versionId, name) {
  const { data, error } = await client.rpc('rename_version', { p_version_id: versionId, p_name: name });
  raise(error, 'Renaming version');
  return data;
}

export async function deleteVersion(client, versionId) {
  const { data, error } = await client.rpc('delete_version', { p_version_id: versionId });
  raise(error, 'Deleting version');
  return data;
}

export async function restoreVersionToDraft(client, versionId) {
  const { data, error } = await client.rpc('restore_version', { p_version_id: versionId });
  raise(error, 'Restoring version');
  return data;
}

export async function resetDraftFromPublished(client) {
  const { data, error } = await client.rpc('reset_draft_from_published');
  raise(error, 'Resetting draft');
  return data;
}
