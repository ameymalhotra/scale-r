import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import {
  SETTINGS, benefitPerDollar, elevate, makeContext, picksForIds, pointLineDist, seawall, seawallTileKeys, snapToShore,
  tilesForBox, toUtm17, topHomes,
} from './whatIfEngine.js';
import { loadJson, tileStore } from './whatIfData.js';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Admin only (D-095, D-200). Engine: whatIfEngine.js, a copy of Modules B and C checked against Python
// (whatIfParity.test.js). Data: "Modelling Data from Web/scripts/benefit/export_what_if.py" (D-199).
const FT = 0.3048;
const SHORT_WALL_FT = 200;
const MAX_SHORE_M = 500;
const BUILDING_ZOOM = 13;
const MAX_VIEW_TILES = 36;
const DAMAGE_STOPS = [[0, '#d9dde1'], [100, '#fdd49e'], [1000, '#fc8d59'], [10000, '#d7301f'], [50000, '#7f0000']];
const EMPTY = { type: 'FeatureCollection', features: [] };

const fmt = (n) => (n == null || Number.isNaN(n) ? 'n/a' : Math.round(n).toLocaleString('en-US'));
function money(v) {
  if (v == null || Number.isNaN(v)) return 'n/a';
  const a = Math.abs(v);
  const s = v < 0 ? '-' : '';
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e4) return `${s}$${Math.round(a / 1e3).toLocaleString('en-US')}k`;
  return `${s}$${Math.round(a).toLocaleString('en-US')}`;
}
const ratio = (v) => (Number.isFinite(v) ? `$${v.toFixed(2)}` : 'n/a');

function aboutHtml() {
  return `
    <p>For every building that floods in at least one storm today, the model knows the water level in five storms (from the 10-year to the 500-year storm, FEMA's 2027 flood study), the building's ground and first-floor height, its value and its type. Standard US Army Corps of Engineers damage curves turn water depth above the floor into dollars of damage, and the five storms are combined into an <b>expected yearly damage</b> (a yearly average over many years). A <b>seawall</b> removes the sea water, in every storm that stays below its crest, for buildings whose straight line to the shore crosses the wall and whose ground is below the crest. <b>Raising a home</b> lifts its first floor. The damage avoided is the yearly damage before minus after. <b>Benefit per dollar</b> is the damage avoided over the project's life (50 years for a seawall, 30 for raising a home, FEMA), discounted at FEMA's 7% (3% shown as a sensitivity), divided by the cost plus upkeep (1% of the cost a year for a seawall, an assumption).</p>
    <p><b>Main limits.</b> Tidal and king-tide flooding are not included, so seawalls are probably understated. Rainfall flooding is modelled only in the C-8 and C-9 basins, so inland benefits are probably understated. Water going around the ends of a wall is not modelled, so short walls look better than they are. Floor heights are mostly estimated. No sea level rise. Damage counts buildings only, not roads or utilities. Property value changes are shown separately and kept out of benefit per dollar. The browser engine matches the Python model to within 0.001% on every Part 2 test project. Details: "Modelling Data from Web/reports/benefit/typical_projects_part2.md" and "admin_what_if_part2.md".</p>`;
}

/** Builds the view into the markup already on the page; returns a cleanup function. */
export function mount() {
  let removed = false;
  const $ = (id) => document.getElementById(id);
  const mobile = () => window.innerWidth <= 768;
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/light-v11',
    center: [-80.3, 25.72],
    zoom: 9.6,
    padding: mobile() ? { bottom: window.innerHeight * 0.5 } : { left: 410 },
    doubleClickZoom: true,
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');

  let man = null; let ctx = null; let store = null; let dryStore = null; let shoreUtm = []; let shoreLL = []; let examples = [];
  let emode = 'area';
  let drawing = null;           // {kind: 'wall' | 'area', pts: [[lon, lat], ...]}
  const projects = [];
  let sel = -1;
  let counter = 0;
  let mapReady = false;
  const tileFeatures = new Map();
  const dryFeatures = new Map();
  const dragTimes = [];
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, className: 'tip', offset: 8 });
  const infoPopup = new mapboxgl.Popup({ closeButton: true, closeOnClick: true, className: 'tip', offset: 10, maxWidth: '280px' });

  $('about').innerHTML = aboutHtml();
  const status = (t) => { $('status').textContent = t || ''; };

  // ---------------------------------------------------------------- data
  const ready = (async () => {
    status('Loading the flood data…');
    const [m, curves, shore, ex] = await Promise.all([
      loadJson('manifest.json'), loadJson('curves.json'), loadJson('shoreline.geojson'),
      loadJson('examples.json').catch(() => []),
    ]);
    man = m; ctx = makeContext(m, curves); store = tileStore(m); dryStore = tileStore(m, undefined, m.dry_tiles); examples = ex;
    shoreLL = shore.features.flatMap((f) => (f.geometry.type === 'LineString' ? [f.geometry.coordinates] : f.geometry.coordinates));
    shoreUtm = shoreLL.map((line) => line.map(([lo, la]) => toUtm17(lo, la)));
    status('');
    return { shore };
  })();
  ready.catch((e) => {
    if (!removed) $('results').innerHTML = `<p class="warn">The flood data could not be loaded (${e.message}). Sign in again, or ask an admin.</p>`;
    status('');
  });

  // ---------------------------------------------------------------- map layers
  map.on('load', async () => {
    let geo;
    try { geo = await ready; } catch { return; }
    if (removed) return;
    const basins = await loadJson('rain_basins.geojson').catch(() => EMPTY);
    map.addSource('wi-grid', { type: 'geojson', data: gridGeo() });
    map.addSource('wi-buildings', { type: 'geojson', data: EMPTY });
    map.addSource('wi-dry', { type: 'geojson', data: EMPTY });
    map.addSource('wi-shore', { type: 'geojson', data: geo.shore });
    map.addSource('wi-basins', { type: 'geojson', data: basins });
    // one label per basin, at the middle of its largest part (polygon labels would repeat on every map tile)
    const labelPts = new Map();
    for (const f of basins.features) {
      const ring = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
      const xs = ring.map((q) => q[0]); const ys = ring.map((q) => q[1]);
      const area = (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys));
      const name = f.properties.basin;
      if (!labelPts.has(name) || labelPts.get(name).area < area) {
        labelPts.set(name, { area, at: [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2] });
      }
    }
    map.addSource('wi-basin-labels', { type: 'geojson', data: { type: 'FeatureCollection', features: [...labelPts].map(([basin, v]) => (
      { type: 'Feature', properties: { basin }, geometry: { type: 'Point', coordinates: v.at } })) } });
    map.addSource('wi-areas', { type: 'geojson', data: EMPTY });
    map.addSource('wi-walls', { type: 'geojson', data: EMPTY });
    map.addSource('wi-hit', { type: 'geojson', data: EMPTY });
    map.addSource('wi-draft', { type: 'geojson', data: EMPTY });
    map.addSource('wi-marks', { type: 'geojson', data: EMPTY });
    const damageColor = (prop) => ['step', ['get', prop], ...DAMAGE_STOPS.flatMap(([v, c], k) => (k === 0 ? [c] : [v, c]))];
    map.addLayer({ id: 'wi-grid', type: 'fill', source: 'wi-grid', maxzoom: BUILDING_ZOOM,
      paint: { 'fill-color': ['step', ['get', 'eyd'], '#f1f1ef', 1e4, '#fdd49e', 1e5, '#fc8d59', 1e6, '#d7301f', 5e6, '#7f0000'], 'fill-opacity': 0.55 } });
    map.addLayer({ id: 'wi-basins-fill', type: 'fill', source: 'wi-basins', paint: { 'fill-color': '#3b6fb6', 'fill-opacity': 0.04 } });
    map.addLayer({ id: 'wi-basins-line', type: 'line', source: 'wi-basins', paint: { 'line-color': '#3b6fb6', 'line-width': 1.6, 'line-dasharray': [3, 2] } });
    map.addLayer({ id: 'wi-basins-label', type: 'symbol', source: 'wi-basin-labels',
      layout: { 'text-field': ['concat', ['get', 'basin'], ' basin:\nrainfall flooding modelled here only'], 'text-size': 11, 'text-allow-overlap': false },
      paint: { 'text-color': '#2a5592', 'text-halo-color': '#fff', 'text-halo-width': 1.4 } });
    map.addLayer({ id: 'wi-shore', type: 'line', source: 'wi-shore', minzoom: 10, paint: { 'line-color': '#2f6db5', 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 15, 2.5], 'line-opacity': 0.85 } });
    // buildings the model expects water never to reach: faint hollow dots (D-200)
    map.addLayer({ id: 'wi-dry', type: 'circle', source: 'wi-dry', minzoom: BUILDING_ZOOM,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 13, 1.4, 16, 3, 18, 5.5], 'circle-color': '#ffffff',
        'circle-stroke-color': '#9aa5ae', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 13, 0.6, 16, 1.2], 'circle-opacity': 0.9 } });
    map.addLayer({ id: 'wi-buildings', type: 'circle', source: 'wi-buildings', minzoom: BUILDING_ZOOM,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 13, 1.8, 16, 4, 18, 7], 'circle-color': damageColor('eyd'),
        'circle-stroke-width': 0, 'circle-opacity': 0.85 } });
    map.addLayer({ id: 'wi-areas-fill', type: 'fill', source: 'wi-areas', paint: { 'fill-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'fill-opacity': 0.12 } });
    map.addLayer({ id: 'wi-areas-line', type: 'line', source: 'wi-areas', paint: { 'line-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'line-width': 2 } });
    map.addLayer({ id: 'wi-hit-halo', type: 'circle', source: 'wi-hit', filter: ['==', ['get', 't'], 'raised'],
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 7, 16, 12, 18, 16], 'circle-color': '#5b2a86', 'circle-opacity': 0.18,
        'circle-stroke-color': '#5b2a86', 'circle-stroke-width': 1.5 } });
    map.addLayer({ id: 'wi-hit', type: 'circle', source: 'wi-hit',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 3.5, 16, 7, 18, 10],
        'circle-color': ['match', ['get', 't'], 'raised', '#5b2a86', '#1a7f4b'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } });
    map.addLayer({ id: 'wi-walls-ghost', type: 'line', source: 'wi-walls', filter: ['==', ['get', 'ghost'], true],
      paint: { 'line-color': '#f47321', 'line-width': 2, 'line-opacity': 0.6, 'line-dasharray': [2, 2] } });
    map.addLayer({ id: 'wi-walls-case', type: 'line', source: 'wi-walls', filter: ['!=', ['get', 'ghost'], true], layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#fff', 'line-width': ['case', ['get', 'sel'], 11, 8] } });
    map.addLayer({ id: 'wi-walls', type: 'line', source: 'wi-walls', filter: ['!=', ['get', 'ghost'], true], layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'line-width': ['case', ['get', 'sel'], 7, 5] } });
    // numbered marker per project, visible at every zoom (the list in the panel uses the same numbers)
    map.addLayer({ id: 'wi-marks-dot', type: 'circle', source: 'wi-marks',
      paint: { 'circle-radius': 11, 'circle-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } });
    map.addLayer({ id: 'wi-marks-num', type: 'symbol', source: 'wi-marks',
      layout: { 'text-field': ['to-string', ['get', 'num']], 'text-size': 12, 'text-allow-overlap': true, 'text-font': ['DIN Pro Bold', 'Arial Unicode MS Bold'] },
      paint: { 'text-color': '#fff' } });
    map.addLayer({ id: 'wi-draft-line', type: 'line', source: 'wi-draft', paint: { 'line-color': '#f47321', 'line-width': 3, 'line-dasharray': [2, 1] } });
    map.addLayer({ id: 'wi-draft-pts', type: 'circle', source: 'wi-draft', filter: ['==', ['geometry-type'], 'Point'],
      paint: { 'circle-radius': 4, 'circle-color': '#f47321', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1 } });
    mapReady = true;
    renderLegend();
    refreshBuildings();
    drawProjects();
  });

  function gridGeo() {
    if (!man) return EMPTY;
    return { type: 'FeatureCollection', features: man.tiles.map((t) => (
      { type: 'Feature', properties: { eyd: t.eyd_mid }, geometry: { type: 'Polygon', coordinates: [[...t.square, t.square[0]]] } })) };
  }

  function renderLegend() {
    const shade = $('shade').checked;
    const wasOpen = $('legend').querySelector('details')?.open;
    $('legend').innerHTML = `<details ${wasOpen ?? !mobile() ? 'open' : ''}><summary>Legend</summary>
      ${shade ? `<div><b>Expected yearly damage today</b></div>
      ${DAMAGE_STOPS.slice(1).map(([v, c], k, a) => `<div><span class="sw" style="background:${c}"></span>${k + 1 < a.length ? `${money(v)} to ${money(a[k + 1][0])}` : `over ${money(v)}`} a building</div>`).join('')}
      <div><span class="sw" style="background:#fff;border:1px solid #9aa5ae"></span>no flooding in the model's storms</div>
      <div class="muted">${map.getZoom() < BUILDING_ZOOM ? 'Zoomed out: 2 km squares by total damage. Zoom in to see buildings.' : 'One dot per building in the national building inventory. A house outline with no dot is not in the inventory.'}</div>` : ''}
      <div><span class="sw" style="background:#1a7f4b"></span>protected by the selected project</div>
      <div><span class="sw" style="background:#5b2a86;box-shadow:0 0 0 3px rgba(91,42,134,0.25)"></span>home raised</div>
      <div><span class="ln"></span>rainfall flooding modelled here only</div>
      <div><span class="ln" style="border-top:2.5px solid #2f6db5"></span>FEMA coastal shoreline: walls are placed on it</div></details>`;
  }

  async function refreshBuildings() {
    if (!mapReady || !man) return;
    const on = $('shade').checked;
    map.setLayoutProperty('wi-buildings', 'visibility', on ? 'visible' : 'none');
    map.setLayoutProperty('wi-dry', 'visibility', on ? 'visible' : 'none');
    map.setLayoutProperty('wi-grid', 'visibility', on ? 'visible' : 'none');
    renderLegend();
    if (!on || map.getZoom() < BUILDING_ZOOM) return;
    const b = map.getBounds();
    const [x0, y0] = toUtm17(b.getWest(), b.getSouth());
    const [x1, y1] = toUtm17(b.getEast(), b.getNorth());
    const box = tilesForBox(x0, y0, x1, y1, man.tile_m);
    const keys = box.filter((k) => store.byKey.has(k)).slice(0, MAX_VIEW_TILES);
    const dkeys = box.filter((k) => dryStore.byKey.has(k)).slice(0, MAX_VIEW_TILES);
    await Promise.all([store.ensure(keys), dryStore.ensure(dkeys)]);
    if (removed) return;
    const features = [];
    for (const k of keys) {
      if (!tileFeatures.has(k)) {
        const t = store.tiles.get(k);
        const c = t.cols;
        const f = new Array(t.n);
        for (let i = 0; i < t.n; i += 1) {
          f[i] = { type: 'Feature', properties: { eyd: c.eyd_mid[i], k, i }, geometry: { type: 'Point', coordinates: [c.lon[i], c.lat[i]] } };
        }
        tileFeatures.set(k, f);
      }
      features.push(...tileFeatures.get(k));
    }
    map.getSource('wi-buildings').setData({ type: 'FeatureCollection', features });
    const dry = [];
    for (const k of dkeys) {
      if (!dryFeatures.has(k)) {
        const t = dryStore.tiles.get(k);
        const c = t.cols;
        const f = new Array(t.n);
        for (let i = 0; i < t.n; i += 1) {
          f[i] = { type: 'Feature', properties: { dk: k, i }, geometry: { type: 'Point', coordinates: [c.lon[i], c.lat[i]] } };
        }
        dryFeatures.set(k, f);
      }
      dry.push(...dryFeatures.get(k));
    }
    map.getSource('wi-dry').setData({ type: 'FeatureCollection', features: dry });
  }
  map.on('moveend', () => { refreshBuildings(); });
  map.on('zoomend', renderLegend);

  // ---------------------------------------------------------------- projects
  function newProject(kind, extra) {
    counter += 1;
    const p = { uid: counter, kind, name: kind === 'seawall' ? `Seawall ${counter}` : `Raise homes ${counter}`, costEdited: false, cost: 0, res: null, ...extra };
    projects.push(p);
    sel = projects.length - 1;
    return p;
  }

  function shoreDistance(line) {
    let best = Infinity;
    const pts = line.map(([lo, la]) => toUtm17(lo, la));
    for (const [x, y] of pts) for (const s of shoreUtm) best = Math.min(best, pointLineDist(x, y, s));
    return best;
  }

  async function compute(p) {
    const t0 = performance.now();
    if (p.kind === 'seawall') {
      // a drawn wall is placed on FEMA's coastal shoreline, as Part 2 placed real walls (D-200); the examples are on it already
      if (!p.onShore) {
        const snap = snapToShore(p.drawn, shoreLL, shoreUtm, MAX_SHORE_M);
        p.line = snap ? snap.line : p.drawn;
        p.snapM = snap ? snap.movedM : null;
      }
      await store.ensure(seawallTileKeys(p.line, man));
      p.res = seawall(store.tiles, p.line, p.crest, ctx, { keepPer: true });
      p.lengthFt = p.res.lengthM / FT;
      p.shoreM = shoreDistance(p.drawn || p.line);
      if (!p.costEdited) p.cost = Math.round(p.lengthFt * SETTINGS.seawall.unitCost);
    } else {
      if (p.mode === 'area') {
        const xs = p.ring.map((q) => toUtm17(q[0], q[1]));
        await store.ensure(tilesForBox(Math.min(...xs.map((q) => q[0])), Math.min(...xs.map((q) => q[1])),
          Math.max(...xs.map((q) => q[0])), Math.max(...xs.map((q) => q[1])), man.tile_m));
        p.picks = topHomes(store.tiles, p.ring, p.n, ctx);
        p.available = p.picks.available;
      } else if (p.mode === 'ids') {
        await store.ensure(p.tiles);
        p.picks = picksForIds(new Map(p.tiles.map((k) => [k, store.tiles.get(k)]).filter(([, t]) => t)), p.fd_ids);
      }
      p.res = elevate(store.tiles, p.picks || [], p.raise, ctx, { keepPer: true });
      p.homes = (p.picks || []).length;
      if (!p.costEdited) p.cost = p.homes * SETTINGS.elevation.unitCost;
    }
    p.totalMs = performance.now() - t0;
    return p;
  }

  async function update(p, { fromDrag = false } = {}) {
    if (!man) return;
    await compute(p);
    if (removed) return;
    if (fromDrag) dragTimes.push({ kind: p.kind, engineMs: p.res.ms, totalMs: p.totalMs });
    drawProjects();
    renderResults();
  }

  function projectCenter(p) {
    let pts = [];
    if (p.kind === 'seawall') pts = p.line;
    else if (p.mode === 'area') pts = p.ring;
    else pts = (p.res?.perBuilding || []).map((q) => [q.lon, q.lat]);
    if (!pts.length) return null;
    const lo = pts.map((q) => q[0]); const la = pts.map((q) => q[1]);
    return [(Math.min(...lo) + Math.max(...lo)) / 2, (Math.min(...la) + Math.max(...la)) / 2];
  }

  function drawProjects() {
    if (!mapReady) return;
    const walls = []; const areas = []; const hits = [];
    projects.forEach((p, k) => {
      const isSel = k === sel;
      if (p.kind === 'seawall' && p.line) walls.push({ type: 'Feature', properties: { k, sel: isSel, ghost: false }, geometry: { type: 'LineString', coordinates: p.line } });
      if (p.kind === 'seawall' && p.snapM > 5) walls.push({ type: 'Feature', properties: { k, sel: isSel, ghost: true }, geometry: { type: 'LineString', coordinates: p.drawn } });
      if (p.kind === 'elevation' && p.mode === 'area') areas.push({ type: 'Feature', properties: { k, sel: isSel }, geometry: { type: 'Polygon', coordinates: [[...p.ring, p.ring[0]]] } });
      if (p.kind === 'elevation') {
        for (const q of p.res?.perBuilding || []) hits.push({ type: 'Feature', properties: { t: 'raised', k }, geometry: { type: 'Point', coordinates: [q.lon, q.lat] } });
      } else if (isSel) {
        for (const q of p.res?.perBuilding || []) if (q.before - q.after > 0) hits.push({ type: 'Feature', properties: { t: 'protected', k }, geometry: { type: 'Point', coordinates: [q.lon, q.lat] } });
      }
    });
    map.getSource('wi-walls').setData({ type: 'FeatureCollection', features: walls });
    map.getSource('wi-areas').setData({ type: 'FeatureCollection', features: areas });
    map.getSource('wi-hit').setData({ type: 'FeatureCollection', features: hits });
    const marks = projects.map((p, k) => ({ type: 'Feature', properties: { num: k + 1, k, sel: k === sel }, geometry: { type: 'Point', coordinates: projectCenter(p) } }))
      .filter((f) => f.geometry.coordinates);
    map.getSource('wi-marks').setData({ type: 'FeatureCollection', features: marks });
    const d = [];
    if (drawing && drawing.pts.length) {
      const pts = drawing.kind === 'area' && drawing.pts.length > 2 ? [...drawing.pts, drawing.pts[0]] : drawing.pts;
      if (pts.length > 1) d.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: pts } });
      drawing.pts.forEach((q) => d.push({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: q } }));
    }
    map.getSource('wi-draft').setData({ type: 'FeatureCollection', features: d });
  }

  // ---------------------------------------------------------------- results
  function renderProjectList() {
    if (projects.length < 2) { $('projects').innerHTML = ''; return; }
    $('projects').innerHTML = `<h2>Projects (${projects.length})</h2><ul class="plist">${projects.map((p, k) => {
      const b = p.res ? benefitPerDollar(p.kind, p.res.avoided.mid, p.cost, SETTINGS.rates.main) : NaN;
      return `<li><button type="button" data-sel="${k}" class="${k === sel ? 'on' : ''}"><span class="pn">${k + 1}. ${p.name}</span><span class="pb" style="color:${b >= 1 ? '#1a7f4b' : '#6b7783'}">${ratio(b)} per $1</span><span class="ps">${p.res ? `${money(p.res.avoided.mid)} a year avoided · ${fmt(p.res.buildingsProtected)} building${p.res.buildingsProtected === 1 ? '' : 's'} protected` : 'computing…'}</span></button></li>`;
    }).join('')}</ul>`;
  }

  function renderResults() {
    renderProjectList();
    const p = projects[sel];
    if (!p || !p.res) {
      $('results').innerHTML = projects.length ? '' : '<p class="muted">No project yet. Draw a wall or raise homes, or press <b>Examples</b>.</p>';
      return;
    }
    const r = p.res;
    const s = SETTINGS[p.kind];
    if (p.kind === 'elevation' && p.mode === 'area') $('n-homes').value = String(p.n);
    if (p.kind === 'seawall') { $('crest').value = String(p.crest); $('crest-out').textContent = `${p.crest.toFixed(1)} ft`; }
    else { $('raise').value = String(p.raise); $('raise-out').textContent = `${p.raise} ft`; }
    const b7 = benefitPerDollar(p.kind, r.avoided.mid, p.cost, SETTINGS.rates.main);
    const b3 = benefitPerDollar(p.kind, r.avoided.mid, p.cost, SETTINGS.rates.sensitivity);
    const b7lo = benefitPerDollar(p.kind, r.avoided.low, p.cost, SETTINGS.rates.main);
    const b7hi = benefitPerDollar(p.kind, r.avoided.high, p.cost, SETTINGS.rates.main);
    const warns = [];
    let what;
    if (p.kind === 'seawall') {
      what = `${fmt(p.lengthFt)} ft wall, crest +${p.crest.toFixed(1)} ft NAVD88`;
      if (p.snapM > 5) what += `. Placed on FEMA's coastal shoreline (the thin blue line), ${fmt(p.snapM)} m from where you drew it: the model can only test a wall on that line. Your line is shown dashed`;
      if (p.lengthFt < SHORT_WALL_FT) warns.push('Wall under 200 ft: water going around the ends is not modelled; result likely overstated.');
      if (r.protectedMedianDistM != null && r.protectedMedianDistM > 300) {
        warns.push(`Most buildings credited to this wall are far from it (half are more than ${fmt(r.protectedMedianDistM)} m away). The model gives a wall every building whose nearest point on FEMA's coastal shoreline lies behind it, and FEMA's shoreline skips canals and creeks, so water could reach many of these buildings another way. Result likely overstated.`);
      }
      if (p.snapM == null && p.shoreM > MAX_SHORE_M) warns.push(`This line is ${(p.shoreM / 1000).toFixed(1)} km from FEMA's coastal shoreline (the thin blue line along the bay and ocean). FEMA's coastal study does not cover the water here (a river, canal or lake), so the model cannot value this wall.`);
    } else {
      what = `${fmt(p.homes)} home${p.homes === 1 ? '' : 's'} raised ${p.raise} ft`;
      if (p.mode === 'area') {
        what += `. This area has ${fmt(p.available)} single-family home${p.available === 1 ? '' : 's'} that flood; the ${p.homes === 1 ? 'most damaged one is' : `${fmt(p.homes)} most damaged are`} raised${p.homes < p.available ? ` <button type="button" class="btn small" id="raise-all">Raise all ${fmt(p.available)}</button>` : ''}`;
      }
      if (!p.homes) warns.push(p.mode === 'area' ? 'No flooding single-family homes in this area.' : 'No homes chosen yet. Zoom in and click buildings.');
    }
    const unit = p.kind === 'seawall' ? `$${SETTINGS.seawall.unitCost.toLocaleString('en-US')} per foot of wall (median of funded Miami-Dade seawalls, Part 1)` : `$${SETTINGS.elevation.unitCost.toLocaleString('en-US')} per home (median FEMA elevation grant in South Florida, 2025 dollars)`;
    $('results').innerHTML = `
      <h2>${p.name}</h2>
      <p class="note">${what}. <span class="tag est">estimated</span> results, <span class="tag asm">assumed</span> cost and settings.</p>
      ${warns.map((w) => `<p class="warn">${w}</p>`).join('')}
      <div class="stats">
        <div class="wide"><div class="n">${money(r.avoided.mid)} a year</div><div class="l">flood damage avoided, middle estimate (range ${money(r.avoided.low)} to ${money(r.avoided.high)} from the damage curves) <span class="tag est">estimated</span></div></div>
        <div><div class="n">${fmt(r.buildingsProtected)}</div><div class="l">buildings protected (yearly damage goes down)</div></div>
        <div><div class="n">${fmt(r.residentsProtected)}</div><div class="l">estimated residents in them (night-time, Census-based, usually 2 to 4 a home) <span class="tag est">estimated</span></div></div>
        <div class="bcr ${b7 >= 1 ? 'good' : 'poor'}"><div class="n">${ratio(b7)}</div><div class="l">benefit per $1 at 7% (FEMA, main). Range ${ratio(b7lo)} to ${ratio(b7hi)}</div></div>
        <div class="bcr ${b3 >= 1 ? 'good' : 'poor'}"><div class="n">${ratio(b3)}</div><div class="l">benefit per $1 at 3% (sensitivity) <span class="tag asm">assumed</span></div></div>
        <div class="wide"><div class="l">Project life ${s.life} years (FEMA)${s.maint ? `; upkeep ${s.maint * 100}% of the cost a year <span class="tag asm">assumed</span>` : '; no upkeep cost'}. Before the project, these buildings expect ${money(r.before.mid)} of damage a year.</div></div>
      </div>
      <div class="cost">
        <label class="field money">Cost <input type="number" id="cost" min="0" step="1000" value="${Math.round(p.cost)}" aria-label="Project cost in dollars"></label>
        <p><span class="tag asm">assumed</span> Default: ${unit}.${p.costEdited ? ' <button type="button" class="btn small" id="cost-reset">Use the typical cost</button>' : ''}</p>
      </div>
      <h3>Property value (kept out of benefit per dollar)</h3>
      <p class="note"><b>About zero from local sales:</b> our own estimate from Miami-Dade home sales finds no reliable price effect of flood damage. <span class="tag est">estimated</span><br>
      <b>Published-discount scenario:</b> ${money(r.valueChangePublished)} in total${r.valueBasePublished > 0 ? ` (${(100 * r.valueChangePublished / r.valueBasePublished).toFixed(1)}% of these homes' value)` : ''}, if homes gain value as in a published Miami study (about 3% for being in the 100-year flood zone). <span class="tag asm">assumed</span></p>
      ${r.valueBasePublished > 0 && Math.abs(r.valueChangePublished / r.valueBasePublished) > 0.05 ? '<p class="warn">This is well above the 3% the study found. The scenario stretches that discount to homes with far more flood damage than a typical flood-zone home, so treat this figure as an upper bound, not an estimate.</p>' : ''}
      <p class="timing">Computed in ${r.ms.toFixed(1)} ms in your browser (${fmt(r.buildingsAffected)} buildings rerun${p.kind === 'seawall' ? `, ${fmt(r.candidates)} checked` : ''}).</p>
      <div class="row-btns"><button type="button" class="btn" id="remove">Remove this project</button></div>`;
  }

  // ---------------------------------------------------------------- controls
  function setTool(t) {
    cancelDrawing();
    document.querySelectorAll('[data-tool]').forEach((b) => b.classList.toggle('on', b.dataset.tool === t));
    $('tool-seawall').hidden = t !== 'seawall';
    $('tool-elevation').hidden = t !== 'elevation';
    renderElevHelp();
  }

  function renderElevHelp() {
    document.querySelectorAll('[data-emode]').forEach((b) => b.classList.toggle('on', b.dataset.emode === emode));
    $('n-field').hidden = emode !== 'area';
    $('elev-draw').textContent = emode === 'area' ? 'Draw an area' : 'Start choosing homes';
    $('elev-help').innerHTML = emode === 'area'
      ? 'Press <b>Draw an area</b>, click its corners on the map, then double-click or press <b>Finish</b>. The most damaged single-family homes inside are raised. Drag the area to move it.'
      : `Press <b>Start choosing homes</b>, zoom in (buildings show from zoom ${BUILDING_ZOOM}) and click buildings to add or remove them. Press <b>Finish</b> when done.`;
  }

  function cancelDrawing() {
    drawing = null;
    map.doubleClickZoom.enable();
    map.getCanvas().style.cursor = '';
    $('wall-draw').classList.remove('active'); $('elev-draw').classList.remove('active');
    $('wall-finish').disabled = true; $('elev-finish').disabled = true;
    status('');
    if (mapReady) drawProjects();
  }

  function startDrawing(kind) {
    if (!man) return;
    cancelDrawing();
    drawing = { kind, pts: [] };
    map.doubleClickZoom.disable();
    map.getCanvas().style.cursor = 'crosshair';
    if (kind === 'wall') { $('wall-draw').classList.add('active'); $('wall-finish').disabled = false; status('Click points along the shore; double-click to finish'); }
    if (kind === 'area') { $('elev-draw').classList.add('active'); $('elev-finish').disabled = false; status('Click the corners of the area; double-click to finish'); }
    if (kind === 'click') {
      $('elev-draw').classList.add('active'); $('elev-finish').disabled = false;
      newProject('elevation', { mode: 'click', picks: [], raise: Number($('raise').value) });
      update(projects[sel]);
      status(map.getZoom() < BUILDING_ZOOM ? 'Zoom in to see buildings, then click them' : 'Click buildings to add or remove them');
    }
  }

  function finishDrawing() {
    if (!drawing) return;
    const d = drawing;
    cancelDrawing();
    if (d.kind === 'wall' && d.pts.length >= 2) {
      update(newProject('seawall', { drawn: d.pts, crest: Number($('crest').value) }));
    } else if (d.kind === 'area' && d.pts.length >= 3) {
      update(newProject('elevation', { mode: 'area', ring: d.pts, n: Math.max(1, Math.round(Number($('n-homes').value) || 1)), raise: Number($('raise').value) }));
    }
  }

  async function loadExamples() {
    if (!man) return;
    cancelDrawing();
    projects.length = 0;
    for (const e of examples) {
      if (e.kind === 'seawall') newProject('seawall', { name: e.label, line: e.line, drawn: e.line, onShore: true, snapM: 0, crest: e.crest_ft });
      else newProject('elevation', { name: e.label, mode: 'ids', fd_ids: e.fd_ids, tiles: e.tiles, raise: e.raise_ft });
    }
    await Promise.all(projects.map((p) => compute(p)));
    if (removed) return;
    sel = 0;
    drawProjects();
    renderResults();
    const pts = projects.flatMap((p) => (p.kind === 'seawall' ? p.line : (p.res?.perBuilding || []).map((q) => [q.lon, q.lat])));
    if (pts.length) {
      const lo = pts.map((q) => q[0]); const la = pts.map((q) => q[1]);
      // fitBounds padding replaces the map's own padding, so keep room for the panel and the legend here
      const pad = mobile() ? { top: 120, left: 30, right: 30, bottom: window.innerHeight * 0.55 } : { top: 70, bottom: 230, left: 470, right: 90 };
      map.fitBounds([[Math.min(...lo), Math.min(...la)], [Math.max(...lo), Math.max(...la)]], { padding: pad, maxZoom: 13.5, duration: 600 });
    }
  }

  function onPanelClick(e) {
    const t = e.target;
    if (t.closest('[data-tool]')) setTool(t.closest('[data-tool]').dataset.tool);
    else if (t.closest('[data-emode]')) { emode = t.closest('[data-emode]').dataset.emode; cancelDrawing(); renderElevHelp(); }
    else if (t.id === 'wall-draw') startDrawing('wall');
    else if (t.id === 'elev-draw') startDrawing(emode === 'area' ? 'area' : 'click');
    else if (t.id === 'wall-finish' || t.id === 'elev-finish') { if (drawing) finishDrawing(); else cancelDrawing(); }
    else if (t.id === 'examples') loadExamples();
    else if (t.id === 'clear-all') { cancelDrawing(); projects.length = 0; sel = -1; drawProjects(); renderResults(); }
    else if (t.id === 'remove') { projects.splice(sel, 1); sel = projects.length - 1; drawProjects(); renderResults(); }
    else if (t.id === 'raise-all') { const p = projects[sel]; p.n = p.available; $('n-homes').value = String(p.n); update(p); }
    else if (t.id === 'cost-reset') { const p = projects[sel]; p.costEdited = false; update(p); }
    else if (t.closest('[data-sel]')) { sel = Number(t.closest('[data-sel]').dataset.sel); drawProjects(); renderResults(); }
  }
  const panel = document.querySelector('.viz-whatif .panel');
  panel.addEventListener('click', onPanelClick);

  function onPanelInput(e) {
    const t = e.target;
    const p = projects[sel];
    if (t.id === 'crest') { $('crest-out').textContent = `${Number(t.value).toFixed(1)} ft`; if (p?.kind === 'seawall') { p.crest = Number(t.value); update(p); } }
    if (t.id === 'raise') { $('raise-out').textContent = `${t.value} ft`; if (p?.kind === 'elevation') { p.raise = Number(t.value); update(p); } }
    if (t.id === 'n-homes' && p?.kind === 'elevation' && p.mode === 'area') { p.n = Math.max(1, Math.round(Number(t.value) || 1)); update(p); }
    if (t.id === 'shade') refreshBuildings();
  }
  function onPanelChange(e) {
    if (e.target.id !== 'cost') return;
    const p = projects[sel];
    if (!p) return;
    p.cost = Math.max(0, Number(e.target.value) || 0);
    p.costEdited = true;
    renderResults();
  }
  panel.addEventListener('input', onPanelInput);
  panel.addEventListener('change', onPanelChange);
  renderElevHelp();

  // ---------------------------------------------------------------- map interaction
  map.on('click', (e) => {
    if (!mapReady) return;
    if (drawing && (drawing.kind === 'wall' || drawing.kind === 'area')) {
      drawing.pts.push([e.lngLat.lng, e.lngLat.lat]);
      drawProjects();
      return;
    }
    if (drawing && drawing.kind === 'click') {
      const f = map.queryRenderedFeatures(e.point, { layers: ['wi-buildings'] })[0];
      if (!f) return;
      const p = projects[sel];
      const { k, i } = f.properties;
      const j = p.picks.findIndex((q) => q.key === k && q.i === i);
      if (j >= 0) p.picks.splice(j, 1); else p.picks.push({ key: k, i });
      update(p);
      return;
    }
    const f = map.queryRenderedFeatures(e.point, { layers: ['wi-marks-dot', 'wi-walls'] })[0];
    if (f && f.properties.k != null) { sel = Number(f.properties.k); drawProjects(); renderResults(); return; }
    const b = map.queryRenderedFeatures(e.point, { layers: ['wi-buildings', 'wi-dry'] })[0];
    if (b) { showBuilding(b, e.lngLat); return; }
    const a = map.queryRenderedFeatures(e.point, { layers: ['wi-areas-fill'] })[0];
    if (a && a.properties.k != null) { sel = Number(a.properties.k); drawProjects(); renderResults(); }
  });
  function showBuilding(f, lngLat) {
    const pr = f.properties;
    let html;
    if (pr.dk != null) {
      const c = dryStore.tiles.get(pr.dk).cols; const i = pr.i;
      html = `<b>No flooding in the model's storms</b><br>${c.res1[i] ? 'Single-family home' : 'Building'}${c.sqft[i] > 0 ? `, ${fmt(c.sqft[i])} sq ft` : ''}<br>Estimated residents: ${fmt(c.residents[i])}<br>Ground ${c.ground[i].toFixed(1)} ft NAVD88: water stays below it even in the 500-year storm`;
    } else {
      const t = store.tiles.get(pr.k); const c = t.cols; const i = pr.i;
      const floor = c.ffe[i] - c.ground[i];
      const occ = man.lists.occtype[c.occ[i]];
      const q = projects[sel]?.res?.perBuilding?.find((x) => x.key === pr.k && x.i === i);
      html = `<b>${ctx.curves.res1[c.occ[i]] ? 'Single-family home' : `Building (${occ})`}</b>${c.sqft[i] > 0 ? `, ${fmt(c.sqft[i])} sq ft` : ''}<br>
        Estimated residents: ${fmt(c.residents[i])}<br>
        Expected flood damage today: <b>${money(c.eyd_mid[i])} a year</b><br>
        First floor ${floor.toFixed(1)} ft above ground${c.ffe_est[i] ? ' (estimated)' : ' (from records)'}
        ${q ? `<br>With the selected project: <b>${money(q.after)} a year</b> (${money(q.before - q.after)} avoided)` : ''}`;
    }
    popup.remove();
    infoPopup.setLngLat(lngLat).setHTML(html).addTo(map);
  }
  map.on('dblclick', (e) => { if (drawing && drawing.kind !== 'click') { e.preventDefault(); finishDrawing(); } });

  // drag a placed wall or area; results update while it moves
  let drag = null;
  let busy = false;
  let pending = false;
  async function dragCompute() {
    if (busy) { pending = true; return; }
    busy = true;
    do {
      pending = false;
      await update(projects[drag?.k ?? sel], { fromDrag: true });
    } while (pending && !removed);
    busy = false;
  }
  function startDrag(e) {
    if (drawing) return;
    const f = map.queryRenderedFeatures(e.point, { layers: ['wi-walls', 'wi-walls-ghost', 'wi-areas-fill'] })[0];
    if (!f) return;
    e.preventDefault();
    const k = Number(f.properties.k);
    const p = projects[k];
    sel = k;
    drag = { k, start: [e.lngLat.lng, e.lngLat.lat], orig: JSON.parse(JSON.stringify(p.kind === 'seawall' ? p.drawn : p.ring)) };
    map.dragPan.disable();
    map.getCanvas().style.cursor = 'grabbing';
  }
  function moveDrag(e) {
    if (!drag) return;
    const dx = e.lngLat.lng - drag.start[0]; const dy = e.lngLat.lat - drag.start[1];
    const moved = drag.orig.map(([lo, la]) => [lo + dx, la + dy]);
    const p = projects[drag.k];
    if (p.kind === 'seawall') { p.drawn = moved; p.onShore = false; } else p.ring = moved;
    drawProjects();
    dragCompute();
  }
  function endDrag() {
    if (!drag) return;
    drag = null;
    map.dragPan.enable();
    map.getCanvas().style.cursor = '';
  }
  map.on('mousedown', 'wi-walls', startDrag);
  map.on('mousedown', 'wi-walls-ghost', startDrag);
  map.on('mousedown', 'wi-areas-fill', startDrag);
  map.on('touchstart', 'wi-walls', (e) => { if (e.points.length === 1) startDrag(e); });
  map.on('touchstart', 'wi-areas-fill', (e) => { if (e.points.length === 1) startDrag(e); });
  map.on('mousemove', moveDrag);
  map.on('touchmove', moveDrag);
  map.on('mouseup', endDrag);
  map.on('touchend', endDrag);
  for (const l of ['wi-walls', 'wi-areas-fill']) {
    map.on('mouseenter', l, () => { if (!drawing && !drag) map.getCanvas().style.cursor = 'grab'; });
    map.on('mouseleave', l, () => { if (!drawing && !drag) map.getCanvas().style.cursor = ''; });
  }
  map.on('mousemove', 'wi-buildings', (e) => {
    if (drag) return;
    const f = e.features[0];
    if (infoPopup.isOpen()) return;
    popup.setLngLat(e.lngLat).setHTML(`Expected yearly damage today: <b>${money(f.properties.eyd)}</b><br><span style="color:#6b7783">click for details</span>`).addTo(map);
  });
  map.on('mouseleave', 'wi-buildings', () => popup.remove());

  if (import.meta.env.DEV) {
    // for the timing check in the Part 2 report (drag measurement) and screenshots
    window.__whatIf = { map, projects, dragTimes, loadExamples, update, compute, get sel() { return sel; },
      add: (kind, extra) => update(newProject(kind, extra)) };
  }

  return () => {
    removed = true;
    panel.removeEventListener('click', onPanelClick);
    panel.removeEventListener('input', onPanelInput);
    panel.removeEventListener('change', onPanelChange);
    popup.remove();
    infoPopup.remove();
    map.remove();
    if (import.meta.env.DEV) delete window.__whatIf;
  };
}
