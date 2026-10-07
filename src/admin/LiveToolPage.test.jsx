import React, { useMemo } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AdminAuthContext } from './contexts.js';
import { DraftProvider } from './draftStore.jsx';
import { FiltersProvider } from './filtersStore.jsx';
import LiveToolPage from './LiveToolPage.jsx';
import { DEFAULT_FILTER_CONFIG, cloneConfig } from '../filters/filterConfig.js';

const row = (id, extra) => ({
  id,
  implementa: `SCALER-000${id}`,
  project_na: `Project ${id}`,
  city: 'Miami',
  latitude: 25.77,
  longitude: -80.19,
  estimated_cost: 100,
  project_status: 'Completed',
  disaster_f: 'Flooding',
  ...extra,
});

const publishedRows = [
  row(1, { infrastruc: 'Gray Infrastructure', project_st: '2020' }),
  row(2, { infrastruc: 'Gray Infrastructure', project_st: '2022' }),
  row(3, { infrastruc: 'Living Shoreline', project_st: '2022' }),
  row(4, { infrastruc: 'Blue Infrastructure', estimated_cost: 0 }),
];

const dataVersions = [
  {
    id: 7,
    version_no: 7,
    name: 'Fall update',
    created_at: '2026-09-30T15:00:00Z',
    created_by: 'prof@miami.edu',
    note: 'October projects',
    row_count: 4,
    is_current: true,
  },
];

const liveFilters = cloneConfig(DEFAULT_FILTER_CONFIG);
const filterVersions = [
  {
    id: 12,
    version_no: 2,
    name: null,
    note: 'Paper filters',
    config: liveFilters,
    is_current: true,
    created_at: '2026-10-01T15:00:00Z',
    created_by: 'axm8832@miami.edu',
  },
  {
    id: 11,
    version_no: 1,
    name: 'First try',
    note: 'Initial',
    config: liveFilters,
    is_current: false,
    created_at: '2026-09-30T15:00:00Z',
    created_by: 'axm8832@miami.edu',
  },
];

function renderLiveTool({ versions = filterVersions, draft = null } = {}) {
  const draftApi = {
    fetchDraftRows: vi.fn().mockResolvedValue(publishedRows),
    fetchPublishedRows: vi.fn().mockResolvedValue(publishedRows),
    fetchVersions: vi.fn().mockResolvedValue(dataVersions),
  };
  const filtersApi = {
    fetchFilterState: vi.fn().mockResolvedValue({ draft, versions }),
    saveFiltersDraft: vi.fn().mockResolvedValue(undefined),
    publishFilters: vi.fn().mockResolvedValue({ version_no: 3 }),
    makeFiltersVersionLive: vi.fn().mockResolvedValue({ version_no: 1 }),
    restoreFiltersVersion: vi.fn().mockResolvedValue(undefined),
    renameFiltersVersion: vi.fn().mockResolvedValue(undefined),
    deleteFiltersVersion: vi.fn().mockResolvedValue(undefined),
    resetFiltersDraft: vi.fn().mockResolvedValue(undefined),
  };
  function Harness() {
    const auth = useMemo(() => ({ client: {}, email: 'prof@miami.edu', signOut: vi.fn() }), []);
    return (
      <MemoryRouter initialEntries={['/admin/live-tool']}>
        <AdminAuthContext.Provider value={auth}>
          <DraftProvider api={draftApi}>
            <FiltersProvider api={filtersApi}>
              <LiveToolPage />
            </FiltersProvider>
          </DraftProvider>
        </AdminAuthContext.Provider>
      </MemoryRouter>
    );
  }
  render(<Harness />);
  return filtersApi;
}

const filterCard = (name) => screen.getByRole('region', { name: `${name} filter` });

afterEach(() => vi.restoreAllMocks());

describe('Live tool page', () => {
  it('shows what is live and the values found in the data', async () => {
    renderLiveTool();
    expect(await screen.findByText('"Fall update" (version 7)')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/3 projects on the map/)).toBeInTheDocument());
    expect(screen.getByText('Filter version 2')).toBeInTheDocument();
    expect(
      screen.getByText(/4 filters shown: City, Project Status, Infrastructure Type, Disaster Focus/),
    ).toBeInTheDocument();

    const infra = filterCard('Infrastructure Type');
    expect(within(infra).getByText('2 of 2 values shown')).toBeInTheDocument();
    expect(within(infra).getByText('1 new value in data')).toBeInTheDocument();

    fireEvent.click(within(infra).getByRole('button', { name: 'Infrastructure Type' }));
    expect(within(infra).getByText('Living Shoreline')).toBeInTheDocument();
    expect(within(infra).getByText('New in data')).toBeInTheDocument();
    expect(within(infra).getAllByText('No projects in the live data')).toHaveLength(3);
    expect(within(infra).getByText('2 projects')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Add option/ })).not.toBeInTheDocument();
  });

  it('labels, hides and recolors values, updating the preview', async () => {
    renderLiveTool();
    await screen.findByText('Filter version 2');
    const infra = filterCard('Infrastructure Type');
    fireEvent.click(within(infra).getByRole('button', { name: 'Infrastructure Type' }));

    fireEvent.change(within(infra).getByLabelText('Label for Living Shoreline'), {
      target: { value: 'Living shorelines' },
    });
    fireEvent.change(within(infra).getByLabelText('Color for Living Shoreline'), { target: { value: '#16a085' } });
    fireEvent.click(within(infra).getByLabelText('Show Gray Infrastructure on the map'));

    const preview = screen.getByRole('complementary', { name: 'Preview of the map filters' });
    expect(within(preview).getByText('Living shorelines')).toBeInTheDocument();
    expect(within(preview).queryByText('Gray')).not.toBeInTheDocument();
    expect(within(infra).getByText('Edited')).toBeInTheDocument();
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save draft' })).toBeEnabled();
  });

  it('switching a city off and on again leaves the filter unchanged', async () => {
    renderLiveTool();
    await screen.findByText('Filter version 2');
    const city = filterCard('City');
    expect(within(city).getByText('1 new value in data')).toBeInTheDocument();
    fireEvent.click(within(city).getByRole('button', { name: 'City' }));

    const toggle = within(city).getByLabelText('Show Miami on the map');
    fireEvent.click(toggle);
    expect(within(city).getByText('0 of 1 values shown')).toBeInTheDocument();
    expect(within(city).queryByText(/new value/)).not.toBeInTheDocument();
    expect(within(city).queryByText('New in data')).not.toBeInTheDocument();
    expect(within(city).getByText('Edited')).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(within(city).getByText('1 of 1 values shown')).toBeInTheDocument();
    expect(within(city).getByText('1 new value in data')).toBeInTheDocument();
    expect(within(city).queryByText('Edited')).not.toBeInTheDocument();
    expect(screen.getByText('The draft matches the live map')).toBeInTheDocument();
  });

  it('hides a whole filter, adds a custom one and publishes with a note', async () => {
    const api = renderLiveTool();
    await screen.findByText('Filter version 2');

    fireEvent.click(screen.getByLabelText('Show the Disaster Focus filter on the map'));
    fireEvent.click(screen.getByRole('button', { name: '+ Add filter' }));
    const dialog = screen.getByRole('dialog', { name: 'Add a filter' });
    fireEvent.change(within(dialog).getByLabelText('Project column it filters on'), {
      target: { value: 'project_st' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add filter' }));

    const year = filterCard('Reported year');
    expect(within(year).getByText('2020')).toBeInTheDocument();
    expect(within(year).getByText('2 projects')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Publish filters…' }));
    const publish = screen.getByRole('dialog', { name: 'Publish filters to the public map' });
    expect(within(publish).getByText('Hide the "Disaster Focus" filter')).toBeInTheDocument();
    expect(within(publish).getByText('Add the "Reported year" filter')).toBeInTheDocument();
    const button = within(publish).getByRole('button', { name: 'Publish filters' });
    expect(button).toBeDisabled();
    fireEvent.change(within(publish).getByLabelText(/What changed/), { target: { value: 'Year filter' } });
    fireEvent.click(button);

    await waitFor(() => expect(api.publishFilters).toHaveBeenCalledWith({}, 'Year filter', null));
    const saved = api.saveFiltersDraft.mock.calls[0][1];
    expect(saved.filters.find((f) => f.id === 'disaster').visible).toBe(false);
    expect(saved.filters.at(-1)).toMatchObject({ id: 'custom-project_st', column: 'project_st', visible: true });
    expect(await screen.findByText(/Filter version 3 is live/)).toBeInTheDocument();
  });

  it('blocks publishing when every filter is hidden', async () => {
    renderLiveTool();
    await screen.findByText('Filter version 2');
    for (const name of ['City', 'Project Status', 'Infrastructure Type', 'Disaster Focus']) {
      fireEvent.click(screen.getByLabelText(`Show the ${name} filter on the map`));
    }
    expect(screen.getByText('At least one filter must be shown on the map.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish filters…' })).toBeDisabled();
  });

  it('makes an older filter version live and deletes one', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const api = renderLiveTool();
    await screen.findByText('Filter version 2');

    fireEvent.click(screen.getByRole('button', { name: 'Make filter version 1 live' }));
    await waitFor(() => expect(api.makeFiltersVersionLive).toHaveBeenCalledWith({}, 11));
    expect(await screen.findByText(/"First try" \(filter v1\) is now live/)).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Delete filter version 2' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Delete filter version 1' }));
    await waitFor(() => expect(api.deleteFiltersVersion).toHaveBeenCalledWith({}, 11));
  });

  it('starts from the built-in filters when nothing has been published', async () => {
    renderLiveTool({ versions: [] });
    expect(await screen.findByText('Built-in filters (never published)')).toBeInTheDocument();
    expect(screen.getByText(/Nothing published yet/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish filters…' })).toBeEnabled();
  });
});
