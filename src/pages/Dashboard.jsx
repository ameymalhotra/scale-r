import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import mapboxgl from 'mapbox-gl';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { searchProjects } from '../utils/searchProjects.js';
import { highlightText } from '../utils/highlightText.jsx';
import { reprojectFeatureCollectionIfNeeded } from '../utils/geoProcessing.js';
import DataParserWorker from '../workers/dataParser.worker.js?worker';

const DASHBOARD_CITY_LISTBOX_ID = 'dashboard-city-listbox';
const DASHBOARD_CITY_TRIGGER_ID = 'dashboard-city-trigger';
const DASHBOARD_SEARCH_LISTBOX_ID = 'dashboard-search-listbox';
const DASHBOARD_SEARCH_INPUT_ID = 'dashboard-project-search';
const DASHBOARD_SEARCH_LIVE_ID = 'dashboard-search-live';

/**
 * Promise wrapper around one round-trip to the data-parsing worker.
 * Each task carries an id so several can be in flight at once.
 */
let workerTaskId = 0;
const runWorkerTask = (worker, task, payload) =>
  new Promise((resolve, reject) => {
    const id = ++workerTaskId;
    const onMessage = (event) => {
      if (event.data?.id !== id) return;
      worker.removeEventListener('message', onMessage);
      if (event.data.ok) resolve(event.data.result);
      else reject(new Error(event.data.error));
    };
    worker.addEventListener('message', onMessage);
    worker.postMessage({ id, task, payload });
  });

// Canonical project status values from the dataset `Project__1` column.
// Filter UI order (2×2): Completed | Ongoing / Funded | Planned
const PROJECT_STATUS_OPTIONS = ['Completed', 'Ongoing', 'Funded', 'Planned'];

const PROJECT_STATUS_COLORS = {
  Completed: '#27ae60',
  Ongoing: '#b45309',
  Funded: '#0f766e',
  Planned: '#2563eb',
};

const getProjectStatus = (props = {}) => {
  const raw = String(props['Project__1'] ?? props['Project Status'] ?? '').trim();
  if (PROJECT_STATUS_OPTIONS.includes(raw)) return raw;
  // Case-insensitive match for slightly inconsistent source values.
  const lower = raw.toLowerCase();
  const matched = PROJECT_STATUS_OPTIONS.find((s) => s.toLowerCase() === lower);
  return matched ?? (raw || 'Ongoing');
};

// Rewrite Point geometry to use lon/lat from feature properties (e.g. for EPSG:3087 layers that store X,Y in props)
const applyLonLatFromProperties = (featureCollection, lonField, latField) => {
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

/** Miami-Dade urban core — where most inventory projects cluster. */
const MIAMI_DADE_DEFAULT_CENTER = [-80.25, 25.78];
const MIAMI_DADE_DEFAULT_ZOOM = 10;
const MIAMI_DADE_COUNTY_BOUNDS = {
  west: -80.9,
  south: 25.2,
  east: -80.1,
  north: 25.98,
};

const OVERVIEW_FIT_PADDING = { top: 10, bottom: 300, left: 200, right: 10 };

const percentileValue = (sorted, p) => {
  if (!sorted.length) return null;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * p)));
  return sorted[idx];
};

/**
 * Bounds covering where most projects sit (percentile cluster inside Miami-Dade).
 * Ignores sparse western/southern tails so the opening view stays on the urban corridor.
 */
const getMostProjectsBounds = (lngLats) => {
  if (!lngLats?.length) return null;

  const inCounty = lngLats.filter(
    ({ lng, lat }) =>
      lng >= MIAMI_DADE_COUNTY_BOUNDS.west &&
      lng <= MIAMI_DADE_COUNTY_BOUNDS.east &&
      lat >= MIAMI_DADE_COUNTY_BOUNDS.south &&
      lat <= MIAMI_DADE_COUNTY_BOUNDS.north
  );
  const pts = inCounty.length >= 10 ? inCounty : lngLats;
  const lngs = pts.map((p) => p.lng).sort((a, b) => a - b);
  const lats = pts.map((p) => p.lat).sort((a, b) => a - b);

  // ~10th–90th percentile: most markers, without Everglades / far-south outliers.
  const west = percentileValue(lngs, 0.1);
  const east = percentileValue(lngs, 0.9);
  const south = percentileValue(lats, 0.1);
  const north = percentileValue(lats, 0.9);
  if ([west, east, south, north].some((v) => v == null)) return null;

  const bounds = new mapboxgl.LngLatBounds([west, south], [east, north]);
  // Guard against a degenerate box when nearly all points coincide.
  if (east - west < 0.05) {
    bounds.extend([west - 0.08, south]);
    bounds.extend([east + 0.08, north]);
  }
  if (north - south < 0.05) {
    bounds.extend([west, south - 0.06]);
    bounds.extend([east, north + 0.06]);
  }
  return bounds;
};

const fitMapToMostProjects = (mapInstance, markers, { duration = 0, maxZoom = 11 } = {}) => {
  if (!mapInstance || !markers?.length) return false;
  const lngLats = markers.map((marker) => {
    const { lng, lat } = marker.getLngLat();
    return { lng, lat };
  });
  const bounds = getMostProjectsBounds(lngLats);
  if (!bounds || bounds.isEmpty()) return false;
  mapInstance.fitBounds(bounds, {
    padding: OVERVIEW_FIT_PADDING,
    maxZoom,
    duration,
  });
  return true;
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

/** Display label for infrastructure type: "Blue Infrastructure" → "Blue". */
const formatInfrastructureType = (type) => {
  if (!type || typeof type !== 'string') return type;
  const short = type.replace(/\s+infrastructure$/i, '').trim() || type;
  // American English: normalize British "Grey" → "Gray"
  if (/^grey$/i.test(short)) return 'Gray';
  return short;
};

/** Preferred Infrastructure Type filter order (2×2 grid). */
const INFRASTRUCTURE_TYPE_ORDER = ['Blue', 'Green', 'Gray', 'Hybrid'];

/**
 * Definitions for Infrastructure Type filter info icons (shown on click).
 */
const INFRASTRUCTURE_TYPE_DEFINITIONS = {
  Blue:
    'Blue infrastructure encompasses natural and engineered water-based systems that mitigate flooding, support adaptation to sea-level rise, improve water quality, and sustain diverse aquatic ecosystems.',
  Green:
    'Green infrastructure integrates vegetation, soils, and ecological processes to mitigate urban heat, manage stormwater, improve air and water quality, and support biodiversity.',
  Gray:
    'Gray infrastructure comprises conventional engineered systems constructed with materials such as concrete and steel to deliver essential urban services, including stormwater conveyance, flood control, and transportation.',
  Hybrid:
    'Hybrid infrastructure integrates elements of blue, green, and gray systems to deliver adaptive, multi-functional solutions.',
};

const getInfrastructureTypeDefinition = (type) => {
  const label = formatInfrastructureType(type);
  if (!label) return '';
  const normalized = String(label).trim();
  const key = Object.keys(INFRASTRUCTURE_TYPE_DEFINITIONS).find(
    (k) => k.toLowerCase() === normalized.toLowerCase()
  );
  if (key) return INFRASTRUCTURE_TYPE_DEFINITIONS[key];
  // Legacy British spelling still present in some source data
  if (/^grey$/i.test(normalized)) return INFRASTRUCTURE_TYPE_DEFINITIONS.Gray;
  return '';
};

/** Info icon with a fixed-position tooltip that stays inside the viewport (click to toggle). */
function InfrastructureTypeInfoIcon({ label, definition }) {
  const btnRef = useRef(null);
  const tipRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, placement: 'below' });

  const updatePosition = useCallback(() => {
    const btn = btnRef.current;
    const tip = tipRef.current;
    if (!btn || !tip) return;

    const margin = 8;
    const gap = 8;
    const rect = btn.getBoundingClientRect();
    const tipWidth = tip.offsetWidth;
    const tipHeight = tip.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const spaceBelow = vh - rect.bottom - margin;
    const spaceAbove = rect.top - margin;
    const preferBelow = spaceBelow >= tipHeight + gap || spaceBelow >= spaceAbove;
    const placement = preferBelow ? 'below' : 'above';
    let top = preferBelow
      ? rect.bottom + gap
      : rect.top - tipHeight - gap;

    if (top < margin) top = margin;
    if (top + tipHeight > vh - margin) top = Math.max(margin, vh - margin - tipHeight);

    // Prefer centering on the icon; clamp horizontally so the box stays on-screen.
    let left = rect.left + rect.width / 2 - tipWidth / 2;
    if (left + tipWidth > vw - margin) left = vw - margin - tipWidth;
    if (left < margin) left = margin;

    setCoords({ top, left, placement });
  }, []);

  useLayoutEffect(() => {
    if (!open) return undefined;
    updatePosition();
    const onReposition = () => updatePosition();
    window.addEventListener('resize', onReposition);
    window.addEventListener('scroll', onReposition, true);
    return () => {
      window.removeEventListener('resize', onReposition);
      window.removeEventListener('scroll', onReposition, true);
    };
  }, [open, definition, updatePosition]);

  useEffect(() => {
    if (!open) return undefined;

    const onPointerDown = (event) => {
      const target = event.target;
      if (btnRef.current?.contains(target) || tipRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <span className="infra-type-info">
      <button
        ref={btnRef}
        type="button"
        className="infra-type-info__btn"
        aria-label={`About ${label} infrastructure`}
        aria-expanded={open}
        aria-controls={definition ? `infra-type-tip-${label}` : undefined}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!definition) return;
          setOpen((prev) => !prev);
        }}
      >
        <svg
          className="infra-type-info__icon"
          viewBox="0 0 16 16"
          width="14"
          height="14"
          aria-hidden="true"
          focusable="false"
        >
          <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="8" cy="4.75" r="0.9" fill="currentColor" />
          <path
            d="M8 7.1v4.2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>
      {open && definition
        ? createPortal(
            <span
              ref={tipRef}
              id={`infra-type-tip-${label}`}
              className={`infra-type-info__tooltip infra-type-info__tooltip--portal infra-type-info__tooltip--${coords.placement}`}
              role="tooltip"
              style={{ top: coords.top, left: coords.left }}
            >
              {definition}
            </span>,
            document.body
          )
        : null}
    </span>
  );
}

const infrastructureTypeSortKey = (type) => {
  const label = formatInfrastructureType(type);
  const idx = INFRASTRUCTURE_TYPE_ORDER.findIndex(
    (o) => o.toLowerCase() === String(label || '').toLowerCase()
  );
  return idx === -1 ? INFRASTRUCTURE_TYPE_ORDER.length : idx;
};

/**
 * Case-insensitive key for disaster focus. Folds pre-Stage4 category names onto
 * the current taxonomy so archived exports filter alongside the hosted dataset.
 */
const DISASTER_FOCUS_ALIASES = {
  'storm surge': 'storms & hurricanes',
  storms: 'storms & hurricanes',
  'critical infrastructure': 'infrastructure failure',
  'multi-hazard': 'multi-hazard',
};

const disasterFocusKey = (focus) => {
  if (typeof focus !== 'string') return '';
  const key = focus.trim().toLowerCase();
  return DISASTER_FOCUS_ALIASES[key] ?? key;
};

/** Canonical display label for a disaster focus key. */
const DISASTER_FOCUS_LABELS = {
  flooding: 'Flooding',
  'storms & hurricanes': 'Storms & Hurricanes',
  'coastal hazards': 'Coastal Hazards',
  'extreme heat': 'Extreme Heat',
  'multi-hazard': 'Multi-Hazard',
  'infrastructure failure': 'Infrastructure Failure',
};

const formatDisasterFocus = (focus) => {
  if (!focus || typeof focus !== 'string') return focus;
  const trimmed = focus.trim();
  return DISASTER_FOCUS_LABELS[disasterFocusKey(trimmed)] ?? trimmed;
};

/** Preferred Disaster Focus filter order; hazard types first, compound/systems last. */
const DISASTER_FOCUS_ORDER = [
  'Flooding',
  'Storms & Hurricanes',
  'Coastal Hazards',
  'Extreme Heat',
  'Multi-Hazard',
  'Infrastructure Failure',
];

const disasterFocusSortKey = (focus) => {
  const label = formatDisasterFocus(focus);
  const idx = DISASTER_FOCUS_ORDER.findIndex(
    (o) => disasterFocusKey(o) === disasterFocusKey(label)
  );
  return idx === -1 ? DISASTER_FOCUS_ORDER.length : idx;
};

const disasterFocusMatches = (selectedFocuses, focus) => {
  if (!selectedFocuses.length) return true;
  const key = disasterFocusKey(focus);
  return selectedFocuses.some((selected) => disasterFocusKey(selected) === key);
};

const SUPABASE_STORAGE = 'https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data';
const PROJECTS_GEOJSON_FILE = 'projects_merged_conf1.geojson';

/** Raster size for overlay glyphs; paired with pixelRatio 2 in addImage for crisp symbols. */
const OVERLAY_SYMBOL_ICON_PX = 128;

/** Mapbox image ids for point overlay symbol layers (registered before layer add; re-registered after setStyle). */
const OVERLAY_SYMBOL_IMAGES = {
  medicalCross: 'cr-overlay-medical-cross',
  eocCross: 'cr-overlay-eoc-cross',
  community: 'cr-overlay-community',
  disasterRecovery: 'cr-overlay-disaster-recovery',
  riskShelter: 'cr-overlay-risk-shelter',
};

const CRITICAL_INFRA_NEUTRAL = {
  black: '#111111',
  white: '#ffffff',
  darkGray: '#2f2f2f',
  midGray: '#6f6f6f',
  lightGray: '#d9d9d9',
  borderGray: '#4a4a4a',
};

function createImageDataFromCanvas(draw) {
  const s = OVERLAY_SYMBOL_ICON_PX;
  const canvas = document.createElement('canvas');
  canvas.width = s;
  canvas.height = s;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  draw(ctx, s);
  return ctx.getImageData(0, 0, s, s);
}

/** Circular cross icon used by emergency layers; palette can be swapped per layer. */
function imageDataMedicalCross(fillHex, crossHex = '#ffffff', strokeHex = 'rgba(255, 255, 255, 0.42)') {
  return createImageDataFromCanvas((ctx, s) => {
    const cx = s / 2;
    const cy = s / 2;
    const r = s * 0.42;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = fillHex;
    ctx.fill();
    ctx.strokeStyle = strokeHex;
    ctx.lineWidth = Math.max(1, s * 0.02);
    ctx.stroke();
    const arm = s * 0.3;
    const thick = s * 0.11;
    ctx.fillStyle = crossHex;
    ctx.fillRect(cx - thick / 2, cy - arm / 2, thick, arm);
    ctx.fillRect(cx - arm / 2, cy - thick / 2, arm, thick);
  });
}

/** Neutral disk + people glyph for community-serving sites. */
function imageDataCommunityCenter() {
  return createImageDataFromCanvas((ctx, s) => {
    const cx = s / 2;
    const cy = s / 2;
    const r = s * 0.42;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.black;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.32)';
    ctx.lineWidth = Math.max(1, s * 0.018);
    ctx.stroke();
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.white;
    const headR = s * 0.08;
    const shoulderW = s * 0.2;
    const shoulderH = s * 0.09;
    ctx.beginPath();
    ctx.arc(cx - s * 0.11, cy - s * 0.1, headR, 0, Math.PI * 2);
    ctx.arc(cx + s * 0.11, cy - s * 0.1, headR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillRect(cx - s * 0.25, cy + s * 0.01, shoulderW, shoulderH);
    ctx.fillRect(cx + s * 0.05, cy + s * 0.01, shoulderW, shoulderH);
    ctx.strokeStyle = '#ffffff';
    ctx.lineCap = 'round';
    ctx.lineWidth = s * 0.06;
    ctx.beginPath();
    ctx.moveTo(cx - s * 0.26, cy + s * 0.2);
    ctx.lineTo(cx + s * 0.26, cy + s * 0.2);
    ctx.stroke();
  });
}

/** Neutral disk + shield + check (recovery / assistance). */
function imageDataDisasterRecovery() {
  return createImageDataFromCanvas((ctx, s) => {
    const cx = s / 2;
    const cy = s / 2;
    const r = s * 0.42;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.darkGray;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.28)';
    ctx.lineWidth = Math.max(1, s * 0.018);
    ctx.stroke();
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.white;
    ctx.beginPath();
    ctx.moveTo(cx, cy - s * 0.26);
    ctx.lineTo(cx + s * 0.22, cy - s * 0.08);
    ctx.lineTo(cx + s * 0.18, cy + s * 0.28);
    ctx.lineTo(cx - s * 0.18, cy + s * 0.28);
    ctx.lineTo(cx - s * 0.22, cy - s * 0.08);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = CRITICAL_INFRA_NEUTRAL.black;
    ctx.lineWidth = s * 0.05;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.moveTo(cx - s * 0.12, cy + s * 0.02);
    ctx.lineTo(cx - s * 0.02, cy + s * 0.14);
    ctx.lineTo(cx + s * 0.16, cy - s * 0.1);
    ctx.stroke();
  });
}

/** Neutral disk + home glyph for risk and recovery centers. */
function imageDataRiskShelter() {
  return createImageDataFromCanvas((ctx, s) => {
    const cx = s / 2;
    const cy = s / 2;
    const houseYOffset = -s * 0.05;
    const r = s * 0.42;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.darkGray;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.28)';
    ctx.lineWidth = Math.max(1, s * 0.018);
    ctx.stroke();
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.white;
    const hw = s * 0.26;
    const hh = s * 0.2;
    const baseY = cy + s * 0.02 + houseYOffset;
    ctx.fillRect(cx - hw / 2, baseY, hw, hh);
    ctx.beginPath();
    ctx.moveTo(cx, cy - s * 0.12 + houseYOffset);
    ctx.lineTo(cx - hw / 2 - s * 0.02, baseY);
    ctx.lineTo(cx + hw / 2 + s * 0.02, baseY);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = CRITICAL_INFRA_NEUTRAL.black;
    ctx.fillRect(cx - s * 0.035, cy + s * 0.09 + houseYOffset, s * 0.07, s * 0.1);
  });
}

let communityLegendIconDataUrl = '';
let medicalLegendIconDataUrl = '';
let riskLegendIconDataUrl = '';
function getMedicalLegendIconDataUrl() {
  if (medicalLegendIconDataUrl) return medicalLegendIconDataUrl;
  if (typeof document === 'undefined') return '';
  const s = OVERLAY_SYMBOL_ICON_PX;
  const canvas = document.createElement('canvas');
  canvas.width = s;
  canvas.height = s;
  const ctx = canvas.getContext('2d');
  const imageData = imageDataMedicalCross(
    CRITICAL_INFRA_NEUTRAL.black,
    CRITICAL_INFRA_NEUTRAL.white,
    'rgba(255, 255, 255, 0.32)',
  );
  if (!ctx || !imageData) return '';
  ctx.putImageData(imageData, 0, 0);
  medicalLegendIconDataUrl = canvas.toDataURL('image/png');
  return medicalLegendIconDataUrl;
}
function getCommunityLegendIconDataUrl() {
  if (communityLegendIconDataUrl) return communityLegendIconDataUrl;
  if (typeof document === 'undefined') return '';
  const s = OVERLAY_SYMBOL_ICON_PX;
  const canvas = document.createElement('canvas');
  canvas.width = s;
  canvas.height = s;
  const ctx = canvas.getContext('2d');
  const imageData = imageDataCommunityCenter();
  if (!ctx || !imageData) return '';
  ctx.putImageData(imageData, 0, 0);
  communityLegendIconDataUrl = canvas.toDataURL('image/png');
  return communityLegendIconDataUrl;
}
function getRiskLegendIconDataUrl() {
  if (riskLegendIconDataUrl) return riskLegendIconDataUrl;
  if (typeof document === 'undefined') return '';
  const s = OVERLAY_SYMBOL_ICON_PX;
  const canvas = document.createElement('canvas');
  canvas.width = s;
  canvas.height = s;
  const ctx = canvas.getContext('2d');
  const imageData = imageDataRiskShelter();
  if (!ctx || !imageData) return '';
  ctx.putImageData(imageData, 0, 0);
  riskLegendIconDataUrl = canvas.toDataURL('image/png');
  return riskLegendIconDataUrl;
}

function registerOverlaySymbolImages(mapInstance) {
  if (!mapInstance) return;
  const reg = (id, imageData) => {
    if (!imageData || mapInstance.hasImage(id)) return;
    try {
      mapInstance.addImage(id, imageData, { pixelRatio: 2 });
    } catch (e) {
      console.warn('[Overlay] addImage failed', id, e);
    }
  };
  reg(
    OVERLAY_SYMBOL_IMAGES.medicalCross,
    imageDataMedicalCross(
      CRITICAL_INFRA_NEUTRAL.black,
      CRITICAL_INFRA_NEUTRAL.white,
      'rgba(255, 255, 255, 0.32)',
    ),
  );
  reg(
    OVERLAY_SYMBOL_IMAGES.eocCross,
    imageDataMedicalCross(
      CRITICAL_INFRA_NEUTRAL.white,
      CRITICAL_INFRA_NEUTRAL.black,
      'rgba(17, 17, 17, 0.24)',
    ),
  );
  reg(OVERLAY_SYMBOL_IMAGES.community, imageDataCommunityCenter());
  reg(OVERLAY_SYMBOL_IMAGES.disasterRecovery, imageDataDisasterRecovery());
  reg(OVERLAY_SYMBOL_IMAGES.riskShelter, imageDataRiskShelter());
}

const OVERLAY_LAYERS_CONFIG = [
  { id: 'overlay-community-centers', label: 'Community Centers', url: `${SUPABASE_STORAGE}/Community%20Cent_FeaturesToJSO.geojson`, style: { type: 'symbol', iconImage: OVERLAY_SYMBOL_IMAGES.community, iconSize: 0.42 }, popupTitleField: 'Name', popupFields: ['Address', 'City'] },
  { id: 'overlay-disaster-recovery', label: 'Disaster Recovery Centers', url: `${SUPABASE_STORAGE}/Disaster%20Recov_FeaturesToJSO.geojson`, style: { type: 'symbol', iconImage: OVERLAY_SYMBOL_IMAGES.riskShelter, iconSize: 0.42 }, popupTitleField: 'Name', popupFields: ['Address', 'City'] },
  { id: 'overlay-emergency-medical', label: 'Emergency Medical', url: `${SUPABASE_STORAGE}/EmergencyMedical_FeaturesToJSO.geojson`, style: { type: 'symbol', iconImage: OVERLAY_SYMBOL_IMAGES.medicalCross, iconSize: 0.42 }, popupTitleField: 'Name', popupFields: ['Address', 'City'], pointLonLatFields: ['X', 'Y'] },
  { id: 'overlay-emergency-ops', label: 'Emergency Operations Centers', url: `${SUPABASE_STORAGE}/Emergency%20Oper_FeaturesToJSO.geojson`, style: { type: 'symbol', iconImage: OVERLAY_SYMBOL_IMAGES.eocCross, iconSize: 0.42 } },
  { id: 'overlay-evacuation-routes', label: 'Evacuation Routes', url: `${SUPABASE_STORAGE}/Evacuation%20Rou_FeaturesToJSO.geojson`, style: { type: 'line', paint: { 'line-color': '#34495e', 'line-width': 3 } } },
  { id: 'overlay-military', label: 'Military Installations', url: `${SUPABASE_STORAGE}/MILITARY_FeaturesToJSO.geojson`, style: { type: 'fill', paint: { 'fill-color': CRITICAL_INFRA_NEUTRAL.lightGray, 'fill-opacity': 0.42, 'fill-outline-color': CRITICAL_INFRA_NEUTRAL.black, 'line-color': CRITICAL_INFRA_NEUTRAL.black } }, popupTitleField: 'NAME', popupFields: ['GEOID', 'FEMAIndexR'] },
  { id: 'overlay-risk-shelters', label: 'Risk Shelters', url: `${SUPABASE_STORAGE}/Risk%20Shelter%20I_FeaturesToJSO.geojson`, style: { type: 'symbol', iconImage: OVERLAY_SYMBOL_IMAGES.riskShelter, iconSize: 0.42 }, popupTitleField: 'Name', popupFields: ['Address', 'City'] },
];

/** Combined Critical Infrastructure sublayers: one UI toggle loads multiple GeoJSON sources. */
const OVERLAY_GROUP_CRITICAL_FACILITIES = {
  id: 'overlay-group-critical-facilities',
  label: 'Emergency & Medical Services',
  memberIds: ['overlay-emergency-medical', 'overlay-emergency-ops', 'overlay-military'],
};

const OVERLAY_GROUP_RISK_AND_RECOVERY = {
  id: 'overlay-group-risk-recovery',
  label: 'Risk and recovery centers',
  memberIds: ['overlay-risk-shelters', 'overlay-disaster-recovery'],
};

const CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS = [OVERLAY_GROUP_CRITICAL_FACILITIES, OVERLAY_GROUP_RISK_AND_RECOVERY];
const CRITICAL_INFRASTRUCTURE_DEFAULT_GROUP_KEYS = [
  ...CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.map((g) => g.id),
  'overlay-community-centers',
  'overlay-evacuation-routes',
];
const CRITICAL_INFRA_GROUP_LEGEND_REPRESENTATIVE_LAYER_ID = {
  [OVERLAY_GROUP_CRITICAL_FACILITIES.id]: 'overlay-emergency-medical',
  [OVERLAY_GROUP_RISK_AND_RECOVERY.id]: 'overlay-risk-shelters',
};

function expandCriticalInfraSublayerKeys(keys) {
  const out = [];
  keys.forEach((k) => {
    const group = CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.find((g) => g.id === k);
    if (group) out.push(...group.memberIds);
    else out.push(k);
  });
  return [...new Set(out)];
}

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

/** Gap (px) between search dropdown bottom and top of modelling layer stack */
const SEARCH_DROPDOWN_GAP_ABOVE_MODELLING = 12;
const SEARCH_DROPDOWN_MARGIN_TOP = 4;

const Dashboard = () => {
  const mapContainer = useRef(null);
  const searchInputRowRef = useRef(null);
  const desktopMapOverlaysRef = useRef(null);
  const mobileMapOverlaysRef = useRef(null);
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
  const [selectedDisasterFocus, setSelectedDisasterFocus] = useState([]);
  const [selectedProjectStatuses, setSelectedProjectStatuses] = useState([]);
  const [selectedCity, setSelectedCity] = useState('');
  const [cityDropdownOpen, setCityDropdownOpen] = useState(false);
  const [projectsLayerVisible, setProjectsLayerVisible] = useState(true);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedResultIndex, setSelectedResultIndex] = useState(-1);
  const [searchDropdownMaxHeightPx, setSearchDropdownMaxHeightPx] = useState(400);

  const enabledOverlayLayerIds = useMemo(
    () => (activeCensusView === 'critical-infrastructure' ? expandCriticalInfraSublayerKeys(CRITICAL_INFRASTRUCTURE_DEFAULT_GROUP_KEYS) : []),
    [activeCensusView]
  );
  const overlayDataCacheRef = useRef({});

  // Debounce search input before running search (reduces work on mobile)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearchQuery(searchQuery), 200);
    return () => clearTimeout(t);
  }, [searchQuery]);
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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

  const updateSearchDropdownMaxHeight = useCallback(() => {
    if (typeof window === 'undefined') return;
    const inputRow = searchInputRowRef.current;
    const panel = isMobileRef.current ? mobileMapOverlaysRef.current : desktopMapOverlaysRef.current;
    const fallback = 400;
    if (!inputRow) {
      setSearchDropdownMaxHeightPx(fallback);
      return;
    }
    if (!panel) {
      setSearchDropdownMaxHeightPx(fallback);
      return;
    }
    const inputBottom = inputRow.getBoundingClientRect().bottom;
    const panelTop = panel.getBoundingClientRect().top;
    const raw = panelTop - inputBottom - SEARCH_DROPDOWN_MARGIN_TOP - SEARCH_DROPDOWN_GAP_ABOVE_MODELLING;
    const capped = Math.min(fallback, Math.max(80, Math.floor(raw)));
    setSearchDropdownMaxHeightPx(capped);
  }, []);

  useLayoutEffect(() => {
    updateSearchDropdownMaxHeight();
  }, [
    updateSearchDropdownMaxHeight,
    isMobile,
    censusLayersReady,
    censusStats,
    loading,
    showSearchResults,
    searchResults.length,
    activeCensusView,
    enabledOverlayLayerIds,
  ]);

  useEffect(() => {
    window.addEventListener('resize', updateSearchDropdownMaxHeight);
    const ro = new ResizeObserver(() => updateSearchDropdownMaxHeight());
    const d = desktopMapOverlaysRef.current;
    const m = mobileMapOverlaysRef.current;
    const inputRow = searchInputRowRef.current;
    if (d) ro.observe(d);
    if (m) ro.observe(m);
    if (inputRow) ro.observe(inputRow);
    return () => {
      window.removeEventListener('resize', updateSearchDropdownMaxHeight);
      ro.disconnect();
    };
  }, [
    updateSearchDropdownMaxHeight,
    isMobile,
    censusLayersReady,
    censusStats,
    showSearchResults,
    searchResults.length,
    loading,
  ]);

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

  // Define district boundaries
  

  // Get marker color based on project type
  const addOverlaySourceAndLayer = useCallback((mapInstance, layerId, config, geojson) => {
    if (!mapInstance || !config) return;
    const layerMapId = layerId + '-layer';
    if (mapInstance.getSource(layerId)) return;
    mapInstance.addSource(layerId, { type: 'geojson', data: geojson });
    const styleCfg = config.style || {};
    const { type: layerType, paint } = styleCfg;
    const baseLayer = { id: layerMapId, source: layerId, layout: { visibility: 'visible' }, paint: {} };
    if (layerType === 'symbol') {
      registerOverlaySymbolImages(mapInstance);
      baseLayer.type = 'symbol';
      baseLayer.layout['icon-image'] = styleCfg.iconImage;
      baseLayer.layout['icon-size'] = styleCfg.iconSize ?? 0.4;
      baseLayer.layout['icon-allow-overlap'] = true;
      baseLayer.layout['icon-ignore-placement'] = false;
      baseLayer.layout['icon-anchor'] = 'center';
      baseLayer.filter = ['any', ['==', ['geometry-type'], 'Point'], ['==', ['geometry-type'], 'MultiPoint']];
    } else if (layerType === 'circle') {
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
        const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === layerId);
        const styleCfg = config?.style || {};
        map.current.setLayoutProperty(layerMapId, 'visibility', 'visible');
        if (styleCfg.type === 'symbol') {
          registerOverlaySymbolImages(map.current);
          if (styleCfg.iconImage) map.current.setLayoutProperty(layerMapId, 'icon-image', styleCfg.iconImage);
          if (styleCfg.iconSize != null) map.current.setLayoutProperty(layerMapId, 'icon-size', styleCfg.iconSize);
        }
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
    try {
      const response = await fetch(config.url);
      if (!response.ok) throw new Error(`Failed to load ${config.label}`);
      let geojson = await response.json();
      if (config.pointLonLatFields && config.pointLonLatFields.length >= 2) {
        geojson = applyLonLatFromProperties(geojson, config.pointLonLatFields[0], config.pointLonLatFields[1]);
      }
      geojson = reprojectFeatureCollectionIfNeeded(geojson);
      overlayDataCacheRef.current[layerId] = geojson;
      addOverlaySourceAndLayer(map.current, layerId, config, geojson);
    } catch (err) {
      console.error('Error loading overlay layer:', layerId, err);
    }
  }, [addOverlaySourceAndLayer]);

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
            <div style="font-size: 0.85em; color: #445461; margin-bottom: 10px;">Tract ID: ${tractId}</div>
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

    // Long-lived for the page, like the map itself: it is never torn down, so
    // it is not terminated in a cleanup (which StrictMode's double-invoke in
    // development would otherwise kill before the second run could reuse it).
    const dataWorker = new DataParserWorker();

    // miami_cities.geojson (2.0 MB) used to be fetched and parsed here to build
    // districtsRef: a centroid and zoom level per city polygon. The only code
    // that ever read districtsRef is the district-layer rendering commented out
    // below and in the style-change handler, so the download, the parse and the
    // per-feature logging produced nothing that reaches the screen. Reviving the
    // district layers means reviving this loader with it.

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: MIAMI_DADE_DEFAULT_CENTER,
      zoom: MIAMI_DADE_DEFAULT_ZOOM,
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

      // Fetching, JSON.parse and all feature reshaping now happen in a worker;
      // the main thread only applies the results to the map. Both jobs start
      // together so their downloads overlap, but they are applied in the same
      // order as before: projects and their markers first, census tracts second.
      const supabaseBaseUrl = import.meta.env.VITE_SUPABASE_URL || SUPABASE_STORAGE.split('/storage/')[0];
      const projectsJob = runWorkerTask(dataWorker, 'projects', {
        url: `${supabaseBaseUrl}/storage/v1/object/public/project-data/${PROJECTS_GEOJSON_FILE}`,
      });
      const censusJob = runWorkerTask(dataWorker, 'census', {
        censusUrl: '/femaindex.geojson',
        creUrl: '/FL_CRE.csv',
      });

      try {
        const { filteredData, markerSpecs, skipped, projectsSourceUrl, bufferSourceUrl } =
          await projectsJob;

        if (skipped.length) {
          console.warn('[Projects] Skipped features with invalid coordinates:', skipped);
        }

        setAllProjectsData(filteredData);

        // Both sources are handed to mapbox as blob: URLs, so mapbox fetches and
        // parses them inside its own worker instead of on the main thread.
        map.current.addSource('projects', {
          type: 'geojson',
          data: projectsSourceUrl
        });

        // Invisible buffer zones around each marker, to intercept mouse events.
        // The layer itself is added in addCensusSourceAndLayers, after the
        // census layers, so the stacking order is unchanged.
        map.current.addSource('marker-buffers', {
          type: 'geojson',
          data: bufferSourceUrl
        });

        const markers = markerSpecs.map(({ featureIndex, lngLat, color }) => {
          const feature = filteredData.features[featureIndex];

          const marker = new mapboxgl.Marker({
            color,
            scale: isMobileRef.current ? 0.35 : 0.49
          })
            .setLngLat(lngLat);

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
          return marker;
        });

        setAllMarkers(markers);

        // Frame the dense Miami-Dade project cluster (not full county extent / empty fringes)
        if (markers.length > 0) {
          fitMapToMostProjects(map.current, markers, { duration: 0, maxZoom: 11 });
        }

        setLoading(false);
      } catch (err) {
        console.error('Error loading project data:', err);
        setError('Unable to load project data. Please ensure the GeoJSON file is available or use a CORS proxy.');
        setLoading(false);
      }

      try {
        const { censusSourceUrl, statsPayload, creError } = await censusJob;

        if (creError) {
          console.warn('Error loading FL_CRE.csv:', creError);
        }

        // A blob: URL rather than the parsed object, so mapbox parses the tract
        // geometry in its own worker. censusDataRef is only ever handed to
        // addSource / setData, so a URL serves exactly the same purpose.
        censusDataRef.current = censusSourceUrl;
        censusStatsRef.current = statsPayload;
        setCensusStats(statsPayload);
        addCensusSourceAndLayers();

        // The block that used to follow built a LngLatBounds over every tract
        // and called map.fitBounds with it. It threw TypeError on its first
        // line — LngLatBounds has no .set() method — on every single load, so
        // the fitBounds never ran and the map kept the framing that
        // fitMapToMostProjects had already applied. It is left out rather than
        // repaired: repairing it would move the camera and change what the user
        // sees. Restoring the tract-extent zoom is a deliberate design change,
        // not a performance fix.
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
    if (isCriticalInfra) {
      enabledOverlayLayerIds.forEach((id) => {
        if (!map.current?.getSource(id)) ensureOverlayLayerLoaded(id);
      });
    }
    OVERLAY_LAYERS_CONFIG.forEach((config) => {
      const layerMapId = config.id + '-layer';
      if (map.current.getLayer(layerMapId)) {
        const visible = isCriticalInfra && enabledOverlayLayerIds.includes(config.id);
        map.current.setLayoutProperty(layerMapId, 'visibility', visible ? 'visible' : 'none');
      }
    });
  }, [activeCensusView, enabledOverlayLayerIds, ensureOverlayLayerLoaded]);

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
  const criticalInfraLegendItems = useMemo(
    () =>
      CRITICAL_INFRASTRUCTURE_DEFAULT_GROUP_KEYS
        .map((key) => {
          const group = CRITICAL_INFRASTRUCTURE_SUBLAYER_GROUPS.find((g) => g.id === key);
          if (group) {
            const representativeLayerId = CRITICAL_INFRA_GROUP_LEGEND_REPRESENTATIVE_LAYER_ID[group.id] || group.memberIds[0];
            const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === representativeLayerId);
            if (!config?.style) return null;
            return { id: group.id, label: group.label, config };
          }
          const config = OVERLAY_LAYERS_CONFIG.find((c) => c.id === key);
          if (!config?.style) return null;
          return { id: key, label: config.label, config };
        })
        .filter(Boolean),
    []
  );

  const renderOverlayLegendSymbol = (config) => {
    if (!config?.style) return null;
    const legendMarkerSize = 18;
    const { type, paint, iconImage } = config.style;
    if (type === 'line') {
      const color = paint?.['line-color'] ?? '#666';
      return (
        <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <div style={{ width: '16px', height: '3px', backgroundColor: color, borderRadius: 2 }} />
        </div>
      );
    }
    if (type === 'fill') {
      const color = paint?.['fill-color'] ?? '#666';
      const border = paint?.['fill-outline-color'] ?? paint?.['line-color'] ?? '#4d4d4d';
      return <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, backgroundColor: color, border: `1px solid ${border}`, borderRadius: 2, flexShrink: 0 }} />;
    }
    if (type === 'symbol') {
      // Keep legend icons visually aligned with map symbology.
      if (iconImage === OVERLAY_SYMBOL_IMAGES.medicalCross || iconImage === OVERLAY_SYMBOL_IMAGES.eocCross) {
        const src = iconImage === OVERLAY_SYMBOL_IMAGES.medicalCross ? getMedicalLegendIconDataUrl() : '';
        if (src) {
          return (
            <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'visible', flexShrink: 0 }}>
              <img src={src} alt="" aria-hidden style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px` }} />
            </div>
          );
        }
        const cross = iconImage === OVERLAY_SYMBOL_IMAGES.medicalCross ? CRITICAL_INFRA_NEUTRAL.white : CRITICAL_INFRA_NEUTRAL.black;
        const circle = iconImage === OVERLAY_SYMBOL_IMAGES.medicalCross ? CRITICAL_INFRA_NEUTRAL.black : CRITICAL_INFRA_NEUTRAL.white;
        const border = iconImage === OVERLAY_SYMBOL_IMAGES.medicalCross ? 'rgba(255,255,255,0.32)' : 'rgba(0,0,0,0.24)';
        return (
          <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: circle, border: `1px solid ${border}`, position: 'relative', flexShrink: 0 }}>
            <div style={{ position: 'absolute', left: '50%', top: '20%', transform: 'translateX(-50%)', width: '3px', height: '60%', borderRadius: 1, backgroundColor: cross }} />
            <div style={{ position: 'absolute', left: '20%', top: '50%', transform: 'translateY(-50%)', width: '60%', height: '3px', borderRadius: 1, backgroundColor: cross }} />
          </div>
        );
      }
      if (iconImage === OVERLAY_SYMBOL_IMAGES.community) {
        const src = getCommunityLegendIconDataUrl();
        if (src) {
          return (
            <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'visible', flexShrink: 0 }}>
              <img src={src} alt="" aria-hidden style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px` }} />
            </div>
          );
        }
        return <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: CRITICAL_INFRA_NEUTRAL.black, border: '1px solid rgba(255,255,255,0.32)', flexShrink: 0 }} />;
      }
      if (iconImage === OVERLAY_SYMBOL_IMAGES.disasterRecovery) {
        return <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: CRITICAL_INFRA_NEUTRAL.darkGray, border: `1px solid ${CRITICAL_INFRA_NEUTRAL.borderGray}`, flexShrink: 0 }} />;
      }
      if (iconImage === OVERLAY_SYMBOL_IMAGES.riskShelter) {
        const src = getRiskLegendIconDataUrl();
        if (src) {
          return (
            <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'visible', flexShrink: 0 }}>
              <img src={src} alt="" aria-hidden style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px` }} />
            </div>
          );
        }
        return (
          <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: CRITICAL_INFRA_NEUTRAL.darkGray, border: `1px solid ${CRITICAL_INFRA_NEUTRAL.borderGray}`, position: 'relative', flexShrink: 0 }}>
            <div style={{ position: 'absolute', left: '22%', top: '46%', width: '56%', height: '30%', backgroundColor: CRITICAL_INFRA_NEUTRAL.white, borderRadius: '1px' }} />
            <div style={{ position: 'absolute', left: '50%', top: '25%', transform: 'translateX(-50%)', width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderBottom: `5px solid ${CRITICAL_INFRA_NEUTRAL.white}` }} />
            <div style={{ position: 'absolute', left: '50%', top: '54%', transform: 'translateX(-50%)', width: '12%', height: '20%', backgroundColor: CRITICAL_INFRA_NEUTRAL.black, borderRadius: '1px' }} />
          </div>
        );
      }
      return <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: '#666', border: '1px solid #555', flexShrink: 0 }} />;
    }
    const color = paint?.['circle-color'] ?? '#666';
    const border = paint?.['circle-stroke-color'] ?? color;
    return <div style={{ width: `${legendMarkerSize}px`, height: `${legendMarkerSize}px`, borderRadius: '50%', backgroundColor: color, border: `1px solid ${border}`, flexShrink: 0 }} />;
  };

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
  const uniqueTypes = (
    infrastructureTypes.length > 0 ? infrastructureTypes : (legacyTypes.length > 0 ? legacyTypes : fallbackTypes)
  ).slice().sort((a, b) => {
    const diff = infrastructureTypeSortKey(a) - infrastructureTypeSortKey(b);
    if (diff !== 0) return diff;
    return (formatInfrastructureType(a) || '').localeCompare(formatInfrastructureType(b) || '', undefined, { sensitivity: 'base' });
  });
  const disasterFocusNew = getUniqueValues('Disaster_F');
  const disasterFocusLegacy = getUniqueValues('Disaster Focus');
  const uniqueDisasterFocusRaw = disasterFocusNew.length > 0 ? disasterFocusNew : disasterFocusLegacy;
  // Dedupe case-insensitively so Multi-Hazard / Multi-hazard appear once
  const disasterFocusByKey = new Map();
  uniqueDisasterFocusRaw.forEach((focus) => {
    const key = disasterFocusKey(focus);
    if (!key) return;
    if (!disasterFocusByKey.has(key)) {
      disasterFocusByKey.set(key, formatDisasterFocus(focus));
    }
  });
  const uniqueDisasterFocus = Array.from(disasterFocusByKey.values()).sort((a, b) => {
    const diff = disasterFocusSortKey(a) - disasterFocusSortKey(b);
    if (diff !== 0) return diff;
    return (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' });
  });
  // Get unique cities - prefer NAME field, fallback to City; dedupe case-insensitively so "Miami"/"miami"/"MIAMI" show once
  const uniqueCitiesRaw = getUniqueValues('NAME');
  const cityByLower = new Map();
  uniqueCitiesRaw.forEach((c) => {
    const key = (c || '').toLowerCase();
    if (!cityByLower.has(key)) cityByLower.set(key, c);
  });
  const uniqueCities = Array.from(cityByLower.values()).sort((a, b) => (a || '').localeCompare(b || '', undefined, { sensitivity: 'base' }));

  // Zoom to city markers when city is selected
  const zoomToCity = useCallback((cityName) => {
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
      // "All Cities": frame where most projects are; specific city: exact marker bounds
      if (!cityName || cityName === '') {
        fitMapToMostProjects(map.current, markersToZoom, { duration: 1500, maxZoom: 11 });
      } else {
        map.current.fitBounds(bounds, {
          padding: OVERVIEW_FIT_PADDING,
          maxZoom: 12,
          duration: 1500
        });
      }
    }
  }, [allMarkers]);

  // Filter markers based on selected filters
  useEffect(() => {
    if (!allMarkers.length || !map.current) return;

    allMarkers.forEach(marker => {
      if (!marker.feature) return;
      const props = marker.feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'];
      const disasterFocus = props['Disaster_F'] || props['Disaster Focus'];
      const projectStatus = getProjectStatus(props);
      const city = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);

      const typeMatch = selectedTypes.length === 0 || selectedTypes.includes(type);
      const disasterMatch = disasterFocusMatches(selectedDisasterFocus, disasterFocus);
      const statusMatch = selectedProjectStatuses.length === 0 || selectedProjectStatuses.includes(projectStatus);
      const selectedCityTrimmed = selectedCity ? selectedCity.trim() : selectedCity;
      const cityMatch = !selectedCityTrimmed || selectedCityTrimmed === '' || (city || '').toLowerCase() === (selectedCityTrimmed || '').toLowerCase();

      const shouldShow = projectsLayerVisible && typeMatch && disasterMatch && statusMatch && cityMatch;

      // Only write when the value actually changes. This effect also re-runs on
      // every popup open/close (activeFeature is a dependency, and must stay one
      // so a filtered-out project's popup still closes), which otherwise meant
      // 1,664 redundant inline-style writes per popup interaction.
      const element = marker.getElement();
      if (shouldShow) {
        if (element.style.display !== 'block') element.style.display = 'block';
      } else {
        if (element.style.display !== 'none') element.style.display = 'none';
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
  }, [projectsLayerVisible, selectedTypes, selectedDisasterFocus, selectedProjectStatuses, selectedCity, allMarkers, activeFeature]);

  // Zoom to city when selected (including "All Cities")
  useEffect(() => {
    if (map.current && allMarkers.length && selectedCity !== undefined) {
      // Use setTimeout to ensure markers are filtered/displayed first
      const timeoutId = setTimeout(() => {
        zoomToCity(selectedCity);
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [selectedCity, allMarkers.length, zoomToCity]);

  /**
   * The set of projects matching the current filters.
   *
   * filteredStats and pieChartData ran this same predicate over every feature
   * independently, so each filter change walked the full collection twice.
   * Both now derive from this one memo; the predicate itself is unchanged.
   */
  const filteredProjectFeatures = useMemo(() => {
    if (!allProjectsData?.features) return [];

    const selectedCityTrimmed = selectedCity ? selectedCity.trim() : selectedCity;
    const selectedCityLower = (selectedCityTrimmed || '').toLowerCase();

    return allProjectsData.features.filter(feature => {
      const props = feature.properties || {};
      const type = props['Infrastruc'] || props['Infrastructure Type'] || props['Type'];
      const disasterFocus = props['Disaster_F'] || props['Disaster Focus'];
      const projectStatus = getProjectStatus(props);
      const city = (props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']);

      const typeMatch = selectedTypes.length === 0 || selectedTypes.includes(type);
      const disasterMatch = disasterFocusMatches(selectedDisasterFocus, disasterFocus);
      const statusMatch = selectedProjectStatuses.length === 0 || selectedProjectStatuses.includes(projectStatus);
      const cityMatch = !selectedCityTrimmed || selectedCityTrimmed === '' || (city || '').toLowerCase() === selectedCityLower;

      return typeMatch && disasterMatch && statusMatch && cityMatch;
    });
  }, [allProjectsData, selectedTypes, selectedDisasterFocus, selectedProjectStatuses, selectedCity]);

  // Calculate filtered statistics (project count and total investment)
  const filteredStats = useMemo(() => {
    const filteredFeatures = filteredProjectFeatures;

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
  }, [filteredProjectFeatures]);

  // Calculate pie chart data based on city, disaster focus, and infrastructure type filters
  const pieChartData = useMemo(() => {
    const filteredFeatures = filteredProjectFeatures;

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
      } else if (
        type === 'Grey Infrastructure' ||
        type === 'Grey' ||
        type === 'Gray Infrastructure' ||
        type === 'Gray' ||
        (typeof type === 'string' && /^gr[ae]y(\s+infrastructure)?$/i.test(type.trim()))
      ) {
        normalizedType = 'Gray';
      } else if (type === 'Hybrid') {
        normalizedType = 'Hybrid';
      }
      
      typeCounts[normalizedType] = (typeCounts[normalizedType] || 0) + 1;
    });

    // Convert to array format for recharts
    const colors = {
      'Blue': '#3498db',
      'Green': '#27ae60',
      'Gray': '#95a5a6',
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
  }, [filteredProjectFeatures]);

  const pieChartSummary = useMemo(() => {
    if (!pieChartData.length) return '';
    const total = pieChartData.reduce((sum, row) => sum + row.value, 0);
    if (!total) return 'No projects in the current filter.';
    const parts = pieChartData.map((row) => {
      const pct = Math.round((row.value / total) * 100);
      return `${row.name}: ${row.value} (${pct}%)`;
    });
    return `${total} projects total. ${parts.join('; ')}.`;
  }, [pieChartData]);

  const searchHasQuery = debouncedSearchQuery.trim().length > 0;
  const searchListboxActive = showSearchResults && searchResults.length > 0;
  const searchLiveMessage =
    searchHasQuery && showSearchResults
      ? (searchResults.length === 0 ? 'No projects found.' : `${searchResults.length} project${searchResults.length === 1 ? '' : 's'} found.`)
      : '';

  return (
    <div style={{ display: 'flex', flex: 1, width: '100%', overflow: 'hidden', boxSizing: 'border-box', minHeight: 0, position: 'relative' }}>
        <h1 className="sr-only">Project map and filters</h1>
        {isMobile && !sidebarOpen && (
          <button
            type="button"
            className="dashboard-mobile-filters-open"
            aria-label="Open project filters"
            aria-expanded={false}
            aria-controls="dashboard-filters-sidebar"
            onClick={() => setSidebarOpen(true)}
            style={{
              position: 'fixed',
              left: 'max(12px, env(safe-area-inset-left))',
              top: 'max(12px, env(safe-area-inset-top))',
              zIndex: 1101,
              width: 44,
              height: 44,
              borderRadius: 10,
              border: '1px solid rgba(0,0,0,0.12)',
              background: 'rgba(255,255,255,0.92)',
              boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#2c3e50',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" focusable="false">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
          </button>
        )}
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
        <aside
          id="dashboard-filters-sidebar"
          aria-label="Project filters"
          aria-hidden={isMobile && !sidebarOpen ? true : undefined}
          style={{
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
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
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
                width: 32,
                height: 18,
                borderRadius: 9,
                border: '1px solid rgba(0,0,0,0.2)',
                boxSizing: 'border-box',
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
                  top: '50%',
                  left: projectsLayerVisible ? 14 : 2,
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  background: '#fff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
                  transform: 'translateY(-50%)',
                  transition: 'left 0.2s ease'
                }}
              />
            </button>
          </div>
          {/* City Filter */}
          <div style={{ marginBottom: '24px', position: 'relative' }} data-city-dropdown>
            <h2 id="dashboard-city-heading" style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              City
            </h2>
            <button
              type="button"
              id={DASHBOARD_CITY_TRIGGER_ID}
              aria-haspopup="listbox"
              aria-expanded={cityDropdownOpen}
              aria-controls={DASHBOARD_CITY_LISTBOX_ID}
              aria-labelledby="dashboard-city-heading"
              onClick={() => setCityDropdownOpen((open) => !open)}
              onKeyDown={(e) => {
                if (e.key === 'Escape' && cityDropdownOpen) {
                  e.preventDefault();
                  setCityDropdownOpen(false);
                }
                if ((e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') && !cityDropdownOpen) {
                  e.preventDefault();
                  setCityDropdownOpen(true);
                }
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '0.9em',
                color: selectedCity ? '#2c3e50' : '#5d6d7e',
                border: '1px solid rgba(255, 255, 255, 0.4)',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(10px) saturate(180%)',
                WebkitBackdropFilter: 'blur(10px) saturate(180%)',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
                transition: 'all 0.2s ease',
                fontFamily: 'inherit',
              }}
            >
              <span>{selectedCity ? formatCityName(selectedCity) : 'All Cities'}</span>
              <span style={{ fontSize: '0.7em' }} aria-hidden="true">▼</span>
            </button>
            {cityDropdownOpen && (
              <ul
                id={DASHBOARD_CITY_LISTBOX_ID}
                role="listbox"
                aria-labelledby="dashboard-city-heading"
                style={{
                  listStyle: 'none',
                  margin: 0,
                  padding: '4px',
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
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
                }}
              >
                <li role="presentation" style={{ margin: 0, padding: 0 }}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={selectedCity === ''}
                    onClick={() => {
                      setSelectedCity('');
                      setCityDropdownOpen(false);
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      background: selectedCity === '' ? 'rgba(240, 248, 255, 0.7)' : 'transparent',
                      padding: '8px 12px',
                      cursor: 'pointer',
                      fontSize: '0.9em',
                      color: selectedCity === '' ? '#3498db' : '#2c3e50',
                      borderRadius: '6px',
                      transition: 'all 0.2s ease',
                      fontFamily: 'inherit',
                    }}
                    onMouseEnter={(e) => {
                      if (selectedCity !== '') e.currentTarget.style.backgroundColor = 'rgba(240, 248, 255, 0.5)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = selectedCity === '' ? 'rgba(240, 248, 255, 0.7)' : 'transparent';
                    }}
                  >
                    All Cities
                  </button>
                </li>
                {uniqueCities.map((city) => (
                  <li key={city} role="presentation" style={{ margin: 0, padding: 0 }}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selectedCity === city}
                      onClick={() => {
                        setSelectedCity(city);
                        setCityDropdownOpen(false);
                      }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        border: 'none',
                        background: selectedCity === city ? 'rgba(240, 248, 255, 0.7)' : 'transparent',
                        padding: '8px 12px',
                        cursor: 'pointer',
                        fontSize: '0.9em',
                        color: selectedCity === city ? '#3498db' : '#2c3e50',
                        borderRadius: '6px',
                        transition: 'all 0.2s ease',
                        fontFamily: 'inherit',
                      }}
                      onMouseEnter={(e) => {
                        if (selectedCity !== city) e.currentTarget.style.backgroundColor = 'rgba(240, 248, 255, 0.5)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = selectedCity === city ? 'rgba(240, 248, 255, 0.7)' : 'transparent';
                      }}
                    >
                      {formatCityName(city)}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          {/* Project Status Filter — 2×2: Completed | Ongoing / Funded | Planned */}
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              Project Status
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                columnGap: '16px',
                rowGap: '10px',
                alignItems: 'center',
              }}
            >
              {PROJECT_STATUS_OPTIONS.map(status => (
                <label key={status} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedProjectStatuses.includes(status)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedProjectStatuses([...selectedProjectStatuses, status]);
                      } else {
                        setSelectedProjectStatuses(selectedProjectStatuses.filter(s => s !== status));
                      }
                    }}
                    style={{ marginRight: '8px', cursor: 'pointer' }}
                  />
                  <span style={{ color: '#445461', fontSize: '0.9em' }}>{status}</span>
                </label>
              ))}
            </div>
            {selectedProjectStatuses.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedProjectStatuses([])}
                style={{
                  marginTop: '8px',
                  padding: '4px 8px',
                  fontSize: '0.85em',
                  background: 'transparent',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#445461'
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Type Filter — 2×2: Blue | Green / Gray | Hybrid */}
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              Infrastructure Type
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                columnGap: '16px',
                rowGap: '10px',
                alignItems: 'center',
              }}
            >
              {uniqueTypes.map(type => {
                const typeLabel = formatInfrastructureType(type);
                const typeDefinition = getInfrastructureTypeDefinition(type);
                return (
                  <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '4px', minWidth: 0 }}>
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
                        style={{ marginRight: '4px', cursor: 'pointer' }}
                      />
                      <span style={{ color: '#445461', fontSize: '0.9em' }}>{typeLabel}</span>
                    </label>
                    <InfrastructureTypeInfoIcon
                      label={typeLabel}
                      definition={typeDefinition}
                    />
                  </div>
                );
              })}
            </div>
            {selectedTypes.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedTypes([])}
                style={{
                  marginTop: '8px',
                  padding: '4px 8px',
                  fontSize: '0.85em',
                  background: 'transparent',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#445461'
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Disaster Focus Filter — two-column grid */}
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.1em', fontWeight: '500', color: '#2c3e50', marginBottom: '12px' }}>
              Disaster Focus
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                columnGap: '16px',
                rowGap: '10px',
                alignItems: 'center',
              }}
            >
              {uniqueDisasterFocus.map(focus => (
                <label key={focus} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
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
                  <span style={{ color: '#445461', fontSize: '0.9em' }}>{focus}</span>
                </label>
              ))}
            </div>
            {selectedDisasterFocus.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedDisasterFocus([])}
                style={{
                  marginTop: '8px',
                  padding: '4px 8px',
                  fontSize: '0.85em',
                  background: 'transparent',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: '#445461'
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
                color: '#445461',
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
                color: '#445461',
                fontWeight: 500
              }}>
                Total Investment
              </div>
            </div>
          </div>

          {/* Pie Chart */}
          {pieChartData.length > 0 && (
            <figure style={{
              marginTop: '24px',
              paddingTop: '24px',
              borderTop: '1px solid rgba(0, 0, 0, 0.1)',
              marginLeft: 0,
              marginRight: 0,
              marginBottom: 0,
            }}>
              <h2 style={{
                fontSize: '1em',
                fontWeight: '500',
                color: '#2c3e50',
                marginBottom: '12px',
                textAlign: 'center',
              }}>
                Infrastructure Type Distribution
              </h2>
              <figcaption className="sr-only">{pieChartSummary}</figcaption>
              <div
                role="img"
                aria-label={pieChartSummary}
                style={{
                  background: 'rgba(255, 255, 255, 0.8)',
                  backdropFilter: 'blur(10px) saturate(180%)',
                  WebkitBackdropFilter: 'blur(10px) saturate(180%)',
                  border: '1px solid rgba(255, 255, 255, 0.4)',
                  borderRadius: '12px',
                  padding: '12px',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.5)',
                }}
              >
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
                        <Cell key={`cell-${index}`} fill={entry.color} stroke="#ffffff" strokeWidth={1} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => [`${value} projects`, 'Count']}
                      contentStyle={{
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        border: '1px solid rgba(0, 0, 0, 0.1)',
                        borderRadius: '8px',
                        padding: '8px',
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      wrapperStyle={{ fontSize: '0.75em', paddingTop: '8px', color: '#445461' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </figure>
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
                color: '#445461',
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
                <button
                  type="button"
                  aria-expanded={showDisclaimer}
                  aria-controls="disclaimer-panel"
                  onClick={() => setShowDisclaimer((v) => !v)}
                  style={{
                    fontSize: '0.75em',
                    color: '#3498db',
                    textDecoration: 'none',
                    cursor: 'pointer',
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    fontFamily: 'inherit',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.textDecoration = 'underline';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.textDecoration = 'none';
                  }}
                >
                  Disclaimer
                </button>
                <div
                  id="disclaimer-panel"
                  hidden={!showDisclaimer}
                  style={{ fontSize: '0.75em', color: '#445461', marginTop: '6px', lineHeight: 1.5 }}
                >
                  Any opinions, findings, and conclusions or recommendations expressed in this website are those of the investigator(s) and do not necessarily reflect the views of the National Science Foundation.
                </div>
              </div>
              <p style={{
                fontSize: '0.75em',
                color: '#445461',
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
          {/* role=application: focus moves to map canvas when user activates the map; avoid tabIndex on wrapper (false positive from jsx-a11y). */}
          <div
            ref={mapContainer}
            className="dashboard-map-area"
            role="application"
            aria-label="Interactive map of Miami-Dade climate resilience projects. Use the project filters in the sidebar and the search field for a non-map view."
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
              <label htmlFor={DASHBOARD_SEARCH_INPUT_ID} className="sr-only">
                Search projects by name, city, or keyword
              </label>
              <span id={DASHBOARD_SEARCH_LIVE_ID} className="sr-only" aria-live="polite">
                {searchLiveMessage}
              </span>
              <div
                ref={searchInputRowRef}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: isMobile ? '8px 12px' : '12px 16px',
                  gap: isMobile ? '8px' : '12px'
                }}
              >
                <svg
                  width={isMobile ? 18 : 20}
                  height={isMobile ? 18 : 20}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#445461"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ flexShrink: 0 }}
                  aria-hidden="true"
                  focusable="false"
                >
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
                <input
                  type="text"
                  id={DASHBOARD_SEARCH_INPUT_ID}
                  role="combobox"
                  aria-autocomplete="list"
                  aria-expanded={showSearchResults && searchHasQuery}
                  aria-controls={
                    searchListboxActive
                      ? DASHBOARD_SEARCH_LISTBOX_ID
                      : showSearchResults && searchHasQuery && searchResults.length === 0
                        ? 'dashboard-search-empty'
                        : undefined
                  }
                  aria-activedescendant={
                    selectedResultIndex >= 0 && searchListboxActive
                      ? `search-option-${selectedResultIndex}`
                      : undefined
                  }
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
                    background: 'transparent',
                    fontSize: isMobile ? '16px' : '0.95em',
                    color: '#2c3e50',
                    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
                  }}
                />
                <button
                  type="button"
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
                    color: '#445461',
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
                      e.currentTarget.style.color = '#445461';
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
                    aria-hidden="true"
                    focusable="false"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>

              {/* Search Results Dropdown */}
              {showSearchResults && searchResults.length > 0 && (
                <ul
                  id={DASHBOARD_SEARCH_LISTBOX_ID}
                  role="listbox"
                  aria-label="Search results"
                  style={{
                    listStyle: 'none',
                    margin: 0,
                    padding: 0,
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    marginTop: '4px',
                    maxHeight: searchDropdownMaxHeightPx,
                    overflowY: 'auto',
                    ...mapOverlayGlassStyle,
                    borderRadius: '12px',
                    zIndex: 2,
                  }}
                >
                  {searchResults.map((result, index) => {
                    const props = result.properties || {};
                    const projectName = props['Project_Na'] || props['Project Name'] || 'Unnamed Project';
                    const city = (props['NAME'] || props['City']) ? formatCityName((props['NAME'] || props['City']).trim()) : '—';
                    const infrastructureType = formatInfrastructureType(
                      props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || '—'
                    );
                    const description = props['New_15_25_'] || props['New 15-25 Words Project Description'] || '';
                    const isSelected = index === selectedResultIndex;

                    return (
                      <li key={result.id || index} role="presentation" style={{ margin: 0, padding: 0 }}>
                        <button
                          type="button"
                          id={`search-option-${index}`}
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => navigateToProject(result)}
                          style={{
                            width: '100%',
                            textAlign: 'left',
                            border: 'none',
                            borderBottom: index < searchResults.length - 1 ? '1px solid rgba(0, 0, 0, 0.05)' : 'none',
                            backgroundColor: isSelected ? 'rgba(52, 152, 219, 0.1)' : 'transparent',
                            transition: 'background-color 0.2s ease',
                            padding: '12px 16px',
                            cursor: 'pointer',
                            fontFamily: 'inherit',
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
                            marginBottom: '4px',
                          }}>
                            {highlightText(projectName, searchQuery)}
                          </div>
                          <div style={{
                            fontSize: '0.85em',
                            color: '#445461',
                            display: 'flex',
                            gap: '12px',
                            flexWrap: 'wrap',
                          }}>
                            <span>{highlightText(city, searchQuery)}</span>
                            <span aria-hidden="true">•</span>
                            <span>{highlightText(infrastructureType, searchQuery)}</span>
                          </div>
                          {description && (
                            <div style={{
                              fontSize: '0.75em',
                              color: '#5d656d',
                              marginTop: '6px',
                              lineHeight: 1.4,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}>
                              {highlightText(description, searchQuery)}
                            </div>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}

              {/* No Results Message */}
              {showSearchResults && debouncedSearchQuery.trim() && searchResults.length === 0 && (
                <div
                  id="dashboard-search-empty"
                  role="status"
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    marginTop: '4px',
                    padding: '16px',
                    maxHeight: searchDropdownMaxHeightPx,
                    overflowY: 'auto',
                    ...mapOverlayGlassStyle,
                    borderRadius: '12px',
                    zIndex: 2,
                    textAlign: 'center',
                    color: '#445461',
                    fontSize: '0.9em',
                  }}
                >
                  No projects found matching &quot;{debouncedSearchQuery}&quot;
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
                    ref={mobileMapOverlaysRef}
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
                    {censusVisible && activeCensusView === 'critical-infrastructure' && criticalInfraLegendItems.length > 0 && (
                      <div style={{ borderTop: '1px solid rgba(0,0,0,0.08)', marginTop: '10px', paddingTop: '10px' }}>
                        {criticalInfraLegendItems.map((item) => {
                          const { id, label, config } = item;
                          return (
                            <div key={id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '0.85em', color: '#1b3a4b' }}>
                              {renderOverlayLegendSymbol(config)}
                              <span>{label}</span>
                            </div>
                          );
                        })}
                      </div>
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
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#445461' }}><span>Very Low</span><span>Very High</span></div>
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
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#445461' }}>
                          <span>{censusStats.pred3PE.min?.toFixed(1) || '0'}%</span>
                          <span>{censusStats.pred3PE.max?.toFixed(1) || '0'}%</span>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div
                  ref={desktopMapOverlaysRef}
                  style={{
                    position: 'absolute',
                    bottom: '20px',
                    right: '20px',
                    zIndex: 1000,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    width: '320px',
                    maxHeight: 'calc(100vh - 100px)',
                  }}
                >
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
                        return (
                          <div
                            key={view}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', marginBottom: '8px' }}
                          >
                            <span style={{ fontSize: '0.95em', fontWeight: 500, color: '#2c3e50', flex: 1, minWidth: 0 }}>{label}</span>
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

              {/* Legend: fixed height for risk/pred3pe; taller for critical infra (4 symbol rows, no scroll) */}
              <div style={{
                ...mapOverlayGlassStyle,
                padding: '10px 12px 4px',
                borderRadius: '12px',
                width: '320px',
                ...(censusVisible && activeCensusView === 'critical-infrastructure' && criticalInfraLegendItems.length > 0
                  ? { minHeight: '124px', height: 'auto', overflow: 'visible' }
                  : { minHeight: '96px', height: '96px', overflow: 'hidden' }),
                boxSizing: 'border-box',
                display: 'flex',
                flexDirection: 'column',
              }}>
                {!(censusVisible && activeCensusView === 'risk' && sortedRatings.length > 0) &&
                 !(censusVisible && activeCensusView === 'pred3pe' && censusStats?.pred3PE) &&
                 !(censusVisible && activeCensusView === 'critical-infrastructure' && criticalInfraLegendItems.length > 0) && (
                  <div style={{ fontSize: '0.95em', fontWeight: 600, color: '#1b3a4b' }}>
                    Select a layer
                  </div>
                )}
                {censusVisible && activeCensusView === 'risk' && sortedRatings.length > 0 && (
                  <>
                    <div style={{ fontSize: '0.95em', fontWeight: 600, color: '#1b3a4b', marginBottom: '6px' }}>
                      FEMA Risk Rating
                    </div>
                    <div style={{ marginBottom: '4px' }}>
                      <div style={{
                        width: '100%',
                        height: '14px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        marginBottom: '4px'
                      }}>
                        <div style={{
                          width: '100%',
                          height: '100%',
                          background: 'linear-gradient(to right, #FFF9C4 0%, #FFF9C4 20%, #FFE082 25%, #FFE082 40%, #FFB74D 45%, #FFB74D 60%, #FF8A65 65%, #FF8A65 80%, #E64A19 85%, #E64A19 100%)'
                        }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#445461' }}>
                        <span>Very Low</span>
                        <span>Very High</span>
                      </div>
                    </div>
                  </>
                )}
                {censusVisible && activeCensusView === 'pred3pe' && censusStats?.pred3PE && (
                  <>
                    <div style={{ fontSize: '0.95em', fontWeight: 600, color: '#1b3a4b', marginBottom: '6px' }}>
                      Resilience Index (%)
                    </div>
                    <div style={{ marginBottom: '4px' }}>
                      <div style={{
                        width: '100%',
                        height: '14px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        marginBottom: '4px'
                      }}>
                        <div style={{
                          width: '100%',
                          height: '100%',
                          background: 'linear-gradient(to right, #E8D4F5 0%, #E8D4F5 10%, #D4B3E8 20%, #C298DB 35%, #A866C7 50%, #7A3FA8 65%, #5A1D85 80%, #2D0045 90%, #2D0045 100%)'
                        }}></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7em', color: '#445461' }}>
                        <span>{censusStats.pred3PE.min?.toFixed(1) || '0'}%</span>
                        <span>{censusStats.pred3PE.max?.toFixed(1) || '0'}%</span>
                      </div>
                    </div>
                  </>
                )}
                {censusVisible && activeCensusView === 'critical-infrastructure' && criticalInfraLegendItems.length > 0 && (
                  <div>
                    {criticalInfraLegendItems.map((item) => {
                      const { id, label, config } = item;
                      return (
                        <div key={id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', fontSize: '0.82em', color: '#1b3a4b' }}>
                          {renderOverlayLegendSymbol(config)}
                          <span>{label}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

                  {/* Satellite toggle inside desktop flex column */}
                  <div style={{
                    ...mapOverlayGlassStyle,
                    borderRadius: '25px',
                    overflow: 'hidden'
                  }}>
                    <button
                      type="button"
                      onClick={toggleMapStyle}
                      aria-label={isSatelliteView ? 'Switch map to standard view' : 'Switch map to satellite view'}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 12px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.8em', color: '#2c3e50', transition: 'all 0.3s', width: '100%' }}
                    >
                      <div style={{ marginRight: '8px', fontSize: '16px', display: 'flex', alignItems: 'center' }} aria-hidden="true">
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
              type="button"
              onClick={toggleMapStyle}
              aria-label={isSatelliteView ? 'Switch map to standard view' : 'Switch map to satellite view'}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 12px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.8em', color: '#2c3e50', transition: 'all 0.3s', minWidth: '120px' }}
            >
              <div style={{ marginRight: '8px', fontSize: '16px', display: 'flex', alignItems: 'center' }} aria-hidden="true">
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
          width: 32px;
          height: 18px;
          border-radius: 9px;
          border: 1px solid rgba(0, 0, 0, 0.2);
          box-sizing: border-box;
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
          top: 50%;
          left: 2px;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.22);
          pointer-events: none;
          transform: translateY(-50%) scale(0.92);
          transition:
            left 1s cubic-bezier(0.33, 1, 0.32, 1),
            transform 1s cubic-bezier(0.33, 1, 0.32, 1),
            box-shadow 1s ease;
        }
        .modelling-switch-track[aria-checked="true"] .modelling-switch-thumb {
          left: 16px;
          transform: translateY(-50%) scale(1);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
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
              <td style={{ color: '#2c3e50' }}>{formatInfrastructureType(props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || '—')}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Focus</td>
              <td style={{ color: '#2c3e50' }}>{formatDisasterFocus(props['Disaster_F'] || props['Disaster Focus'] || '—')}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>City</td>
              <td style={{ color: '#2c3e50' }}>{(props['NAME'] || props['City']) ? formatCityName((props['NAME'] || props['City']).trim()) : '—'}</td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Status</td>
              <td style={{ color: PROJECT_STATUS_COLORS[getProjectStatus(props)] || '#b45309', fontWeight: 700 }}>
                {getProjectStatus(props)}
              </td>
            </tr>
            <tr>
              <td style={{ color: '#34495e', fontWeight: 600 }}>Cost</td>
              <td style={{ color: ((props['Estimated_'] || props['Estimated Project Cost']) == null) ?'#b45309' : '#27ae60', fontWeight: 700 }}>{
                  formatCostCompact(props['Estimated_'] || props['Estimated Project Cost']) || 'Not Disclosed'}</td>
            </tr>
          </tbody>
        </table>
        {(props['New_15_25_'] || props['New 15-25 Words Project Description']) && (
          <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid #ecf0f1', color: '#000000', fontSize: '0.9em', lineHeight: 1.4 }}>
            {props['New_15_25_'] || props['New 15-25 Words Project Description']}
          </div>
        )}
      </div>,
      contentRef.current
    )}</>
  );
};
