import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DraftContext, isNewRowId, useAdminAuth } from './contexts.js';
import {
  fetchDraftRows,
  fetchPublishedRows,
  fetchVersions,
  publishDraft,
  renameVersion as renameVersionApi,
  deleteVersion as deleteVersionApi,
  makeVersionLive as makeVersionLiveApi,
  rebuildMapFile as rebuildMapFileApi,
  resetDraftFromPublished,
  restoreVersionToDraft,
  saveDraftChanges,
} from './api.js';
import { diffCount, diffRows, valuesEqual } from './diff.js';
import { emptyRow } from './fieldSchema.js';
import { nextProjectId } from './projectId.js';
import { loadTractLookup } from './tractLookup.js';
import { validateRows } from './validation.js';

/**
 * Local edits on top of the saved draft:
 *   patches     Map<id, { field: value }> for saved rows (only fields that differ)
 *   newRows     rows added locally, with temporary "new-N" ids. `_autoId` marks
 *               rows whose Project ID (implementa) is generated; it is never saved.
 *   deletedIds  Set of saved row ids marked for deletion
 */
export function DraftProvider({ children, api: apiOverrides }) {
  const { client } = useAdminAuth();
  const api = useMemo(
    () => ({
      fetchDraftRows,
      fetchPublishedRows,
      fetchVersions,
      publishDraft,
      renameVersion: renameVersionApi,
      deleteVersion: deleteVersionApi,
      makeVersionLive: makeVersionLiveApi,
      rebuildMapFile: rebuildMapFileApi,
      resetDraftFromPublished,
      restoreVersionToDraft,
      saveDraftChanges,
      loadTractLookup,
      ...apiOverrides,
    }),
    [apiOverrides],
  );

  const [serverRows, setServerRows] = useState([]);
  const [publishedRows, setPublishedRows] = useState([]);
  const [versions, setVersions] = useState([]);
  const [load, setLoad] = useState({ status: 'loading', error: null });
  const [patches, setPatches] = useState(() => new Map());
  const [newRows, setNewRows] = useState([]);
  const [deletedIds, setDeletedIds] = useState(() => new Set());
  const [busy, setBusy] = useState(null);
  const newIdCounter = useRef(0);

  const clearLocal = useCallback(() => {
    setPatches(new Map());
    setNewRows([]);
    setDeletedIds(new Set());
  }, []);

  const reload = useCallback(async () => {
    setLoad((prev) => ({ status: prev.status === 'ready' ? 'refreshing' : 'loading', error: null }));
    try {
      const [draft, published, versionList] = await Promise.all([
        api.fetchDraftRows(client),
        api.fetchPublishedRows(client),
        api.fetchVersions(client),
      ]);
      setServerRows(draft);
      setPublishedRows(published);
      setVersions(versionList);
      clearLocal();
      setLoad({ status: 'ready', error: null });
    } catch (e) {
      setLoad({ status: 'error', error: e.message });
    }
  }, [api, client, clearLocal]);

  useEffect(() => {
    reload();
  }, [reload]);

  const serverById = useMemo(() => new Map(serverRows.map((r) => [r.id, r])), [serverRows]);

  const rows = useMemo(() => {
    const merged = serverRows.map((r) => (patches.has(r.id) ? { ...r, ...patches.get(r.id) } : r));
    return [...newRows, ...merged];
  }, [serverRows, patches, newRows]);

  const activeRows = useMemo(() => rows.filter((r) => !deletedIds.has(r.id)), [rows, deletedIds]);
  const validation = useMemo(() => validateRows(activeRows), [activeRows]);

  const unsavedCount = patches.size + newRows.length + deletedIds.size;
  const unpublishedDiff = useMemo(() => diffRows(publishedRows, serverRows), [publishedRows, serverRows]);
  const currentVersion = versions.find((v) => v.is_current) ?? null;

  const rowState = useCallback(
    (id) => {
      if (isNewRowId(id)) return 'new';
      if (deletedIds.has(id)) return 'deleted';
      if (patches.has(id)) return 'edited';
      return null;
    },
    [deletedIds, patches],
  );

  const editedFields = useCallback((id) => Object.keys(patches.get(id) ?? {}), [patches]);

  const updateCell = useCallback(
    (id, key, value) => {
      if (isNewRowId(id)) {
        setNewRows((prev) =>
          prev.map((r) => {
            if (r.id !== id) return r;
            const next = { ...r, [key]: value };
            if (key === 'implementa') next._autoId = false;
            return next;
          }),
        );
        return;
      }
      const original = serverById.get(id);
      if (!original) return;
      setPatches((prev) => {
        const next = new Map(prev);
        const patch = { ...(next.get(id) ?? {}) };
        if (valuesEqual(original[key], value)) delete patch[key];
        else patch[key] = value;
        if (Object.keys(patch).length) next.set(id, patch);
        else next.delete(id);
        return next;
      });
    },
    [serverById],
  );

  // Published rows are included so an id deleted from the draft but still live
  // is not handed out again before the next publish.
  const generateProjectId = useCallback(
    (excludeId) =>
      nextProjectId(
        [...rows, ...publishedRows].filter((r) => r.id !== excludeId).map((r) => r.implementa),
      ),
    [rows, publishedRows],
  );

  const addRow = useCallback(() => {
    newIdCounter.current += 1;
    const id = `new-${newIdCounter.current}`;
    const implementa = generateProjectId();
    setNewRows((prev) => [{ ...emptyRow(), id, implementa, _autoId: true }, ...prev]);
    return id;
  }, [generateProjectId]);

  /** Turns automatic Project ID generation on or off for a new row. */
  const setAutoProjectId = useCallback(
    (id, on) => {
      if (!isNewRowId(id)) return;
      const implementa = on ? generateProjectId(id) : undefined;
      setNewRows((prev) =>
        prev.map((r) => {
          if (r.id !== id) return r;
          return on ? { ...r, implementa, _autoId: true } : { ...r, _autoId: false };
        }),
      );
    },
    [generateProjectId],
  );

  const deleteRows = useCallback((ids) => {
    const list = [...ids];
    setNewRows((prev) => prev.filter((r) => !list.includes(r.id)));
    setDeletedIds((prev) => {
      const next = new Set(prev);
      for (const id of list) if (!isNewRowId(id)) next.add(id);
      return next;
    });
  }, []);

  const restoreRows = useCallback((ids) => {
    setDeletedIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) next.delete(id);
      return next;
    });
  }, []);

  const revertRow = useCallback(
    (id) => {
      if (isNewRowId(id)) {
        deleteRows([id]);
        return;
      }
      setPatches((prev) => {
        const next = new Map(prev);
        next.delete(id);
        return next;
      });
      restoreRows([id]);
    },
    [deleteRows, restoreRows],
  );

  /** Resolves to { ok: true, tractWarning? } or { ok: false, error }. */
  const save = useCallback(async () => {
    const changedIds = new Set([...patches.keys(), ...newRows.map((r) => r.id)]);
    const blocking = [...changedIds].filter((id) => {
      const result = validation.byId.get(id);
      return result && Object.keys(result.errors).length;
    });
    if (blocking.length) {
      return {
        ok: false,
        error: `${blocking.length} changed row${blocking.length === 1 ? ' has' : 's have'} errors. Fix the highlighted cells, then save again.`,
      };
    }

    setBusy('saving');
    try {
      const updates = [];
      for (const [id, patch] of patches) {
        if (deletedIds.has(id)) continue;
        updates.push({ ...serverById.get(id), ...patch, _moved: 'latitude' in patch || 'longitude' in patch });
      }
      const inserts = newRows.map((r) => ({ ...r, _moved: true }));

      let tractWarning = null;
      const needsTract = [...updates, ...inserts].filter((r) => r._moved);
      if (needsTract.length) {
        try {
          const lookup = await api.loadTractLookup();
          for (const row of needsTract) row.tract_geoid = lookup(row.longitude, row.latitude);
        } catch (e) {
          for (const row of needsTract) row.tract_geoid = null;
          tractWarning = `Saved, but census tracts could not be assigned (${e.message}).`;
        }
      }

      await api.saveDraftChanges(client, { updates, inserts, deletes: [...deletedIds] });
      await reload();
      return { ok: true, tractWarning };
    } catch (e) {
      return { ok: false, error: e.message };
    } finally {
      setBusy(null);
    }
  }, [api, client, deletedIds, newRows, patches, reload, serverById, validation]);

  const publish = useCallback(
    async (note) => {
      setBusy('publishing');
      try {
        const result = await api.publishDraft(client, note);
        await reload();
        return { ok: true, result };
      } catch (e) {
        await reload();
        return { ok: false, error: e.message };
      } finally {
        setBusy(null);
      }
    },
    [api, client, reload],
  );

  const makeVersionLive = useCallback(
    async (versionId) => {
      setBusy('publishing');
      try {
        const result = await api.makeVersionLive(client, versionId);
        await reload();
        return { ok: true, result };
      } catch (e) {
        await reload();
        return { ok: false, error: e.message };
      } finally {
        setBusy(null);
      }
    },
    [api, client, reload],
  );

  const rebuildMapFile = useCallback(async () => {
    setBusy('publishing');
    try {
      const result = await api.rebuildMapFile(client);
      return { ok: true, result };
    } catch (e) {
      return { ok: false, error: e.message };
    } finally {
      setBusy(null);
    }
  }, [api, client]);

  const restoreVersion = useCallback(
    async (versionId) => {
      setBusy('restoring');
      try {
        const result = await api.restoreVersionToDraft(client, versionId);
        await reload();
        return { ok: true, result };
      } catch (e) {
        return { ok: false, error: e.message };
      } finally {
        setBusy(null);
      }
    },
    [api, client, reload],
  );

  // Version-list changes refresh only the list, so unsaved draft edits survive.
  const updateVersions = useCallback(
    async (change) => {
      try {
        await change();
        setVersions(await api.fetchVersions(client));
        return { ok: true };
      } catch (e) {
        return { ok: false, error: e.message };
      }
    },
    [api, client],
  );

  const renameVersion = useCallback(
    (versionId, name) => updateVersions(() => api.renameVersion(client, versionId, name)),
    [api, client, updateVersions],
  );

  const deleteVersion = useCallback(
    (versionId) => updateVersions(() => api.deleteVersion(client, versionId)),
    [api, client, updateVersions],
  );

  const resetDraft = useCallback(async () => {
    setBusy('resetting');
    try {
      await api.resetDraftFromPublished(client);
      await reload();
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    } finally {
      setBusy(null);
    }
  }, [api, client, reload]);

  const value = useMemo(
    () => ({
      load,
      busy,
      rows,
      serverRows,
      publishedRows,
      versions,
      currentVersion,
      validation,
      unsavedCount,
      unpublishedDiff,
      unpublishedCount: diffCount(unpublishedDiff),
      rowState,
      editedFields,
      updateCell,
      addRow,
      setAutoProjectId,
      deleteRows,
      restoreRows,
      revertRow,
      discard: clearLocal,
      save,
      publish,
      restoreVersion,
      renameVersion,
      deleteVersion,
      makeVersionLive,
      rebuildMapFile,
      resetDraft,
      reload,
      client,
    }),
    [
      load,
      busy,
      rows,
      serverRows,
      publishedRows,
      versions,
      currentVersion,
      validation,
      unsavedCount,
      unpublishedDiff,
      rowState,
      editedFields,
      updateCell,
      addRow,
      setAutoProjectId,
      deleteRows,
      restoreRows,
      revertRow,
      clearLocal,
      save,
      publish,
      restoreVersion,
      renameVersion,
      deleteVersion,
      makeVersionLive,
      rebuildMapFile,
      resetDraft,
      reload,
      client,
    ],
  );

  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>;
}
