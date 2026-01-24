import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';

// Mock mapbox-gl
vi.mock('https://cdn.skypack.dev/mapbox-gl@2.15.0', () => {
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
    once: vi.fn((event, callback) => {
      if (event === 'styledata') {
        setTimeout(callback, 0);
      }
    })
  };

  return {
    default: {
      Map: vi.fn(() => mockMap),
      Marker: vi.fn(() => ({
        setLngLat: vi.fn().mockReturnThis(),
        addTo: vi.fn().mockReturnThis(),
        getElement: vi.fn(() => ({
          addEventListener: vi.fn(),
          style: {},
          getLngLat: vi.fn(() => ({ lng: -80.1918, lat: 25.7617 }))
        })),
        feature: null
      })),
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
global.fetch = vi.fn((url) => {
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
    render(<App />);
    
    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/search projects/i);
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('should show search results when typing', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      expect(screen.getByText(/Miami Beach Flood Protection/i)).toBeInTheDocument();
    });
  });

  it('should clear search when clear button is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      expect(screen.getByText(/Miami Beach Flood Protection/i)).toBeInTheDocument();
    });

    // Find and click clear button
    const clearButton = screen.getByLabelText('Clear search');
    await user.click(clearButton);

    await waitFor(() => {
      expect(searchInput).toHaveValue('');
      expect(screen.queryByText(/Miami Beach Flood Protection/i)).not.toBeInTheDocument();
    });
  });

  it('should show "No results found" for non-matching queries', async () => {
    const user = userEvent.setup();
    render(<App />);

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
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Coral Gables');

    await waitFor(() => {
      expect(screen.getByText(/Coral Gables Green Infrastructure/i)).toBeInTheDocument();
      expect(screen.queryByText(/Miami Beach/i)).not.toBeInTheDocument();
    });
  });

  it('should display project details in search results', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');

    await waitFor(() => {
      // Check that project name is displayed
      expect(screen.getByText(/Miami Beach Flood Protection/i)).toBeInTheDocument();
      // Check that city is displayed (use getAllByText since "Miami Beach" appears in both project name and city)
      const miamiBeachElements = screen.getAllByText(/Miami Beach/i);
      expect(miamiBeachElements.length).toBeGreaterThan(0);
      // Check that infrastructure type is displayed
      expect(screen.getByText(/Blue Infrastructure/i)).toBeInTheDocument();
    });
  });

  it('should handle empty search query', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'Miami');
    
    await waitFor(() => {
      // "Miami Beach" appears in both project name and city, so use getAllByText
      const miamiBeachElements = screen.getAllByText(/Miami Beach/i);
      expect(miamiBeachElements.length).toBeGreaterThan(0);
    });

    // Clear the input
    await user.clear(searchInput);

    await waitFor(() => {
      // After clearing, all "Miami Beach" elements should be gone
      expect(screen.queryByText(/Miami Beach/i)).not.toBeInTheDocument();
    });
  });

  it('should be case-insensitive in search', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search projects/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search projects/i);
    await user.type(searchInput, 'miami beach');

    await waitFor(() => {
      expect(screen.getByText(/Miami Beach Flood Protection/i)).toBeInTheDocument();
    });
  });
});
