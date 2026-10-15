import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard.jsx';
import { normalizeLayerConfig } from './layerConfig.js';

const maps = vi.hoisted(() => []);
vi.mock('mapbox-gl', () => ({ default: {
  Map: class {
    constructor() {
      this.sources = new Map(); this.layers = new Map(); this.events = new Map(); maps.push(this);
      this.dragRotate = { enable() {}, disable() {} }; this.touchZoomRotate = { enableRotation() {}, disableRotation() {} };
    }
    on(event, layerOrCallback, callback) {
      if (event === 'load') setTimeout(layerOrCallback, 0);
      this.events.set(`${event}:${typeof layerOrCallback === 'string' ? layerOrCallback : ''}`, callback || layerOrCallback);
    }
    once(_, callback) { setTimeout(callback, 0); }
    addControl() {} remove() {} flyTo() {} fitBounds() {} setFilter() {} setFeatureState() {} moveLayer() {} resize() {} setStyle() {}
    hasImage() { return true; } addImage() {} getCanvas() { return { style: {} }; } queryRenderedFeatures() { return []; }
    addSource(id, source) { this.sources.set(id, { ...source, setData() {} }); } getSource(id) { return this.sources.get(id); }
    addLayer(layer) { this.layers.set(layer.id, layer); } getLayer(id) { return this.layers.get(id); }
    setPaintProperty(id, key, value) { this.layers.get(id).paint[key] = value; }
    setLayoutProperty(id, key, value) { this.layers.get(id).layout[key] = value; }
    getLayoutProperty(id, key) { return this.layers.get(id)?.layout[key]; }
  },
  NavigationControl: class {}, FullscreenControl: class {}, ScaleControl: class {},
  LngLatBounds: class { extend() { return this; } isEmpty() { return false; } getCenter() { return { lng: -80.2, lat: 25.7 }; } getNorthEast() { return { lng: -80.1, lat: 25.8 }; } getSouthWest() { return { lng: -80.3, lat: 25.6 }; } },
  Popup: class { on() { return this; } off() { return this; } isOpen() { return false; } getElement() { return document.createElement('div'); } setDOMContent() { return this; } setLngLat() { return this; } setHTML() { return this; } addTo() { return this; } remove() {} },
} }));

const surface = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { scenario: '4 ft above MHHW', elevation_band: '2–4 ft', vertical_datum: 'NAVD88', units: 'feet', depth_range: '1–2 ft' }, geometry: { type: 'Polygon', coordinates: [[[-80.2, 25.7], [-80.19, 25.7], [-80.19, 25.71], [-80.2, 25.7]]] } }] };
const empty = { type: 'FeatureCollection', features: [] };
let published;
beforeEach(() => {
  maps.length = 0; published = normalizeLayerConfig(null);
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    const path = String(url);
    const data = path.endsWith('layers_config.json') ? published : path.includes('/layers/') ? surface : path.endsWith('filters_config.json') ? { filters: [] } : empty;
    return { ok: true, json: async () => data, text: async () => 'GEO_ID,PRED3_PE\n1400000US12086000107,10' };
  }));
});

describe('public map published layer behavior', () => {
  it('shows tile loading failures without losing layer controls', async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const toggle = await screen.findByRole('switch', { name: 'Elevation layer' });
    await waitFor(() => expect(maps).toHaveLength(1));
    fireEvent.click(toggle);
    await waitFor(() => expect(maps[0].getSource('elevation')).toBeTruthy());
    act(() => maps[0].events.get('error:')({ sourceId: 'elevation', error: new Error('Tile unavailable') }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This layer could not be loaded');
    expect(screen.getByRole('switch', { name: 'Sea Level Rise — 4 ft layer' })).toBeInTheDocument();
  });
  it('uses admin names/order/availability and lazy-loads one surface at a time', async () => {
    published.builtins.find((l) => l.id === 'risk').visible = false;
    published.builtins.find((l) => l.id === 'elevation').label = 'Ground Elevation';
    published.order = ['elevation', ...published.order.filter((id) => id !== 'elevation')];
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const elevation = await screen.findByRole('switch', { name: 'Ground Elevation layer' });
    await waitFor(() => expect(maps).toHaveLength(1));
    expect(screen.queryByRole('switch', { name: 'FEMA Risk Rating layer' })).not.toBeInTheDocument();
    expect(fetch.mock.calls.some(([url]) => String(url).endsWith('/layers/elevation.geojson'))).toBe(false);
    fireEvent.click(elevation);
    await waitFor(() => expect(maps[0].getLayer('elevation-fill')).toBeTruthy());
    expect(maps[0].getLayer('elevation-fill').layout.visibility).toBe('visible');
    expect(maps[0].getSource('elevation')).toMatchObject({ type: 'vector', tiles: [expect.stringContaining('/layers/elevation/{z}/{x}/{y}.pbf')] });
    expect(maps[0].getLayer('elevation-fill')['source-layer']).toBe('surface');
    fireEvent.click(screen.getByRole('switch', { name: 'Sea Level Rise — 4 ft layer' }));
    await waitFor(() => expect(maps[0].getLayer('sea-level-rise-4ft-fill')).toBeTruthy());
    expect(maps[0].getLayer('elevation-fill').layout.visibility).toBe('none');
    expect(maps[0].getLayer('sea-level-rise-4ft-fill').layout.visibility).toBe('visible');
  });

  it('excludes hidden infrastructure overlays and applies configured colors/opacity', async () => {
    published.builtins.find((l) => l.id === 'overlay-community-centers').visible = false;
    const routes = published.builtins.find((l) => l.id === 'overlay-evacuation-routes');
    routes.symbology.color = '#123456'; routes.style.opacity = 0.5;
    published.builtins.find((l) => l.id === 'critical-infrastructure').style.opacity = 0.4;
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const toggle = await screen.findByRole('switch', { name: 'Critical Infrastructure layer' });
    await waitFor(() => expect(maps).toHaveLength(1));
    fireEvent.click(toggle);
    await waitFor(() => expect(maps[0].getLayer('overlay-evacuation-routes-layer')).toBeTruthy());
    expect(fetch.mock.calls.some(([url]) => String(url).includes('Community%20Cent'))).toBe(false);
    expect(maps[0].getLayer('overlay-evacuation-routes-layer').paint).toMatchObject({ 'line-color': '#123456', 'line-opacity': 0.2 });
  });
});
