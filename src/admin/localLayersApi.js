import { fetchLayerGeojson, fetchLayerState } from './api.js';
import { cloneConfig } from '../layers/layerConfig.js';
import {
  getLocalLayerFile,
  putLocalLayerFile,
  readLocalLayerState,
  writeLocalLayerState,
} from '../layers/localLayers.js';

/**
 * Same calls as the layer functions in api.js, kept in this browser (see
 * layers/localLayers.js). The first load copies the real draft and history
 * from Supabase (read only) so testing starts from what is live.
 */

const now = () => new Date().toISOString();

async function state(client) {
  const saved = readLocalLayerState();
  if (saved) return saved;
  const real = await fetchLayerState(client);
  const seeded = { draft: real.draft, versions: real.versions };
  writeLocalLayerState(seeded);
  return seeded;
}

const update = async (client, change) => {
  const next = change(structuredClone(await state(client)));
  writeLocalLayerState(next);
  return next;
};

const findVersion = (s, versionId) => {
  const version = s.versions.find((v) => v.id === versionId);
  if (!version) throw new Error('That layer version no longer exists');
  return version;
};

export const localLayersApi = {
  fetchLayerState: (client) => state(client),

  saveLayersDraft: (client, config) =>
    update(client, (s) => ({ ...s, draft: cloneConfig(config) })).then(() => undefined),

  publishLayers: async (client, note, name) => {
    if (!note) throw new Error('A publish note is required');
    let published;
    await update(client, (s) => {
      if (!s.draft) throw new Error('Save the layer draft before publishing');
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

  makeLayersVersionLive: async (client, versionId) => {
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

  restoreLayersVersion: (client, versionId) =>
    update(client, (s) => ({ ...s, draft: cloneConfig(findVersion(s, versionId).config) })).then(() => undefined),

  renameLayersVersion: (client, versionId, name) =>
    update(client, (s) => ({
      ...s,
      versions: s.versions.map((v) => (v.id === versionId ? { ...v, name: name?.trim() || null } : v)),
    })).then(() => undefined),

  deleteLayersVersion: (client, versionId) =>
    update(client, (s) => {
      if (findVersion(s, versionId).is_current) throw new Error('The live layer version cannot be deleted');
      return { ...s, versions: s.versions.filter((v) => v.id !== versionId) };
    }).then(() => undefined),

  resetLayersDraft: (client) =>
    update(client, (s) => ({ ...s, draft: s.versions.find((v) => v.is_current)?.config ?? null })).then(
      () => undefined,
    ),

  uploadLayerFile: async (client, layerId, geojson) => {
    const suffix = Math.random().toString(36).slice(2, 10);
    const path = `layers/${layerId}-${suffix}.geojson`;
    await putLocalLayerFile(path, geojson);
    return path;
  },

  fetchLayerGeojson: async (client, path) => (await getLocalLayerFile(path)) ?? fetchLayerGeojson(client, path),
};
