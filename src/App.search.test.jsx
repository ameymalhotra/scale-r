import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from './App.jsx';

const renderApp = () => render(
  <MemoryRouter initialEntries={['/dashboard']}>
    <App />
  </MemoryRouter>
);

// Mock mapbox-gl
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
      setData: vi.fn()
    })),
    getLayer: vi.fn(() => null),
    setPaintProperty: vi.fn(),
    setLayoutProperty: vi.fn(),
    setStyle: vi.fn(),
    getCanvas: vi.fn(() => ({
      style: {}
    })),
    setFeatureState: vi.fn(),
    queryRenderedFeatures: vi.fn(() => []),
    dragRotate: { enable: vi.fn(), disable: vi.fn() },
    touchZoomRotate: { enableRotation: vi.fn(), disableRotation: vi.fn() },
    once: vi.fn((event, callback) => {
      if (event === 'styledata') {
        setTimeout(callback, 0);
      }
    })
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
          feature: null
        };
        return marker;
      }),
      Popup: vi.fn(() => ({
        setLngLat: vi.fn().mockReturnThis(),
        setHTML: vi.fn().mockReturnThis(),
        addTo: vi.fn().mockReturnThis(),
        on: vi.fn(),
        off: vi.fn(),
        remove: vi.fn()
      })),
      NavigationControl: vi.fn(),
      FullscreenControl: vi.fn(),
      ScaleControl: vi.fn(),
      LngLatBounds: vi.fn(() => ({
        extend: vi.fn(),
        isEmpty: vi.fn(() => false),
        getNorthEast: vi.fn(() => ({ lng: -80.1, lat: 25.8 })),
        getSouthWest: vi.fn(() => ({ lng: -80.2, lat: 25.7 })),
        set: vi.fn()
      }))
    },
    accessToken: ''
  };
});

// Mock fetch for GeoJSON data
const mockProjectsGeoJson = () => ({
  type: 'FeatureCollection',
  features: [
    {
      id: 1,
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [-80.1918, 25.7617]
      },
      properties: {
        'Project_Na': 'Miami Beach Flood Protection',
        'NAME': 'Miami Beach',
        'City': 'Miami Beach',
        'Infrastruc': 'Gray Infrastructure',
        'Categories': 'Flood Control',
        'Disaster_F': 'Flooding',
        'New_15_25_': 'Comprehensive flood protection system',
        'Estimated_': '5000000',
        'Project__1': 'Ongoing'
      }
    },
    {
      id: 2,
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [-80.1318, 25.7917]
      },
      properties: {
        'Project_Na': 'Coral Gables Green Infrastructure',
        'NAME': 'Coral Gables',
        'City': 'Coral Gables',
        'Infrastruc': 'Green Infrastructure',
        'Categories': 'Environmental',
        'Disaster_F': 'Hurricane',
        'New_15_25_': 'Green infrastructure project',
        'Estimated_': '3000000',
        'Project__1': 'Completed'
      }
    }
  ]
});

global.fetch = vi.fn((url) => {
  if (url.includes('projects_merged.geojson') || (url.includes('project-data') && url.includes('geojson'))) {
    return Promise.resolve({
      ok: true,
      json: async () => mockProjectsGeoJson()
    });
  }
  if (url.includes('Cities_FeaturesToJSON.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({
        type: 'FeatureCollection',
        features: [
          {
            id: 1,
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [-80.1918, 25.7617]
            },
            properties: {
              'Project_Na': 'Miami Beach Flood Protection',
              'NAME': 'Miami Beach',
              'City': 'Miami Beach',
              'Infrastruc': 'Blue Infrastructure',
              'Categories': 'Flood Control',
              'Disaster_F': 'Flooding',
              'New_15_25_': 'Comprehensive flood protection system',
              'Estimated_': '5000000',
              'Project__1': 'Ongoing'
            }
          },
          {
            id: 2,
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [-80.1318, 25.7917]
            },
            properties: {
              'Project_Na': 'Coral Gables Green Infrastructure',
              'NAME': 'Coral Gables',
              'City': 'Coral Gables',
              'Infrastruc': 'Green Infrastructure',
              'Categories': 'Environmental',
              'Disaster_F': 'Hurricane',
              'New_15_25_': 'Green infrastructure project',
              'Estimated_': '3000000',
              'Project__1': 'Completed'
            }
          }
        ]
      })
    });
  }
  if (url.includes('femaindex.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({
        type: 'FeatureCollection',
        features: []
      })
    });
  }
  if (url.includes('FL_CRE.csv')) {
    return Promise.resolve({
      ok: true,
      text: async () => 'GEO_ID,PRED3_PE\n1400000US12086000107,75.5'
    });
  }
  if (url.includes('miami_cities.geojson')) {
    return Promise.resolve({
      ok: true,
      json: async () => ({
        type: 'FeatureCollection',
        features: []
      })
    });
  }
  return Promise.reject(new Error('Unknown URL'));
});

describe('App Search Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the search bar', async () => {
    renderApp();
    
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/search projects/i);
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('should filter dashboard stats by project status', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Project Status' })).toBeInTheDocument();
    });

    const getProjectCount = () => screen
      .getAllByText('Projects')
      .find(element => /^\d+$/.test(element.previousElementSibling?.textContent?.trim() || ''))
      ?.previousElementSibling;

    await waitFor(() => {
      expect(getProjectCount()).toHaveTextContent('2');
    });

    await user.click(screen.getByLabelText('Completed'));

    await waitFor(() => {
      expect(getProjectCount()).toHaveTextContent('1');
    });

    await user.click(screen.getByLabelText('Ongoing'));

    await waitFor(() => {
      expect(getProjectCount()).toHaveTextContent('2');
    });
  });

  it('should show search results when typing', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Miami Beach Flood Protection/i })).toBeInTheDocument();
    });
  });

  it('should clear search when clear button is clicked', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Miami Beach Flood Protection/i })).toBeInTheDocument();
    });

    // Find and click clear button
    const clearButton = screen.getByLabelText('Clear search');
    await user.click(clearButton);

    await waitFor(() => {
      expect(searchInput).toHaveValue('');
      expect(screen.queryByRole('option', { name: /Miami Beach Flood Protection/i })).not.toBeInTheDocument();
    });
  });

  it('should show "No results found" for non-matching queries', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'NonExistentProject123');

    await waitFor(() => {
      expect(screen.getByText(/No projects found matching/i)).toBeInTheDocument();
    });
  });

  it('should filter results by project name', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Coral Gables');

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Coral Gables Green Infrastructure/i })).toBeInTheDocument();
      expect(screen.queryByRole('option', { name: /Miami Beach/i })).not.toBeInTheDocument();
    });
  });

  it('should display project details in search results', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      const row = screen.getByRole('option', { name: /Miami Beach Flood Protection/i });
      expect(row).toBeInTheDocument();
      expect(row).toHaveTextContent(/Miami Beach/i);
      expect(row).toHaveTextContent(/Gray/i);
    });
  });

  it('should handle empty search query', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');
    
    await waitFor(() => {
      const miamiBeachOptions = screen.getAllByRole('option', { name: /Miami Beach/i });
      expect(miamiBeachOptions.length).toBeGreaterThan(0);
    });

    // Clear the input
    await user.clear(searchInput);

    await waitFor(() => {
      expect(screen.queryByRole('option', { name: /Miami Beach/i })).not.toBeInTheDocument();
    });
  });

  it('should be case-insensitive in search', async () => {
    const user = userEvent.setup();
    renderApp();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'miami beach');

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Miami Beach Flood Protection/i })).toBeInTheDocument();
    });
  });
});
