import React, { useMemo } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AdminAuthContext } from './contexts.js';
import { LayersProvider } from './layersStore.jsx';
import LayersPage from './LayersPage.jsx';
import { createLayer } from '../layers/layerConfig.js';

const polygon = (props) => ({
  type: 'Feature',
  properties: props,
  geometry: { type: 'Polygon', coordinates: [[[-80.2, 25.7], [-80.1, 25.7], [-80.1, 25.8], [-80.2, 25.7]]] },
});

const floodData = {
  type: 'FeatureCollection',
  features: [polygon({ zone: 'AE', depth: 1 }), polygon({ zone: 'X', depth: 4 }), polygon({ zone: 'AE', depth: 9 })],
};

const existingLayer = createLayer({
  id: 'layer-flood',
  file: 'layers/layer-flood-a1.geojson',
  label: 'Flood zones',
  description: '',
  info: {
    geometry: 'polygon',
    featureCount: 3,
    fields: [
      { name: 'zone', type: 'string' },
      { name: 'depth', type: 'number' },
    ],
  },
});

const liveVersion = {
  id: 5,
  version_no: 1,
  name: null,
  note: 'First layers',
  config: { layers: [existingLayer] },
  is_current: true,
  created_at: '2026-10-01T15:00:00Z',
  created_by: 'axm8832@miami.edu',
};

function renderLayers({ versions = [liveVersion], draft = null } = {}) {
  const api = {
    fetchLayerState: vi.fn().mockResolvedValue({ draft, versions }),
    saveLayersDraft: vi.fn().mockResolvedValue(undefined),
    publishLayers: vi.fn().mockResolvedValue({ version_no: 2 }),
    makeLayersVersionLive: vi.fn().mockResolvedValue({ version_no: 1 }),
    restoreLayersVersion: vi.fn().mockResolvedValue(undefined),
    renameLayersVersion: vi.fn().mockResolvedValue(undefined),
    deleteLayersVersion: vi.fn().mockResolvedValue(undefined),
    resetLayersDraft: vi.fn().mockResolvedValue(undefined),
    uploadLayerFile: vi.fn().mockImplementation(async (_client, id) => `layers/${id}-upload.geojson`),
    fetchLayerGeojson: vi.fn().mockResolvedValue(floodData),
  };
  function Harness() {
    const auth = useMemo(() => ({ client: {}, email: 'prof@miami.edu', signOut: vi.fn() }), []);
    return (
      <MemoryRouter initialEntries={['/admin/layers']}>
        <AdminAuthContext.Provider value={auth}>
          <LayersProvider api={api}>
            <LayersPage showPreviewMap={false} />
          </LayersProvider>
        </AdminAuthContext.Provider>
      </MemoryRouter>
    );
  }
  render(<Harness />);
  return api;
}

const geojsonFile = (data, name = 'Sea_level-rise.geojson') =>
  new File([JSON.stringify(data)], name, { type: 'application/geo+json' });

describe('admin map layers page', () => {
  it('edits built-in settings and publishes them alongside uploaded layers', async () => {
    const api = renderLayers();
    await screen.findByText('Layer version 1');
    const region = screen.getByRole('region', { name: 'FEMA Risk Rating layer' });
    fireEvent.click(within(region).getByRole('button', { expanded: false }));
    fireEvent.change(within(region).getByLabelText('Layer name'), { target: { value: 'County Risk' } });
    fireEvent.change(within(region).getByLabelText('Very Low color'), { target: { value: '#123456' } });
    fireEvent.change(within(region).getByLabelText('Opacity'), { target: { value: '0.3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Publish layers…' }));
    const dialog = screen.getByRole('dialog', { name: 'Publish layers to the public map' });
    fireEvent.change(within(dialog).getByLabelText(/What changed/), { target: { value: 'Configure existing risk layer' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Publish layers' }));
    await waitFor(() => expect(api.publishLayers).toHaveBeenCalled());
    const saved = api.saveLayersDraft.mock.calls[0][1];
    expect(saved.builtins.find((l) => l.id === 'risk')).toMatchObject({ label: 'County Risk', style: { opacity: 0.3 }, symbology: { categories: expect.arrayContaining([expect.objectContaining({ value: 'Very Low', color: '#123456' })]) } });
    expect(saved.layers).toEqual([existingLayer]);
  });

  it('can hide a new surface and individual infrastructure overlay and reorder switches', async () => {
    const api = renderLayers();
    await screen.findByText('Layer version 1');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Show the Elevation layer on the map' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Show the Community Centers layer on the map' }));
    fireEvent.click(screen.getByRole('button', { name: 'Move Elevation layer up' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(api.saveLayersDraft).toHaveBeenCalled());
    const saved = api.saveLayersDraft.mock.calls[0][1];
    expect(saved.builtins.find((l) => l.id === 'elevation').visible).toBe(false);
    expect(saved.builtins.find((l) => l.id === 'overlay-community-centers').visible).toBe(false);
    expect(saved.order.indexOf('elevation')).toBeLessThan(saved.order.indexOf('storm-surge-category-3'));
  });

  it('shows the live layers and the history', async () => {
    renderLayers();
    expect(await screen.findByText('Layer version 1')).toBeInTheDocument();
    expect(screen.getByText(/7 layers on the map:.*Flood zones/)).toBeInTheDocument();
    expect(screen.getByText('First layers')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish layers…' })).toBeDisabled();
  });

  it('uploads a GeoJSON file as a new layer and saves the draft', async () => {
    const api = renderLayers({ versions: [] });
    await screen.findByText('None published yet');

    fireEvent.click(screen.getByRole('button', { name: '+ Upload layer' }));
    const dialog = screen.getByRole('dialog', { name: 'Upload a map layer' });
    fireEvent.change(within(dialog).getByLabelText(/GeoJSON file/), { target: { files: [geojsonFile(floodData)] } });
    expect(await within(dialog).findByText(/Polygons: 3 features, 2 attributes/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Name shown on the map')).toHaveValue('Sea level rise');

    fireEvent.click(within(dialog).getByRole('button', { name: 'Upload layer' }));
    await waitFor(() => expect(api.uploadLayerFile).toHaveBeenCalledTimes(1));
    const [, layerId, uploaded] = api.uploadLayerFile.mock.calls[0];
    expect(layerId).toMatch(/^layer-/);
    expect(uploaded.features).toHaveLength(3);

    expect(await screen.findByText(/"Sea level rise" uploaded/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sea level rise layer' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    await waitFor(() => expect(api.saveLayersDraft).toHaveBeenCalledTimes(1));
    const saved = api.saveLayersDraft.mock.calls[0][1];
    expect(saved.layers[0]).toMatchObject({
      id: layerId,
      label: 'Sea level rise',
      file: `layers/${layerId}-upload.geojson`,
      geometry: 'polygon',
      featureCount: 3,
    });
  });

  it('refuses a file that mixes geometry types', async () => {
    renderLayers();
    await screen.findByText('Layer version 1');
    fireEvent.click(screen.getByRole('button', { name: '+ Upload layer' }));
    const dialog = screen.getByRole('dialog', { name: 'Upload a map layer' });
    const mixed = {
      type: 'FeatureCollection',
      features: [polygon({}), { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [-80, 25] } }],
    };
    fireEvent.change(within(dialog).getByLabelText(/GeoJSON file/), { target: { files: [geojsonFile(mixed)] } });
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/mixes polygons and points/);
    expect(within(dialog).getByRole('button', { name: 'Upload layer' })).toBeDisabled();
  });

  it('switches a layer to categorized and graduated symbology from its data', async () => {
    const api = renderLayers();
    await screen.findByText('Layer version 1');
    fireEvent.click(screen.getByRole('button', { name: /Flood zones/, expanded: false }));

    fireEvent.click(screen.getByRole('radio', { name: 'Categorized' }));
    fireEvent.change(screen.getByLabelText('Attribute to categorize by'), { target: { value: 'zone' } });
    expect(await screen.findByLabelText('Color for AE')).toBeInTheDocument();
    expect(screen.getByLabelText('Color for X')).toBeInTheDocument();
    expect(api.fetchLayerGeojson).toHaveBeenCalledWith({}, 'layers/layer-flood-a1.geojson');
    expect(screen.getByText('Edited')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: 'Graduated' }));
    fireEvent.change(screen.getByLabelText('Attribute to graduate by'), { target: { value: 'depth' } });
    fireEvent.change(screen.getByLabelText('Class breaks'), { target: { value: 'equal' } });
    fireEvent.change(screen.getByLabelText('Number of classes'), { target: { value: '2' } });
    expect(await screen.findByLabelText('Color for class 2')).toBeInTheDocument();
    expect(screen.getByLabelText('Class 2 starts at')).toHaveValue(5);
    expect(screen.queryByLabelText('Color for class 3')).not.toBeInTheDocument();

    const preview = screen.getByRole('complementary', { name: 'Preview of the selected layer' });
    expect(within(preview).getByText('1 – 5')).toBeInTheDocument();
    expect(within(preview).getByText('5 – 9')).toBeInTheDocument();
  });

  it('publishes with a required note', async () => {
    const api = renderLayers();
    await screen.findByText('Layer version 1');
    fireEvent.click(screen.getByRole('button', { name: /Flood zones/, expanded: false }));
    fireEvent.change(screen.getByLabelText('Name shown on the map'), { target: { value: 'FEMA flood zones' } });

    fireEvent.click(screen.getByRole('button', { name: 'Publish layers…' }));
    const dialog = screen.getByRole('dialog', { name: 'Publish layers to the public map' });
    expect(within(dialog).getByText('Rename "Flood zones" to "FEMA flood zones"')).toBeInTheDocument();
    const confirm = within(dialog).getByRole('button', { name: 'Publish layers' });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText(/What changed/), { target: { value: 'Renamed flood zones' } });
    fireEvent.click(confirm);

    await waitFor(() => expect(api.publishLayers).toHaveBeenCalledWith({}, 'Renamed flood zones', null));
    expect(api.saveLayersDraft.mock.calls[0][1].layers[0].label).toBe('FEMA flood zones');
    expect(await screen.findByText(/Layer version 2 is live/)).toBeInTheDocument();
  });
});
