import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Same project file the live dashboard reads.
const PROJECTS_URL =
  'https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data/projects_merged_conf1.geojson';

const SLR_MAX = 6;
const HEAT_FROM = 125; // °F threshold at the start of the sweep (hottest surfaces only)
const HEAT_TO = 88; // °F threshold at the end (almost all land)

const MODES = {
  slr: {
    intro: 'Watch ocean-connected water spread inland as sea level rises from today\'s high tide to 6 ft above it, over the county\'s land and the resilience projects built on it.',
    howto: 'Blue is land that would be under ocean-connected water at the level shown; darker blue floods first. The bright band is the land that has just flooded. White dots are completed, ongoing and funded SCALE-R projects; the second counter tallies those that sit inside the flooded area at this level.',
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
  heat: {
    intro: 'Watch the hottest ground surfaces in Miami-Dade light up first, then spread until the county is saturated red, using a summer land surface temperature composite.',
    howto: 'The threshold falls from 125 °F to 88 °F. Every surface at or above the threshold turns red, and the hotter it is above the threshold, the deeper the red. Surfaces below the threshold stay gray. Read it as "where does extreme surface heat appear first", not as warming over time.',
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
  let heatMeta;

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
      $('stat2').textContent = fmtInt(s.projects);
      $('stat2-l').textContent = 'SCALE-R projects inside the flooded area';
    }
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
    $('sub').textContent = 'surfaces at or above this temperature are red';
    $('stat1').textContent = `${share}%`;
    $('stat1-l').textContent = 'of county land at or above this surface temperature';
    $('stat2').textContent = `${heatMeta.percentiles_f['50']} °F`;
    $('stat2-l').textContent = `county median (95th percentile ${heatMeta.percentiles_f['95']} °F)`;
  }

  // ---- Shared controls ------------------------------------------------------

  function render() {
    if (mode === 'slr') renderSlr(value); else renderHeat(value);
  }

  function sourceHtml(src) {
    return `<div class="kicker">${mode === 'slr' ? 'Sea level rise' : 'Surface heat'}</div><h3>${src.name}</h3>` +
      `<dl><dt>Publisher</dt><dd>${src.publisher}</dd><dt>Year</dt><dd>${src.year}</dd><dt>File</dt><dd>${src.file}</dd></dl>` +
      `<div style="margin-top:6px"><a href="${src.link}" target="_blank" rel="noreferrer">${src.link.replace(/^https?:\/\//, '')}</a></div>`;
  }

  function setMode(next) {
    mode = next;
    setPlaying(false);
    const m = MODES[mode];
    document.querySelectorAll('.seg button').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));
    map.setLayoutProperty('slr', 'visibility', mode === 'slr' ? 'visible' : 'none');
    map.setLayoutProperty('heat', 'visibility', mode === 'heat' ? 'visible' : 'none');
    Object.assign(slider, m.slider);
    // Sea level starts dry; heat starts at the hottest threshold.
    value = mode === 'slr' ? 0 : HEAT_FROM;
    slider.value = String(value);
    $('intro').textContent = m.intro;
    $('howto').textContent = m.howto;
    $('caveat').textContent = m.caveat;
    $('source').innerHTML = sourceHtml(m.source);
    $('ramp').style.background = mode === 'slr'
      ? 'linear-gradient(90deg, #0b3d6e, #1f78c1, #4fb3e8, #9be3ff)'
      : 'linear-gradient(90deg, rgba(120,128,140,0.5), #ffc478, #ff6e3c, #dc1e1e, #960014)';
    $('ramp-labels').innerHTML = mode === 'slr'
      ? '<span>Floods first (0 ft)</span><span>Floods last (6 ft)</span>'
      : '<span>Below threshold</span><span>Just above</span><span>14 °F+ above</span>';
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
    const atEnd = mode === 'slr' ? value >= max : value <= min;
    if (atEnd) value = mode === 'slr' ? min : max;
    let last = performance.now();
    const step = (now) => {
      if (!playing || removed) return;
      const delta = ((now - last) / MODES[mode].duration) * span;
      last = now;
      value = mode === 'slr' ? Math.min(max, value + delta) : Math.max(min, value - delta);
      slider.value = String(value);
      render();
      if ((mode === 'slr' && value >= max) || (mode === 'heat' && value <= min)) setPlaying(false);
      else requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  map.on('load', async () => {
    const [slr, heat] = await Promise.all([
      fetch(new URL('./data/slr.json', import.meta.url)).then((r) => r.json()),
      fetch(new URL('./data/heat.json', import.meta.url)).then((r) => r.json()),
    ]);
    if (removed) return;
    slrStats = slr.stats;
    heatMeta = heat;
    const firstLabel = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;

    map.addSource('heat', { type: 'image', url: new URL('./data/heat.png', import.meta.url).href, coordinates: heat.coordinates });
    map.addLayer({
      id: 'heat', type: 'raster', source: 'heat', layout: { visibility: 'none' },
      paint: { 'raster-color': heatColor(HEAT_FROM), 'raster-color-range': [0, 1], 'raster-resampling': 'nearest', 'raster-fade-duration': 0 },
    }, firstLabel);

    map.addSource('slr', { type: 'image', url: new URL('./data/slr.png', import.meta.url).href, coordinates: slr.coordinates });
    map.addLayer({
      id: 'slr', type: 'raster', source: 'slr',
      paint: { 'raster-color': slrColor(0), 'raster-color-range': [0, 1], 'raster-resampling': 'nearest', 'raster-fade-duration': 0 },
    }, firstLabel);

    const projects = await (await fetch(PROJECTS_URL)).json();
    if (removed) return;
    projects.features = projects.features.filter((f) => f.properties.Project__1 !== 'Planned');
    map.addSource('projects', { type: 'geojson', data: projects });
    map.addLayer({
      id: 'projects', type: 'circle', source: 'projects',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 1.4, 14, 4.5],
        'circle-color': '#ffffff', 'circle-opacity': 0.7,
        'circle-stroke-color': '#0e1116', 'circle-stroke-width': 0.4,
      },
    });

    setMode('slr');
    setTimeout(() => { if (!removed) setPlaying(true); }, 800);
  });

  document.querySelectorAll('.seg button').forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));
  $('play').addEventListener('click', () => setPlaying(!playing));
  slider.addEventListener('input', () => {
    setPlaying(false);
    value = Number(slider.value);
    render();
  });
  $('pins').addEventListener('change', (e) => map.setLayoutProperty('projects', 'visibility', e.target.checked ? 'visible' : 'none'));

  return () => {
    removed = true;
    map.remove();
  };
}
