import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FiltersContext, useAdminAuth } from './contexts.js';
import {
  deleteFiltersVersion,
  fetchFilterState,
  makeFiltersVersionLive,
  publishFilters,
  renameFiltersVersion,
  resetFiltersDraft,
  restoreFiltersVersion,
  saveFiltersDraft,
} from './api.js';
import {
  DEFAULT_FILTER_CONFIG,
  cloneConfig,
  normalizeFilterConfig,
  sameSettings,
  validateFilterConfig,
} from '../filters/filterConfig.js';
import { LOCAL_FILTERS } from '../filters/localFilters.js';
import { localFiltersApi } from './localFiltersApi.js';

/**
 * Map filter settings for /admin/live-tool:
 *   liveConfig   what the map uses now (current filter version, or the
 *                built-in defaults when nothing has been published)
 *   savedDraft   the shared draft in filters_draft (liveConfig when empty)
 *   draft        local edits on top of savedDraft
 */
export function FiltersProvider({ children, api: apiOverrides }) {
  const { client } = useAdminAuth();
  const api = useMemo(
    () => ({
      fetchFilterState,
      saveFiltersDraft,
      publishFilters,
      makeFiltersVersionLive,
      restoreFiltersVersion,
      renameFiltersVersion,
      deleteFiltersVersion,
      resetFiltersDraft,
      ...(LOCAL_FILTERS ? localFiltersApi : null),
      ...apiOverrides,
    }),
    [apiOverrides],
  );

  const [versions, setVersions] = useState([]);
  const [savedDraft, setSavedDraft] = useState(() => cloneConfig(DEFAULT_FILTER_CONFIG));
  const [draft, setDraft] = useState(() => cloneConfig(DEFAULT_FILTER_CONFIG));
  const [load, setLoad] = useState({ status: 'loading', error: null });
  const [busy, setBusy] = useState(null);

  const liveVersion = versions.find((v) => v.is_current) ?? null;
  const liveConfig = useMemo(
    () => (liveVersion ? normalizeFilterConfig(liveVersion.config) : cloneConfig(DEFAULT_FILTER_CONFIG)),
    [liveVersion],
  );

  const reload = useCallback(async () => {
    setLoad((prev) => ({ status: prev.status === 'ready' ? 'refreshing' : 'loading', error: null }));
    try {
      const state = await api.fetchFilterState(client);
      const current = state.versions.find((v) => v.is_current);
      const saved = normalizeFilterConfig(state.draft ?? current?.config ?? null);
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

  const errors = useMemo(() => validateFilterConfig(draft), [draft]);
  const hasUnsaved = !sameSettings(draft, savedDraft);
  const hasUnpublished = !sameSettings(savedDraft, liveConfig);
  const differsFromLive = !sameSettings(draft, liveConfig);

  const run = useCallback(
    async (label, fn) => {
      setBusy(label);
      try {
        const result = await fn();
        return { ok: true, result };
      } catch (e) {
        return { ok: false, error: e.message };
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  const save = useCallback(
    () =>
      run('saving', async () => {
        if (errors.length) throw new Error(errors[0]);
        await api.saveFiltersDraft(client, draft);
        await reload();
      }),
    [api, client, draft, errors, reload, run],
  );

  /** Saves the on-screen draft first, so exactly what is shown gets published. */
  const publish = useCallback(
    (note, name) =>
      run('publishing', async () => {
        if (errors.length) throw new Error(errors[0]);
        await api.saveFiltersDraft(client, draft);
        try {
          return await api.publishFilters(client, note, name);
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
          return await api.makeFiltersVersionLive(client, versionId);
        } finally {
          await reload();
        }
      }),
    [api, client, reload, run],
  );

  const restore = useCallback(
    (versionId) =>
      run('restoring', async () => {
        await api.restoreFiltersVersion(client, versionId);
        await reload();
      }),
    [api, client, reload, run],
  );

  const resetToLive = useCallback(
    () =>
      run('resetting', async () => {
        await api.resetFiltersDraft(client);
        await reload();
      }),
    [api, client, reload, run],
  );

  // Version-list changes refresh only the list, so unsaved edits survive.
  const refreshVersions = useCallback(async () => {
    const state = await api.fetchFilterState(client);
    setVersions(state.versions);
  }, [api, client]);

  const rename = useCallback(
    (versionId, name) =>
      run(null, async () => {
        await api.renameFiltersVersion(client, versionId, name);
        await refreshVersions();
      }),
    [api, client, refreshVersions, run],
  );

  const remove = useCallback(
    (versionId) =>
      run(null, async () => {
        await api.deleteFiltersVersion(client, versionId);
        await refreshVersions();
      }),
    [api, client, refreshVersions, run],
  );

  const discard = useCallback(() => setDraft(cloneConfig(savedDraft)), [savedDraft]);

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
    ],
  );

  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}
