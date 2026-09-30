import React, { useMemo } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AdminAuthContext } from './contexts.js';
import { DraftProvider } from './draftStore.jsx';
import AdminLayout from './AdminLayout.jsx';
import DataPage from './DataPage.jsx';
import VersionsPage from './VersionsPage.jsx';

const rows = [
  {
    id: 1,
    implementa: 'SCALER-0001',
    project_na: 'Seawall',
    city: 'Miami',
    latitude: 25.77,
    longitude: -80.19,
    infrastruc: 'Gray Infrastructure',
    estimated_cost: 100,
  },
  {
    id: 2,
    implementa: 'SCALER-0002',
    project_na: 'Bioswale',
    city: 'Doral',
    latitude: 25.8,
    longitude: -80.35,
    infrastruc: 'Green Infrastructure',
    estimated_cost: 200,
  },
];

const versions = [
  { id: 2, version_no: 2, created_at: '2026-09-20T15:00:00Z', created_by: 'prof@miami.edu', note: 'Fixed costs', row_count: 2, is_current: true },
  { id: 1, version_no: 1, created_at: '2026-09-01T15:00:00Z', created_by: 'system', note: 'Initial snapshot', row_count: 1, is_current: false },
];

function renderAdmin(page) {
  const api = {
    fetchDraftRows: vi.fn().mockResolvedValue(rows),
    fetchPublishedRows: vi.fn().mockResolvedValue(rows.slice(0, 1)),
    fetchVersions: vi.fn().mockResolvedValue(versions),
    saveDraftChanges: vi.fn().mockResolvedValue({}),
    publishDraft: vi.fn().mockResolvedValue({ version_no: 3, row_count: 2 }),
    restoreVersionToDraft: vi.fn().mockResolvedValue({ version_no: 1, row_count: 1 }),
    renameVersion: vi.fn().mockResolvedValue({}),
    deleteVersion: vi.fn().mockResolvedValue({}),
    makeVersionLive: vi.fn().mockResolvedValue({ version_no: 1, row_count: 1 }),
    rebuildMapFile: vi.fn().mockResolvedValue({ ok: true, features: 1664 }),
    resetDraftFromPublished: vi.fn().mockResolvedValue({ row_count: 1 }),
    loadTractLookup: vi.fn().mockResolvedValue(() => '12086000500'),
  };
  function Harness() {
    const auth = useMemo(() => ({ client: {}, email: 'prof@miami.edu', signOut: vi.fn() }), []);
    return (
      <MemoryRouter initialEntries={['/admin']}>
        <AdminAuthContext.Provider value={auth}>
          <DraftProvider api={api}>
            <AdminLayout>{page}</AdminLayout>
          </DraftProvider>
        </AdminAuthContext.Provider>
      </MemoryRouter>
    );
  }
  render(<Harness />);
  return api;
}

describe('admin data page', () => {
  it('shows the draft, its unpublished changes, and the table controls', async () => {
    renderAdmin(<DataPage />);
    expect(await screen.findByText('Showing 2 of 2 rows')).toBeInTheDocument();
    expect(screen.getByText('All changes saved')).toBeInTheDocument();
    expect(screen.getByText(/1 saved row change not published \(since version 2\)/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Infrastructure type' })).toBeInTheDocument();
    expect(screen.getByLabelText('Filter Infrastructure type')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save draft' })).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Search all fields'), { target: { value: 'doral' } });
    expect(screen.getByText('Showing 1 of 2 rows')).toBeInTheDocument();
  });

  it('adds a row through the row editor and saves it with a tract', async () => {
    const api = renderAdmin(<DataPage />);
    await screen.findByText('Showing 2 of 2 rows');

    fireEvent.click(screen.getByRole('button', { name: 'Add row' }));
    const editor = screen.getByRole('dialog', { name: 'SCALER-0003' });
    const projectIdInput = within(editor).getByLabelText(/^Project ID/);
    expect(projectIdInput).toHaveValue('SCALER-0003');
    expect(projectIdInput).toHaveAttribute('readonly');
    expect(within(editor).getByRole('checkbox', { name: /Generate the next Project ID/ })).toBeChecked();

    const fill = (label, value) => {
      const input = within(editor).getByLabelText(new RegExp(`^${label}`));
      fireEvent.change(input, { target: { value } });
      fireEvent.blur(input);
    };
    fill('Project name', 'Living shoreline');
    fill('Latitude', '25.6');
    fill('Longitude', '-80.3');
    fill('Estimated cost', '5,000');

    const infraSelect = within(editor).getByRole('combobox', { name: /^Infrastructure type/ });
    expect(within(infraSelect).getAllByRole('option').map((o) => o.textContent)).toEqual([
      '(none)',
      'Blue Infrastructure',
      'Green Infrastructure',
      'Gray Infrastructure',
      'Hybrid',
      'Other (type a new value)…',
    ]);
    fireEvent.change(infraSelect, { target: { value: 'Green Infrastructure' } });
    expect(infraSelect).toHaveValue('Green Infrastructure');

    const hazardSelect = within(editor).getByRole('combobox', { name: /^Hazard focus/ });
    fireEvent.change(hazardSelect, { target: { value: '__other__' } });
    const newHazard = within(editor).getByLabelText('New hazard focus value');
    fireEvent.change(newHazard, { target: { value: 'Drought' } });
    fireEvent.blur(newHazard);
    expect(within(editor).getByText(/"Drought" is a new value/)).toBeInTheDocument();

    expect(screen.getByText('1 unsaved change')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Publish/ })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(api.saveDraftChanges).toHaveBeenCalledTimes(1));
    expect(api.saveDraftChanges.mock.calls[0][1].inserts[0]).toMatchObject({
      implementa: 'SCALER-0003',
      project_na: 'Living shoreline',
      infrastruc: 'Green Infrastructure',
      disaster_f: 'Drought',
      latitude: 25.6,
      longitude: -80.3,
      estimated_cost: 5000,
      tract_geoid: '12086000500',
    });
    expect(await screen.findByText(/Draft saved/)).toBeInTheDocument();
  });

  it('lets a new row use a hand-typed Project ID when auto-generation is off', async () => {
    renderAdmin(<DataPage />);
    await screen.findByText('Showing 2 of 2 rows');

    fireEvent.click(screen.getByRole('button', { name: 'Add row' }));
    const editor = screen.getByRole('dialog', { name: 'SCALER-0003' });
    const toggle = within(editor).getByRole('checkbox', { name: /Generate the next Project ID/ });
    const input = within(editor).getByLabelText(/^Project ID/);

    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
    expect(input).not.toHaveAttribute('readonly');
    fireEvent.change(input, { target: { value: 'SCALER-0500' } });
    fireEvent.blur(input);
    expect(input).toHaveValue('SCALER-0500');

    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
    expect(input).toHaveValue('SCALER-0003');
  });

  it('publishes with a required note', async () => {
    const api = renderAdmin(<DataPage />);
    await screen.findByText('Showing 2 of 2 rows');

    fireEvent.click(screen.getByRole('button', { name: /Publish \(1\)/ }));
    const dialog = screen.getByRole('dialog', { name: /Publish version 3/ });
    expect(within(dialog).getByText('Bioswale')).toBeInTheDocument();
    const confirm = within(dialog).getByRole('button', { name: 'Publish 2 projects' });
    expect(confirm).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/What changed/), { target: { value: 'Added Doral bioswale' } });
    fireEvent.click(confirm);
    await waitFor(() => expect(api.publishDraft).toHaveBeenCalledWith({}, 'Added Doral bioswale'));
    expect(await screen.findByText(/Published version 3/)).toBeInTheDocument();
  });
});

describe('admin versions page', () => {
  it('lists versions and restores one into the draft after confirmation', async () => {
    const api = renderAdmin(<VersionsPage />);
    expect(await screen.findByText('Fixed costs')).toBeInTheDocument();
    expect(screen.getByText('Initial snapshot')).toBeInTheDocument();

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const v1Row = screen.getByText('Initial snapshot').closest('tr');
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Restore to draft' }));
    await waitFor(() => expect(api.restoreVersionToDraft).toHaveBeenCalledWith({}, 1));
    expect(confirmSpy.mock.calls[0][0]).toMatch(/discards 1 saved but unpublished row change/);
    confirmSpy.mockRestore();
  });

  it('compares a past version with the live data', async () => {
    renderAdmin(<VersionsPage loadSnapshot={vi.fn().mockResolvedValue([{ ...rows[0], estimated_cost: 999 }])} />);
    const v1Row = (await screen.findByText('Initial snapshot')).closest('tr');
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Compare with live' }));
    const dialog = await screen.findByRole('dialog', { name: /Restoring version 1/ });
    expect(within(dialog).getByText('Would change (1)')).toBeInTheDocument();
  });

  it('renames a version without touching its note', async () => {
    const api = renderAdmin(<VersionsPage />);
    const v1Row = (await screen.findByText('Initial snapshot')).closest('tr');
    expect(within(v1Row).getByText('Version 1')).toBeInTheDocument();

    api.fetchVersions.mockResolvedValueOnce(
      versions.map((v) => (v.id === 1 ? { ...v, name: 'Baseline from the paper' } : v)),
    );
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Rename version 1' }));
    fireEvent.change(within(v1Row).getByLabelText('Name for version 1'), {
      target: { value: '  Baseline from the paper ' },
    });
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(api.renameVersion).toHaveBeenCalledWith({}, 1, '  Baseline from the paper '));
    expect(await within(v1Row).findByText('Baseline from the paper')).toBeInTheDocument();
    expect(within(v1Row).getByText('Initial snapshot')).toBeInTheDocument();
    expect(within(v1Row).getByText('v1')).toBeInTheDocument();
  });

  it('makes a past version live after confirmation', async () => {
    const api = renderAdmin(<VersionsPage />);
    const v1Row = (await screen.findByText('Initial snapshot')).closest('tr');
    const v2Row = screen.getByText('Fixed costs').closest('tr');
    expect(within(v2Row).queryByRole('button', { name: 'Make version 2 live' })).not.toBeInTheDocument();

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Make version 1 live' }));
    await waitFor(() => expect(api.makeVersionLive).toHaveBeenCalledWith({}, 1));
    expect(confirmSpy.mock.calls[0][0]).toMatch(/Make version 1 live on the public map now\?/);
    expect(confirmSpy.mock.calls[0][0]).toMatch(/discards 1 saved but unpublished row change/);
    expect(await screen.findByText('Version 1 is now live on the public map.')).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it('rebuilds the map file from the live version', async () => {
    const api = renderAdmin(<VersionsPage />);
    const v2Row = (await screen.findByText('Fixed costs')).closest('tr');
    fireEvent.click(within(v2Row).getByRole('button', { name: 'Rebuild map file' }));
    await waitFor(() => expect(api.rebuildMapFile).toHaveBeenCalledWith({}));
    expect(await screen.findByText('Map file rebuilt from the live data (1,664 projects).')).toBeInTheDocument();
  });

  it('deletes a past version after confirmation but never the live one', async () => {
    const api = renderAdmin(<VersionsPage />);
    const v1Row = (await screen.findByText('Initial snapshot')).closest('tr');
    const v2Row = screen.getByText('Fixed costs').closest('tr');
    expect(within(v2Row).getByRole('button', { name: 'Delete version 2' })).toBeDisabled();

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Delete version 1' }));
    expect(api.deleteVersion).not.toHaveBeenCalled();

    api.fetchVersions.mockResolvedValueOnce(versions.filter((v) => v.id !== 1));
    fireEvent.click(within(v1Row).getByRole('button', { name: 'Delete version 1' }));
    await waitFor(() => expect(api.deleteVersion).toHaveBeenCalledWith({}, 1));
    expect(confirmSpy.mock.calls[1][0]).toMatch(/Permanently delete version 1/);
    await waitFor(() => expect(screen.queryByText('Initial snapshot')).not.toBeInTheDocument());
    confirmSpy.mockRestore();
  });
});
