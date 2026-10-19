import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Same project file the live dashboard reads.
const PROJECTS_URL =
  'https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data/projects_merged_conf1.geojson';

const SLR_MAX = 6;
const HEAT_FROM = 125; // °F threshold at the start of the sweep (hottest surfaces only)
const HEAT_TO = 88; // °F threshold at the end (almost all land)
const SURGE_MAX = 5.3; // slider end, just past Category 5 so its water settles before the stop

// Project symbols. A project is "reached" once the hazard covers its location; it then
// rises (column) or swells (dot), flashes white and settles to a color that says whether
// the project is built to address that hazard.
const RESPONDS = {
  slr: ['Flooding', 'Coastal Hazards', 'Storms & Hurricanes', 'Multi-Hazard'],
  surge: ['Flooding', 'Coastal Hazards', 'Storms & Hurricanes', 'Multi-Hazard'],
  heat: ['Extreme Heat', 'Multi-Hazard'],
};
// Warm colors read against the blue water and purple surge, cool ones against the red heat.
const PIN_COLORS = {
  slr: { idle: '#7d8592', responds: '#ffb627', gap: '#ff3d81' },
  surge: { idle: '#7d8592', responds: '#ffb627', gap: '#ff3d81' },
  heat: { idle: '#7d8592', responds: '#3fd8ff', gap: '#b98cff' },
};
// Hexagon footprints are fixed in meters, so a narrower set takes over when zoomed in.
const COLUMN_LAYERS = [
  { id: 'project-columns', radiusM: 200, maxzoom: 11.5 },
  { id: 'project-columns-near', radiusM: 60, minzoom: 11.5 },
];
const COLUMN_IDLE_M = 250; // height before the hazard arrives
const COLUMN_FULL_M = 1600; // height once reached (at zoom 9; scaled down when zoomed in)
// How far past a project's own level the "just reached" flash lasts: 0.6 ft of water,
// matching the bright band on the water, 0.6 of a category, or 4 °F of threshold.
const REACH_SPAN = { slr: 0.6, surge: 0.6, heat: 4 };
// Each surge category's water fades in over the 0.3 before this point and projects are
// reached at it, so the label flips to "Category N" (at N - 0.5) just before its water.
const SURGE_LEAD = 0.2;
const DRY = 99; // flood level for projects still dry at 6 ft or in a Category 5 surge

/** Reads an image source's pixels so a location can look up the value drawn under it (red channel by default). */
async function rasterSampler(url, [[west, north], [east], [, south]]) {
  const img = new Image();
  img.src = url;
  await img.decode();
  const canvas = document.createElement('canvas');
  canvas.width = img.width;
  canvas.height = img.height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  const { data } = ctx.getImageData(0, 0, img.width, img.height);
  // Mapbox stretches image sources linearly in Web Mercator, so rows follow Mercator y.
  const mercY = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const top = mercY(north);
  const span = top - mercY(south);
  return (lng, lat, channel = 0) => {
    const col = Math.floor(((lng - west) / (east - west)) * img.width);
    const row = Math.floor(((top - mercY(lat)) / span) * img.height);
    if (col < 0 || row < 0 || col >= img.width || row >= img.height) return 0;
    return data[(row * img.width + col) * 4 + channel];
  };
}

/** A small hexagon around a point, for fill-extrusion columns (which need polygons). */
function hexagon([lng, lat], radiusM) {
  const dLat = radiusM / 111320;
  const dLng = dLat / Math.cos((lat * Math.PI) / 180);
  const ring = [];
  for (let i = 0; i <= 6; i += 1) {
    const a = (Math.PI / 3) * (i % 6) + Math.PI / 6;
    ring.push([lng + dLng * Math.cos(a), lat + dLat * Math.sin(a)]);
  }
  return { type: 'Polygon', coordinates: [ring] };
}

const MODES = {
  slr: {
    label: 'Sea level rise',
    start: 0,    intro: 'Watch ocean-connected water spread inland as sea level rises from today\'s high tide to 6 ft above it, over the county\'s land and the resilience projects built on it.',
    howto: 'Blue is land that would be under ocean-connected water at the level shown; darker blue floods first. The bright band is the land that has just flooded. Each column is a completed, ongoing or funded SCALE-R project. It stays short and gray while dry, then rises and flashes when the water reaches it, settling amber if the project addresses flooding, coastal hazards or storms, or pink if it was built for something else. The second counter tallies the projects inside the flooded area.',
    legend: { responds: 'Reached; addresses flooding, coastal hazards or storms', gap: 'Reached; built for another hazard', idle: 'Not yet reached' },
    caveat: 'These are water levels, not years. When Miami-Dade reaches each level depends on the emissions scenario (see NOAA\'s 2022 Sea Level Rise Technical Report); that timeline is not shown here. Low-lying areas not connected to the ocean are excluded. Shown on a 30 m grid; areas match the team\'s tract processing within 0.1%.',
    slider: { min: 0, max: SLR_MAX, step: 0.05 },
    duration: 14000,
    source: {
      name: 'Sea Level Rise Inundation Data, Southeast Florida (FL_SE)',
      publisher: 'NOAA Office for Coastal Management',
      year: 'Ocean-connected inundation layers, 0–6 ft above MHHW in 0.5 ft steps; extracted for this page Oct 2026',
      file: 'FL_SE_slr_final_dist.gpkg → slr.png',
      link: 'https://coast.noaa.gov/slrdata/',
    },
  },
  surge: {
    label: 'Storm surge',
    start: 0,
    intro: 'Watch hurricane storm surge spread inland as the storm strengthens from Category 1 to Category 5, over the county\'s land and the resilience projects built on it.',
    howto: 'Purple is land the surge would cover in a storm of the category shown; darker purple floods even in weaker storms. The bright band is the land that has just been added. Each column is a completed, ongoing or funded SCALE-R project. It stays short and gray while dry, then rises and flashes when the surge reaches it, settling amber if the project addresses flooding, coastal hazards or storms, or pink if it was built for something else. Hover a column for the surge depth there in a Category 5 storm.',
    legend: { responds: 'Reached; addresses flooding, coastal hazards or storms', gap: 'Reached; built for another hazard', idle: 'Not yet reached' },
    caveat: 'This is NHC\'s worst case for each category (the Maximum of MOMs): at every spot, the highest surge from thousands of hypothetical storms of that strength arriving at high tide. No single hurricane floods all of it at once. Waves, rainfall and river flooding are not included, and NHC intends the maps for community-level, not parcel-level, use. A few cells (under 0.2% of the flooded land) fall inside one category\'s envelope but not the next; they are kept flooded here. Shown on a 30 m grid from the 10 m source; land shares match the team\'s tract processing.',
    slider: { min: 0, max: SURGE_MAX, step: 0.02 },
    duration: 12000,
    source: {
      name: 'National Storm Surge Hazard Maps v4, Maximum of MOMs (high tide)',
      publisher: 'NOAA National Hurricane Center, Storm Surge Unit',
      year: 'v4 reprocessed June 2026 (fixes a South Florida error in the 2025 release); Categories 1–5',
      file: 'us_Category{1–5}_MOM_Inundation_HIGH.tif → surge.png (scripts/build_surge_animation.py)',
      link: 'https://www.nhc.noaa.gov/nationalsurge/',
    },
  },
  heat: {
    label: 'Surface heat',
    start: HEAT_FROM,
    intro: 'Watch the hottest ground surfaces in Miami-Dade light up first, then spread until the county is saturated red, using a summer land surface temperature composite.',
    howto: 'The threshold falls from 125 °F to 88 °F. Every surface at or above the threshold turns red, and the hotter it is above the threshold, the deeper the red. Surfaces below the threshold stay gray. Each column is a project; it rises when the threshold drops to the surface temperature at its location, settling cyan if it addresses extreme heat and violet if it does not. Read it as "where does extreme surface heat appear first", not as warming over time.',
    legend: { responds: 'Reached; addresses extreme heat', gap: 'Reached; built for another hazard', idle: 'Not yet reached' },
    caveat: 'Land surface temperature is how hot the ground and roofs get, not the air temperature people feel. Values are the median of clear-sky summer daytime Landsat passes (about 10:30–11:00 am local), so they describe a typical summer morning, not a heat wave. The processing script for this composite is not yet in the repository; source details come from the file\'s own metadata.',
    slider: { min: HEAT_TO, max: HEAT_FROM, step: 0.25 },
    duration: 12000,
    source: {
      name: 'Land surface temperature, median composite',
      publisher: 'USGS / NASA Landsat 8 and 9, composite prepared by the SCALE-R team',
      year: 'June–September, 2021–2024 (summer median); 30 m source, shown at 60 m',
      file: 'output/lst/lst_composite_f.tif → heat.png',
      link: 'https://www.usgs.gov/landsat-missions',
    },
  },
};

/** Builds the map into the markup already on the page; returns a cleanup function. */
export function mount() {
  let removed = false;
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/dark-v11',
    center: [-80.3, 25.68],
    zoom: 9.7,
    pitch: 40,
    bearing: -12,
    padding: { left: 360 },
    antialias: true,
  });
  map.addControl(new mapboxgl.NavigationControl(), 'top-right');
  if (import.meta.env.DEV) window.__map = map; // lets the review screenshots probe layer state

  const $ = (id) => document.getElementById(id);
  const slider = $('slider');
  let mode = 'slr';
  let value = 0;
  let playing = false;
  let slrStats = [];
  let surgeStats = [];
  let heatMeta;
  let pinStyle = 'columns';
  let projectCounts = null; // { reached, responds } for the current frame, from the sampled projects
  let projectFeatures = [];
  const stacks = new Map(); // location key -> properties of every project drawn at that point

  function fmtInt(n) { return Math.round(n).toLocaleString(); }

  // ---- Sea level rise -------------------------------------------------------

  // slr.png stores 18 * (1 + 2 * first flooded level in ft): code v floods at (v - 1) / 2 ft.
  // The x18 spacing keeps Mapbox's 256-entry colour lookup from blurring levels together.
  const SLR_CODE_STEP = 18;
  const SLR_COLORS = ['#0b3d6e', '#1f78c1', '#4fb3e8', '#9be3ff'];

  function slrColor(level) {
    // ['step', input, colour for v < 0.5, 0.5, colour for v = 1, 1.5, colour for v = 2, ...]
    const expr = ['step', ['/', ['*', ['raster-value'], 255], SLR_CODE_STEP], 'rgba(0, 0, 0, 0)'];
    for (let v = 1; v <= 1 + 2 * SLR_MAX; v += 1) {
      const ft = (v - 1) / 2;
      const reveal = Math.max(0, Math.min(1, 1 + (level - ft) / 0.5)); // fades in over the half foot before its level
      // The newest water is drawn bright, then settles to its depth color.
      const fresh = level - ft < 0.6;
      const color = fresh ? '#bdf1ff' : SLR_COLORS[Math.min(3, Math.floor(ft / 1.5))];
      expr.push(v - 0.5, hexA(color, reveal * (fresh ? 0.95 : 0.8)));
    }
    return expr;
  }

  function hexA(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a.toFixed(3)})`;
  }

  function renderSlr(level) {
    map.setPaintProperty('slr', 'raster-color', slrColor(level));
    const s = slrStats[Math.max(0, Math.min(slrStats.length - 1, Math.floor(level * 2 + 1e-6)))];
    $('big').textContent = `+${level.toFixed(1)} ft`;
    $('sub').textContent = 'above today\'s mean higher high water (MHHW)';
    if (s) {
      $('stat1').textContent = `${s.km2.toLocaleString()} km²`;
      $('stat1-l').textContent = `of county land under ocean-connected water (${s.pct_land}%) at +${s.ft.toFixed(1)} ft`;
      $('stat2').textContent = fmtInt(projectCounts ? projectCounts.reached : s.projects);
      $('stat2-l').textContent = projectCounts
        ? `SCALE-R projects inside the flooded area; ${fmtInt(projectCounts.responds)} address flood hazards`
        : 'SCALE-R projects inside the flooded area';
    }
  }

  // ---- Storm surge ----------------------------------------------------------

  // surge.png red = 40 * first category that floods the pixel; green = depth class at Category 5.
  const SURGE_CODE_STEP = 40;
  const SURGE_COLORS = ['#2b1a66', '#4b2fa3', '#7653d6', '#a387ef', '#cdbcff'];

  function surgeColor(level) {
    const expr = ['step', ['/', ['*', ['raster-value'], 255], SURGE_CODE_STEP], 'rgba(0, 0, 0, 0)'];
    for (let cat = 1; cat <= 5; cat += 1) {
      const at = cat - SURGE_LEAD;
      const reveal = Math.max(0, Math.min(1, 1 + (level - at) / 0.3));
      const fresh = level - at < 0.6;
      const color = fresh ? '#efe6ff' : SURGE_COLORS[cat - 1];
      expr.push(cat - 0.5, hexA(color, reveal * (fresh ? 0.95 : 0.8)));
    }
    return expr;
  }

  function surgeCategory(level) {
    return Math.max(0, Math.min(5, Math.round(level)));
  }

  function renderSurge(level) {
    map.setPaintProperty('surge', 'raster-color', surgeColor(level));
    const cat = surgeCategory(level);
    const s = surgeStats[cat - 1];
    $('big').textContent = cat ? `Category ${cat}` : 'No storm';
    $('sub').textContent = 'hurricane, worst-case surge arriving at high tide';
    $('stat1').textContent = s ? `${s.km2.toLocaleString()} km²` : '0 km²';
    $('stat1-l').textContent = s
      ? `of county land under storm surge (${s.pct_land}%) in Category ${cat}`
      : 'of county land under storm surge';
    $('stat2').textContent = fmtInt(projectCounts ? projectCounts.reached : (s?.projects ?? 0));
    $('stat2-l').textContent = projectCounts
      ? `SCALE-R projects inside the surge zone; ${fmtInt(projectCounts.responds)} address flood or storm hazards`
      : 'SCALE-R projects inside the surge zone';
  }

  function depthLabel(depthClass) {
    if (depthClass === 1) return 'under 1 ft';
    if (depthClass === 21) return 'more than 20 ft';
    return `${depthClass - 1}–${depthClass} ft`;
  }

  // ---- Surface heat ---------------------------------------------------------

  /** Converts °F to the 0..1 raster value packed by build_animation_data.py. */
  function heatValue(f) {
    const { min_f: lo, max_f: hi } = heatMeta.encoding;
    const clamped = Math.max(lo, Math.min(hi, f));
    return ((clamped - lo) / (hi - lo) * 254 + 1) / 255;
  }

  function heatColor(threshold) {
    const t = heatValue(threshold);
    const eps = 0.5 / 255;
    // Gray below the threshold; at and above it, reds that deepen with the excess heat.
    return ['interpolate', ['linear'], ['raster-value'],
      0, 'rgba(0, 0, 0, 0)',
      1 / 255, 'rgba(120, 128, 140, 0.18)',
      Math.max(t - eps, 1.5 / 255), 'rgba(120, 128, 140, 0.18)',
      t, 'rgba(255, 196, 120, 0.75)',
      Math.min(heatValue(threshold + 6), 1 - 2 * eps), 'rgba(255, 110, 60, 0.85)',
      Math.min(heatValue(threshold + 14), 1 - eps), 'rgba(220, 30, 30, 0.92)',
      1, 'rgba(150, 0, 20, 0.95)',
    ];
  }

  function renderHeat(threshold) {
    map.setPaintProperty('heat', 'raster-color', heatColor(threshold));
    const share = heatMeta.share_at_or_above[String(Math.round(threshold))] ?? 0;
    $('big').textContent = `≥ ${threshold.toFixed(0)} °F`;
    $('sub').textContent = `surfaces at or above this temperature are red · county median ${heatMeta.percentiles_f['50']} °F`;
    $('stat1').textContent = `${share}%`;
    $('stat1-l').textContent = 'of county land at or above this surface temperature';
    if (projectCounts) {
      $('stat2').textContent = fmtInt(projectCounts.reached);
      $('stat2-l').textContent = `SCALE-R projects on surfaces this hot; ${fmtInt(projectCounts.responds)} address extreme heat`;
    } else {
      $('stat2').textContent = `${heatMeta.percentiles_f['50']} °F`;
      $('stat2-l').textContent = `county median (95th percentile ${heatMeta.percentiles_f['95']} °F)`;
    }
  }

  // ---- Projects -------------------------------------------------------------

  /** Negative before the hazard reaches a project, 0 the moment it does, 1 once its flash has settled. */
  function reachOf(p) {
    if (mode === 'slr') return (value - p.slr_ft) / REACH_SPAN.slr;
    if (mode === 'surge') return (value - p.surge_cat + SURGE_LEAD) / REACH_SPAN.surge;
    return (p.lst_f - value) / REACH_SPAN.heat;
  }

  function reachExpr() {
    if (mode === 'slr') return ['/', ['-', value, ['get', 'slr_ft']], REACH_SPAN.slr];
    if (mode === 'surge') return ['/', ['-', value + SURGE_LEAD, ['get', 'surge_cat']], REACH_SPAN.surge];
    return ['/', ['-', ['get', 'lst_f'], value], REACH_SPAN.heat];
  }

  function pinColor() {
    const c = PIN_COLORS[mode];
    const reach = reachExpr();
    const settle = (to) => ['interpolate', ['linear'], reach, 0, '#ffffff', 1, to];
    return ['case', ['<', reach, 0], c.idle, ['get', `responds_${mode}`], settle(c.responds), settle(c.gap)];
  }

  function columnHeight() {
    // Rises past its final height as the hazard arrives, then settles.
    const h = ['interpolate', ['linear'], reachExpr(), 0, COLUMN_IDLE_M, 0.4, COLUMN_FULL_M * 1.3, 1, COLUMN_FULL_M];
    // Shorter when zoomed in, where the footprints are wide enough to read on their own.
    return ['interpolate', ['linear'], ['zoom'], 9, h, 14, ['*', h, 0.15]];
  }

  function dotRadius() {
    const r = ['interpolate', ['linear'], reachExpr(), 0, 2, 0.4, 5.5, 1, 3.5];
    return ['interpolate', ['linear'], ['zoom'], 9, r, 14, ['*', r, 2.2]];
  }

  function renderProjects() {
    if (!projectFeatures.length) return;
    let reached = 0;
    let responds = 0;
    for (const p of projectFeatures) {
      if (reachOf(p) < 0) continue;
      reached += 1;
      if (p[`responds_${mode}`]) responds += 1;
    }
    projectCounts = { reached, responds };
    for (const { id } of COLUMN_LAYERS) {
      map.setPaintProperty(id, 'fill-extrusion-color', pinColor());
      map.setPaintProperty(id, 'fill-extrusion-height', columnHeight());
    }
    map.setPaintProperty('projects', 'circle-color', pinColor());
    map.setPaintProperty('projects', 'circle-radius', dotRadius());
    map.setLayoutProperty('projects', 'circle-sort-key', ['case', ['<', reachExpr(), 0], 0, 1]);
  }

  function showPins() {
    if (!map.getLayer('projects')) return;
    const on = $('pins').checked;
    for (const { id } of COLUMN_LAYERS) map.setLayoutProperty(id, 'visibility', on && pinStyle === 'columns' ? 'visible' : 'none');
    map.setLayoutProperty('projects', 'visibility', on && pinStyle === 'dots' ? 'visible' : 'none');
  }

  function legendHtml() {
    const c = PIN_COLORS[mode];
    const { legend } = MODES[mode];
    return ['responds', 'gap', 'idle']
      .map((k) => `<div><span class="sw${k === 'idle' ? ' idle' : ''}" style="background:${c[k]}"></span>${legend[k]}</div>`)
      .join('');
  }

  function projectTooltip(p) {
    const surge = p.surge_cat === DRY
      ? 'Dry even in a Category 5 surge'
      : `Surge reaches it from Category ${p.surge_cat}${p.surge_cat5 ? `; ${depthLabel(p.surge_cat5)} deep in Category 5` : ''}`;
    const exposure = {
      slr: p.slr_ft === DRY ? 'Dry through +6 ft' : `Floods at +${p.slr_ft.toFixed(1)} ft`,
      surge,
      heat: p.lst_f > 0 ? `Surface ${Math.round(p.lst_f)} °F` : 'No surface temperature',
    }[mode];
    const describe = (q) => `<b>${q.Project_Na || 'Unnamed project'}</b><br>${q.Disaster_F || 'Hazard not recorded'} · ${q.Project__1}`;
    const group = stacks.get(p.loc) ?? [p];
    if (group.length === 1) return `${describe(p)}<br>${exposure}`;
    // Projects at one point share its exposure but can differ in whether they respond to it.
    const c = PIN_COLORS[mode];
    const items = group.map((q) => {
      const color = reachOf(q) < 0 ? c.idle : q[`responds_${mode}`] ? c.responds : c.gap;
      return `<li><span class="sw" style="background:${color}"></span><div>${describe(q)}</div></li>`;
    });
    return `<div class="stack-head">${group.length} projects at this location · ${exposure}</div><ul>${items.join('')}</ul>`;
  }

  // ---- Shared controls ------------------------------------------------------

  function render() {
    renderProjects();
    if (mode === 'slr') renderSlr(value);
    else if (mode === 'surge') renderSurge(value);
    else renderHeat(value);
  }

  function sourceHtml(src) {
    return `<div class="kicker">${MODES[mode].label}</div><h3>${src.name}</h3>` +
      `<dl><dt>Publisher</dt><dd>${src.publisher}</dd><dt>Year</dt><dd>${src.year}</dd><dt>File</dt><dd>${src.file}</dd></dl>` +
      `<div style="margin-top:6px"><a href="${src.link}" target="_blank" rel="noreferrer">${src.link.replace(/^https?:\/\//, '')}</a></div>`;
  }

  function setMode(next) {
    mode = next;
    setPlaying(false);
    const m = MODES[mode];
    document.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));
    for (const id of Object.keys(MODES)) map.setLayoutProperty(id, 'visibility', id === mode ? 'visible' : 'none');
    Object.assign(slider, m.slider);
    // Sea level and surge start dry; heat starts at the hottest threshold.
    value = m.start;
    slider.value = String(value);
    $('intro').textContent = m.intro;
    $('howto').textContent = m.howto;
    $('legend').innerHTML = legendHtml();
    $('caveat').textContent = m.caveat;
    $('source').innerHTML = sourceHtml(m.source);
    $('ramp').style.background = {
      slr: 'linear-gradient(90deg, #0b3d6e, #1f78c1, #4fb3e8, #9be3ff)',
      surge: `linear-gradient(90deg, ${SURGE_COLORS.join(', ')})`,
      heat: 'linear-gradient(90deg, rgba(120,128,140,0.5), #ffc478, #ff6e3c, #dc1e1e, #960014)',
    }[mode];
    $('ramp-labels').innerHTML = {
      slr: '<span>Floods first (0 ft)</span><span>Floods last (6 ft)</span>',
      surge: '<span>Floods in Category 1</span><span>Only in Category 5</span>',
      heat: '<span>Below threshold</span><span>Just above</span><span>14 °F+ above</span>',
    }[mode];
    render();
  }

  function setPlaying(on) {
    playing = on;
    $('play').textContent = on ? '❚❚' : '▶';
    $('play').setAttribute('aria-label', on ? 'Pause' : 'Play');
    if (!on) return;
    const { min, max } = MODES[mode].slider;
    const span = max - min;
    // Restart from the beginning if already at the end.
    // Heat sweeps downward; the water hazards rise.
    const rising = mode !== 'heat';
    const atEnd = rising ? value >= max : value <= min;
    if (atEnd) value = rising ? min : max;
    let last = performance.now();
    const step = (now) => {
      if (!playing || removed) return;
      const delta = ((now - last) / MODES[mode].duration) * span;
      last = now;
      value = rising ? Math.min(max, value + delta) : Math.max(min, value - delta);
      slider.value = String(value);
      render();
      if (rising ? value >= max : value <= min) setPlaying(false);
      else requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  map.on('load', async () => {
    const [slr, surge, heat] = await Promise.all([
      fetch(new URL('./data/slr.json', import.meta.url)).then((r) => r.json()),
      fetch(new URL('./data/surge.json', import.meta.url)).then((r) => r.json()),
      fetch(new URL('./data/heat.json', import.meta.url)).then((r) => r.json()),
    ]);
    if (removed) return;
    slrStats = slr.stats;
    surgeStats = surge.stats;
    heatMeta = heat;
    const firstLabel = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;

    map.addSource('heat', { type: 'image', url: new URL('./data/heat.png', import.meta.url).href, coordinates: heat.coordinates });
    map.addLayer({
      id: 'heat', type: 'raster', source: 'heat', layout: { visibility: 'none' },
      paint: { 'raster-color': heatColor(HEAT_FROM), 'raster-color-range': [0, 1], 'raster-resampling': 'nearest', 'raster-fade-duration': 0 },
    }, firstLabel);

    // Only the red channel holds the category; green carries the Category 5 depth.
    map.addSource('surge', { type: 'image', url: new URL('./data/surge.png', import.meta.url).href, coordinates: surge.coordinates });
    map.addLayer({
      id: 'surge', type: 'raster', source: 'surge', layout: { visibility: 'none' },
      paint: {
        'raster-color': surgeColor(0), 'raster-color-mix': [1, 0, 0, 0], 'raster-color-range': [0, 1],
        'raster-resampling': 'nearest', 'raster-fade-duration': 0,
      },
    }, firstLabel);

    map.addSource('slr', { type: 'image', url: new URL('./data/slr.png', import.meta.url).href, coordinates: slr.coordinates });
    map.addLayer({
      id: 'slr', type: 'raster', source: 'slr',
      paint: { 'raster-color': slrColor(0), 'raster-color-range': [0, 1], 'raster-resampling': 'nearest', 'raster-fade-duration': 0 },
    }, firstLabel);

    const [projects, slrAt, surgeAt, heatAt] = await Promise.all([
      fetch(PROJECTS_URL).then((r) => r.json()),
      rasterSampler(new URL('./data/slr.png', import.meta.url).href, slr.coordinates),
      rasterSampler(new URL('./data/surge.png', import.meta.url).href, surge.coordinates),
      rasterSampler(new URL('./data/heat.png', import.meta.url).href, heat.coordinates),
    ]);
    if (removed) return;
    const { min_f: lo, max_f: hi } = heat.encoding;
    projects.features = projects.features.filter((f) => f.properties.Project__1 !== 'Planned');
    for (const f of projects.features) {
      const [lng, lat] = f.geometry.coordinates;
      const p = f.properties;
      const slrCode = slrAt(lng, lat);
      const heatCode = heatAt(lng, lat);
      p.slr_ft = slrCode ? (slrCode / SLR_CODE_STEP - 1) / 2 : DRY;
      p.surge_cat = surgeAt(lng, lat) / SURGE_CODE_STEP || DRY;
      p.surge_cat5 = surgeAt(lng, lat, 1);
      p.lst_f = heatCode ? lo + ((heatCode - 1) / 254) * (hi - lo) : -DRY;
      p.responds_slr = RESPONDS.slr.includes(p.Disaster_F);
      p.responds_surge = RESPONDS.surge.includes(p.Disaster_F);
      p.responds_heat = RESPONDS.heat.includes(p.Disaster_F);
      p.loc = `${lng.toFixed(6)},${lat.toFixed(6)}`;
      if (!stacks.has(p.loc)) stacks.set(p.loc, []);
      stacks.get(p.loc).push(p);
    }
    projectFeatures = projects.features.map((f) => f.properties);
    map.addSource('projects', { type: 'geojson', data: projects });
    // Flat alternative: a dark outline keeps each dot separate from the water or heat under it.
    map.addLayer({
      id: 'projects', type: 'circle', source: 'projects', layout: { visibility: 'none' },
      paint: { 'circle-stroke-color': '#0e1116', 'circle-stroke-width': 1.2 },
    });
    for (const { id, radiusM, ...zooms } of COLUMN_LAYERS) {
      map.addSource(id, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: projects.features.map((f) => ({ ...f, geometry: hexagon(f.geometry.coordinates, radiusM) })),
        },
      });
      map.addLayer({
        id, type: 'fill-extrusion', source: id, ...zooms,
        paint: { 'fill-extrusion-base': 0, 'fill-extrusion-opacity': 0.95, 'fill-extrusion-vertical-gradient': true },
      });
    }

    const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, className: 'pin-tip' });
    for (const layer of ['projects', ...COLUMN_LAYERS.map((l) => l.id)]) {
      map.on('mousemove', layer, (e) => {
        map.getCanvas().style.cursor = 'pointer';
        popup.setLngLat(e.lngLat).setHTML(projectTooltip(e.features[0].properties)).addTo(map);
      });
      map.on('mouseleave', layer, () => {
        map.getCanvas().style.cursor = '';
        popup.remove();
      });
    }

    showPins();
    setMode('slr');
    setTimeout(() => { if (!removed) setPlaying(true); }, 800);
  });

  document.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));
  document.querySelectorAll('[data-pins]').forEach((b) => b.addEventListener('click', () => {
    pinStyle = b.dataset.pins;
    document.querySelectorAll('[data-pins]').forEach((x) => x.classList.toggle('on', x === b));
    showPins();
  }));
  $('play').addEventListener('click', () => setPlaying(!playing));
  slider.addEventListener('input', () => {
    setPlaying(false);
    value = Number(slider.value);
    render();
  });
  $('pins').addEventListener('change', showPins);

  return () => {
    removed = true;
    map.remove();
  };
}
