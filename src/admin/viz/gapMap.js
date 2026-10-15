import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Same project file the live dashboard reads.
const PROJECTS_URL =
  'https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data/projects_merged_conf1.geojson';

// Provenance for everything drawn on the map. Shown in the left source card and
// the right "Data sources" panel, so the two can never disagree.
const SOURCES = {
  projects: {
    role: 'Investment (horizontal axis) and project dots',
    name: 'SCALE-R Resilience Project Inventory',
    publisher: 'SCALE-R research team, compiled from public agency documents',
    year: 'Project reporting years 1998–2026 (94% from 2020–2026); tract analysis run 12 Sep 2026',
    measure: 'Dollars from completed, ongoing and funded projects assigned to each tract, divided by residents.',
    detail: '1,664 projects from 449 public documents across 43 jurisdictions. 786 come from Miami-Dade County Local Mitigation Strategy (LMS) project lists; the rest from municipal capital improvement plans, SFWMD and other agency reports. 1,405 projects ($8.55B) are counted; 259 planned projects are excluded.',
    file: 'Modelling Data from Web/SCALE-R_Database.csv → tract_investment.csv',
  },
  population: {
    role: 'Denominator for investment per person',
    name: 'American Community Survey 5-year estimates, table B01001',
    publisher: 'U.S. Census Bureau',
    year: '2020–2024 (5-year)',
    measure: 'Total residents per census tract.',
    file: 'tract-level/ACS Data/B01001-SexByAge',
    link: 'https://data.census.gov',
  },
  slr: {
    role: 'Need measure',
    name: 'Sea Level Rise Inundation Data, Southeast Florida (FL_SE)',
    publisher: 'NOAA Office for Coastal Management',
    year: 'Downloaded 2026; tract shares computed 22 Sep 2026',
    measure: 'Share of tract land area inundated by ocean-connected water at 3 ft above mean higher high water (MHHW).',
    detail: 'Unconnected low-lying areas (NOAA "_low_" layers) are excluded. Water areas are removed using Census TIGER/Line 2024.',
    caveat: 'A water-level scenario, not a forecast for a particular year. 553 of 706 tracts have zero exposure.',
    file: 'Physical Indicators/FL_SE_slr_data_dist → slr_tract.csv',
    link: 'https://coast.noaa.gov/slrdata/',
  },
  surge: {
    role: 'Need measure',
    name: 'SLOSH Maximum of MEOWs (MOM) storm surge inundation, v4',
    publisher: 'NOAA National Hurricane Center',
    year: 'v4, reprocessed June 2026 (fixes a South Florida error in the 2025 release); shares computed 22 Sep 2026',
    measure: 'Share of tract land area with any surge inundation in a Category 3 hurricane at high tide.',
    caveat: 'A worst-case envelope across ~100,000 simulated storms per category, not the footprint of any single hurricane.',
    file: 'Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617 → surge_tract.csv',
    link: 'https://www.nhc.noaa.gov/nationalsurge/',
  },
  eal: {
    role: 'Need measure',
    name: 'National Risk Index: Expected Annual Loss score',
    publisher: 'FEMA',
    year: 'December 2025 tract file (version inferred from columns; confirm against FEMA release notes)',
    measure: 'Expected yearly dollar loss to buildings, population and agriculture from 18 natural hazards, as a national percentile score (0–100).',
    caveat: 'Hazard-only. This is the component the team\'s NRI audit recommends for analysis.',
    file: 'fema_miami_dade_dec_2025.csv',
    link: 'https://hazards.fema.gov/nri/',
  },
  nri: {
    role: 'Need measure',
    name: 'National Risk Index: composite Risk score',
    publisher: 'FEMA',
    year: 'December 2025 tract file (version inferred from columns; confirm against FEMA release notes)',
    measure: 'National percentile score (0–100) combining expected annual loss, social vulnerability and community resilience.',
    caveat: 'Already includes CDC social vulnerability and Census community resilience, so it is not a pure hazard measure. The team\'s NRI audit advises against it for analysis.',
    file: 'fema_miami_dade_dec_2025.csv',
    link: 'https://hazards.fema.gov/nri/',
  },
  sovi: {
    role: 'Need measure',
    name: 'National Risk Index: Social Vulnerability score',
    publisher: 'FEMA, derived from the CDC/ATSDR Social Vulnerability Index',
    year: 'December 2025 FEMA NRI tract file',
    measure: 'Susceptibility of residents to harm from hazards, as a national percentile score (0–100).',
    caveat: 'FEMA rescales CDC SVI. The CDC SVI year inside this NRI release should be confirmed against FEMA documentation.',
    file: 'fema_miami_dade_dec_2025.csv',
    link: 'https://hazards.fema.gov/nri/social-vulnerability',
  },
  pov: {
    role: 'Need measure',
    name: 'Social Vulnerability Index (SVI), variable EP_POV150',
    publisher: 'CDC / ATSDR',
    year: '2022 release (built from ACS 2018–2022), Florida tract file',
    measure: 'Percent of residents with income below 150% of the federal poverty line.',
    caveat: 'Two years older than the population figures (ACS 2020–2024).',
    file: 'tract-level/SVI Data → tract_analysis.csv',
    link: 'https://www.atsdr.cdc.gov/place-health/php/svi/',
  },
  tracts: {
    role: 'Map geography',
    name: 'Census tracts (2020 definitions)',
    publisher: 'U.S. Census Bureau',
    year: 'Display shapes from the live tool\'s FEMA layer; TIGER/Line 2024 used for area calculations',
    measure: '706 Miami-Dade tracts with land, joined by 11-digit GEOID.',
    file: 'public/femaindex-4326.geojson',
  },
  basemap: {
    role: 'Background map',
    name: 'Mapbox Dark v11',
    publisher: 'Mapbox, OpenStreetMap contributors',
    year: 'Live',
    measure: 'Streets, labels and water for orientation only.',
  },
};

const METRICS = [
  { id: 'slr', field: 'slr_3ft_area_share', label: 'Sea level rise, 3 ft (share of tract flooded)', axis: 'Sea level rise →', noun: '3 ft sea level rise exposure', fmt: pct },
  { id: 'surge', field: 'surge_cat3_area_share', label: 'Storm surge, Category 3 (share of tract flooded)', axis: 'Storm surge →', noun: 'Category 3 surge exposure', fmt: pct },
  { id: 'eal', field: 'EAL_SCORE', label: 'FEMA expected annual loss (score)', axis: 'FEMA loss →', noun: 'FEMA expected annual loss', fmt: (v) => v.toFixed(1) },
  { id: 'nri', field: 'RISK_SCORE', label: 'FEMA composite risk (score)', axis: 'FEMA risk →', noun: 'FEMA composite risk', fmt: (v) => v.toFixed(1) },
  { id: 'sovi', field: 'SOVI_SCORE', label: 'Social vulnerability (FEMA NRI, from CDC SVI)', axis: 'Vulnerability →', noun: 'social vulnerability', fmt: (v) => v.toFixed(1) },
  { id: 'pov', field: 'EP_POV150', label: 'Poverty: below 150% of poverty line (CDC SVI 2022)', axis: 'Poverty →', noun: 'poverty', fmt: (v) => `${v.toFixed(1)}%` },
];

// Stevens bivariate scheme, indexed [exposure][investment], 0 = low.
const COLORS = [
  ['#e8e8e8', '#b0d5df', '#64acbe'],
  ['#e4acac', '#ad9ea5', '#627f8c'],
  ['#c85a5a', '#985356', '#574249'],
];
const GAP = 6; // exposure high, investment low
const NONE = -2; // matches no tract; unpopulated tracts use -1
const DIM = '#1c2129';
const MAX_HEIGHT = 6000; // metres for the top-ranked tract; exaggerated so the county reads as a skyline
const COLUMN_RADIUS = 260; // metres
const HEIGHT_HINTS = {
  exposure: 'Taller = higher county rank on the need measure. Tall red columns are high-need tracts with little investment per resident.',
  investment_per_capita: 'Taller = more dollars per resident. Gap tracts sit low despite high need.',
  investment_total: 'Taller = more total dollars, before adjusting for population.',
  population: 'Taller = more residents (ACS 2020–2024). Shows how many people each color affects.',
};

function sourceCard(key, { compact = false } = {}) {
  const src = SOURCES[key];
  const rows = [['Publisher', src.publisher], ['Year', src.year]];
  if (!compact) rows.push(['File', src.file]);
  return `<div class="kicker">${src.role}</div><h3>${src.name}</h3><div>${src.measure}</div>` +
    (src.detail && !compact ? `<div style="margin-top:6px">${src.detail}</div>` : '') +
    `<dl>${rows.filter(([, v]) => v).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` +
    (src.caveat ? `<div class="caveat">${src.caveat}</div>` : '') +
    (src.link ? `<div style="margin-top:6px"><a href="${src.link}" target="_blank" rel="noreferrer">${src.link.replace(/^https?:\/\//, '')}</a></div>` : '');
}

function renderSources(metric) {
  document.getElementById('metric-source').innerHTML =
    `${sourceCard(metric.id, { compact: true })}<div class="hint">Full details: Sources panel →</div>`;
  const order = ['projects', 'population', ...METRICS.map((m) => m.id), 'tracts', 'basemap'];
  document.getElementById('source-list').innerHTML = order
    .map((key) => `<div class="src${key === metric.id ? ' active' : ''}">${sourceCard(key)}</div>`)
    .join('');
}

function pct(v) { return `${(v * 100).toFixed(v < 0.1 ? 1 : 0)}%`; }
function money(v) {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e4) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${Math.round(v).toLocaleString()}`;
}

/**
 * Returns a value -> 0|1|2 classifier using county terciles. When a third or
 * more of tracts are exactly zero (e.g. no sea level rise exposure), zero is
 * "low" and the nonzero tracts are split at their median instead.
 */
/** Returns a value -> 0..1 percentile rank among the given values. */
function ranker(values) {
  const sorted = values.filter((v) => v != null).sort((a, b) => a - b);
  return (v) => {
    if (v == null || !sorted.length) return 0;
    let lo = 0;
    let hi = sorted.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (sorted[mid] < v) lo = mid + 1; else hi = mid;
    }
    return v <= 0 ? 0 : lo / sorted.length;
  };
}

function colorExpr(only) {
  const match = ['match', ['get', 'bi'], ...COLORS.flatMap((row, r) => row.flatMap((c, i) => [r * 3 + i, c])), '#2a2f37'];
  return only == null ? match : ['case', ['==', ['get', 'bi'], only], match, DIM];
}

function heightExpr(scale) {
  return ['*', ['+', ['get', 'h'], ['case', ['>=', ['get', 'bi'], 0], 0.015, 0]], MAX_HEIGHT * scale];
}

/** A 20-sided polygon approximating a circle of `radius` metres. */
function circle(lng, lat, radius) {
  const dLat = radius / 111320;
  const dLng = dLat / Math.cos((lat * Math.PI) / 180);
  const ring = Array.from({ length: 21 }, (_, k) => {
    const a = (k % 20) * (Math.PI / 10);
    return [lng + dLng * Math.cos(a), lat + dLat * Math.sin(a)];
  });
  return { type: 'Polygon', coordinates: [ring] };
}

function classifier(values) {
  const sorted = values.filter((v) => v != null).sort((a, b) => a - b);
  const zeros = sorted.filter((v) => v <= 0).length;
  if (zeros >= sorted.length / 3) {
    const positive = sorted.slice(zeros);
    const mid = positive[Math.floor(positive.length / 2)];
    return { fn: (v) => (v <= 0 ? 0 : v < mid ? 1 : 2), breaks: [0, mid] };
  }
  const t1 = sorted[Math.floor(sorted.length / 3)];
  const t2 = sorted[Math.floor((2 * sorted.length) / 3)];
  return { fn: (v) => (v <= t1 ? 0 : v <= t2 ? 1 : 2), breaks: [t1, t2] };
}

/** Builds the map into the markup already on the page; returns a cleanup function. */
export function mount() {
  let removed = false;
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/dark-v11',
    center: [-80.42, 25.64],
    zoom: 9.4,
    padding: { left: 350, right: 380 },
    antialias: true,
    attributionControl: true,
  });
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');

  const metricSelect = document.getElementById('metric');
  const grid = document.getElementById('grid');
  let tracts;
  let metric = METRICS[0];
  let investBreaks;
  let riskBreaks;
  let activeCell = null;
  let is3d = true;
  let heightField = 'exposure';
  let orbiting = false;
  let baseOpacity = 0.82;
  let populatedCount = 0;

  METRICS.forEach((m) => metricSelect.add(new Option(m.label, m.id)));

  // Draw the 3x3 legend with exposure rising bottom-to-top.
  for (let r = 2; r >= 0; r -= 1) {
    for (let i = 0; i < 3; i += 1) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.style.background = COLORS[r][i];
      cell.dataset.bi = String(r * 3 + i);
      cell.addEventListener('mouseenter', () => highlight(r * 3 + i));
      cell.addEventListener('mouseleave', () => highlight(activeCell));
      cell.addEventListener('click', () => {
        activeCell = activeCell === r * 3 + i ? null : r * 3 + i;
        document.getElementById('gap-only').checked = activeCell === GAP;
        highlight(activeCell);
      });
      grid.appendChild(cell);
    }
  }

  function highlight(bi) {
    grid.querySelectorAll('.cell').forEach((c) => c.classList.toggle('active', Number(c.dataset.bi) === bi));
    if (!map.getLayer('tracts-fill')) return;
    map.setPaintProperty('tracts-fill', 'fill-opacity',
      bi == null ? baseOpacity : ['case', ['==', ['get', 'bi'], bi], baseOpacity + 0.1, 0.08]);
    map.setFilter('tracts-focus', ['==', ['get', 'bi'], bi ?? NONE]);
    map.setPaintProperty('tracts-3d', 'fill-extrusion-color', colorExpr(bi));
  }

  function classify() {
    const feats = tracts.features;
    const populated = (f) => (f.properties.population ?? 0) > 0;
    const inv = classifier(feats.filter(populated).map((f) => f.properties.investment_per_capita));
    const risk = classifier(feats.filter(populated).map((f) => f.properties[metric.field]));
    investBreaks = inv.breaks;
    riskBreaks = risk.breaks;

    let gapTracts = 0;
    populatedCount = feats.filter(populated).length;
    let gapPeople = 0;
    feats.forEach((f) => {
      const p = f.properties;
      const value = p[metric.field];
      if (!populated(f) || value == null || p.investment_per_capita == null) {
        p.bi = -1;
        return;
      }
      p.r = risk.fn(value);
      p.i = inv.fn(p.investment_per_capita);
      p.bi = p.r * 3 + p.i;
      if (p.bi === GAP) {
        gapTracts += 1;
        gapPeople += p.population;
      }
    });

    document.getElementById('y-label').textContent = metric.axis;
    document.getElementById('gap-count').textContent = `${gapTracts} tracts`;
    document.getElementById('gap-detail').textContent =
      `${gapPeople.toLocaleString()} residents live where ${metric.noun} is in the county's top tier but investment per person is in the bottom third (under ${money(investBreaks[0])}).`;
    document.getElementById('method').innerHTML =
      `<b>Tier cut-offs for this view.</b> Need: ${riskBreaks[0] === 0 ? `none / under ${metric.fmt(riskBreaks[1])} / ${metric.fmt(riskBreaks[1])}+` : `up to ${metric.fmt(riskBreaks[0])} / up to ${metric.fmt(riskBreaks[1])} / above`}. ` +
      `Investment per person: up to ${money(investBreaks[0])} / up to ${money(investBreaks[1])} / above. ` +
      `County terciles across ${populatedCount} populated tracts.`;
    renderSources(metric);

    const field = heightField === 'exposure' ? metric.field : heightField;
    const rank = ranker(feats.filter(populated).map((f) => f.properties[field]));
    feats.forEach((f) => { f.properties.h = f.properties.bi >= 0 ? rank(f.properties[field]) : 0; });
    document.getElementById('height-hint').textContent = HEIGHT_HINTS[heightField];

    map.getSource('tracts')?.setData(tracts);
    map.getSource('columns')?.setData(columns());
  }

  // One column per populated tract, so big rural tracts don't read as walls.
  // Zero-height tracts are left as flat ground color rather than stubs.
  function columns() {
    return {
      type: 'FeatureCollection',
      features: tracts.features.filter((f) => f.properties.bi >= 0 && f.properties.h > 0).map((f) => ({
        type: 'Feature',
        properties: { GEOID: f.properties.GEOID, bi: f.properties.bi, h: f.properties.h },
        geometry: circle(f.properties.cx, f.properties.cy, COLUMN_RADIUS),
      })),
    };
  }

  /** Raises the columns from the ground over `ms` milliseconds. */
  function grow(ms) {
    const start = performance.now();
    const step = (now) => {
      if (removed) return;
      const t = Math.min(1, (now - start) / ms);
      map.setPaintProperty('tracts-3d', 'fill-extrusion-height', heightExpr(1 - (1 - t) ** 3));
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function setView(threeD) {
    is3d = threeD;
    document.getElementById('view-2d').classList.toggle('on', !threeD);
    document.getElementById('view-3d').classList.toggle('on', threeD);
    document.getElementById('controls-3d').style.display = threeD ? '' : 'none';
    document.getElementById('orbit-row').style.display = threeD ? '' : 'none';
    ['tracts-focus', 'tracts-hover'].forEach((id) =>
      map.setLayoutProperty(id, 'visibility', threeD ? 'none' : 'visible'));
    map.setLayoutProperty('tracts-3d', 'visibility', threeD ? 'visible' : 'none');
    // Pins drawn at ground level float over the columns, so 3D starts without them.
    const pins = document.getElementById('pins');
    pins.checked = !threeD;
    map.setLayoutProperty('projects', 'visibility', pins.checked ? 'visible' : 'none');
    baseOpacity = threeD ? 0.4 : 0.82;
    highlight(activeCell);
    if (threeD) {
      map.easeTo({ center: [-80.33, 25.71], pitch: 60, bearing: -28, zoom: 10, duration: 2200 });
      grow(1800);
    } else {
      setOrbit(false);
      map.easeTo({ center: [-80.42, 25.64], pitch: 0, bearing: 0, zoom: 9.4, duration: 1200 });
    }
  }

  function setOrbit(on) {
    orbiting = on;
    document.getElementById('orbit').checked = on;
    if (!on) return;
    let last = performance.now();
    const step = (now) => {
      if (!orbiting || removed) return;
      map.setBearing(map.getBearing() + (now - last) * 0.004);
      last = now;
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  const TIERS = ['Low', 'Medium', 'High'];

  /** The tract's legend square, named the same way as the color key. */
  function classBadge(p) {
    if (p.bi < 0) return '<span class="pp-badge"><i style="background:#2a2f37"></i>No residents: not scored</span>';
    const label = p.bi === GAP ? 'Gap: high need, low investment'
      : `${TIERS[p.r]} need · ${TIERS[p.i].toLowerCase()} investment`;
    return `<span class="pp-badge${p.bi === GAP ? ' gap' : ''}"><i style="background:${COLORS[p.r][p.i]}"></i>${label}</span>`;
  }

  function rowsHtml(rows) {
    return `<dl class="pp-rows">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`;
  }

  function popupHtml(p) {
    const need = p[metric.field];
    const tier = (t) => (p.bi >= 0 ? ` <span class="pp-tier">${TIERS[t].toLowerCase()} tier</span>` : '');
    return `<div class="pp-kicker">Census tract · GEOID ${p.GEOID}</div>` +
      `<h3 class="pp-title">${(p.name ?? p.GEOID).replace('Census Tract ', 'Tract ')}</h3>` +
      classBadge(p) +
      `<div class="pp-section">Need</div>` +
      rowsHtml([[metric.label.split(' (')[0], (need != null ? metric.fmt(need) : '—') + tier(p.r)]]) +
      `<div class="pp-section">Investment</div>` +
      rowsHtml([
        ['Per person', (p.investment_per_capita != null ? money(p.investment_per_capita) : '—') + tier(p.i)],
        ['Total', p.investment_total != null ? money(p.investment_total) : '—'],
        ['Projects touching tract', p.project_count ?? '—'],
        ['Residents', (p.population ?? 0).toLocaleString()],
      ]) +
      `<div class="pp-from">Need: ${SOURCES[metric.id].publisher.split(',')[0]} · Investment: SCALE-R inventory · Residents: ACS 2020–2024</div>`;
  }

  function projectPopupHtml(p) {
    const cost = Number(p.Estimated_);
    return `<div class="pp-kicker">Project · ${p.Implementa ?? ''}</div>` +
      `<h3 class="pp-title">${p.Project_Na}</h3>` +
      (p.New_15_25_ ? `<p class="pp-desc">${p.New_15_25_}</p>` : '') +
      rowsHtml([
        ['Type', p.Infrastruc || '—'],
        ['Status', p.Project__1 || '—'],
        ['Hazard', p.Disaster_F || '—'],
        ['Scale', p.Categories || '—'],
        ['Location', p.City || '—'],
        ['Cost', cost ? money(cost) : 'Not reported'],
      ]) +
      `<div class="pp-from">Source: SCALE-R inventory${p.Link_to_Da ? ` · <a href="${p.Link_to_Da}" target="_blank" rel="noreferrer">original document ↗</a>` : ''}</div>`;
  }

  map.on('load', async () => {
    tracts = await (await fetch(new URL('./data/tracts.geojson', import.meta.url))).json();
    if (removed) return;
    classify();

    const firstLabel = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;
    map.addSource('tracts', { type: 'geojson', data: tracts });
    map.addLayer({
      id: 'tracts-fill',
      type: 'fill',
      source: 'tracts',
      paint: {
        'fill-color': ['match', ['get', 'bi'],
          ...COLORS.flatMap((row, r) => row.flatMap((c, i) => [r * 3 + i, c])),
          '#2a2f37'],
        'fill-opacity': 0.82,
        'fill-opacity-transition': { duration: 250 },
      },
    }, firstLabel);
    map.addLayer({
      id: 'tracts-line', type: 'line', source: 'tracts',
      paint: { 'line-color': '#0e1116', 'line-width': 0.4, 'line-opacity': 0.6 },
    }, firstLabel);
    map.addLayer({
      id: 'tracts-focus', type: 'line', source: 'tracts', filter: ['==', ['get', 'bi'], NONE],
      paint: { 'line-color': '#ffffff', 'line-width': 1.2 },
    });
    map.addLayer({
      id: 'tracts-hover', type: 'line', source: 'tracts', filter: ['==', 'GEOID', ''],
      paint: { 'line-color': '#ffffff', 'line-width': 2.5 },
    });
    map.addSource('columns', { type: 'geojson', data: columns() });
    map.addLayer({
      id: 'tracts-3d',
      type: 'fill-extrusion',
      source: 'columns',
      layout: { visibility: 'none' },
      paint: {
        'fill-extrusion-color': colorExpr(null),
        'fill-extrusion-height': heightExpr(0),
        'fill-extrusion-opacity': 0.95,
        'fill-extrusion-vertical-gradient': true,
        'fill-extrusion-ambient-occlusion-intensity': 0.35,
      },
    });
    map.setFog({
      range: [1, 12],
      color: '#1a1f2b',
      'high-color': '#24324a',
      'horizon-blend': 0.12,
      'space-color': '#0b0e14',
      'star-intensity': 0.15,
    });

    const projects = await (await fetch(PROJECTS_URL)).json();
    if (removed) return;
    projects.features = projects.features.filter((f) => f.properties.Project__1 !== 'Planned');
    map.addSource('projects', { type: 'geojson', data: projects });
    map.addLayer({
      id: 'projects',
      type: 'circle',
      source: 'projects',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 1.6, 14, 5],
        'circle-color': '#ffffff',
        'circle-opacity': 0.75,
        'circle-stroke-color': '#0e1116',
        'circle-stroke-width': 0.5,
      },
    });

    map.on('mousemove', 'tracts-fill', (e) => {
      map.getCanvas().style.cursor = 'pointer';
      map.setFilter('tracts-hover', ['==', 'GEOID', e.features[0].properties.GEOID]);
    });
    map.on('mouseleave', 'tracts-fill', () => {
      map.getCanvas().style.cursor = '';
      map.setFilter('tracts-hover', ['==', 'GEOID', '']);
    });
    map.on('click', (e) => {
      const project = map.queryRenderedFeatures(e.point, { layers: ['projects'] })[0];
      if (project) {
        new mapboxgl.Popup({ className: 'gap-popup', maxWidth: '320px' })
          .setLngLat(e.lngLat).setHTML(projectPopupHtml(project.properties)).addTo(map);
        return;
      }
      const tract = map.queryRenderedFeatures(e.point, { layers: [is3d ? 'tracts-3d' : 'tracts-fill'] })[0];
      if (!tract) return;
      // Rendered features lose nested values; read the source record instead.
      const p = tracts.features.find((f) => f.properties.GEOID === tract.properties.GEOID).properties;
      new mapboxgl.Popup({ className: 'gap-popup', maxWidth: '320px' }).setLngLat(e.lngLat).setHTML(popupHtml(p)).addTo(map);
    });
    map.on('mousemove', 'tracts-3d', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'tracts-3d', () => { map.getCanvas().style.cursor = ''; });
    // Grabbing the map stops the orbit so it never fights the user.
    map.on('mousedown', () => setOrbit(false));
    map.on('touchstart', () => setOrbit(false));

    setView(true);
  });

  metricSelect.addEventListener('change', () => {
    metric = METRICS.find((m) => m.id === metricSelect.value);
    classify();
    if (is3d) grow(900);
  });
  document.getElementById('height').addEventListener('change', (e) => {
    heightField = e.target.value;
    classify();
    grow(900);
  });
  document.getElementById('view-2d').addEventListener('click', () => { if (is3d) setView(false); });
  document.getElementById('view-3d').addEventListener('click', () => { if (!is3d) setView(true); });
  document.getElementById('orbit').addEventListener('change', (e) => setOrbit(e.target.checked));
  document.querySelectorAll('.tabs button').forEach((btn) => btn.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b === btn));
    document.querySelectorAll('.tab-body').forEach((body) => { body.hidden = body.dataset.tab !== btn.dataset.tab; });
    const right = document.getElementById('right');
    right.classList.remove('closed');
    document.getElementById('toggle-right').textContent = '–';
  }));
  document.getElementById('toggle-right').addEventListener('click', (e) => {
    const closed = document.getElementById('right').classList.toggle('closed');
    e.target.textContent = closed ? '+' : '–';
    e.target.setAttribute('aria-label', closed ? 'Show panel' : 'Hide panel');
    e.target.setAttribute('aria-expanded', String(!closed));
  });
  document.getElementById('pins').addEventListener('change', (e) => {
    map.setLayoutProperty('projects', 'visibility', e.target.checked ? 'visible' : 'none');
  });
  document.getElementById('gap-only').addEventListener('change', (e) => {
    activeCell = e.target.checked ? GAP : null;
    highlight(activeCell);
  });

  return () => {
    removed = true;
    map.remove();
  };
}
