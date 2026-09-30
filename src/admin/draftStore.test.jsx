import React, { useMemo } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { act, render, waitFor } from '@testing-library/react';
import { AdminAuthContext, useDraft } from './contexts.js';
import { DraftProvider } from './draftStore.jsx';

const saved = [
  {
    id: 10,
    implementa: 'SCALER-0010',
    project_na: 'Seawall',
    latitude: 25.77,
    longitude: -80.13,
    estimated_cost: 1000,
    tract_geoid: '12086000100',
  },
  {
    id: 11,
    implementa: 'SCALER-0011',
    project_na: 'Pump station',
    latitude: 25.8,
    longitude: -80.2,
    estimated_cost: 2000,
    tract_geoid: '12086000200',
  },
];

function setup() {
  const api = {
    fetchDraftRows: vi.fn().mockResolvedValue(saved),
    fetchPublishedRows: vi.fn().mockResolvedValue(saved),
    fetchVersions: vi.fn().mockResolvedValue([{ id: 1, version_no: 1, is_current: true }]),
    saveDraftChanges: vi.fn().mockResolvedValue({}),
    publishDraft: vi.fn().mockResolvedValue({ version_no: 2, row_count: 2 }),
    loadTractLookup: vi.fn().mockResolvedValue(() => '12086009999'),
  };
  const draft = { current: null };

  function Probe() {
    draft.current = useDraft();
    return null;
  }
  function Harness() {
    const auth = useMemo(() => ({ client: {} }), []);
    return (
      <AdminAuthContext.Provider value={auth}>
        <DraftProvider api={api}>
          <Probe />
        </DraftProvider>
      </AdminAuthContext.Provider>
    );
  }

  render(<Harness />);
  return { api, draft };
}

describe('DraftProvider', () => {
  it('tracks edits, drops edits that return to the saved value, and counts unsaved changes', async () => {
    const { draft } = setup();
    await waitFor(() => expect(draft.current.load.status).toBe('ready'));

    act(() => draft.current.updateCell(10, 'estimated_cost', 5000));
    expect(draft.current.unsavedCount).toBe(1);
    expect(draft.current.rowState(10)).toBe('edited');
    expect(draft.current.editedFields(10)).toEqual(['estimated_cost']);

    act(() => draft.current.updateCell(10, 'estimated_cost', 1000));
    expect(draft.current.unsavedCount).toBe(0);
    expect(draft.current.rowState(10)).toBeNull();
  });

  it('saves edits, new rows and deletions in one call and assigns tracts only to moved or new rows', async () => {
    const { api, draft } = setup();
    await waitFor(() => expect(draft.current.load.status).toBe('ready'));

    let newId;
    act(() => {
      draft.current.updateCell(10, 'project_na', 'Seawall phase 2');
      draft.current.updateCell(11, 'latitude', 25.81);
      newId = draft.current.addRow();
    });
    act(() => {
      draft.current.updateCell(newId, 'implementa', 'SCALER-9000');
      draft.current.updateCell(newId, 'project_na', 'Living shoreline');
      draft.current.updateCell(newId, 'latitude', 25.6);
      draft.current.updateCell(newId, 'longitude', -80.3);
      draft.current.updateCell(newId, 'estimated_cost', 10);
    });

    let result;
    await act(async () => {
      result = await draft.current.save();
    });
    expect(result.ok).toBe(true);

    const payload = api.saveDraftChanges.mock.calls[0][1];
    const byId = Object.fromEntries(payload.updates.map((r) => [r.id, r]));
    expect(byId[10].project_na).toBe('Seawall phase 2');
    expect(byId[10].tract_geoid).toBe('12086000100');
    expect(byId[11].tract_geoid).toBe('12086009999');
    expect(payload.inserts).toHaveLength(1);
    expect(payload.inserts[0]).toMatchObject({ project_na: 'Living shoreline', tract_geoid: '12086009999' });
    expect(payload.deletes).toEqual([]);
    expect(api.fetchDraftRows).toHaveBeenCalledTimes(2);
  });

  it('refuses to save a changed row that has validation errors', async () => {
    const { api, draft } = setup();
    await waitFor(() => expect(draft.current.load.status).toBe('ready'));

    act(() => draft.current.updateCell(11, 'implementa', 'SCALER-0010'));
    let result;
    await act(async () => {
      result = await draft.current.save();
    });
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/errors/);
    expect(api.saveDraftChanges).not.toHaveBeenCalled();
  });

  it('sends deletions and removes unsaved new rows locally', async () => {
    const { api, draft } = setup();
    await waitFor(() => expect(draft.current.load.status).toBe('ready'));

    let newId;
    act(() => {
      newId = draft.current.addRow();
    });
    act(() => draft.current.deleteRows([11, newId]));
    expect(draft.current.rowState(11)).toBe('deleted');
    expect(draft.current.rows.some((r) => r.id === newId)).toBe(false);

    await act(async () => {
      await draft.current.save();
    });
    expect(api.saveDraftChanges.mock.calls[0][1]).toMatchObject({ updates: [], inserts: [], deletes: [11] });
    expect(api.loadTractLookup).not.toHaveBeenCalled();
  });
});
