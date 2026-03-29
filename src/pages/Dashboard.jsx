import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import mapboxgl from 'https://cdn.skypack.dev/mapbox-gl@2.15.0';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { searchProjects } from '../utils/searchProjects.js';
import { highlightText } from '../utils/highlightText.jsx';


const parseNumericValue = (value) => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  const cleaned = String(value).replace(/[^0-9eE.+-]/g, '');
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
};

const toWgs84Coordinate = ([x, y]) => {
  const originShift = 20037508.34;
  const lon = (x / originShift) * 180;
  let lat = (y / originShift) * 180;
  lat = (180 / Math.PI) * (2 * Math.atan(Math.exp((lat * Math.PI) / 180)) - Math.PI / 2);
  return [lon, lat];
};

const transformToWgs84 = (coords) => {
  if (!Array.isArray(coords)) return coords;
  if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
    return toWgs84Coordinate(coords);
  }
  return coords.map(transformToWgs84);
};

const walkCoordinates = (geometry, callback) => {
  if (!geometry || !geometry.coordinates) return;
  const traverse = (coords) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      callback(coords);
      return;
    }
    coords.forEach(traverse);
  };
  traverse(geometry.coordinates);
};

const reprojectFeatureCollectionIfNeeded = (featureCollection) => {
  if (!featureCollection?.features?.length) return featureCollection;
  let firstCoord = null;
  for (const feature of featureCollection.features) {
    if (!feature?.geometry) continue;
    walkCoordinates(feature.geometry, (coord) => {
      if (!firstCoord) firstCoord = coord;
    });
    if (firstCoord) break;
  }
  if (!firstCoord) return featureCollection;
  const needsReprojection = Math.abs(firstCoord[0]) > 180 || Math.abs(firstCoord[1]) > 90;
  if (!needsReprojection) return featureCollection;
  console.info('[Census] Reprojecting GeoJSON from EPSG:3857 to EPSG:4326');
  return {
    ...featureCollection,
    features: featureCollection.features.map((feature) => {
      if (!feature?.geometry) return feature;
      return {
        ...feature,
        geometry: {
          ...feature.geometry,
          coordinates: transformToWgs84(feature.geometry.coordinates)
        }
      };
    })
  };
};

// Rewrite Point geometry to use lon/lat from feature properties (e.g. for EPSG:3087 layers that store X,Y in props)
const useLonLatFromProperties = (featureCollection, lonField, latField) => {
  if (!featureCollection?.features?.length || !lonField || !latField) return featureCollection;
  return {
    ...featureCollection,
    features: featureCollection.features.map((feature) => {
      if (feature?.geometry?.type !== 'Point' || !feature.properties) return feature;
      const lon = parseFloat(feature.properties[lonField]);
      const lat = parseFloat(feature.properties[latField]);
      if (Number.isFinite(lon) && Number.isFinite(lat)) {
        return { ...feature, geometry: { ...feature.geometry, coordinates: [lon, lat] } };
      }
      return feature;
    })
  };
};

const getRangeStats = (values) => {
  if (!values.length) return { min: null, mid: null, max: null };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mid = min + (max - min) / 2;
  return { min, mid, max };
};

// Create a small circle polygon around a point to use as a buffer zone
const createCircleBuffer = (center, radiusInMeters = 50) => {
  const [lng, lat] = center;
  const points = 32; // Number of points in the circle
  const circle = [];
  
  for (let i = 0; i <= points; i++) {
    const angle = (i * 360) / points;
    const dx = radiusInMeters * Math.cos((angle * Math.PI) / 180);
    const dy = radiusInMeters * Math.sin((angle * Math.PI) / 180);
    
    // Approximate conversion: 1 degree latitude ≈ 111,000 meters
    // 1 degree longitude ≈ 111,000 * cos(latitude) meters
    const latOffset = dy / 111000;
    const lngOffset = dx / (111000 * Math.cos((lat * Math.PI) / 180));
    
    circle.push([lng + lngOffset, lat + latOffset]);
  }
  
  return circle;
};

const formatWithCommas = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US').format(value);
};

const formatRiskValue = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(2);
};

// Format cost using compact notation (e.g., "3M", "1.2B")
const formatCostCompact = (cost) => {
  try {
    if (!cost || cost === null || cost === undefined) return null;
    
    // Convert to number if it's a string
    const numericCost = typeof cost === 'string' 
      ? parseFloat(cost.replace(/[$,]/g, '')) 
      : parseFloat(cost);
    
    if (isNaN(numericCost) || !isFinite(numericCost)) return null;
    
    // Format using Intl.NumberFormat with compact notation
    const options = { notation: "compact", compactDisplay: "short" };
    const formattedNumber = new Intl.NumberFormat("en-US", options).format(numericCost);
    
    // Add dollar sign prefix
    return `$${formattedNumber}`;
  } catch (error) {
    console.error('Error formatting cost:', error);
    return null;
  }
};

// Format city name to title case (first letter of each word capitalized)
const formatCityName = (cityName) => {
  if (!cityName || typeof cityName !== 'string') return cityName;
  return cityName
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const SUPABASE_STORAGE = 'https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data';
const PROJECTS_GEOJSON_FILE = 'projects_merged.geojson';

const OVERLAY_LAYERS_CONFIG = [
  { id: 'overlay-community-centers', label: 'Community Centers', url: `${SUPABASE_STORAGE}/Community%20Cent_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#e67e22', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#d35400', 'circle-stroke-width': 1 } } },
  { id: 'overlay-communications', label: 'Communications', url: `${SUPABASE_STORAGE}/Communications_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#9b59b6', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#8e44ad', 'circle-stroke-width': 1 } } },
  { id: 'overlay-disaster-recovery', label: 'Disaster Recovery Centers', url: `${SUPABASE_STORAGE}/Disaster%20Recov_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#1abc9c', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#16a085', 'circle-stroke-width': 1 } } },
  { id: 'overlay-emergency-medical', label: 'Emergency Medical', url: `${SUPABASE_STORAGE}/EmergencyMedical_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#c0392b', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#922b21', 'circle-stroke-width': 1 } }, popupTitleField: 'Name', popupFields: ['Address', 'City'], pointLonLatFields: ['X', 'Y'] },
  { id: 'overlay-emergency-ops', label: 'Emergency Operations Centers', url: `${SUPABASE_STORAGE}/Emergency%20Oper_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#f39c12', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#e67e22', 'circle-stroke-width': 1 } } },
  { id: 'overlay-evacuation-routes', label: 'Evacuation Routes', url: `${SUPABASE_STORAGE}/Evacuation%20Rou_FeaturesToJSO.geojson`, style: { type: 'line', paint: { 'line-color': '#34495e', 'line-width': 3 } } },
  { id: 'overlay-military', label: 'Military Installations', url: `${SUPABASE_STORAGE}/MILITARY_FeaturesToJSO.geojson`, style: { type: 'fill', paint: { 'fill-color': '#2c3e50', 'fill-opacity': 0.35, 'fill-outline-color': '#1a252f', 'line-color': '#1a252f' } }, popupTitleField: 'NAME', popupFields: ['GEOID', 'FEMAIndexR'] },
  { id: 'overlay-risk-shelters', label: 'Risk Shelters', url: `${SUPABASE_STORAGE}/Risk%20Shelter%20I_FeaturesToJSO.geojson`, style: { type: 'circle', paint: { 'circle-color': '#d35400', 'circle-radius': 5, 'circle-opacity': 0.8, 'circle-stroke-color': '#a04000', 'circle-stroke-width': 1 } }, popupTitleField: 'Name', popupFields: ['Address', 'City'] },
];

/** Combined Critical Infrastructure sublayers: one UI toggle loads multiple GeoJSON sources. */
const OVERLAY_GROUP_CRITICAL_FACILITIES = {
  id: 'overlay-group-critical-facilities',
  label: 'Emergency medical, EOC & military',
  memberIds: ['overlay-emergency-medical', 'overlay-emergency-ops', 'overlay-military'],
};

const OVERLAY_GROUP_RISK_AND_RECOVERY = {
  id: 'overlay-group-risk-recovery',
  label: 'Risk shelters & disaster recovery',
  memberIds: ['overlay-risk-shelters', 'overlay-disaster-recovery'],
};

const CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS = [OVERLAY_GROUP_CRITICAL_FACILITIES, OVERLAY_GROUP_RISK_AND_RECOVERY];

const OVERLAY_LAYER_ID_TO_GROUP_ID = (() => {
  const m = {};
  CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.forEach((g) => {
    g.memberIds.forEach((mid) => {
      m[mid] = g.id;
    });
  });
  return m;
})();

function expandCriticalInfraSublayerKeys(keys) {
  const out = [];
  keys.forEach((k) => {
    const group = CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.find((g) => g.id === k);
    if (group) out.push(...group.memberIds);
    else out.push(k);
  });
  return [...new Set(out)];
}

const CRITICAL_INFRASTRUCTURE_SUBLAYER_UI_ITEMS = [
  ...CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.map((g) => ({ kind: 'group', id: g.id, label: g.label })),
  ...OVERLAY_LAYERS_CONFIG.filter((c) => !OVERLAY_LAYER_ID_TO_GROUP_ID[c.id]).map((c) => ({ kind: 'layer', id: c.id, label: c.label })),
];

/** Matches filter sidebar frosted glass (map overlays). */
const mapOverlayGlassStyle = {
  background: 'rgba(255, 255, 255, 0.5)',
  backdropFilter: 'blur(28px) saturate(200%)',
  WebkitBackdropFilter: 'blur(28px) saturate(200%)',
  border: '1px solid rgba(255, 255, 255, 0.55)',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.14), inset 0 0 0 1px rgba(255, 255, 255, 0.65)',
};

const MODELLING_LAYER_OPTIONS = [
  { view: 'none', label: 'No Layer', ariaLabel: 'No modelling layer' },
  { view: 'risk', label: 'FEMA Risk Rating', ariaLabel: 'FEMA Risk Rating layer' },
  { view: 'pred3pe', label: 'Resilience Index', ariaLabel: 'Resilience Index layer' },
  { view: 'critical-infrastructure', label: 'Critical Infrastructure', ariaLabel: 'Critical Infrastructure layer' },
];

/** Mobile map: legends sit above the combined Modelling + sublayers card */
const MOBILE_CENSUS_OVERLAY_BOTTOM = 'calc(62px + min(62vh, 520px) + 20px)';

/** Above modelling/legend map overlays (z-index 1000); below mobile filter drawer backdrop (1099). */
const SEARCH_BAR_OVERLAY_Z_INDEX = 1050;

const Dashboard = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const districtsRef = useRef({});
  const censusDataRef = useRef(null);
  const hoveredCensusIdRef = useRef(null);
  const censusStatsRef = useRef(null);
  const censusViewRef = useRef('risk');
  const pred3PEDataRef = useRef({}); // Mapping of GEOID to PRED3_PE values
  const isHoveringMarkerRef = useRef(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [allMarkers, setAllMarkers] = useState([]);
  const [currentDistrict, setCurrentDistrict] = useState(null);
  const [allProjectsData, setAllProjectsData] = useState(null);
  const [isSatelliteView, setIsSatelliteView] = useState(false);
  const [activeFeature, setActiveFeature] = useState(null);
  const isSwitchingFeatureRef = useRef(false);
  const [censusStats, setCensusStats] = useState(null);
  const [censusLayersReady, setCensusLayersReady] = useState(false);
  const [activeCensusView, setActiveCensusView] = useState('risk');
  const [censusVisible, setCensusVisible] = useState(true);
  const censusEventsBoundRef = useRef(false);
  const censusVisibleRef = useRef(true);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedDisasterFocus, setSelectedDisasterFocus] = useState([]);
  const [selectedCity, setSelectedCity] = useState('');
  const [cityDropdownOpen, setCityDropdownOpen] = useState(false);
  const [projectsLayerVisible, setProjectsLayerVisible] = useState(true);
  const [showTooltip, setShowTooltip] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedResultIndex, setSelectedResultIndex] = useState(-1);

  const [criticalInfraSublayerKeys, setCriticalInfraSublayerKeys] = useState([]);
  const [loadingOverlayLayer, setLoadingOverlayLayer] = useState(null);
  const enabledOverlayLayerIds = useMemo(
    () => expandCriticalInfraSublayerKeys(criticalInfraSublayerKeys),
    [criticalInfraSublayerKeys]
  );
  const overlayDataCacheRef = useRef({});

  // Debounce search input before running search (reduces work on mobile)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearchQuery(searchQuery), 200);
    return () => clearTimeout(t);
  }, [searchQuery]);
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modellingLayerOpen, setModellingLayerOpen] = useState(false);
  const isMobileRef = useRef(isMobile);

  // Mobile breakpoint listener
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 768px)');
    const handler = (e) => setIsMobile(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);
  useEffect(() => {
    isMobileRef.current = isMobile;
  }, [isMobile]);

  // Apply mobile rotation (disable rotation on mobile) when map is ready and isMobile/loading change
  useEffect(() => {
    if (loading || !map.current) return;
    if (isMobile) {
      map.current.dragRotate.disable();
      map.current.touchZoomRotate.disableRotation();
    } else {
      map.current.dragRotate.enable();
      map.current.touchZoomRotate.enableRotation();
    }
  }, [isMobile, loading]);

  // Listen for popup close events to reset activeFeature state
  useEffect(() => {
    const handlePopupClosed = () => {
      // Don't clear activeFeature if we're intentionally switching to a new feature
      if (!isSwitchingFeatureRef.current) {
        setActiveFeature(null);
      }
    };

    window.addEventListener('popupClosed', handlePopupClosed);

    return () => {
      window.removeEventListener('popupClosed', handlePopupClosed);
    };
  }, []);

  // Close city dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const cityDropdown = document.querySelector('[data-city-dropdown]');
      if (cityDropdownOpen && cityDropdown && !cityDropdown.contains(event.target)) {
        setCityDropdownOpen(false);
      }
    };

    if (cityDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [cityDropdownOpen]);

  // Navigate to a specific project (zoom and open popup)
  const navigateToProject = useCallback((feature) => {
    if (!map.current || !feature || !feature.geometry) return;

    const coords = feature.geometry.coordinates;
    if (!coords || coords.length < 2) return;

    // Find the corresponding marker (if it exists)
    const marker = allMarkers.find(m => {
      if (!m.feature) return false;
      const markerCoords = m.feature.geometry?.coordinates;
      if (!markerCoords) return false;
      // Compare coordinates (with small tolerance for floating point)
      return Math.abs(markerCoords[0] - coords[0]) < 0.0001 && 
             Math.abs(markerCoords[1] - coords[1]) < 0.0001;
    });

    // If marker exists and is hidden, make it visible temporarily
    if (marker && marker.getElement().style.display === 'none') {
      marker.getElement().style.display = 'block';
    }

    // Zoom to the project location
    map.current.flyTo({
      center: [coords[0], coords[1]],
      zoom: 15,
      duration: 1500
    });

    // Mark that we're switching features to prevent popupClosed from clearing it
    isSwitchingFeatureRef.current = true;
    
    // Set active feature to open popup
    setActiveFeature(feature);
    
    // Reset the flag after a short delay to allow the popup to update
    setTimeout(() => {
      isSwitchingFeatureRef.current = false;
    }, 100);

    // Close search results
    setShowSearchResults(false);
    setSearchQuery('');
    setSelectedResultIndex(-1);
  }, [allMarkers]);

  // Handle search query changes (uses debounced value to reduce work per keystroke)
  useEffect(() => {
    if (!debouncedSearchQuery.trim()) {
      setSearchResults([]);
      setShowSearchResults(false);
      setSelectedResultIndex(-1);
      return;
    }

    const results = searchProjects(debouncedSearchQuery, allProjectsData);
    setSearchResults(results);
    setShowSearchResults(true); // Show dropdown even if no results (to display "no results" message)
    setSelectedResultIndex(-1);
  }, [debouncedSearchQuery, allProjectsData]);

  // Close search dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const searchContainer = document.querySelector('[data-search-container]');
      if (showSearchResults && searchContainer && !searchContainer.contains(event.target)) {
        setShowSearchResults(false);
      }
    };

    if (showSearchResults) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showSearchResults]);

  // Handle keyboard navigation for search
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (!showSearchResults || searchResults.length === 0) return;

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSelectedResultIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : prev
        );
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSelectedResultIndex(prev => prev > 0 ? prev - 1 : -1);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        const index = selectedResultIndex >= 0 ? selectedResultIndex : 0;
        if (searchResults[index]) {
          navigateToProject(searchResults[index]);
        }
      } else if (event.key === 'Escape') {
        setShowSearchResults(false);
        setSearchQuery('');
        setSelectedResultIndex(-1);
      }
    };

    if (showSearchResults) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showSearchResults, searchResults, selectedResultIndex, navigateToProject]);

  const handleCensusViewChange = (view) => {
    censusViewRef.current = view;
    setActiveCensusView(view);
    // If "none" is selected, hide the census layer; otherwise show it
    if (view === 'none') {
      setCensusVisible(false);
    } else {
      setCensusVisible(true);
    }
  };

  const isModellingLayerSwitchOn = (view) => {
    if (view === 'none') return !censusVisible || activeCensusView === 'none';
    return censusVisible && activeCensusView === view;
  };

  const handleModellingLayerSwitch = (view) => {
    const on = isModellingLayerSwitchOn(view);
    if (view === 'none') {
      if (on) handleCensusViewChange('risk');
      else handleCensusViewChange('none');
    } else if (on) {
      handleCensusViewChange('none');
    } else {
      handleCensusViewChange(view);
    }
  };

  const handleCensusVisibilityToggle = () => {
    setCensusVisible((prev) => !prev);
  };

  // Define district boundaries
  

  // Get marker color based on project type
  const getMarkerColor = (projectType) => {
    switch(projectType) {
      case 'Blue Infrastructure':
      case 'Blue':
        return '#3498db';
      case 'Green Infrastructure':
      case 'Green':
        return '#27ae60';
      case 'Grey Infrastructure':
      case 'Grey':
        return '#95a5a6';
      case 'Hybrid':
        return '#9b59b6'; // Purple for hybrid infrastructure
      default:
        return '#95a5a6';
    }
  };

  // Get marker size based on project cost
  const getMarkerSize = (cost) => {
    if (!cost) return 8;
    const numericCost = parseFloat(cost.replace(/[$,]/g, ''));
    if (numericCost > 50000000) return 15;
    if (numericCost > 10000000) return 12;
    return 8;
  };


  

  // Check if point is within district
  const isPointInDistrict = (point, districtCoords) => {
    const [lng, lat] = point;
    let inside = false;
    
    for (let i = 0, j = districtCoords.length - 1; i < districtCoords.length; j = i++) {
      const [xi, yi] = districtCoords[i];
      const [xj, yj] = districtCoords[j];
      
      const intersect = ((yi > lat) !== (yj > lat)) &&
          (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    
    return inside;
  };

  // Zoom to district
  const zoomToDistrict = (districtId) => {
    const district = districtsRef.current[districtId];
    if (!district || !map.current) return;

    setCurrentDistrict(districtId);
    console.log(district.zoom);
    map.current.flyTo({
      center: district.center,
      zoom: district.zoom,
      duration: 1500
    });

    Object.keys(districtsRef.current).forEach(id => {
      map.current.setPaintProperty(
        `${id}-fill`,
        'fill-opacity',
        id === districtId ? 0.3 : 0.1
      );
      map.current.setPaintProperty(
        `${id}-outline`,
        'line-opacity',
        id === districtId ? 1 : 0.5
      );
      map.current.setPaintProperty(
        `${id}-outline`,
        'line-width',
        id === districtId ? 3 : 2
      );
    });

    allMarkers.forEach(marker => {
      const coords = marker.getLngLat();
      const pointInDistrict = isPointInDistrict(
        [coords.lng, coords.lat],
        district.coordinates
      );

      if (pointInDistrict) {
        marker.getElement().style.opacity = '1';
        marker.getElement().style.transform = 'scale(1.3)';
        marker.getElement().style.zIndex = '1000';
      } else {
        marker.getElement().style.opacity = '0.3';
        marker.getElement().style.transform = 'scale(0.8)';
        marker.getElement().style.zIndex = '1';
      }
    });
  };

  // Reset view
  const resetView = () => {
    if (!map.current) return;
    
    setCurrentDistrict(null);
    handleCensusViewChange('risk');

    Object.keys(districtsRef.current).forEach(id => {
      map.current.setPaintProperty(`${id}-fill`, 'fill-opacity', 0.1);
      map.current.setPaintProperty(`${id}-outline`, 'line-opacity', 0.5);
      map.current.setPaintProperty(`${id}-outline`, 'line-width', 2);
    });

    allMarkers.forEach(marker => {
      marker.getElement().style.opacity = '1';
      marker.getElement().style.transform = 'scale(1)';
      marker.getElement().style.zIndex = '1';
    });

    // Use shifted bounds for reset view (shifted northeast)
    if (allMarkers.length > 0) {
      const bounds = new mapboxgl.LngLatBounds();
      allMarkers.forEach(marker => {
        const coords = marker.getLngLat();
        bounds.extend([coords.lng, coords.lat]);
      });
      if (!bounds.isEmpty()) {
        const shiftedBounds = shiftBoundsNortheast(bounds);
        map.current.fitBounds(shiftedBounds, { 
          padding: { top: 10, bottom: 300, left: 200, right: 10 },
          maxZoom: 13,
          duration: 1500 
        });
      }
    } else {
    map.current.flyTo({
      center: [-80.70, 26.15],
      zoom: 11,
      duration: 1500
    });
    }
  };




  const addOverlaySourceAndLayer = useCallback((mapInstance, layerId, config, geojson) => {
    if (!mapInstance || !config) return;
    const layerMapId = layerId + '-layer';
    if (mapInstance.getSource(layerId)) return;
    mapInstance.addSource(layerId, { type: 'geojson', data: geojson });
    const { type: layerType, paint } = config.style || {};
    const baseLayer = { id: layerMapId, source: layerId, layout: { visibility: 'visible' }, paint: {} };
    if (layerType === 'circle') {
      baseLayer.type = 'circle';
      baseLayer.paint['circle-color'] = paint['circle-color'] ?? '#3498db';
      baseLayer.paint['circle-radius'] = paint['circle-radius'] ?? 5;
      baseLayer.paint['circle-opacity'] = paint['circle-opacity'] ?? 0.8;
      baseLayer.paint['circle-stroke-color'] = paint['circle-stroke-color'] ?? '#2980b9';
      baseLayer.paint['circle-stroke-width'] = paint['circle-stroke-width'] ?? 1;
    } else if (layerType === 'line') {
      baseLayer.type = 'line';
      baseLayer.paint['line-color'] = paint['line-color'] ?? '#2980b9';
      baseLayer.paint['line-width'] = paint['line-width'] ?? 1;
    } else {
      baseLayer.type = 'fill';
      baseLayer.paint['fill-color'] = paint['fill-color'] ?? '#3498db';
      baseLayer.paint['fill-opacity'] = paint['fill-opacity'] ?? 0.25;
      if (paint['line-color']) baseLayer.paint['fill-outline-color'] = paint['line-color'];
    }
    mapInstance.addLayer(baseLayer);
    mapInstance.moveLayer(layerMapId);

    if (config.popupFields?.length || config.popupTitleField) {
      mapInstance.on('click', layerMapId, (e) => {
        if (!e.features?.length) return;
        const props = e.features[0].properties;
        const title = config.popupTitleField ? (props[config.popupTitleField] || config.label) : config.label;
        const rows = (config.popupFields || [])
          .map((f) => {
            const key = typeof f === 'object' ? f.field : f;
            const label = typeof f === 'object' ? f.label : f.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
            const val = props[key] ?? '—';
            return `<tr><td style="color:#34495e;font-weight:600;width:90px;padding:3px 0">${label}</td><td style="color:#2c3e50;padding:3px 0">${val}</td></tr>`;
          })
          .join('');
        const html = `<div style="max-width:340px">` +
          `<div style="font-size:1.05em;font-weight:700;color:#2c3e50;margin-bottom:10px">${title}</div>` +
          (rows ? `<table style="width:100%;border-collapse:separate;border-spacing:0 4px;font-size:0.9em"><tbody>${rows}</tbody></table>` : '') +
          `</div>`;
        new mapboxgl.Popup({ closeButton: true, closeOnClick: true, offset: 14, maxWidth: '360px' })
          .setLngLat(e.lngLat)
          .setHTML(html)
          .addTo(mapInstance);
      });
      mapInstance.on('mouseenter', layerMapId, () => { mapInstance.getCanvas().style.cursor = 'pointer'; });
      mapInstance.on('mouseleave', layerMapId, () => { mapInstance.getCanvas().style.cursor = ''; });
    }
  }, []);

  const ensureOverlayLayerLoaded = useCallback(async (layerId) => {
    if (!map.current) return;
    const layerMapId = layerId + '-layer';
    if (map.current.getSource(layerId)) {
      if (map.current.getLayer(layerMapId)) {
        map.current.setLayoutProperty(layerMapId, 'visibility', 'visible');
      }
      return;
    }
    const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === layerId);
    if (!config) return;
    const cached = overlayDataCacheRef.current[layerId];
    if (cached) {
      addOverlaySourceAndLayer(map.current, layerId, config, cached);
      return;
    }
    setLoadingOverlayLayer(layerId);
    try {
      const response = await fetch(config.url);
      if (!response.ok) throw new Error(`Failed to load ${config.label}`);
      let geojson = await response.json();
      if (config.pointLonLatFields && config.pointLonLatFields.length >= 2) {
        geojson = useLonLatFromProperties(geojson, config.pointLonLatFields[0], config.pointLonLatFields[1]);
      }
      geojson = reprojectFeatureCollectionIfNeeded(geojson);
      overlayDataCacheRef.current[layerId] = geojson;
      addOverlaySourceAndLayer(map.current, layerId, config, geojson);
    } catch (err) {
      console.error('Error loading overlay layer:', layerId, err);
    } finally {
      setLoadingOverlayLayer(null);
    }
  }, [addOverlaySourceAndLayer]);

  const MAX_CRITICAL_INFRASTRUCTURE_SUBLAYERS = 2;

  /** Toggle one sublayer or combined group; max 2 logical selections — adding a third drops the first (FIFO). */
  const handleCriticalInfraSublayerToggle = useCallback((key) => {
    setCriticalInfraSublayerKeys((prev) => {
      let next;
      if (prev.includes(key)) {
        next = prev.filter((k) => k !== key);
      } else if (prev.length < MAX_CRITICAL_INFRASTRUCTURE_SUBLAYERS) {
        next = [...prev, key];
      } else {
        next = [prev[1], key];
      }
      next = [...new Set(next)].slice(0, MAX_CRITICAL_INFRASTRUCTURE_SUBLAYERS);

      const prevLayerIds = expandCriticalInfraSublayerKeys(prev);
      const nextLayerIds = expandCriticalInfraSublayerKeys(next);

      prevLayerIds.forEach((id) => {
        if (!nextLayerIds.includes(id) && map.current?.getLayer(`${id}-layer`)) {
          map.current.setLayoutProperty(`${id}-layer`, 'visibility', 'none');
        }
      });

      const toAdd = nextLayerIds.filter((id) => !prevLayerIds.includes(id));
      if (toAdd.length) {
        queueMicrotask(() => {
          toAdd.forEach((id) => ensureOverlayLayerLoaded(id));
        });
      }

      return next;
    });
  }, [ensureOverlayLayerLoaded]);

  const addCensusSourceAndLayers = useCallback(() => {
    if (!map.current || !censusDataRef.current) return;

    const stats = censusStatsRef.current;
    const view = censusViewRef.current;

    if (!stats) return;

    // Build color expression based on risk rating categories (categorical mapping)
    const buildRiskRatingColorExpression = () => {
      // Map each category directly to a color (light yellow to orange red)
      return [
        'case',
        ['==', ['get', '__riskRating'], 'Very Low'],
        '#FFF9C4',           // Light Yellow (Very Low)
        ['==', ['get', '__riskRating'], 'Relatively Low'],
        '#FFE082',           // Light Yellow-Orange (Relatively Low)
        ['==', ['get', '__riskRating'], 'Relatively Moderate'],
        '#FFB74D',           // Orange (Relatively Moderate)
        ['==', ['get', '__riskRating'], 'Relatively High'],
        '#FF8A65',           // Orange-Red (Relatively High)
        ['==', ['get', '__riskRating'], 'Very High'],
        '#E64A19',           // Dark Orange-Red (Very High)
        '#9e9e9e'            // Gray for unknown/missing ratings
      ];
    };

    const riskColorExpression = buildRiskRatingColorExpression();
    
    // Build color expression for PRED3_PE (percentage values)
    const buildPred3PEColorExpression = () => {
      const pred3PEStats = stats.pred3PE;
      if (!pred3PEStats || pred3PEStats.min === null || pred3PEStats.max === null) {
        return [
          'case',
          ['==', ['typeof', ['get', '__pred3PE']], 'number'],
          '#9e9e9e',
          '#9e9e9e'
        ];
      }
      if (pred3PEStats.min === pred3PEStats.max) {
        return [
          'case',
          ['==', ['typeof', ['get', '__pred3PE']], 'number'],
          '#49006A',
          '#9e9e9e'
        ];
      }
      // Continuous color scale from light purple (low) to dark purple (high)
      // Multiple color stops for better differentiation
      const range = pred3PEStats.max - pred3PEStats.min;
      return [
        'case',
        ['==', ['typeof', ['get', '__pred3PE']], 'number'],
        [
          'interpolate',
          ['linear'],
          ['get', '__pred3PE'],
          pred3PEStats.min, '#E8D4F5',        // Very light purple for minimum values
          pred3PEStats.min + range * 0.1667, '#D4B3E8',  // Light purple
          pred3PEStats.min + range * 0.3333, '#C298DB',  // Medium-light purple
          pred3PEStats.min + range * 0.5, '#A866C7',     // Medium purple
          pred3PEStats.min + range * 0.6667, '#7A3FA8',  // Medium-dark purple (darkened)
          pred3PEStats.min + range * 0.8333, '#5A1D85',  // Dark purple (darkened)
          pred3PEStats.max, '#2D0045'                     // Very dark purple for maximum values (darkened)
        ],
        '#9e9e9e'
      ];
    };

    const pred3PEColorExpression = buildPred3PEColorExpression();
    const isVisible = censusVisibleRef.current;
    const riskVisibility = view === 'risk' && isVisible ? 'visible' : 'none';
    const pred3PEVisibility = view === 'pred3pe' && isVisible ? 'visible' : 'none';
    const outlineVisibility = isVisible && (view === 'risk' || view === 'pred3pe') ? 'visible' : 'none';

    if (map.current.getSource('census-tracts')) {
      map.current.getSource('census-tracts').setData(censusDataRef.current);
    } else {
      map.current.addSource('census-tracts', {
        type: 'geojson',
        data: censusDataRef.current
      });
    }

    if (!map.current.getLayer('census-tracts-risk')) {
      map.current.addLayer({
        id: 'census-tracts-risk',
        type: 'fill',
        source: 'census-tracts',
        layout: {
          visibility: riskVisibility
        },
        paint: {
          'fill-color': riskColorExpression,
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.7,
            0.5
          ]
        }
      });
    } else {
      map.current.setPaintProperty('census-tracts-risk', 'fill-color', riskColorExpression);
      map.current.setLayoutProperty('census-tracts-risk', 'visibility', riskVisibility);
    }

    // Add PRED3_PE layer
    if (!map.current.getLayer('census-tracts-pred3pe')) {
      map.current.addLayer({
        id: 'census-tracts-pred3pe',
        type: 'fill',
        source: 'census-tracts',
        layout: {
          visibility: pred3PEVisibility
        },
        paint: {
          'fill-color': pred3PEColorExpression,
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.8,
            0.6
          ]
        }
      });
    } else {
      map.current.setPaintProperty('census-tracts-pred3pe', 'fill-color', pred3PEColorExpression);
      map.current.setLayoutProperty('census-tracts-pred3pe', 'visibility', pred3PEVisibility);
    }

    // Removed: census-tracts-population layer - population layer disabled
    /* if (!map.current.getLayer('census-tracts-population')) {
      map.current.addLayer({
        id: 'census-tracts-population',
        type: 'fill',
        source: 'census-tracts',
        layout: {
          visibility: populationVisibility
        },
        paint: {
          'fill-color': populationColorExpression,
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.8,
            0.6
          ]
        }
      });
    } else {
      map.current.setPaintProperty('census-tracts-population', 'fill-color', populationColorExpression);
      map.current.setLayoutProperty('census-tracts-population', 'visibility', populationVisibility);
    } */

    if (!map.current.getLayer('census-tracts-outline')) {
      map.current.addLayer({
        id: 'census-tracts-outline',
        type: 'line',
        source: 'census-tracts',
        layout: {
          visibility: outlineVisibility
        },
        paint: {
          'line-color': '#777777',
          'line-width': 1,
          'line-opacity': 0.6
        }
      });
    } else {
      map.current.setLayoutProperty('census-tracts-outline', 'visibility', outlineVisibility);
    }

    // Add marker buffer layer above census layers if it exists
    if (map.current.getSource('marker-buffers') && !map.current.getLayer('marker-buffers')) {
      map.current.addLayer({
        id: 'marker-buffers',
        type: 'fill',
        source: 'marker-buffers',
        paint: {
          'fill-color': 'transparent',
          'fill-opacity': 0
        }
      });

      // Add event handlers to buffer layer to prevent census hover
      map.current.on('mouseenter', 'marker-buffers', () => {
        isHoveringMarkerRef.current = true;
        if (hoveredCensusIdRef.current !== null && map.current) {
          map.current.setFeatureState(
            { source: 'census-tracts', id: hoveredCensusIdRef.current },
            { hover: false }
          );
          hoveredCensusIdRef.current = null;
        }
      });

      map.current.on('mouseleave', 'marker-buffers', () => {
        isHoveringMarkerRef.current = false;
      });

      map.current.on('mousemove', 'marker-buffers', () => {
        isHoveringMarkerRef.current = true;
        if (hoveredCensusIdRef.current !== null && map.current) {
          map.current.setFeatureState(
            { source: 'census-tracts', id: hoveredCensusIdRef.current },
            { hover: false }
          );
          hoveredCensusIdRef.current = null;
        }
      });
    }

    if (!censusEventsBoundRef.current) {
      const censusLayerIds = ['census-tracts-risk', 'census-tracts-pred3pe'];

      const handleHover = (e) => {
        if (!map.current) return;
        // Don't activate census hover if we're hovering over a marker
        if (isHoveringMarkerRef.current) return;
        
        const feature = e.features && e.features[0];
        if (!feature || feature.id === undefined || feature.id === null) return;

        if (hoveredCensusIdRef.current !== null) {
          map.current.setFeatureState(
            { source: 'census-tracts', id: hoveredCensusIdRef.current },
            { hover: false }
          );
        }

        hoveredCensusIdRef.current = feature.id;
        map.current.setFeatureState(
          { source: 'census-tracts', id: hoveredCensusIdRef.current },
          { hover: true }
        );
      };

      const handleLeave = () => {
        if (!map.current) return;
        if (hoveredCensusIdRef.current !== null) {
          map.current.setFeatureState(
            { source: 'census-tracts', id: hoveredCensusIdRef.current },
            { hover: false }
          );
        }
        hoveredCensusIdRef.current = null;
        map.current.getCanvas().style.cursor = '';
      };

      const handleClick = (e) => {
        if (!map.current) return;
        const features = map.current.queryRenderedFeatures(e.point);
        const overlayLayerIds = OVERLAY_LAYERS_CONFIG.map((c) => c.id + '-layer');
        if (features.length > 0 && overlayLayerIds.includes(features[0].layer.id)) return;
        const feature = e.features && e.features[0];
        if (!feature) return;
        const props = feature.properties || {};
        const tractName = props['L0Census_Tracts.NAME'] || 'Census Tract';
        const tractId = props['L0Census_Tracts.GEOID'] || feature.id || 'N/A';
        const riskRating = props['__riskRating'] || props['T_FEMA_National_Risk_Index_$_.FEMAIndexRating'] || 'Not Rated';
        const pred3PE = props['__pred3PE'];
        // Removed: riskIndexRaw - only showing rating now

        const popupHtml = `
          <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-width: 220px;">
            <div style="font-size: 1.05em; font-weight: 700; color: #1b3a4b; margin-bottom: 4px;">${tractName}</div>
            <div style="font-size: 0.85em; color: #546e7a; margin-bottom: 10px;">Tract ID: ${tractId}</div>
            <hr style="border: none; border-top: 1px solid #e0e6ed; margin: 8px 0;" />
            <div style="font-size: 0.9em; color: #1b3a4b; margin-bottom: 4px;">
              <span style="font-weight: 600;">FEMA Risk Rating:</span>
              <span style="margin-left: 6px;">${riskRating}</span>
            </div>
            ${pred3PE !== null && pred3PE !== undefined ? `
            <div style="font-size: 0.9em; color: #1b3a4b; margin-bottom: 12px;">
              <span style="font-weight: 600;">Resilience Index:</span>
              <span style="margin-left: 6px;">${pred3PE.toFixed(2)}%</span>
            </div>
            ` : ''}
          </div>
        `;

        new mapboxgl.Popup({ closeButton: true, closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(popupHtml)
          .addTo(map.current);
      };

      censusLayerIds.forEach((layerId) => {
        map.current.on('click', layerId, handleClick);
        map.current.on('mouseenter', layerId, () => {
          if (map.current) {
            map.current.getCanvas().style.cursor = 'pointer';
          }
        });
        map.current.on('mousemove', layerId, handleHover);
        map.current.on('mouseleave', layerId, handleLeave);
      });

      censusEventsBoundRef.current = true;
    }

    setCensusLayersReady(true);
  }, []);

  // Toggle between satellite and standard map
  const toggleMapStyle = () => {
    if (!map.current) return;
    
    const newStyle = isSatelliteView ? 'mapbox://styles/mapbox/light-v11' : 'mapbox://styles/mapbox/satellite-v9';
    
    map.current.once('styledata', () => {
      // Commented out: Re-add district polygons after style change (miami_cities.geojson)
      /* Object.keys(districtsRef.current).forEach(districtId => {
        const district = districtsRef.current[districtId];
        
        if (!map.current.getSource(districtId)) {
          map.current.addSource(districtId, {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'Polygon',
                coordinates: [district.coordinates]
              }
            }
          });
        }

        if (!map.current.getLayer(`${districtId}-fill`)) {
          map.current.addLayer({
            id: `${districtId}-fill`,
            type: 'fill',
            source: districtId,
            paint: {
              'fill-color': '#3498db',
              'fill-opacity': 0.1
            }
          });
        }

        if (!map.current.getLayer(`${districtId}-outline`)) {
          map.current.addLayer({
            id: `${districtId}-outline`,
            type: 'line',
            source: districtId,
            paint: {
              'line-color': '#2980b9',
              'line-width': 2,
              'line-opacity': 0.5
            }
          });
        }

        // Re-add event listeners
        map.current.on('click', `${districtId}-fill`, () => {
          zoomToDistrict(districtId);
        });

        map.current.on('mouseenter', `${districtId}-fill`, () => {
          map.current.getCanvas().style.cursor = 'pointer';
        });

        map.current.on('mouseleave', `${districtId}-fill`, () => {
          map.current.getCanvas().style.cursor = '';
        });
      }); */

      // Re-add project markers
      if (allProjectsData) {
        allMarkers.forEach(marker => {
          marker.addTo(map.current);
        });
      }

      addCensusSourceAndLayers();

      const cache = overlayDataCacheRef.current;
      enabledOverlayLayerIds.forEach((layerId) => {
        const geojson = cache[layerId];
        if (!geojson) return;
        const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === layerId);
        if (config) addOverlaySourceAndLayer(map.current, layerId, config, geojson);
      });
    });
    
    map.current.setStyle(newStyle);
    setIsSatelliteView(!isSatelliteView);
  };

  // Helper function to shift bounds northeast (to avoid south and west areas)
  const shiftBoundsNortheast = (bounds) => {
    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    
    // Calculate ranges
    const lngRange = ne.lng - sw.lng;
    const latRange = ne.lat - sw.lat;
    
    // Shift southwest corner northeast: 55% east, 50% north
    const shiftLng = lngRange * 0.55;
    const shiftLat = latRange * 0.50;
    
    // Create new bounds with shifted southwest corner
    const shiftedBounds = new mapboxgl.LngLatBounds();
    shiftedBounds.extend([sw.lng + shiftLng, sw.lat + shiftLat]);
    shiftedBounds.extend([ne.lng, ne.lat]);
    
    return shiftedBounds;
  };

  useEffect(() => {
    if (map.current) return;

    // Get Mapbox access token from environment variable
    const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) {
      console.error('Mapbox access token is missing. Please set VITE_MAPBOX_ACCESS_TOKEN in your .env file.');
      setError('Mapbox access token is not configured. Please check your environment variables.');
      setLoading(false);
      return;
    }
    mapboxgl.accessToken = mapboxToken;
    
    const loadDistricts = async () => {
    try {
      const response = await fetch('/miami_cities.geojson');
      const geojson = await response.json();

      const districts = {};

      geojson.features.forEach((feature) => {
        const coordinates = feature.geometry.coordinates[0];
        const lngs = coordinates.map(c => c[0]);
        const lats = coordinates.map(c => c[1]);
        const name = feature.properties['NAME'];
        const center = {
          lng: lngs.reduce((a, b) => a + b) / lngs.length,
          lat: lats.reduce((a, b) => a + b) / lats.length
        };
        const districtId = feature.properties['OBJECTID'];
        const cn = Math.pow(-(Math.min(...lngs) - Math.max(...lngs)), 0.12);
        const cs = Math.pow(-(Math.min(...lats) - Math.max(...lats)), 0.12);
        let cf = 0;
        if(cn > cs) {
          cf = cn;
        } else {
          cf = cs
        }
        const zoom = 9 / cf;
        console.log(name + ": " + zoom + " " + cn);
        districts[districtId] = {
          name,
          coordinates,
          zoom,
          center
        }
       {}});
      districtsRef.current = districts;
    }catch(err) {
      console.error('Error loading cities:', err);
    }
    }

    const init = async () => {
      await loadDistricts();
    };

    init();

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-80.70, 26.15],
      zoom: 11,
      attributionControl: false
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-left');
    map.current.addControl(new mapboxgl.FullscreenControl(), 'top-left');
    map.current.addControl(new mapboxgl.ScaleControl({
      maxWidth: 100,
      unit: 'imperial'
    }), 'bottom-left');

    const applyMobileRotation = () => {
      if (!map.current) return;
      if (isMobileRef.current) {
        map.current.dragRotate.disable();
        map.current.touchZoomRotate.disableRotation();
      } else {
        map.current.dragRotate.enable();
        map.current.touchZoomRotate.enableRotation();
      }
    };

    map.current.on('load', async () => {
      applyMobileRotation();
      try {
        // Commented out: miami_cities.geojson layer rendering
        /* Object.keys(districtsRef.current).forEach(districtId => {
          const district = districtsRef.current[districtId];

          map.current.addSource(districtId, {
            type: 'geojson',
            data: {
              type: 'Feature',
              geometry: {
                type: 'Polygon',
                coordinates: [district.coordinates]
              }
            }
          });

          map.current.addLayer({
            id: `${districtId}-fill`,
            type: 'fill',
            source: districtId,
            paint: {
              'fill-color': '#3498db',
              'fill-opacity': 0.1
            }
          });

          map.current.addLayer({
            id: `${districtId}-outline`,
            type: 'line',
            source: districtId,
            paint: {
              'line-color': '#2980b9',
              'line-width': 2,
              'line-opacity': 0.5
            }
          });

          map.current.on('click', `${districtId}-fill`, () => {
            zoomToDistrict(districtId);
          });

          map.current.on('mouseenter', `${districtId}-fill`, () => {
            map.current.getCanvas().style.cursor = 'pointer';
          });

          map.current.on('mouseleave', `${districtId}-fill`, () => {
            map.current.getCanvas().style.cursor = '';
          });
        }); */
      } catch (err) {
        console.error('Map initialization error:', err);
        setError('Error initializing map');
        setLoading(false);
      }

      try {
        const projectsGeoJsonUrl =
          import.meta.env.VITE_SUPABASE_URL &&
          `${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/project-data/${PROJECTS_GEOJSON_FILE}`;
        if (!projectsGeoJsonUrl) {
          throw new Error('VITE_SUPABASE_URL is not set. Set it in .env to load project data from Storage.');
        }
        const response = await fetch(projectsGeoJsonUrl, { cache: 'no-store' });

        if (!response.ok) {
          throw new Error(`Failed to load project data: ${response.status}`);
        }

        const data = await response.json();
        console.log('[Projects] Loaded Storage', PROJECTS_GEOJSON_FILE + ':', data.features?.length ?? 0, 'features');
        console.log('[Projects] Sample properties:', data.features[0]?.properties ? Object.keys(data.features[0].properties).slice(0, 10) : 'No properties');
        console.log('[Projects] Sample Infrastruc value:', data.features[0]?.properties?.Infrastruc);
        console.log('[Projects] Sample NAME (city) value:', data.features[0]?.properties?.NAME);
        setAllProjectsData(data);

        map.current.addSource('projects', {
          type: 'geojson',
          data: data
        });

        // Create invisible buffer zones around each marker
        const bufferFeatures = data.features.map((feature, index) => {
          const coordinates = feature.geometry.coordinates;
          const circleCoords = createCircleBuffer(coordinates, 30); // 30 meter radius buffer
          return {
            type: 'Feature',
            id: `marker-buffer-${index}`,
            geometry: {
              type: 'Polygon',
              coordinates: [circleCoords]
            },
            properties: {
              markerIndex: index
            }
          };
        });

        const bufferGeoJSON = {
          type: 'FeatureCollection',
          features: bufferFeatures
        };

        // Add buffer zones as an invisible layer to intercept mouse events
        map.current.addSource('marker-buffers', {
          type: 'geojson',
          data: bufferGeoJSON
        });

        // Buffer layer will be added in addCensusSourceAndLayers after census layers

        const markers = [];
        data.features.forEach(feature => {
          const geometry = feature.geometry;
          const coordinates = geometry && geometry.coordinates;
          // Skip features without valid point coordinates
          if (
            !geometry ||
            geometry.type !== 'Point' ||
            !Array.isArray(coordinates) ||
            coordinates.length < 2 ||
            typeof coordinates[0] !== 'number' ||
            typeof coordinates[1] !== 'number' ||
            !Number.isFinite(coordinates[0]) ||
            !Number.isFinite(coordinates[1])
          ) {
            console.warn('[Projects] Skipping feature with invalid coordinates:', feature.id);
            return;
          }

          const properties = feature.properties;
          
          // Normalize city property by trimming whitespace (use NAME field, fallback to City)
          const cityField = properties['NAME'] || properties['City'];
          if (cityField) {
            if (properties['NAME']) {
              properties['NAME'] = properties['NAME'].trim();
            }
            if (properties['City']) {
              properties['City'] = properties['City'].trim();
            }
          }

          const marker = new mapboxgl.Marker({
            color: getMarkerColor(properties['Infrastruc'] || properties['Infrastructure Type'] || properties['Type']),
            scale: isMobileRef.current ? 0.5 : 0.7
          })
            .setLngLat(coordinates);

          marker.getElement().addEventListener('click', (e) => {
            e.stopPropagation();
            // Mark that we're switching features to prevent popupClosed from clearing it
            isSwitchingFeatureRef.current = true;
            setActiveFeature(feature);
            // Reset the flag after a short delay to allow the popup to update
            setTimeout(() => {
              isSwitchingFeatureRef.current = false;
            }, 100);
          });

          if (!isMobileRef.current) {
            marker.getElement().addEventListener('mouseenter', (e) => {
              e.stopPropagation();
              // Set flag to prevent census hover
              isHoveringMarkerRef.current = true;
              // Clear any active census hover state
              if (hoveredCensusIdRef.current !== null && map.current) {
                map.current.setFeatureState(
                  { source: 'census-tracts', id: hoveredCensusIdRef.current },
                  { hover: false }
                );
                hoveredCensusIdRef.current = null;
              }
            });

            marker.getElement().addEventListener('mouseleave', (e) => {
              e.stopPropagation();
              // Clear flag to allow census hover again
              isHoveringMarkerRef.current = false;
            });
          }

          marker.addTo(map.current);
          marker.feature = feature;
          markers.push(marker);
        });

        setAllMarkers(markers);

        // Use marker positions (valid points only) to compute initial bounds
        if (markers.length > 0) {
          const bounds = new mapboxgl.LngLatBounds();
          markers.forEach(marker => {
            const coords = marker.getLngLat();
            bounds.extend([coords.lng, coords.lat]);
          });
          if (!bounds.isEmpty()) {
            // Use shifted bounds for default position (shifted northeast)
            const shiftedBounds = shiftBoundsNortheast(bounds);
            map.current.fitBounds(shiftedBounds, { 
              padding: { top: 10, bottom: 300, left: 200, right: 10 },
              maxZoom: 13,
              duration: 0 // No animation on initial load
            });
          }
        }

        setLoading(false);
      } catch (err) {
        console.error('Error loading project data:', err);
        setError('Unable to load project data. Please ensure the GeoJSON file is available or use a CORS proxy.');
        setLoading(false);
      }

      // Load FL_CRE.csv data
      try {
        const csvResponse = await fetch('/FL_CRE.csv');
        if (csvResponse.ok) {
          const csvText = await csvResponse.text();
          const lines = csvText.split('\n').filter(line => line.trim());
          
          // Simple CSV parser that handles quoted fields
          const parseCSVLine = (line) => {
            const result = [];
            let current = '';
            let inQuotes = false;
            for (let i = 0; i < line.length; i++) {
              const char = line[i];
              if (char === '"') {
                inQuotes = !inQuotes;
              } else if (char === ',' && !inQuotes) {
                result.push(current.trim());
                current = '';
              } else {
                current += char;
              }
            }
            result.push(current.trim());
            return result;
          };
          
          const headers = parseCSVLine(lines[0]);
          const geoIdIndex = headers.indexOf('GEO_ID');
          const pred3PEIndex = headers.indexOf('PRED3_PE');
          
          const pred3PEMap = {};
          for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            const values = parseCSVLine(lines[i]);
            if (values.length > Math.max(geoIdIndex, pred3PEIndex)) {
              const geoId = values[geoIdIndex]?.trim();
              const pred3PE = parseFloat(values[pred3PEIndex]?.trim());
              
              if (geoId && !isNaN(pred3PE)) {
                // Convert "1400000US12086000107" to "12086000107"
                const geoid = geoId.replace('1400000US', '');
                pred3PEMap[geoid] = pred3PE;
              }
            }
          }
          pred3PEDataRef.current = pred3PEMap;
          console.log(`[PRED3_PE] Loaded ${Object.keys(pred3PEMap).length} census tract values`);
        }
      } catch (csvError) {
        console.warn('Error loading FL_CRE.csv:', csvError);
      }

      try {
        const response = await fetch('/femaindex.geojson');
        if (!response.ok) {
          throw new Error(`Failed to load census tract data: ${response.status}`);
        }

        const rawGeojson = await response.json();
        const reprojected = reprojectFeatureCollectionIfNeeded(rawGeojson);
        const processedFeatures = (reprojected.features || []).map((feature, index) => {
          const properties = { ...(feature.properties || {}) };
          const riskRating = properties['T_FEMA_National_Risk_Index_$_.FEMAIndexRating'] || null;
          const populationValue = parseNumericValue(
            properties['T_CENSUS_Community_Resilience_Est$_.Total_population__excludes_adult_correctional_juvenile_facilitie']
          );
          const geoid = properties['L0Census_Tracts.GEOID'];
          const pred3PE = geoid ? pred3PEDataRef.current[geoid] : null;

          return {
            ...feature,
            id: feature.id ?? geoid ?? index,
            properties: {
              ...properties,
              __riskRating: riskRating,
              __population: populationValue,
              __pred3PE: pred3PE !== null && pred3PE !== undefined ? pred3PE : null
            }
          };
        });

        const processedGeojson = {
          ...reprojected,
          features: processedFeatures
        };

        const riskRatings = processedFeatures
          .map(feature => feature.properties.__riskRating)
          .filter(value => value !== null && value !== undefined);
        const populationValues = processedFeatures
          .map(feature => feature.properties.__population)
          .filter(value => Number.isFinite(value));
        const pred3PEValues = processedFeatures
          .map(feature => feature.properties.__pred3PE)
          .filter(value => value !== null && value !== undefined && Number.isFinite(value));

        // Get unique risk ratings for stats
        const uniqueRatings = [...new Set(riskRatings)];
        const riskStats = { ratings: uniqueRatings, count: riskRatings.length };
        const populationStats = getRangeStats(populationValues);
        const pred3PEStats = getRangeStats(pred3PEValues);

        const riskMissing = processedFeatures.length - riskRatings.length;
        const populationMissing = processedFeatures.length - populationValues.length;
        const pred3PEMissing = processedFeatures.length - pred3PEValues.length;

        censusDataRef.current = processedGeojson;
        const statsPayload = {
          risk: riskStats,
          population: populationStats,
          pred3PE: pred3PEStats,
          counts: {
            total: processedFeatures.length,
            missingRisk: riskMissing,
            missingPopulation: populationMissing,
            missingPred3PE: pred3PEMissing
          }
        };
        censusStatsRef.current = statsPayload;
        setCensusStats(statsPayload);
        addCensusSourceAndLayers();

        const bounds = new mapboxgl.LngLatBounds();
        let hasBounds = false;
        processedFeatures.forEach(feature => {
          if (!feature.geometry) return;
          walkCoordinates(feature.geometry, coord => {
            if (!hasBounds) {
              bounds.set(coord, coord);
              hasBounds = true;
            } else {
              bounds.extend(coord);
            }
          });
        });

        if (hasBounds) {
          map.current.fitBounds(bounds, { padding: { top: 10, bottom: 300, left: 350, right: 10 }, duration: 1200 });
        }

        console.groupCollapsed('[Census] Census Tract Data Summary');
        console.log('Total tracts loaded:', processedFeatures.length);
        console.log('FEMA Risk Ratings found:', uniqueRatings);
        console.log('Population range:', populationStats.min, populationStats.max);
        if (riskMissing > 0) {
          console.warn(`Missing FEMA Risk Rating for ${riskMissing} tracts`, processedFeatures
            .filter(feature => !feature.properties.__riskRating)
            .slice(0, 10)
            .map(feature => feature.properties['L0Census_Tracts.GEOID'] || feature.id));
        }
        if (populationMissing > 0) {
          console.warn(`Missing population for ${populationMissing} tracts`, processedFeatures
            .filter(feature => !Number.isFinite(feature.properties.__population))
            .slice(0, 10)
            .map(feature => feature.properties['L0Census_Tracts.GEOID'] || feature.id));
        }
        console.groupEnd();
        console.info('[Census] Census tract layers added successfully');
      } catch (censusError) {
        console.error('Error loading census tract data:', censusError);
      }
    });
  }, [addCensusSourceAndLayers]);

  useEffect(() => {
    censusVisibleRef.current = censusVisible;
  }, [censusVisible]);

  useEffect(() => {
    censusViewRef.current = activeCensusView;
    if (!map.current) return;
    const riskVisibility = censusVisible && activeCensusView === 'risk' ? 'visible' : 'none';
    const pred3PEVisibility = censusVisible && activeCensusView === 'pred3pe' ? 'visible' : 'none';
    if (map.current.getLayer('census-tracts-risk')) {
      map.current.setLayoutProperty('census-tracts-risk', 'visibility', riskVisibility);
    }
    if (map.current.getLayer('census-tracts-pred3pe')) {
      map.current.setLayoutProperty('census-tracts-pred3pe', 'visibility', pred3PEVisibility);
    }
    const showCensusOutline = censusVisible && (activeCensusView === 'risk' || activeCensusView === 'pred3pe');
    if (map.current.getLayer('census-tracts-outline')) {
      map.current.setLayoutProperty('census-tracts-outline', 'visibility', showCensusOutline ? 'visible' : 'none');
    }
    if (!censusVisible) {
      if (hoveredCensusIdRef.current !== null) {
        map.current.setFeatureState(
          { source: 'census-tracts', id: hoveredCensusIdRef.current },
          { hover: false }
        );
        hoveredCensusIdRef.current = null;
      }
      map.current.getCanvas().style.cursor = '';
    }
    if (censusLayersReady) {
      addCensusSourceAndLayers();
    }
  }, [activeCensusView, censusVisible, censusLayersReady, addCensusSourceAndLayers]);

  useEffect(() => {
    if (!map.current) return;
    const isCriticalInfra = activeCensusView === 'critical-infrastructure';
    OVERLAY_LAYERS_CONFIG.forEach((config) => {
      const layerMapId = config.id + '-layer';
      if (map.current.getLayer(layerMapId)) {
        const visible = isCriticalInfra && enabledOverlayLayerIds.includes(config.id);
        map.current.setLayoutProperty(layerMapId, 'visibility', visible ? 'visible' : 'none');
      }
    });
  }, [activeCensusView, enabledOverlayLayerIds]);

  useEffect(() => {
    if (censusStats) {
      censusStatsRef.current = censusStats;
      if (censusLayersReady) {
        addCensusSourceAndLayers();
      }
    }
  }, [censusStats, censusLayersReady, addCensusSourceAndLayers]);

  // Legend for risk ratings - now using continuous yellow-to-red scale
  const legendRatings = censusStats?.risk?.ratings || [];
  const sortedRatings = ['Very Low', 'Relatively Low', 'Relatively Moderate', 'Relatively High', 'Very High']
    .filter(rating => legendRatings.includes(rating));

  // Extract unique values for filters
  const getUniqueValues = (field) => {
    if (!allProjectsData?.features) return [];
    const values = allProjectsData.features
      .map(f => {
        // For city, prefer NAME field, fallback to City
        let value;
        if (field === 'City' || field === 'NAME') {
          value = f.properties?.['NAME'] || f.properties?.['City'];
        } else {
          value = f.properties?.[field];
        }
        // Trim whitespace for city fields
        return ((field === 'City' || field === 'NAME') && value) ? value.trim() : value;
      })
      .filter(v => v && v !== null && v !== undefined && v !== 'Null')
      .filter((v, i, arr) => arr.indexOf(v) === i)
      .sort();
    return values;
  };

  // Get unique types - prefer 'Infrastruc', fallback to 'Infrastructure Type' or 'Type'
  const infrastructureTypes = getUniqueValues('Infrastruc');
  const legacyTypes = getUniqueValues('Infrastructure Type');
  const fallbackTypes = getUniqueValues('Type');
  const uniqueTypes = infrastructureTypes.length > 0 ? infrastructureTypes : (legacyTypes.length > 0 ? legacyTypes : fallbackTypes);
  const uniqueCategories = getUniqueValues('Categories');
  const disasterFocusNew = getUniqueValues('Disaster_F');
  const disasterFocusLegacy = getUniqueValues('Disaster Focus');
  const uniqueDisasterFocus = disasterFocusNew.length > 0 ? disasterFocusNew : disasterFocusLegacy;
  // Get unique cities - prefer NAME field, fallback to City; dedupe case-insensitively so "Miami"/"miami"/"MIAMI" show once
  const uniqueCitiesRaw = getUniqueValues('NAME');
  const cityByLower = new Map();
  uniqueCitiesRaw.forEach((c) => {
    const key = (c || '').toLowerCase();
    if (!cityByLower.has(key)) cityByLower.set(key, c);
  });
  const uniqueCities = Array.from(cityByLower.values()).sort((a, b) => (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' }));

  // Zoom to city markers when city is selected
  const zoomToCity = (cityName) => {
    if (!map.current || !allMarkers.length) return;

    // If no city selected (All Cities), zoom to all markers (respecting other filters)
    // Filter markers for the selected city, or use all markers if "All Cities"
    const markersToZoom = (!cityName || cityName === '') 
      ? allMarkers.filter(marker => {
          // Include all markers that are currently visible (respecting Type/Disaster Focus filters)
          return marker.getElement().style.display !== 'none';
        })
      : // Filter markers for the selected city
        allMarkers.filter(marker => {
          if (!marker.feature) return false;
          const props = marker.feature.properties || {};
          const markerCity = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);
          const selectedCityTrimmed = cityName ? cityName.trim() : cityName;
          return (markerCity || '').toLowerCase() === (selectedCityTrimmed || '').toLowerCase();
        });

    if (markersToZoom.length === 0) return;

    // Calculate bounding box from marker positions
    const bounds = new mapboxgl.LngLatBounds();
    markersToZoom.forEach(marker => {
      const coords = marker.getLngLat();
      bounds.extend([coords.lng, coords.lat]);
    });

    if (!bounds.isEmpty()) {
      // If "All Cities" is selected, shift bounds to avoid south and west areas
      if (!cityName || cityName === '') {
        const shiftedBounds = shiftBoundsNortheast(bounds);
        
        map.current.fitBounds(shiftedBounds, { 
          padding: { top: 10, bottom: 300, left: 200, right: 10 },
          maxZoom: 13,
          duration: 1500 
        });
      } else {
        map.current.fitBounds(bounds, { 
          padding: { top: 10, bottom: 300, left: 200, right: 10 },
          maxZoom: 12,
          duration: 1500 
        });
      }
    }
  };

  // Filter markers based on selected filters
  useEffect(() => {
    if (!allMarkers.length || !map.current) return;

    allMarkers.forEach(marker => {
      if (!marker.feature) return;
      const props = marker.feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'];
      const category = props['Categories'];
      const disasterFocus = props['Disaster_F'] || props['Disaster Focus'];
      const city = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);

      const typeMatch = selectedTypes.length === 0 || selectedTypes.includes(type);
      const disasterMatch = selectedDisasterFocus.length === 0 || selectedDisasterFocus.includes(disasterFocus);
      const selectedCityTrimmed = selectedCity ? selectedCity.trim() : selectedCity;
      const cityMatch = !selectedCityTrimmed || selectedCityTrimmed === '' || (city || '').toLowerCase() === (selectedCityTrimmed || '').toLowerCase();

      const shouldShow = projectsLayerVisible && typeMatch && disasterMatch && cityMatch;

      if (shouldShow) {
        marker.getElement().style.display = 'block';
      } else {
        marker.getElement().style.display = 'none';
        // Close popup if the hidden marker's feature is currently active
        if (activeFeature && marker.feature) {
          // Check if it's the same feature (same object reference or same coordinates)
          const isSameFeature = activeFeature === marker.feature ||
            (activeFeature.geometry?.coordinates && marker.feature.geometry?.coordinates &&
             activeFeature.geometry.coordinates[0] === marker.feature.geometry.coordinates[0] &&
             activeFeature.geometry.coordinates[1] === marker.feature.geometry.coordinates[1]);
          
          if (isSameFeature) {
            setActiveFeature(null);
          }
        }
      }
    });
  }, [projectsLayerVisible, selectedTypes, selectedDisasterFocus, selectedCity, allMarkers, activeFeature]);

  // Zoom to city when selected (including "All Cities")
  useEffect(() => {
    if (map.current && allMarkers.length && selectedCity !== undefined) {
      // Use setTimeout to ensure markers are filtered/displayed first
      const timeoutId = setTimeout(() => {
        zoomToCity(selectedCity);
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [selectedCity]);

  // Calculate filtered statistics (project count and total investment)
  const filteredStats = useMemo(() => {
    if (!allProjectsData?.features) {
      return { projectCount: 0, totalInvestment: 0 };
    }

    const filteredFeatures = allProjectsData.features.filter(feature => {
      const props = feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'];
      const disasterFocus = props['Disaster_F'] || props['Disaster Focus'];
      const city = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);
      
      const typeMatch = selectedTypes.length === 0 || selectedTypes.includes(type);
      const disasterMatch = selectedDisasterFocus.length === 0 || selectedDisasterFocus.includes(disasterFocus);
      const selectedCityTrimmed = selectedCity ? selectedCity.trim() : selectedCity;
      const cityMatch = !selectedCityTrimmed || selectedCityTrimmed === '' || (city || '').toLowerCase() === (selectedCityTrimmed || '').toLowerCase();

      return typeMatch && disasterMatch && cityMatch;
    });

    const projectCount = filteredFeatures.length;
    
    // Calculate total investment
    const totalInvestment = filteredFeatures.reduce((sum, feature) => {
      const cost = feature.properties?.['Estimated_'] || feature.properties?.['Estimated Project Cost'];
      if (!cost || cost === null || cost === undefined) return sum;
      
      // Convert to number if it's a string
      const numericCost = typeof cost === 'string' 
        ? parseFloat(cost.replace(/[$,]/g, '')) 
        : parseFloat(cost);
      
      if (isNaN(numericCost) || !isFinite(numericCost)) return sum;
      
      return sum + numericCost;
    }, 0);

    return { projectCount, totalInvestment };
  }, [allProjectsData, selectedTypes, selectedDisasterFocus, selectedCity]);

  // Calculate pie chart data based on city, disaster focus, and infrastructure type filters
  const pieChartData = useMemo(() => {
    if (!allProjectsData?.features) {
      return [];
    }

    // Filter by city, disaster focus, and infrastructure type
    const filteredFeatures = allProjectsData.features.filter(feature => {
      const props = feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'];
      const disasterFocus = props['Disaster_F'] || props['Disaster Focus'];
      const city = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);
      
      const typeMatch = selectedTypes.length === 0 || selectedTypes.includes(type);
      const disasterMatch = selectedDisasterFocus.length === 0 || selectedDisasterFocus.includes(disasterFocus);
      const selectedCityTrimmed = selectedCity ? selectedCity.trim() : selectedCity;
      const cityMatch = !selectedCityTrimmed || selectedCityTrimmed === '' || (city || '').toLowerCase() === (selectedCityTrimmed || '').toLowerCase();

      return typeMatch && disasterMatch && cityMatch;
    });

    // Count projects by infrastructure type
    const typeCounts = {};
    filteredFeatures.forEach(feature => {
      const props = feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || 'Unknown';
      
      // Normalize type names
      let normalizedType = type;
      if (type === 'Blue Infrastructure' || type === 'Blue') {
        normalizedType = 'Blue';
      } else if (type === 'Green Infrastructure' || type === 'Green') {
        normalizedType = 'Green';
      } else if (type === 'Grey Infrastructure' || type === 'Grey') {
        normalizedType = 'Grey';
      } else if (type === 'Hybrid') {
        normalizedType = 'Hybrid';
      }
      
      typeCounts[normalizedType] = (typeCounts[normalizedType] || 0) + 1;
    });

    // Convert to array format for recharts
    const colors = {
      'Blue': '#3498db',
      'Green': '#27ae60',
      'Grey': '#95a5a6',
      'Hybrid': '#9b59b6',
      'Unknown': '#95a5a6'
    };

    return Object.entries(typeCounts)
      .map(([name, value]) => ({
        name,
        value,
        color: colors[name] || '#95a5a6'
      }))
      .sort((a, b) => b.value - a.value); // Sort by count descending
  }, [allProjectsData, selectedTypes, selectedDisasterFocus, selectedCity]);

  return (
    <div style={{ display: 'flex', flex: 1, width: '100%', overflow: 'hidden', boxSizing: 'border-box', minHeight: 0, position: 'relative' }}>
        {isMobile && sidebarOpen && (
          <div
            role="presentation"
            aria-hidden
            onClick={() => setSidebarOpen(false)}
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 1099,
              backgroundColor: 'rgba(0,0,0,0.35)',
              transition: 'opacity 0.2s ease'
            }}
          />
        )}
        <aside style={{
          maxWidth: 320,
          background: 'rgba(255, 255, 255, 0.5)',
          backdropFilter: 'blur(28px) saturate(200%)',
          WebkitBackdropFilter: 'blur(28px) saturate(200%)',
          borderRight: '1px solid rgba(255, 255, 255, 0.55)',
          overflowY: 'auto',
          padding: '20px',
          paddingTop: isMobile ? 'max(20px, env(safe-area-inset-top))' : '20px',
          boxShadow: '4px 0 32px rgba(0, 0, 0, 0.14), inset 0 0 0 1px rgba(255, 255, 255, 0.65)',
          ...(isMobile ? {
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            width: '85%',
            zIndex: 1100,
            transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
            transition: 'transform 0.25s ease-out'
          } : {
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: 'clamp(240px, 26vw, 320px)',
            minWidth: 240,
            zIndex: 101,
          })
        }}>
          {isMobile && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px' }}>
              <button
                type="button"
                aria-label="Close filters"
                onClick={() => setSidebarOpen(false)}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: '1px solid rgba(0,0,0,0.15)',
                  background: 'rgba(255,255,255,0.8)',
                  color: '#2c3e50',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          )}
          {/* Projects layer toggle */}
          <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
            <span style={{ fontSize: '0.95em', fontWeight: '500', color: '#2c3e50' }}>Projects</span>
            <button
              type="button"
              role="switch"
              aria-checked={projectsLayerVisible}
              aria-label={projectsLayerVisible ? 'Hide projects layer' : 'Show projects layer'}
              onClick={() => setProjectsLayerVisible(v => !v)}
              style={{
                width: 40,
                height: 22,
                borderRadius: 11,
                border: '1px solid rgba(0,0,0,0.2)',
                background: projectsLayerVisible ? '#3498db' : 'rgba(200,200,200,0.8)',
                cursor: 'pointer',
                padding: 0,
                flexShrink: 0,
                position: 'relative',
                transition: 'background 0.2s ease'
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  top: 2,
                  left: projectsLayerVisible ? 20 : 2,
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  background: '#fff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
                  transition: 'left 0.2s ease'
                }}
              />
            </button>
          </div>
          {/* City Filter */}
          <div style={{ marginBottom: '24px', position: 'relative' }} data-city-dropdown>
            <h3 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              City
            </h3>
            <div
              onClick={() => setCityDropdownOpen(!cityDropdownOpen)}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '0.9em',
                color: selectedCity ? '#2c3e50' : '#999',
                border: '1px solid rgba(255, 255, 255, 0.4)',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(10px) saturate(180%)',
                WebkitBackdropFilter: 'blur(10px) saturate(180%)',
                cursor: 'pointer',
                outline: 'none',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
                transition: 'all 0.2s ease'
              }}
            >
              <span>{selectedCity ? formatCityName(selectedCity) : 'All Cities'}</span>
              <span style={{ fontSize: '0.7em' }}>▼</span>
            </div>
            {cityDropdownOpen && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                maxHeight: '150px',
                height: '150px',
                overflowY: 'auto',
                backgroundColor: 'rgba(255, 255, 255, 0.85)',
                backdropFilter: 'blur(20px) saturate(180%)',
                WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                border: '1px solid rgba(255, 255, 255, 0.4)',
                borderRadius: '8px',
                marginTop: '4px',
                zIndex: 1000,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.5)'
              }}>
                <div
                  onClick={() => {
                    setSelectedCity('');
                    setCityDropdownOpen(false);
                  }}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    color: selectedCity === '' ? '#3498db' : '#2c3e50',
                    backgroundColor: selectedCity === '' ? 'rgba(240, 248, 255, 0.7)' : 'transparent',
                    borderRadius: '6px',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(240, 248, 255, 0.5)'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = selectedCity === '' ? 'rgba(240, 248, 255, 0.7)' : 'transparent'}
                >
                  All Cities
                </div>
                {uniqueCities.map(city => (
                  <div
                    key={city}
                    onClick={() => {
                      setSelectedCity(city);
                      setCityDropdownOpen(false);
                    }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      fontSize: '0.9em',
                      color: selectedCity === city ? '#3498db' : '#2c3e50',
                      backgroundColor: selectedCity === city ? 'rgba(240, 248, 255, 0.7)' : 'transparent',
                      borderRadius: '6px',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(240, 248, 255, 0.5)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = selectedCity === city ? 'rgba(240, 248, 255, 0.7)' : 'transparent'}
                  >
                    {formatCityName(city)}
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Type Filter */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              Infrastructure Type
            </h3>
            <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
              {uniqueTypes.map(type => (
                <label key={type} style={{ display: 'flex', alignItems: 'center', marginBottom: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedTypes([...selectedTypes, type]);
                      } else {
                        setSelectedTypes(selectedTypes.filter(t => t !== type));
                      }
                    }}
                    style={{ marginRight: '8px', cursor: 'pointer' }}
                  />
                  <span style={{ color: '#546e7a', fontSize: '0.9em' }}>{type}</span>
                </label>
              ))}
            </div>
            {selectedTypes.length > 0 && (
              <button
                onClick={() => setSelectedTypes([])}
                style={{
                  marginTop: '8px',
                  padding: '4px 8px',
                  fontSize: '0.85em',
                  background: 'transparent',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#546e7a'
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Disaster Focus Filter */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              Disaster Focus
            </h3>
            <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
              {uniqueDisasterFocus.map(focus => (
                <label key={focus} style={{ display: 'flex', alignItems: 'center', marginBottom: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedDisasterFocus.includes(focus)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDisasterFocus([...selectedDisasterFocus, focus]);
                      } else {
                        setSelectedDisasterFocus(selectedDisasterFocus.filter(f => f !== focus));
                      }
                    }}
                    style={{ marginRight: '8px', cursor: 'pointer' }}
                  />
                  <span style={{ color: '#546e7a', fontSize: '0.9em' }}>{focus}</span>
                </label>
              ))}
            </div>
            {selectedDisasterFocus.length > 0 && (
              <button
                onClick={() => setSelectedDisasterFocus([])}
                style={{
                  marginTop: '8px',
                  padding: '4px 8px',
                  fontSize: '0.85em',
                  background: 'transparent',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#546e7a'
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Statistics Squares */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '12px', 
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(0, 0, 0, 0.1)'
          }}>
            {/* Total Projects Square */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px) saturate(180%)',
              WebkitBackdropFilter: 'blur(10px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.4)',
              borderRadius: '12px',
              padding: '16px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
              textAlign: 'center'
            }}>
              <div style={{ 
                fontSize: '1.75em', 
                fontWeight: 700, 
                color: '#2c3e50',
                marginBottom: '4px'
              }}>
                {filteredStats.projectCount}
              </div>
              <div style={{ 
                fontSize: '0.75em', 
                color: '#546e7a',
                fontWeight: 500
              }}>
                Projects
              </div>
            </div>
            
            {/* Total Investment Square */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px) saturate(180%)',
              WebkitBackdropFilter: 'blur(10px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.4)',
              borderRadius: '12px',
              padding: '16px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
              textAlign: 'center'
            }}>
              <div style={{ 
                fontSize: '1.5em', 
                fontWeight: 700, 
                color: '#2c3e50',
                marginBottom: '4px',
                lineHeight: 1.2
              }}>
                {filteredStats.totalInvestment > 0 
                  ? formatCostCompact(filteredStats.totalInvestment)
                  : '—'}
              </div>
              <div style={{ 
                fontSize: '0.75em', 
                color: '#546e7a',
                fontWeight: 500
              }}>
                Total Investment
              </div>
            </div>
          </div>

          {/* Pie Chart */}
          {pieChartData.length > 0 && (
            <div style={{
              marginTop: '24px',
              paddingTop: '24px',
              borderTop: '1px solid rgba(0, 0, 0, 0.1)'
            }}>
              <h3 style={{ 
                fontSize: '1em', 
                fontWeight: '500', 
                color: '#2c3e50', 
                marginBottom: '12px',
                textAlign: 'center'
              }}>
                Infrastructure Type Distribution
              </h3>
              <div style={{
                background: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(10px) saturate(180%)',
                WebkitBackdropFilter: 'blur(10px) saturate(180%)',
                border: '1px solid rgba(255, 255, 255, 0.4)',
                borderRadius: '12px',
                padding: '12px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)'
              }}>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      outerRadius={55}
                      fill="#8884d8"
                      dataKey="value"
                      isAnimationActive={false}
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => [`${value} projects`, 'Count']}
                      contentStyle={{
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        border: '1px solid rgba(0, 0, 0, 0.1)',
                        borderRadius: '8px',
                        padding: '8px'
                      }}
                    />
                    <Legend 
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      wrapperStyle={{ fontSize: '0.75em', paddingTop: '8px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* NSF Disclaimer */}
          <div style={{
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px) saturate(180%)',
              WebkitBackdropFilter: 'blur(10px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.4)',
              borderRadius: '12px',
              padding: '16px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)'
            }}>
              <p style={{
                fontSize: '0.75em',
                color: '#546e7a',
                lineHeight: 1.6,
                margin: 0,
                textAlign: 'justify'
              }}>
                This project is based upon work supported by the National Science Foundation under Grant Number (
                <a 
                  href="https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2435008&HistoricalAwards=false"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: '#3498db',
                    textDecoration: 'none'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                  onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                >
                  2435008
                </a>
                ).
              </p>
              <div style={{ marginTop: '8px' }}>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setShowDisclaimer(!showDisclaimer);
                  }}
                  style={{
                    fontSize: '0.75em',
                    color: '#3498db',
                    textDecoration: 'none',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                  onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                >
                  Disclaimer
                </a>
                {showDisclaimer && (
                  <span style={{ fontSize: '0.75em', color: '#546e7a' }}>: Any opinions, findings, and conclusions or recommendations expressed in this website are those of the investigator(s) and do not necessarily reflect the views of the National Science Foundation.</span>
                )}
              </div>
              <p style={{
                fontSize: '0.75em',
                color: '#546e7a',
                lineHeight: 1.6,
                margin: '12px 0 0 0',
                textAlign: 'left'
              }}>
                For more information and suggestions, contact Dr. Sarbeswar Praharaj at <a 
                  href="mailto:spraharaj@miami.edu"
                  style={{
                    color: '#3498db',
                    textDecoration: 'none'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                  onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                >
                  spraharaj@miami.edu
                </a>.
              </p>
            </div>
          </div>
        </aside>

        
        


        <div style={{ flex: 1, position: 'relative', height: '100%', width: '100%', minWidth: 0, overflow: 'hidden', boxSizing: 'border-box' }}>
          <div
            ref={mapContainer}
            className="dashboard-map-area"
            style={{ width: '100%', height: '100%', minWidth: 0, overflow: 'hidden', boxSizing: 'border-box' }}
          />
          
          {/* Search Bar Overlay */}
          {!loading && (
          <div
            data-search-container
            style={{
              position: 'absolute',
              top: isMobile ? '8px' : '20px',
              ...(isMobile ? { left: '50%', transform: 'translateX(-50%)' } : { right: '20px', left: 'auto', transform: 'none' }),
              zIndex: SEARCH_BAR_OVERLAY_Z_INDEX,
              width: isMobile ? 'min(300px, 78vw)' : '320px',
              maxWidth: isMobile ? 'min(300px, 78vw)' : '320px'
            }}
          >
            <div style={{
              position: 'relative',
              ...mapOverlayGlassStyle,
              borderRadius: isMobile ? '8px' : '12px',
              overflow: 'visible'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: isMobile ? '8px 12px' : '12px 16px',
                gap: isMobile ? '8px' : '12px'
              }}>
                <svg
                  width={isMobile ? 18 : 20}
                  height={isMobile ? 18 : 20}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#546e7a"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ flexShrink: 0 }}
                >
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowSearchResults(!!e.target.value.trim());
                  }}
                  onFocus={() => {
                    if (searchResults.length > 0) {
                      setShowSearchResults(true);
                    }
                  }}
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    fontSize: isMobile ? '16px' : '0.95em',
                    color: '#2c3e50',
                    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
                  }}
                />
                <button
                  aria-label="Clear search"
                  onClick={() => {
                    setSearchQuery('');
                    setSearchResults([]);
                    setShowSearchResults(false);
                    setSelectedResultIndex(-1);
                  }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: searchQuery ? 'pointer' : 'default',
                    padding: isMobile ? '2px' : '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#546e7a',
                    transition: 'color 0.2s ease, opacity 0.2s ease',
                    opacity: searchQuery ? 1 : 0,
                    visibility: searchQuery ? 'visible' : 'hidden',
                    flexShrink: 0,
                    width: isMobile ? 22 : 26,
                    height: isMobile ? 22 : 26
                  }}
                  onMouseEnter={(e) => {
                    if (searchQuery) {
                      e.currentTarget.style.color = '#2c3e50';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (searchQuery) {
                      e.currentTarget.style.color = '#546e7a';
                    }
                  }}
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>

              {/* Search Results Dropdown */}
              {showSearchResults && searchResults.length > 0 && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '4px',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  ...mapOverlayGlassStyle,
                  borderRadius: '12px',
                  zIndex: 2
                }}>
                  {searchResults.map((result, index) => {
                    const props = result.properties || {};
                    const projectName = props['Project_Na'] || props['Project Name'] || 'Unnamed Project';
                    const city = (props['NAME'] || props['City']) ? formatCityName((props['NAME'] || props['City']).trim()) : '—';
                    const infrastructureType = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || '—';
                    const description = props['New_15_25_'] || props['New 15-25 Words Project Description'] || '';
                    const isSelected = index === selectedResultIndex;

                    return (
                      <div
                        key={result.id || index}
                        onClick={() => navigateToProject(result)}
                        style={{
                          padding: '12px 16px',
                          cursor: 'pointer',
                          borderBottom: index < searchResults.length - 1 ? '1px solid rgba(0, 0, 0, 0.05)' : 'none',
                          backgroundColor: isSelected ? 'rgba(52, 152, 219, 0.1)' : 'transparent',
                          transition: 'background-color 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected) {
                            e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.03)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) {
                            e.currentTarget.style.backgroundColor = 'transparent';
                          }
                        }}
                      >
                        <div style={{
                          fontSize: '0.95em',
                          fontWeight: 600,
                          color: '#2c3e50',
                          marginBottom: '4px'
                        }}>
                          {highlightText(projectName, searchQuery)}
                        </div>
                        <div style={{
                          fontSize: '0.85em',
                          color: '#546e7a',
                          display: 'flex',
                          gap: '12px',
                          flexWrap: 'wrap'
                        }}>
                          <span>{highlightText(city, searchQuery)}</span>
                          <span>•</span>
                          <span>{highlightText(infrastructureType, searchQuery)}</span>
                        </div>
                        {description && (
                          <div style={{
                            fontSize: '0.75em',
                            color: '#7f8c8d',
                            marginTop: '6px',
                            lineHeight: 1.4,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {highlightText(description, searchQuery)}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* No Results Message */}
              {showSearchResults && debouncedSearchQuery.trim() && searchResults.length === 0 && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '4px',
                  padding: '16px',
                  ...mapOverlayGlassStyle,
                  borderRadius: '12px',
                  zIndex: 2,
                  textAlign: 'center',
                  color: '#546e7a',
                  fontSize: '0.9em'
                }}>
                  No projects found matching "{debouncedSearchQuery}"
                </div>
              )}
            </div>
          </div>
          )}

          {map.current && (
            <MapboxPopup map={map.current} activeFeature={activeFeature} />
          )}

          {censusLayersReady && censusStats && (
            <>
              {isMobile ? (
                <>
                  {/* Mobile: Modelling Layer switches above Satellite */}
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '62px',
                      right: 'max(16px, env(safe-area-inset-right))',
                      zIndex: 1000,
                      minWidth: '260px',
                      maxWidth: 'min(92vw, 320px)',
                      maxHeight: 'min(72vh, 580px)',
                      overflowY: 'auto',
                      padding: '12px 14px',
                      borderRadius: '10px',
                      ...mapOverlayGlassStyle,
                    }}
                  >
                    <div style={{ fontSize: '0.9em', fontWeight: 600, color: '#1b3a4b', marginBottom: '10px' }}>
                      Modelling Layer
                    </div>
                    <div role="group" aria-label="Modelling layer">
                      {MODELLING_LAYER_OPTIONS.map(({ view, label, ariaLabel }) => {
                        const checked = isModellingLayerSwitchOn(view);
                        if (view === 'critical-infrastructure') {
                          return (
                            <React.Fragment key={view}>
                              <div
                                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '8px' }}
                              >
                                <span style={{ fontSize: '0.85em', fontWeight: 500, color: '#1b3a4b', flex: 1, minWidth: 0 }}>{label}</span>
                                <button
                                  type="button"
                                  role="switch"
                                  className="modelling-switch-track"
                                  aria-checked={checked}
                                  aria-label={ariaLabel}
                                  onClick={() => handleModellingLayerSwitch(view)}
                                >
                                  <span className="modelling-switch-thumb" aria-hidden />
                                </button>
                              </div>
                              <div
                                style={{
                                  marginTop: '2px',
                                  marginBottom: '4px',
                                  paddingTop: '10px',
                                  borderTop: '1px solid rgba(0,0,0,0.08)',
                                }}
                              >
                                <div style={{ fontSize: '0.7em', color: '#546e7a', marginBottom: '8px', lineHeight: 1.35 }}>
                                  Sublayers (max 2). Combined layers count as one. Visible when Critical Infrastructure is on.
                                </div>
                                <div role="group" aria-label="Critical infrastructure sublayers">
                                  {CRITICAL_INFRASTRUCTURE_SUBLAYER_UI_ITEMS.map((item) => {
                                    const subOn = criticalInfraSublayerKeys.includes(item.id);
                                    return (
                                      <div
                                        key={item.id}
                                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '8px' }}
                                      >
                                        <span style={{ fontSize: '0.78em', fontWeight: 500, color: '#1b3a4b', flex: 1, minWidth: 0, lineHeight: 1.25 }}>{item.label}</span>
                                        <button
                                          type="button"
                                          role="switch"
                                          className="modelling-switch-track"
                                          aria-checked={subOn}
                                          aria-label={`${item.label} sublayer`}
                                          onClick={() => handleCriticalInfraSublayerToggle(item.id)}
                                        >
                                          <span className="modelling-switch-thumb" aria-hidden />
                                        </button>
                                      </div>
                                    );
                                  })}
                                </div>
                                {loadingOverlayLayer && (
                                  <div style={{ fontSize: '0.78em', color: '#546e7a', marginTop: '6px' }}>Loading layer…</div>
                                )}
                              </div>
                            </React.Fragment>
                          );
                        }
                        return (
                          <div
                            key={view}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '8px' }}
                          >
                            <span style={{ fontSize: '0.85em', fontWeight: 500, color: '#1b3a4b', flex: 1, minWidth: 0 }}>{label}</span>
                            <button
                              type="button"
                              role="switch"
                              className="modelling-switch-track"
                              aria-checked={checked}
                              aria-label={ariaLabel}
                              onClick={() => handleModellingLayerSwitch(view)}
                            >
                              <span className="modelling-switch-thumb" aria-hidden />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                    {censusVisible && activeCensusView === 'critical-infrastructure' && enabledOverlayLayerIds.length > 0 && (
                      <>
                        <div style={{ borderTop: '1px solid rgba(0,0,0,0.08)', marginTop: '10px', paddingTop: '10px', fontSize: '0.88em', fontWeight: 600, color: '#1b3a4b', marginBottom: '6px' }}>Data markers</div>
                        <div style={{ maxHeight: '100px', overflowY: 'auto' }}>
                        {enabledOverlayLayerIds.map((layerId) => {
                          const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === layerId);
                          if (!config?.style?.paint) return null;
                          const paint = config.style.paint;
                          const isLine = config.style.type === 'line';
                          const color = paint['circle-color'] ?? paint['line-color'] ?? '#666';
                          return (
                            <div key={layerId} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '0.85em', color: '#1b3a4b' }}>
                              {isLine ? (
                                <div style={{ width: '16px', height: '3px', backgroundColor: color, borderRadius: 1 }} />
                              ) : (
                                <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: color, border: `1px solid ${paint['circle-stroke-color'] || color}` }} />
                              )}
                              <span>{config.label}</span>
                            </div>
                          );
                        })}
                        </div>
                      </>
                    )}
                  </div>
                  {/* Mobile: Legend always visible when layer is active (above Layers dropdown) */}
                  {censusVisible && activeCensusView === 'risk' && sortedRatings.length > 0 && (
                    <div style={{ position: 'absolute', right: 'max(16px, env(safe-area-inset-right))', bottom: MOBILE_CENSUS_OVERLAY_BOTTOM, zIndex: 1000, ...mapOverlayGlassStyle, padding: '12px 14px', borderRadius: '10px', minWidth: '180px' }}>
                      <div style={{ fontSize: '0.9em', fontWeight: 600, color: '#1b3a4b', marginBottom: '8px' }}>FEMA Risk Rating</div>
                      <div style={{ marginBottom: '4px' }}>
                        <div style={{ width: '100%', height: '14px', borderRadius: '4px', overflow: 'hidden', marginBottom: '4px' }}>
                          <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to right, #FFF9C4 0%, #FFF9C4 20%, #FFE082 25%, #FFE082 40%, #FFB74D 45%, #FFB74D 60%, #FF8A65 65%, #FF8A65 80%, #E64A19 85%, #E64A19 100%)' }}></div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#546e7a' }}><span>Very Low</span><span>Very High</span></div>
                      </div>
                    </div>
                  )}
                  {censusVisible && activeCensusView === 'pred3pe' && censusStats?.pred3PE && (
                    <div style={{ position: 'absolute', right: 'max(16px, env(safe-area-inset-right))', bottom: MOBILE_CENSUS_OVERLAY_BOTTOM, zIndex: 1000, ...mapOverlayGlassStyle, padding: '12px 14px', borderRadius: '10px', minWidth: '180px' }}>
                      <div style={{ fontSize: '0.9em', fontWeight: 600, color: '#1b3a4b', marginBottom: '8px' }}>Resilience Index (%)</div>
                      <div style={{ marginBottom: '4px' }}>
                        <div style={{ width: '100%', height: '14px', borderRadius: '4px', overflow: 'hidden', marginBottom: '4px' }}>
                          <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to right, #E8D4F5 0%, #E8D4F5 10%, #D4B3E8 20%, #C298DB 35%, #A866C7 50%, #7A3FA8 65%, #5A1D85 80%, #2D0045 90%, #2D0045 100%)' }}></div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#546e7a' }}>
                          <span>{censusStats.pred3PE.min?.toFixed(1) || '0'}%</span>
                          <span>{censusStats.pred3PE.max?.toFixed(1) || '0'}%</span>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div style={{
                  position: 'absolute',
                  bottom: '20px',
                  right: '20px',
                  zIndex: 1000,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  width: '320px',
                  maxHeight: 'calc(100vh - 100px)',
                }}>
                  <div style={{
                    ...mapOverlayGlassStyle,
                    padding: '16px',
                    borderRadius: '12px',
                    overflowY: 'auto',
                  }}>
                    <div style={{ fontSize: '1em', fontWeight: 600, color: '#1b3a4b', marginBottom: '10px' }}>
                      Modelling Layer
                    </div>
                    <div role="group" aria-label="Modelling layer">
                      {MODELLING_LAYER_OPTIONS.map(({ view, label, ariaLabel }) => {
                        const checked = isModellingLayerSwitchOn(view);
                        if (view === 'critical-infrastructure') {
                          return (
                            <React.Fragment key={view}>
                              <div
                                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}
                              >
                                <span style={{ fontSize: '0.95em', fontWeight: 500, color: '#2c3e50' }}>{label}</span>
                                <button
                                  type="button"
                                  role="switch"
                                  className="modelling-switch-track"
                                  aria-checked={checked}
                                  aria-label={ariaLabel}
                                  onClick={() => handleModellingLayerSwitch(view)}
                                >
                                  <span className="modelling-switch-thumb" aria-hidden />
                                </button>
                              </div>
                              <div
                                style={{
                                  marginTop: '4px',
                                  marginBottom: '4px',
                                  paddingTop: '12px',
                                  borderTop: '1px solid rgba(0,0,0,0.08)',
                                }}
                              >
                                <div style={{ fontSize: '0.75em', color: '#546e7a', marginBottom: '10px', lineHeight: 1.35 }}>
                                  Sublayers (max 2). Combined layers count as one. Visible when Critical Infrastructure is on.
                                </div>
                                <div role="group" aria-label="Critical infrastructure sublayers">
                                  {CRITICAL_INFRASTRUCTURE_SUBLAYER_UI_ITEMS.map((item) => {
                                    const subOn = criticalInfraSublayerKeys.includes(item.id);
                                    return (
                                      <div
                                        key={item.id}
                                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}
                                      >
                                        <span style={{ fontSize: '0.88em', fontWeight: 500, color: '#2c3e50', flex: 1, minWidth: 0, lineHeight: 1.3 }}>{item.label}</span>
                                        <button
                                          type="button"
                                          role="switch"
                                          className="modelling-switch-track"
                                          aria-checked={subOn}
                                          aria-label={`${item.label} sublayer`}
                                          onClick={() => handleCriticalInfraSublayerToggle(item.id)}
                                        >
                                          <span className="modelling-switch-thumb" aria-hidden />
                                        </button>
                                      </div>
                                    );
                                  })}
                                </div>
                                {loadingOverlayLayer && (
                                  <div style={{ fontSize: '0.82em', color: '#546e7a', marginTop: '6px' }}>Loading layer…</div>
                                )}
                              </div>
                            </React.Fragment>
                          );
                        }
                        return (
                          <div
                            key={view}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}
                          >
                            <span style={{ fontSize: '0.95em', fontWeight: 500, color: '#2c3e50' }}>{label}</span>
                            <button
                              type="button"
                              role="switch"
                              className="modelling-switch-track"
                              aria-checked={checked}
                              aria-label={ariaLabel}
                              onClick={() => handleModellingLayerSwitch(view)}
                            >
                              <span className="modelling-switch-thumb" aria-hidden />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

              {/* Legend: single fixed-size container so position/size stay constant */}
              <div style={{
                ...mapOverlayGlassStyle,
                padding: '16px',
                borderRadius: '12px',
                width: '320px',
                minHeight: '120px',
                height: '120px',
                boxSizing: 'border-box',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}>
                {!(censusVisible && activeCensusView === 'risk' && sortedRatings.length > 0) &&
                 !(censusVisible && activeCensusView === 'pred3pe' && censusStats?.pred3PE) &&
                 !(censusVisible && activeCensusView === 'critical-infrastructure' && enabledOverlayLayerIds.length > 0) && (
                  <div style={{ fontSize: '1em', fontWeight: 600, color: '#1b3a4b' }}>
                    Select a layer
                  </div>
                )}
                {censusVisible && activeCensusView === 'risk' && sortedRatings.length > 0 && (
                  <>
                    <div style={{ fontSize: '1em', fontWeight: 600, color: '#1b3a4b', marginBottom: '12px' }}>
                      FEMA Risk Rating
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{
                        width: '100%',
                        height: '20px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        marginBottom: '8px'
                      }}>
                        <div style={{
                          width: '100%',
                          height: '100%',
                          background: 'linear-gradient(to right, #FFF9C4 0%, #FFF9C4 20%, #FFE082 25%, #FFE082 40%, #FFB74D 45%, #FFB74D 60%, #FF8A65 65%, #FF8A65 80%, #E64A19 85%, #E64A19 100%)'
                        }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75em', color: '#546e7a' }}>
                        <span>Very Low</span>
                        <span>Very High</span>
                      </div>
                    </div>
                  </>
                )}
                {censusVisible && activeCensusView === 'pred3pe' && censusStats?.pred3PE && (
                  <>
                    <div style={{ fontSize: '1em', fontWeight: 600, color: '#1b3a4b', marginBottom: '12px' }}>
                      Resilience Index (%)
                    </div>
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{
                        width: '100%',
                        height: '20px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        marginBottom: '8px'
                      }}>
                        <div style={{
                          width: '100%',
                          height: '100%',
                          background: 'linear-gradient(to right, #E8D4F5 0%, #E8D4F5 10%, #D4B3E8 20%, #C298DB 35%, #A866C7 50%, #7A3FA8 65%, #5A1D85 80%, #2D0045 90%, #2D0045 100%)'
                        }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75em', color: '#546e7a' }}>
                        <span>{censusStats.pred3PE.min?.toFixed(1) || '0'}%</span>
                        <span>{censusStats.pred3PE.max?.toFixed(1) || '0'}%</span>
                      </div>
                    </div>
                  </>
                )}
                {censusVisible && activeCensusView === 'critical-infrastructure' && enabledOverlayLayerIds.length > 0 && (
                  <>
                    <div style={{ fontSize: '1em', fontWeight: 600, color: '#1b3a4b', marginBottom: '12px', flexShrink: 0 }}>
                      Data markers
                    </div>
                    <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
                      {enabledOverlayLayerIds.map((layerId) => {
                        const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === layerId);
                        if (!config?.style?.paint) return null;
                        const paint = config.style.paint;
                        const isLine = config.style.type === 'line';
                        const color = paint['circle-color'] ?? paint['line-color'] ?? '#666';
                        return (
                          <div key={layerId} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', fontSize: '0.9em', color: '#1b3a4b' }}>
                            {isLine ? (
                              <div style={{ width: '20px', height: '4px', backgroundColor: color, borderRadius: 2 }} />
                            ) : (
                              <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: color, border: `1px solid ${paint['circle-stroke-color'] || color}` }} />
                            )}
                            <span>{config.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>

                  {/* Satellite toggle inside desktop flex column */}
                  <div style={{
                    ...mapOverlayGlassStyle,
                    borderRadius: '25px',
                    overflow: 'hidden'
                  }}>
                    <button
                      onClick={toggleMapStyle}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 12px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.8em', color: '#2c3e50', transition: 'all 0.3s', width: '100%' }}
                    >
                      <div style={{ marginRight: '8px', fontSize: '16px', display: 'flex', alignItems: 'center' }}>
                        {isSatelliteView ? '\uD83D\uDDFA\uFE0F' : '\uD83D\uDEF0\uFE0F'}
                      </div>
                      <span style={{ fontWeight: '500' }}>{isSatelliteView ? 'Standard' : 'Satellite'}</span>
                    </button>
                  </div>

                </div>
              )}
            </>
          )}

          {loading && (
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(20px) saturate(180%)', WebkitBackdropFilter: 'blur(20px) saturate(180%)', padding: '20px', borderRadius: '16px', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.6)', border: '1px solid rgba(255, 255, 255, 0.3)', zIndex: 1000 }}>
              <div style={{ width: '40px', height: '40px', border: '4px solid #f3f3f3', borderTop: '4px solid #3498db', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 10px' }}></div>
              <div>{error || 'Loading map and projects...'}</div>
            </div>
          )}

          {/* Mobile Map Style Toggle */}
          {isMobile && (
          <div style={{
            position: 'absolute',
            bottom: 'max(16px, env(safe-area-inset-bottom))',
            right: 'max(16px, env(safe-area-inset-right))',
            ...mapOverlayGlassStyle,
            borderRadius: '20px',
            zIndex: 1000,
            overflow: 'hidden'
          }}>
            <button
              onClick={toggleMapStyle}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 12px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.8em', color: '#2c3e50', transition: 'all 0.3s', minWidth: '120px' }}
            >
              <div style={{ marginRight: '8px', fontSize: '16px', display: 'flex', alignItems: 'center' }}>
                {isSatelliteView ? '🗺️' : '🛰️'}
              </div>
              <span style={{ fontWeight: '500' }}>{isSatelliteView ? 'Standard' : 'Satellite'}</span>
            </button>
          </div>
          )}

      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .modelling-switch-track {
          width: 40px;
          height: 22px;
          border-radius: 11px;
          border: 1px solid rgba(0, 0, 0, 0.2);
          cursor: pointer;
          padding: 0;
          flex-shrink: 0;
          position: relative;
          background: rgba(200, 200, 200, 0.88);
          box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.07);
          transition:
            background 1s cubic-bezier(0.4, 0, 0.2, 1),
            box-shadow 1s cubic-bezier(0.4, 0, 0.2, 1),
            border-color 0.85s ease;
        }
        .modelling-switch-track[aria-checked="true"] {
          background: #3498db;
          border-color: rgba(41, 128, 185, 0.55);
          box-shadow:
            0 2px 16px rgba(52, 152, 219, 0.42),
            0 0 0 1px rgba(52, 152, 219, 0.2);
        }
        .modelling-switch-thumb {
          position: absolute;
          top: 2px;
          left: 2px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.22);
          pointer-events: none;
          transition:
            left 1s cubic-bezier(0.33, 1, 0.32, 1),
            transform 1s cubic-bezier(0.33, 1, 0.32, 1),
            box-shadow 1s ease;
        }
        .modelling-switch-track[aria-checked="true"] .modelling-switch-thumb {
          left: 20px;
          transform: scale(1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .modelling-switch-track:not([aria-checked="true"]) .modelling-switch-thumb {
          transform: scale(0.92);
        }
        .modelling-switch-track:focus-visible {
          outline: 2px solid #3498db;
          outline-offset: 2px;
        }
        @media (prefers-reduced-motion: reduce) {
          .modelling-switch-track,
          .modelling-switch-thumb {
            transition-duration: 0.01ms !important;
          }
        }
        .mapboxgl-popup-content {
          background: rgba(255, 255, 255, 0.85) !important;
          backdrop-filter: blur(20px) saturate(180%) !important;
          -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
          border-radius: 16px !important;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.6) !important;
          padding-right: 30px;
        }
        .mapboxgl-popup {
          z-index: 10000 !important;
        }
        .mapboxgl-popup-close-button {
          position: absolute;
          top: 6px;
          right: 6px;
          transform: none;
          background: rgba(255, 255, 255, 0.8) !important;
          backdrop-filter: blur(10px) saturate(180%) !important;
          -webkit-backdrop-filter: blur(10px) saturate(180%) !important;
          border-radius: 6px;
          width: 22px;
          height: 22px;
          line-height: 20px;
          text-align: center;
          border: 1px solid rgba(255, 255, 255, 0.4);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1), inset 0 0 0 1px rgba(255, 255, 255, 0.5);
        }
      ` }} />
    </div>
  );
};

export default Dashboard;

// React-based Mapbox Popup using a portal to render rich content
const MapboxPopup = ({ map, activeFeature }) => {
  const popupRef = useRef(null);
  const contentRef = useRef(typeof document !== 'undefined' ? document.createElement('div') : null);

  // Create popup instance on mount
  useEffect(() => {
    if (!map) return;
    popupRef.current = new mapboxgl.Popup({ closeOnClick: false, offset: 20 });
    
    // Add event listener for popup close event
    const handlePopupClose = () => {
      // Dispatch custom event to notify App component that popup was closed
      window.dispatchEvent(new CustomEvent('popupClosed'));
    };
    
    popupRef.current.on('close', handlePopupClose);
    
    return () => {
      if (popupRef.current) {
        popupRef.current.off('close', handlePopupClose);
        popupRef.current.remove();
      }
    };
  }, [map]);

  // Update popup when activeFeature changes
  useEffect(() => {
    if (!map || !popupRef.current) return;
    if (!activeFeature) {
      popupRef.current.remove();
      return;
    }

    const coords = activeFeature.geometry?.coordinates;
    if (!coords) return;

    // Remove existing popup first to prevent close event from interfering
    // This ensures a clean transition between popups
    popupRef.current.remove();

    // Use requestAnimationFrame to ensure DOM is ready and popup is fully removed
    requestAnimationFrame(() => {
      if (!map || !popupRef.current || !activeFeature) return;
      
      const coords = activeFeature.geometry?.coordinates;
      if (!coords) return;

      popupRef.current
        .setLngLat(coords)
        .setHTML(contentRef.current.outerHTML)
        .addTo(map);
    });
  }, [map, activeFeature]);

  if (!contentRef.current) return null;

  const props = activeFeature?.properties || {};

  return (
    <>{createPortal(
      <div className="portal-content" style={{ maxWidth: 360 }}>
        <div style={{ fontSize: '1.05em', fontWeight: 700, color: '#2c3e50', marginBottom: 10 }}>
          {props['Project_Na'] || props['Project Name'] || 'Project'}
        </div>
        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px', fontSize: '0.9em' }}>
          <tbody>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600, width: 110 }}>Infrastructure Type</td>
              <td style={{ color: '#2c3e50' }}>{props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || '—'}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Category</td>
              <td style={{ color: '#2c3e50' }}>{props['Categories'] || '—'}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Focus</td>
              <td style={{ color: '#2c3e50' }}>{props['Disaster_F'] || props['Disaster Focus'] || '—'}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>City</td>
              <td style={{ color: '#2c3e50' }}>{(props['NAME'] || props['City']) ? formatCityName((props['NAME'] || props['City']).trim()) : '—'}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Status</td>
              <td style={{ color: (props['Project__1'] || props['Project Status'] || '').toLowerCase() === 'completed' ? '#27ae60' : '#f39c12', fontWeight: 700 }}>
                {props['Project__1'] || props['Project Status'] || 'Unknown'}
              </td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Cost</td>
              <td style={{ color: ((props['Estimated_'] || props['Estimated Project Cost']) == null) ?'#f39c12' : '#27ae60', fontWeight: 700 }}>{
                  formatCostCompact(props['Estimated_'] || props['Estimated Project Cost']) || 'Not Disclosed'}</td>
            </tr>
          </tbody>
        </table>
        {(props['New_15_25_'] || props['New 15-25 Words Project Description']) && (
          <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid #ecf0f1', color: '#7f8c8d', fontSize: '0.85em', lineHeight: 1.4 }}>
            {props['New_15_25_'] || props['New 15-25 Words Project Description']}
          </div>
        )}
      </div>,
      contentRef.current
    )}</>
  );
};