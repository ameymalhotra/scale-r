import { fetchFilterState } from './api.js';
import { cloneConfig } from '../filters/filterConfig.js';
import { readLocalFilterState, writeLocalFilterState } from '../filters/localFilters.js';

/**
 * Same calls as the filter functions in api.js, kept in localStorage (see
 * filters/localFilters.js). The first load copies the real draft and history
 * from Supabase (read only) so testing starts from what is live.
 */

const now = () => new Date().toISOString();

async function state(client) {
  const saved = readLocalFilterState();
  if (saved) return saved;
  const real = await fetchFilterState(client);
  const seeded = { draft: real.draft, versions: real.versions };
  writeLocalFilterState(seeded);
  return seeded;
}

const update = async (client, change) => {
  const next = change(cloneConfig(await state(client)));
  writeLocalFilterState(next);
  return next;
};

const findVersion = (s, versionId) => {
  const version = s.versions.find((v) => v.id === versionId);
  if (!version) throw new Error('That filter version no longer exists');
  return version;
};

export const localFiltersApi = {
  fetchFilterState: (client) => state(client),

  saveFiltersDraft: (client, config) =>
    update(client, (s) => ({ ...s, draft: cloneConfig(config) })).then(() => undefined),

  publishFilters: async (client, note, name) => {
    if (!note) throw new Error('A publish note is required');
    let published;
    await update(client, (s) => {
      if (!s.draft) throw new Error('Save the filter draft before publishing');
      const versionNo = Math.max(0, ...s.versions.map((v) => v.version_no)) + 1;
      const id = Math.max(0, ...s.versions.map((v) => v.id)) + 1;
      published = { version_id: id, version_no: versionNo };
      const versions = s.versions.map((v) => ({ ...v, is_current: false }));
      versions.unshift({
        id,
        version_no: versionNo,
        name: name || null,
        note,
        config: cloneConfig(s.draft),
        is_current: true,
        created_at: now(),
        created_by: 'local test',
      });
      return { ...s, versions };
    });
    return published;
  },

  makeFiltersVersionLive: async (client, versionId) => {
    let live;
    await update(client, (s) => {
      live = findVersion(s, versionId);
      return {
        draft: cloneConfig(live.config),
        versions: s.versions.map((v) => ({ ...v, is_current: v.id === versionId })),
      };
    });
    return { version_id: live.id, version_no: live.version_no };
  },

  restoreFiltersVersion: (client, versionId) =>
    update(client, (s) => ({ ...s, draft: cloneConfig(findVersion(s, versionId).config) })).then(() => undefined),

  renameFiltersVersion: (client, versionId, name) =>
    update(client, (s) => ({
      ...s,
      versions: s.versions.map((v) => (v.id === versionId ? { ...v, name: name?.trim() || null } : v)),
    })).then(() => undefined),

  deleteFiltersVersion: (client, versionId) =>
    update(client, (s) => {
      if (findVersion(s, versionId).is_current) throw new Error('The live filter version cannot be deleted');
      return { ...s, versions: s.versions.filter((v) => v.id !== versionId) };
    }).then(() => undefined),

  resetFiltersDraft: (client) =>
    update(client, (s) => ({ ...s, draft: s.versions.find((v) => v.is_current)?.config ?? null })).then(
      () => undefined,
    ),
};
