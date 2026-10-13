/**
 * Acceptance tests for previewing filters against draft project data.
 *
 * Requirement: when an admin changes the project data in the draft (for example
 * adds a project with a new infrastructure type), the Live tool's filter values
 * and filter preview reflect that draft, so the filters can be checked and set
 * up before the new filters and data go live. The live map itself must not
 * change until the data is published.
 */
import React, { useMemo } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AdminAuthContext, useDraft } from './contexts.js';
import { DraftProvider } from './draftStore.jsx';
import { FiltersProvider } from './filtersStore.jsx';
import LiveToolPage from './LiveToolPage.jsx';
import { DEFAULT_FILTER_CONFIG, cloneConfig } from '../filters/filterConfig.js';

const row = (id, extra) => ({
  id,
  implementa: `SCALER-00${id}`,
  project_na: `Project ${id}`,
  city: 'Miami',
  latitude: 25.77,
  longitude: -80.19,
  estimated_cost: 100,
  project_status: 'Completed',
  disaster_f: 'Flooding',
  infrastruc: 'Gray Infrastructure',
  ...extra,
});

// Live data: 3 projects on the map (Gray x2, Living Shoreline x1). The Blue
// project has no cost, so the public map does not show it.
const LIVE_ROWS = [
  row(1),
  row(2),
  row(3, { infrastruc: 'Living Shoreline' }),
  row(4, { infrastruc: 'Blue Infrastructure', estimated_cost: 0 }),
];

const NEW_TYPE = 'Floating Wetland';

const liveFilters = cloneConfig(DEFAULT_FILTER_CONFIG);
const FILTER_VERSIONS = [
  {
    id: 12,
    version_no: 2,
    name: null,
    note: 'Paper filters',
    config: liveFilters,
    is_current: true,
    created_at: '2026-10-01T15:00:00Z',
    created_by: 'admin@miami.edu',
  },
];
const DATA_VERSIONS = [
  {
    id: 7,
    version_no: 7,
    name: null,
    created_at: '2026-09-30T15:00:00Z',
    created_by: 'prof@miami.edu',
    note: 'Live data',
    row_count: LIVE_ROWS.length,
    is_current: true,
  },
];

/** Buttons that act on the shared draft the way the Project data page would. */
function DataPageActions() {
  const { updateCell, save, publish } = useDraft();
  return (
    <div>
      <button type="button" onClick={() => updateCell(1, 'infrastruc', NEW_TYPE)}>
        test: edit project 1 type without saving
      </button>
      <button type="button" onClick={() => save()}>
        test: save data draft
      </button>
      <button type="button" onClick={() => publish('Publish the new data')}>
        test: publish data
      </button>
    </div>
  );
}

function renderAdmin({ draftRows, publishedAfterDataPublish } = {}) {
  let published = LIVE_ROWS;
  let draft = draftRows ?? LIVE_ROWS;
  const draftApi = {
    fetchDraftRows: vi.fn(async () => draft),
    fetchPublishedRows: vi.fn(async () => published),
    fetchVersions: vi.fn(async () => DATA_VERSIONS),
    publishDraft: vi.fn(async () => {
      published = publishedAfterDataPublish ?? draft;
      return { version_no: 8 };
    }),
    saveDraftChanges: vi.fn(async (_client, { updates }) => {
      const byId = new Map(updates.map((u) => [u.id, u]));
      draft = draft.map((r) => (byId.has(r.id) ? { ...r, ...byId.get(r.id), _moved: undefined } : r));
    }),
    loadTractLookup: vi.fn(async () => () => null),
  };
  const filtersApi = {
    fetchFilterState: vi.fn().mockResolvedValue({ draft: null, versions: FILTER_VERSIONS }),
    saveFiltersDraft: vi.fn().mockResolvedValue(undefined),
    publishFilters: vi.fn().mockResolvedValue({ version_no: 3 }),
    makeFiltersVersionLive: vi.fn(),
    restoreFiltersVersion: vi.fn(),
    renameFiltersVersion: vi.fn(),
    deleteFiltersVersion: vi.fn(),
    resetFiltersDraft: vi.fn(),
  };
  function Harness() {
    const auth = useMemo(() => ({ client: {}, email: 'prof@miami.edu', signOut: vi.fn() }), []);
    return (
      <MemoryRouter initialEntries={['/admin/live-tool']}>
        <AdminAuthContext.Provider value={auth}>
          <DraftProvider api={draftApi}>
            <FiltersProvider api={filtersApi}>
              <DataPageActions />
              <LiveToolPage />
            </FiltersProvider>
          </DraftProvider>
        </AdminAuthContext.Provider>
      </MemoryRouter>
    );
  }
  render(<Harness />);
  return { draftApi, filtersApi };
}

const infraCard = () => screen.getByRole('region', { name: 'Infrastructure Type filter' });
const preview = () => screen.getByRole('complementary', { name: 'Preview of the map filters' });
const valueRows = (value) =>
  within(infraCard())
    .queryAllByText(value)
    .map((el) => el.closest('tr'))
    .filter(Boolean);
const valueRow = (value) => valueRows(value)[0] ?? null;
const NOT_LIVE = /not (yet )?live|draft only|only in (the )?draft|unpublished/i;

async function openInfrastructure() {
  await screen.findByText('Filter version 2');
  await waitFor(() => expect(screen.getByText(/3 projects on the map/)).toBeInTheDocument());
  fireEvent.click(within(infraCard()).getByRole('button', { name: 'Infrastructure Type' }));
}

afterEach(() => vi.restoreAllMocks());

describe('Live tool: filters reflect the draft project data', () => {
  it('a new type added in the saved draft shows in the filter values and the preview before the data is published', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: NEW_TYPE }), row(6, { infrastruc: NEW_TYPE })] });
    await openInfrastructure();

    const newRow = await waitFor(() => {
      const r = valueRow(NEW_TYPE);
      expect(r).not.toBeNull();
      return r;
    });
    expect(newRow).toHaveTextContent(/(^|\D)2 projects/);
    expect(within(preview()).getByText(NEW_TYPE)).toBeInTheDocument();
  });

  it('marks a draft-only value as not live yet, so the admin knows the public map does not have it', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: NEW_TYPE })] });
    await openInfrastructure();

    await waitFor(() => expect(valueRow(NEW_TYPE)).not.toBeNull());
    expect(valueRow(NEW_TYPE)).toHaveTextContent(NOT_LIVE);
    expect(valueRow('Gray Infrastructure')).not.toHaveTextContent(NOT_LIVE);
  });

  it('shows no "not live" warnings when the draft data matches the live data', async () => {
    renderAdmin();
    await openInfrastructure();
    expect(within(infraCard()).queryByText(NOT_LIVE)).not.toBeInTheDocument();
  });

  it('lets the admin label and color a draft-only value, and that setting is saved and published with the filters', async () => {
    const { filtersApi } = renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: NEW_TYPE })] });
    await openInfrastructure();
    await waitFor(() => expect(valueRow(NEW_TYPE)).not.toBeNull());

    fireEvent.change(within(infraCard()).getByLabelText(`Label for ${NEW_TYPE}`), {
      target: { value: 'Wetlands (floating)' },
    });
    fireEvent.change(within(infraCard()).getByLabelText(`Color for ${NEW_TYPE}`), {
      target: { value: '#123456' },
    });
    expect(within(preview()).getByText('Wetlands (floating)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Publish filters…' }));
    const dialog = screen.getByRole('dialog', { name: 'Publish filters to the public map' });
    fireEvent.change(within(dialog).getByLabelText(/What changed/), { target: { value: 'Label new type' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Publish filters' }));

    await waitFor(() => expect(filtersApi.publishFilters).toHaveBeenCalled());
    const saved = filtersApi.saveFiltersDraft.mock.calls.at(-1)[1];
    const infra = saved.filters.find((f) => f.id === 'infrastructure');
    expect(infra.options).toContainEqual(
      expect.objectContaining({ value: NEW_TYPE, label: 'Wetlands (floating)', color: '#123456' }),
    );
  });

  it('a type that no draft project uses any more disappears from the preview', async () => {
    renderAdmin({ draftRows: LIVE_ROWS.filter((r) => r.infrastruc !== 'Living Shoreline') });
    await openInfrastructure();
    await waitFor(() => expect(within(preview()).queryByText('Living Shoreline')).not.toBeInTheDocument());
    expect(within(preview()).getByText('Gray')).toBeInTheDocument();
  });

  it('counts per value come from the draft data', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5), row(6)] });
    await openInfrastructure();
    await waitFor(() => expect(valueRow('Gray Infrastructure')).toHaveTextContent(/(^|\D)4 projects/));
  });

  it('uses the public map rule: a draft project the map would not show does not add its type', async () => {
    renderAdmin({
      draftRows: [
        ...LIVE_ROWS,
        row(5, { infrastruc: NEW_TYPE, estimated_cost: 0 }),
        row(6, { infrastruc: NEW_TYPE, latitude: null, longitude: null }),
      ],
    });
    await openInfrastructure();
    expect(valueRow(NEW_TYPE)).toBeNull();
    expect(within(preview()).queryByText(NEW_TYPE)).not.toBeInTheDocument();
  });

  it('a different capitalisation of an existing type is not listed as a separate value', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: 'gray infrastructure' })] });
    await openInfrastructure();
    await waitFor(() => expect(valueRows(/^gray infrastructure$/i)).toHaveLength(1));
    expect(within(preview()).getAllByText(/^gray$/i)).toHaveLength(1);
  });

  it('"Live now" keeps describing the live data while the draft differs', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: NEW_TYPE }), row(6, { infrastruc: NEW_TYPE })] });
    await screen.findByText('Filter version 2');
    await waitFor(() => expect(screen.getByText(/3 projects on the map/)).toBeInTheDocument());
  });

  it('after the draft is saved from the data page, the Live tool picks up the change without a page reload', async () => {
    renderAdmin();
    await openInfrastructure();
    expect(valueRow(NEW_TYPE)).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'test: edit project 1 type without saving' }));
    fireEvent.click(screen.getByRole('button', { name: 'test: save data draft' }));

    await waitFor(() => expect(valueRow(NEW_TYPE)).not.toBeNull());
    expect(within(preview()).getByText(NEW_TYPE)).toBeInTheDocument();
  });

  it('once the data is published, the new value is still listed and no longer flagged as not live', async () => {
    renderAdmin({ draftRows: [...LIVE_ROWS, row(5, { infrastruc: NEW_TYPE })] });
    await openInfrastructure();
    await waitFor(() => expect(valueRow(NEW_TYPE)).toHaveTextContent(NOT_LIVE));

    fireEvent.click(screen.getByRole('button', { name: 'test: publish data' }));

    await waitFor(() => expect(valueRow(NEW_TYPE)).not.toHaveTextContent(NOT_LIVE));
    expect(within(preview()).getByText(NEW_TYPE)).toBeInTheDocument();
  });
});
