import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { builtinForFile } from '../layers/builtinRegistry.js';
import { reprojectFeatureCollectionIfNeeded } from '../utils/geoProcessing.js';
import { LayersContext, useAdminAuth } from './contexts.js';
import {
  deleteLayersVersion,
  fetchLayerGeojson,
  fetchLayerState,
  makeLayersVersionLive,
  publishLayers,
  renameLayersVersion,
  resetLayersDraft,
  restoreLayersVersion,
  saveLayersDraft,
  uploadLayerFile,
} from './api.js';
import {
  EMPTY_LAYER_CONFIG,
  cloneConfig,
  normalizeLayerConfig,
  sameLayerSettings,
  validateLayerConfig,
} from '../layers/layerConfig.js';
import { LOCAL_LAYERS } from '../layers/localLayers.js';
import { localLayersApi } from './localLayersApi.js';

/**
 * Uploaded map layers for /admin/layers:
 *   liveConfig   what the map shows now (current layer version, or no layers)
 *   savedDraft   the shared draft in layers_draft (liveConfig when empty)
 *   draft        local edits on top of savedDraft
 * Layer GeoJSON is cached by storage path, so attribute values for the
 * symbology editor and the preview load once per file.
 */
export function LayersProvider({ children, api: apiOverrides }) {
  const { client } = useAdminAuth();
  const api = useMemo(
    () => ({
      fetchLayerState,
      saveLayersDraft,
      publishLayers,
      makeLayersVersionLive,
      restoreLayersVersion,
      renameLayersVersion,
      deleteLayersVersion,
      resetLayersDraft,
      uploadLayerFile,
      fetchLayerGeojson,
      ...(LOCAL_LAYERS ? localLayersApi : null),
      ...apiOverrides,
    }),
    [apiOverrides],
  );

  const [versions, setVersions] = useState([]);
  const [savedDraft, setSavedDraft] = useState(() => cloneConfig(EMPTY_LAYER_CONFIG));
  const [draft, setDraft] = useState(() => cloneConfig(EMPTY_LAYER_CONFIG));
  const [load, setLoad] = useState({ status: 'loading', error: null });
  const [busy, setBusy] = useState(null);
  const geojsonCache = useRef(new Map());

  const liveVersion = versions.find((v) => v.is_current) ?? null;
  const liveConfig = useMemo(
    () => (liveVersion ? normalizeLayerConfig(liveVersion.config) : cloneConfig(EMPTY_LAYER_CONFIG)),
    [liveVersion],
  );

  const reload = useCallback(async () => {
    setLoad((prev) => ({ status: prev.status === 'ready' ? 'refreshing' : 'loading', error: null }));
    try {
      const state = await api.fetchLayerState(client);
      const current = state.versions.find((v) => v.is_current);
      const saved = normalizeLayerConfig(state.draft ?? current?.config ?? null);
      setVersions(state.versions);
      setSavedDraft(saved);
      setDraft(cloneConfig(saved));
      setLoad({ status: 'ready', error: null });
    } catch (e) {
      setLoad({ status: 'error', error: e.message });
    }
  }, [api, client]);

  useEffect(() => {
    reload();
  }, [reload]);

  const errors = useMemo(() => validateLayerConfig(draft), [draft]);
  const hasUnsaved = !sameLayerSettings(draft, savedDraft);
  const hasUnpublished = !sameLayerSettings(savedDraft, liveConfig);
  const differsFromLive = !sameLayerSettings(draft, liveConfig);

  const run = useCallback(async (label, fn) => {
    setBusy(label);
    try {
      const result = await fn();
      return { ok: true, result };
    } catch (e) {
      return { ok: false, error: e.message };
    } finally {
      setBusy(null);
    }
  }, []);

  const save = useCallback(
    () =>
      run('saving', async () => {
        if (errors.length) throw new Error(errors[0]);
        await api.saveLayersDraft(client, draft);
        await reload();
      }),
    [api, client, draft, errors, reload, run],
  );

  /** Saves the on-screen draft first, so exactly what is shown gets published. */
  const publish = useCallback(
    (note, name) =>
      run('publishing', async () => {
        if (errors.length) throw new Error(errors[0]);
        await api.saveLayersDraft(client, draft);
        try {
          return await api.publishLayers(client, note, name);
        } finally {
          await reload();
        }
      }),
    [api, client, draft, errors, reload, run],
  );

  const makeLive = useCallback(
    (versionId) =>
      run('publishing', async () => {
        try {
          return await api.makeLayersVersionLive(client, versionId);
        } finally {
          await reload();
        }
      }),
    [api, client, reload, run],
  );

  const restore = useCallback(
    (versionId) =>
      run('restoring', async () => {
        await api.restoreLayersVersion(client, versionId);
        await reload();
      }),
    [api, client, reload, run],
  );

  const resetToLive = useCallback(
    () =>
      run('resetting', async () => {
        await api.resetLayersDraft(client);
        await reload();
      }),
    [api, client, reload, run],
  );

  const refreshVersions = useCallback(async () => {
    const state = await api.fetchLayerState(client);
    setVersions(state.versions);
  }, [api, client]);

  const rename = useCallback(
    (versionId, name) =>
      run(null, async () => {
        await api.renameLayersVersion(client, versionId, name);
        await refreshVersions();
      }),
    [api, client, refreshVersions, run],
  );

  const remove = useCallback(
    (versionId) =>
      run(null, async () => {
        await api.deleteLayersVersion(client, versionId);
        await refreshVersions();
      }),
    [api, client, refreshVersions, run],
  );

  const discard = useCallback(() => setDraft(cloneConfig(savedDraft)), [savedDraft]);

  /** Uploads checked GeoJSON for a layer. Resolves to the storage path; the data is cached. */
  const uploadFile = useCallback(
    async (layerId, geojson) => {
      setBusy('uploading');
      try {
        const path = await api.uploadLayerFile(client, layerId, geojson);
        geojsonCache.current.set(path, Promise.resolve(geojson));
        return path;
      } finally {
        setBusy(null);
      }
    },
    [api, client],
  );

  const loadGeojson = useCallback(
    (path) => {
      const cache = geojsonCache.current;
      if (!cache.has(path)) {
        const pending = (async () => {
          const builtin = builtinForFile(path);
          if (!builtin) return api.fetchLayerGeojson(client, path);
          if (builtin.group) return { type: 'FeatureCollection', features: [] };
          if (builtin.sourceType === 'vector') return { type: 'FeatureCollection', features: [] };
          if (builtin.census) {
            const { runTask } = await import('../workers/dataParser.core.js');
            const result = await runTask('census', { censusUrl: '/femaindex.geojson', creUrl: '/FL_CRE.csv' });
            try {
              const response = await fetch(result.censusSourceUrl);
              return await response.json();
            } finally { URL.revokeObjectURL(result.censusSourceUrl); }
          }
          const url = builtin.sourcePath.startsWith('/') ? builtin.sourcePath : client.storage.from('project-data').getPublicUrl(builtin.sourcePath).data.publicUrl;
          const response = await fetch(url);
          if (!response.ok) throw new Error(`Loading ${builtin.label}: HTTP ${response.status}`);
          const data = reprojectFeatureCollectionIfNeeded(await response.json());
          if (builtin.id === 'overlay-emergency-medical') {
            for (const feature of data.features) {
              const x = Number(feature.properties?.X), y = Number(feature.properties?.Y);
              if (feature.properties?.X != null && feature.properties?.Y != null && Number.isFinite(x) && Number.isFinite(y) && Math.abs(x) <= 180 && Math.abs(y) <= 90) feature.geometry = { type: 'Point', coordinates: [x, y] };
            }
          }
          return data;
        })().catch((e) => {
          cache.delete(path);
          throw e;
        });
        cache.set(path, pending);
      }
      return cache.get(path);
    },
    [api, client],
  );

  const value = useMemo(
    () => ({
      load,
      busy,
      versions,
      liveVersion,
      liveConfig,
      savedDraft,
      draft,
      setDraft,
      errors,
      hasUnsaved,
      hasUnpublished,
      differsFromLive,
      save,
      discard,
      publish,
      makeLive,
      restore,
      resetToLive,
      rename,
      remove,
      reload,
      uploadFile,
      loadGeojson,
    }),
    [
      load,
      busy,
      versions,
      liveVersion,
      liveConfig,
      savedDraft,
      draft,
      errors,
      hasUnsaved,
      hasUnpublished,
      differsFromLive,
      save,
      discard,
      publish,
      makeLive,
      restore,
      resetToLive,
      rename,
      remove,
      reload,
      uploadFile,
      loadGeojson,
    ],
  );

  return <LayersContext.Provider value={value}>{children}</LayersContext.Provider>;
}
