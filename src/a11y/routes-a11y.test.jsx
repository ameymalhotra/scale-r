/**
 * Automated accessibility checks (axe-core in jsdom via jest-axe).
 * Run: npm run a11y
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import App from '../App.jsx';

expect.extend(toHaveNoViolations);

vi.mock('mapbox-gl', () => {
  const mockMap = {
    on: vi.fn((event, callback) => {
      if (event === 'load') {
        setTimeout(callback, 0);
      }
    }),
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    flyTo: vi.fn(),
    fitBounds: vi.fn(),
    getSource: vi.fn(() => ({
      setData: vi.fn(),
    })),
    getLayer: vi.fn(() => null),
    setPaintProperty: vi.fn(),
    setLayoutProperty: vi.fn(),
    setStyle: vi.fn(),
    getCanvas: vi.fn(() => ({
      style: {},
    })),
    setFeatureState: vi.fn(),
    queryRenderedFeatures: vi.fn(() => []),
    dragRotate: { enable: vi.fn(), disable: vi.fn() },
    touchZoomRotate: { enableRotation: vi.fn(), disableRotation: vi.fn() },
    once: vi.fn((event, callback) => {
      if (event === 'styledata') {
        setTimeout(callback, 0);
      }
    }),
  };

  return {
    default: {
      Map: vi.fn(() => mockMap),
      Marker: vi.fn(() => {
        const element = {
          addEventListener: vi.fn(),
          style: {},
        };
        let lngLat = { lng: -80.1918, lat: 25.7617 };
        const marker = {
          setLngLat: vi.fn((coords) => {
            lngLat = Array.isArray(coords) ? { lng: coords[0], lat: coords[1] } : coords;
            return marker;
          }),
          addTo: vi.fn(() => marker),
          getElement: vi.fn(() => element),
          getLngLat: vi.fn(() => lngLat),
          feature: null,
        };
        return marker;
      }),
      Popup: vi.fn(() => ({
        setLngLat: vi.fn().mockReturnThis(),
        setHTML: vi.fn().mockReturnThis(),
        addTo: vi.fn().mockReturnThis(),
        on: vi.fn(),
        off: vi.fn(),
        remove: vi.fn(),
      })),
      NavigationControl: vi.fn(),
      FullscreenControl: vi.fn(),
      ScaleControl: vi.fn(),
      LngLatBounds: vi.fn(() => ({
        extend: vi.fn(),
        isEmpty: vi.fn(() => false),
        getNorthEast: vi.fn(() => ({ lng: -80.1, lat: 25.8 })),
        getSouthWest: vi.fn(() => ({ lng: -80.2, lat: 25.7 })),
        set: vi.fn(),
      })),
    },
    accessToken: '',
  };
});

const mockProjectsGeoJson = () => ({
  type: 'FeatureCollection',
  features: [
    {
      id: 1,
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-80.1918, 25.7617] },
      properties: {
        Project_Na: 'Miami Beach Flood Protection',
        NAME: 'Miami Beach',
        City: 'Miami Beach',
        Infrastruc: 'Gray Infrastructure',
        Categories: 'Flood Control',
        Disaster_F: 'Flooding',
        New_15_25_: 'Comprehensive flood protection system',
        Estimated_: '5000000',
        Project__1: 'Ongoing',
      },
    },
    {
      id: 2,
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-80.1318, 25.7917] },
      properties: {
        Project_Na: 'Coral Gables Green Infrastructure',
        NAME: 'Coral Gables',
        City: 'Coral Gables',
        Infrastruc: 'Green Infrastructure',
        Categories: 'Environmental',
        Disaster_F: 'Hurricane',
        New_15_25_: 'Green infrastructure project',
        Estimated_: '3000000',
        Project__1: 'Completed',
      },
    },
  ],
});

global.fetch = vi.fn((url) => {
  const u = String(url);
  if (u.includes('projects_merged.geojson') || (u.includes('project-data') && u.includes('geojson'))) {
    return Promise.resolve({
      ok: true,
      json: async () => mockProjectsGeoJson(),
    });
  }
  if (u.includes('Cities_FeaturesToJSON.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({
        type: 'FeatureCollection',
        features: mockProjectsGeoJson().features,
      }),
    });
  }
  if (u.includes('femaindex.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ type: 'FeatureCollection', features: [] }),
    });
  }
  if (u.includes('FL_CRE.csv')) {
    return Promise.resolve({
      ok: true,
      text: async () => 'GEO_ID,PRED3_PE\n1400000US12086000107,75.5',
    });
  }
  if (u.includes('miami_cities.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ type: 'FeatureCollection', features: [] }),
    });
  }
  return Promise.resolve({
    ok: true,
    json: async () => ({}),
    text: async () => '',
  });
});

const ROUTES = ['/about', '/dashboard', '/team', '/partners', '/docs', '/outputs'];

const renderRoute = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );

const axeOptions = {
  iframes: false,
  rules: {
    // jsdom cannot compute real contrast; use WAVE / manual checks for color.
    'color-contrast': { enabled: false },
  },
};

describe('Route accessibility (axe)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each(ROUTES)('%s has no detectable WCAG 2.0 A/AA violations (axe, excl. contrast)', async (path) => {
    const { container } = renderRoute(path);

    if (path === '/dashboard') {
      await waitFor(
        () => {
          expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
        },
        { timeout: 15000 },
      );
    } else if (path === '/docs') {
      await waitFor(
        () => {
          expect(screen.getByRole('heading', { name: /^Technical Documentation$/i })).toBeInTheDocument();
        },
        { timeout: 20000 },
      );
    } else {
      await waitFor(() => {
        expect(container.querySelector('main')).toBeInTheDocument();
      });
    }

    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });
});
