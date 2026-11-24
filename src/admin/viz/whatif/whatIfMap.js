import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import {
  SETTINGS, benefitPerDollar, elevate, explainBuilding, makeContext, picksForIds, pointLineDist, seawallReasons,
  seawallTileKeys, snapToShore, tilesForBox, toUtm17, topHomes,
} from './whatIfEngine.js';
import { REASON_STYLE, cardHtml, facts, moneyShort, nearestWater, reasonSentence, shortSentence } from './whatIfExplain.js';
import { loadJson, tileStore } from './whatIfData.js';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Admin only (D-095, D-200). Engine: whatIfEngine.js, a copy of Modules B and C checked against Python
// (whatIfParity.test.js). Data: "Modelling Data from Web/scripts/benefit/export_what_if.py" (D-199).
// Layout (D-208): map first, a small toolbar, one result card; reasons and other layers behind "Show why".
const FT = 0.3048;
const SHORT_WALL_FT = 200;
const MAX_SHORE_M = 500;
const BUILDING_ZOOM = 13;
const MAX_VIEW_TILES = 36;
const DAMAGE_STOPS = [[0, '#d9dde1'], [100, '#fdd49e'], [1000, '#fc8d59'], [10000, '#d7301f'], [50000, '#7f0000']];
const STILL_FLOODS = '#a3acb4';
const PROTECTED = '#1a7f4b';
const EMPTY = { type: 'FeatureCollection', features: [] };
const HINT_KEY = 'whatif-hint-done';

const fmt = (n) => (n == null || Number.isNaN(n) ? 'n/a' : Math.round(n).toLocaleString('en-US'));
const money = moneyShort;
const ratio = (v) => (Number.isFinite(v) ? `$${v.toFixed(2)}` : 'n/a');
const plural = (n, one, many) => `${fmt(n)} ${Math.round(n) === 1 ? one : many}`;
const esc = (t) => String(t).replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
function storageGet(k) { try { return window.localStorage.getItem(k); } catch { return null; } }
function storageSet(k, v) { try { window.localStorage.setItem(k, v); } catch { /* private window: the hint shows again next time */ } }

function aboutHtml() {
  return `
    <div class="about-head"><h2>About this tool</h2><button type="button" class="btn small" id="about-close">Close</button></div>
    <ul class="about-list">
      <li><b>What it does:</b> place a seawall or raise homes, and see how much flood damage it prevents each year and whether that pays back its cost.</li>
      <li><b>Data:</b> buildings from the national building inventory; storm water levels from FEMA's 2027 Miami-Dade flood study; costs from funded Miami-Dade seawalls and FEMA home-raising grants.</li>
      <li><b>How projects work:</b> a seawall keeps sea water out up to its height, for buildings behind it whose nearest water is that shore, within 1 km. Raising a home lifts its first floor.</li>
      <li><b>Benefit per dollar:</b> damage prevented over the project's life (50 years for a wall, 30 for a home), discounted at 7% a year as FEMA does, divided by the cost. Above $1, it pays back.</li>
      <li><b>Main limits:</b> rainfall flooding is modelled only in two basins (C-8 and C-9); floor heights are mostly estimated; high-tide (king tide) flooding is not included.</li>
    </ul>
    <details class="more"><summary>More detail</summary>
      <p>Damage curves from the US Army Corps of Engineers turn water depth above the first floor into dollars. The five storms (10, 25, 50, 100 and 500-year) are combined into a yearly average. A seawall counts only for buildings whose straight line to the shore crosses the wall, whose ground is below the wall top, whose nearest open water is that shore rather than a canal, creek or inner waterway (FEMA 2027 water lines), and that are within 1 km of the wall. Water flowing around the ends over open ground is not modelled, so short walls can look better than they are. Seawall upkeep: 1% of the cost a year (assumed). FEMA has used 7% since 2025; the 3.1% rate FEMA used in 2023 and 2024 is shown as a sensitivity (FEMA BCA Toolkit help content, 28 August 2025, page 59). No sea level rise. Damage counts buildings only, not roads or utilities. Property value changes are shown separately and kept out of benefit per dollar. The browser engine matches the Python model to within 0.001% on every Part 2 test project. Heights are in feet above NAVD88, the standard US land datum.</p>
      <p>Reports: "Modelling Data from Web/reports/benefit/typical_projects_part2.md" and "admin_what_if_part2.md".</p>
    </details>
    <p class="about-foot">Estimates for discussion, not for decisions. Other views: <a href="/admin/viz">Resilience gap map</a> · <a href="/admin/viz/scenario">Scenarios</a></p>`;
}

/** Builds the view into the markup already on the page; returns a cleanup function. */
export function mount() {
  let removed = false;
  const $ = (id) => document.getElementById(id);
  const root = document.querySelector('.viz-whatif');
  const mobile = () => window.innerWidth <= 768;
  const sidePad = () => {
    if (!mobile()) return { left: 390, right: 90, top: 60, bottom: 200 };   // room for the side column and the legend
    const h = $('side')?.getBoundingClientRect().height || 120;
    return { top: Math.min(h, window.innerHeight * 0.5) + 30, left: 40, right: 40, bottom: 170 };
  };
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/light-v11',
    center: [-80.3, 25.72],
    zoom: 9.6,
    padding: mobile() ? { top: 110 } : { left: 380 },
    doubleClickZoom: true,
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');

  let man = null; let ctx = null; let store = null; let dryStore = null; let shoreUtm = []; let shoreLL = []; let examples = [];
  let tool = null;
  let ownProjects = null; // the user's own projects, set aside while the Examples tab is open (D-213)
  let damageExpr = STILL_FLOODS;
  let emode = 'area';
  let why = false;
  let showLinks = false;
  let drawing = null;           // {kind: 'wall' | 'area' | 'click', pts: [[lon, lat], ...]}
  const projects = [];
  let sel = -1;
  let counter = 0;
  let mapReady = false;
  let editingCost = false;
  const tileFeatures = new Map();
  const dryFeatures = new Map();
  const dragTimes = [];
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, className: 'tip', offset: 8 });
  const infoPopup = new mapboxgl.Popup({ closeButton: true, closeOnClick: true, className: 'tip', offset: 10, maxWidth: '260px' });
  // building card, anchored to the building (D-211); mapbox picks the side with room
  const cardPopup = new mapboxgl.Popup({ closeButton: true, closeOnClick: false, className: 'cardpop', offset: 12, maxWidth: '340px', focusAfterOpen: false });


  $('about').innerHTML = aboutHtml();
  const status = (t) => { $('status').textContent = t || ''; };
  if (storageGet(HINT_KEY) !== '1') $('hint').hidden = false;
  function hideHint() { $('hint').hidden = true; storageSet(HINT_KEY, '1'); }

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
    if (!removed) { $('results').hidden = false; $('results').innerHTML = `<p class="warn">The flood data could not be loaded (${esc(e.message)}). Sign in again, or ask an admin.</p>`; }
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
    for (const s of ['wi-areas', 'wi-walls', 'wi-hit', 'wi-draft', 'wi-marks', 'wi-reason', 'wi-links']) map.addSource(s, { type: 'geojson', data: EMPTY });
    const damageColor = (prop) => ['step', ['get', prop], ...DAMAGE_STOPS.flatMap(([v, c], k) => (k === 0 ? [c] : [v, c]))];
    map.addLayer({ id: 'wi-grid', type: 'fill', source: 'wi-grid', maxzoom: BUILDING_ZOOM,
      paint: { 'fill-color': ['step', ['get', 'eyd'], '#f1f1ef', 1e4, '#fdd49e', 1e5, '#fc8d59', 1e6, '#d7301f', 5e6, '#7f0000'], 'fill-opacity': 0.55 } });
    map.addLayer({ id: 'wi-basins-fill', type: 'fill', source: 'wi-basins', paint: { 'fill-color': '#3b6fb6', 'fill-opacity': 0.04 } });
    map.addLayer({ id: 'wi-basins-line', type: 'line', source: 'wi-basins', paint: { 'line-color': '#3b6fb6', 'line-width': 1.6, 'line-dasharray': [3, 2] } });
    map.addLayer({ id: 'wi-basins-label', type: 'symbol', source: 'wi-basin-labels',
      layout: { 'text-field': ['concat', ['get', 'basin'], ' basin:\nrain flooding modelled'], 'text-size': 11, 'text-allow-overlap': false },
      paint: { 'text-color': '#2a5592', 'text-halo-color': '#fff', 'text-halo-width': 1.4 } });
    map.addLayer({ id: 'wi-shore', type: 'line', source: 'wi-shore', minzoom: 10, paint: { 'line-color': '#2f6db5', 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 15, 2.5], 'line-opacity': 0.85 } });
    // buildings the model expects water never to reach: faint hollow dots (D-200), under "Show why"
    map.addLayer({ id: 'wi-dry', type: 'circle', source: 'wi-dry', minzoom: BUILDING_ZOOM,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 13, 1.4, 16, 3, 18, 5.5], 'circle-color': '#ffffff',
        'circle-stroke-color': '#9aa5ae', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 13, 0.6, 16, 1.2], 'circle-opacity': 0.9 } });
    map.addLayer({ id: 'wi-buildings', type: 'circle', source: 'wi-buildings', minzoom: BUILDING_ZOOM,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 13, 1.8, 16, 4, 18, 7], 'circle-color': STILL_FLOODS,
        'circle-stroke-width': 0, 'circle-opacity': 0.85 } });

    damageExpr = damageColor('eyd');
    // explanation layer (D-204): each flooding building near the selected wall coloured by its reason, and an optional
    // line to the water it is matched to; under "Show why" (D-208)
    const reasonColor = ['match', ['get', 'r'], ...Object.entries(REASON_STYLE).flatMap(([k, v]) => [k, v.color]), '#999'];
    map.addLayer({ id: 'wi-links', type: 'line', source: 'wi-links', paint: { 'line-color': reasonColor, 'line-width': 0.9, 'line-opacity': 0.75 } });
    map.addLayer({ id: 'wi-reason', type: 'circle', source: 'wi-reason',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 2.5, 16, 5.5, 18, 8], 'circle-color': reasonColor,
        'circle-stroke-color': '#fff', 'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 12, 0.3, 16, 1] } });
    map.addLayer({ id: 'wi-areas-fill', type: 'fill', source: 'wi-areas', paint: { 'fill-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'fill-opacity': 0.12 } });
    map.addLayer({ id: 'wi-areas-line', type: 'line', source: 'wi-areas', paint: { 'line-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'line-width': 2 } });
    // protected buildings (green) and raised homes (green with a ring), at every zoom
    map.addLayer({ id: 'wi-hit-halo', type: 'circle', source: 'wi-hit', filter: ['==', ['get', 't'], 'raised'],
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 7, 16, 12, 18, 16], 'circle-color': PROTECTED, 'circle-opacity': 0.15,
        'circle-stroke-color': PROTECTED, 'circle-stroke-width': 1.5 } });
    map.addLayer({ id: 'wi-hit', type: 'circle', source: 'wi-hit',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 3, 16, 5.5, 18, 9],
        'circle-color': PROTECTED, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.2 } });
    map.addLayer({ id: 'wi-walls-ghost', type: 'line', source: 'wi-walls', filter: ['==', ['get', 'ghost'], true],
      paint: { 'line-color': '#f47321', 'line-width': 2, 'line-opacity': 0.6, 'line-dasharray': [2, 2] } });
    map.addLayer({ id: 'wi-walls-case', type: 'line', source: 'wi-walls', filter: ['!=', ['get', 'ghost'], true], layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#fff', 'line-width': ['case', ['get', 'sel'], 11, 8] } });
    map.addLayer({ id: 'wi-walls', type: 'line', source: 'wi-walls', filter: ['!=', ['get', 'ghost'], true], layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'line-width': ['case', ['get', 'sel'], 7, 5] } });
    // numbered marker per project, visible at every zoom (the project chips use the same numbers)
    map.addLayer({ id: 'wi-marks-dot', type: 'circle', source: 'wi-marks',
      paint: { 'circle-radius': 11, 'circle-color': ['case', ['get', 'sel'], '#f47321', '#01321e'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } });
    map.addLayer({ id: 'wi-marks-num', type: 'symbol', source: 'wi-marks',
      layout: { 'text-field': ['to-string', ['get', 'num']], 'text-size': 12, 'text-allow-overlap': true, 'text-font': ['DIN Pro Bold', 'Arial Unicode MS Bold'] },
      paint: { 'text-color': '#fff' } });
    map.addLayer({ id: 'wi-draft-line', type: 'line', source: 'wi-draft', paint: { 'line-color': '#f47321', 'line-width': 3, 'line-dasharray': [2, 1] } });
    map.addLayer({ id: 'wi-draft-pts', type: 'circle', source: 'wi-draft', filter: ['==', ['geometry-type'], 'Point'],
      paint: { 'circle-radius': 4, 'circle-color': '#f47321', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1 } });
    mapReady = true;
    applyLayers();
    refreshBuildings();
    drawProjects();
  });

  function gridGeo() {
    if (!man) return EMPTY;
    return { type: 'FeatureCollection', features: man.tiles.map((t) => (
      { type: 'Feature', properties: { eyd: t.eyd_mid }, geometry: { type: 'Polygon', coordinates: [[...t.square, t.square[0]]] } })) };
  }

  /** What the map shows: simple by default, everything else under "Show why" (D-208). */
  function applyLayers() {
    if (!mapReady) return;
    const vis = (id, on) => map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
    for (const id of ['wi-grid', 'wi-dry', 'wi-basins-fill', 'wi-basins-line', 'wi-basins-label', 'wi-reason']) vis(id, why);
    vis('wi-links', why && showLinks);
    vis('wi-shore', why || tool === 'seawall' || drawing?.kind === 'wall');
    map.setPaintProperty('wi-buildings', 'circle-color', why ? damageExpr : STILL_FLOODS);
    renderLegend();
  }

  function renderLegend() {
    const p = projects[sel];
    const hasWall = projects.some((q) => q.kind === 'seawall');
    const items = [];
    const dot = (c, t, extra = '') => `<div><span class="sw" style="background:${c};${extra}"></span>${t}</div>`;
    if (!why) {
      if (projects.length) items.push(dot(PROTECTED, 'Protected'));
      items.push(dot(STILL_FLOODS, projects.length ? 'Still floods' : 'Floods in a storm today'));
      if (projects.some((q) => q.kind === 'elevation')) items.push(dot(PROTECTED, 'Raised home', 'box-shadow:0 0 0 3px rgba(26,127,75,0.25)'));
    } else {
      items.push(`<div class="ramp"><span>Yearly damage</span>${DAMAGE_STOPS.slice(1).map(([, c]) => `<i style="background:${c}"></i>`).join('')}<span>$100 to $50k+</span></div>`);
      items.push(dot('#fff', 'Stays dry in every storm', 'border:1px solid #9aa5ae'));
      if (p?.kind === 'seawall' && p.reasonCounts) {
        items.push(`<div class="lg-h">Near ${esc(p.name)}</div>`);
        for (const [k, v] of Object.entries(REASON_STYLE)) {
          if (p.reasonCounts[k]) items.push(`<div title="${esc(v.label)}"><span class="sw" style="background:${v.color}"></span>${v.short} <b>${fmt(p.reasonCounts[k])}</b></div>`);
        }
        items.push(`<label class="check"><input type="checkbox" id="links" ${showLinks ? 'checked' : ''}> Lines to nearest water</label>`);
      }
      items.push('<div><span class="ln"></span>Rain flooding modelled (C-8, C-9)</div>');
    }
    if (hasWall) items.push('<div><span class="ln" style="border-top:3px solid #f47321"></span>Wall</div>');
    if (why || tool === 'seawall' || drawing?.kind === 'wall') items.push('<div><span class="ln" style="border-top:2.5px solid #2f6db5"></span>Coast: walls go here</div>');
    if (map.getZoom() < BUILDING_ZOOM) items.push('<div class="muted">Zoom in to see buildings</div>');
    $('legend').innerHTML = `<label class="switch"><input type="checkbox" id="why" ${why ? 'checked' : ''}><span>Show why</span></label><div class="items">${items.join('')}</div>`;
  }
  function setWhy(on) { why = on; applyLayers(); refreshBuildings(); drawProjects(); }
  $('legend').addEventListener('change', (e) => {
    if (e.target.id === 'why') setWhy(e.target.checked);
    if (e.target.id === 'links') { showLinks = e.target.checked; applyLayers(); drawProjects(); }
  });

  async function refreshBuildings() {
    if (!mapReady || !man) return;
    renderLegend();
    if (map.getZoom() < BUILDING_ZOOM) return;
    const b = map.getBounds();
    const [x0, y0] = toUtm17(b.getWest(), b.getSouth());
    const [x1, y1] = toUtm17(b.getEast(), b.getNorth());
    const box = tilesForBox(x0, y0, x1, y1, man.tile_m);
    const keys = box.filter((k) => store.byKey.has(k)).slice(0, MAX_VIEW_TILES);
    const dkeys = why ? box.filter((k) => dryStore.byKey.has(k)).slice(0, MAX_VIEW_TILES) : [];
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
    if (!$('hint').hidden) hideHint();
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
      // the reason for every flooding building near the wall, same rule as Module C (D-204)
      const whyRes = seawallReasons(store.tiles, p.line, p.crest, ctx);
      p.res = whyRes.res;
      p.reasons = whyRes.items;
      p.reasonCounts = whyRes.counts;
      p.reasonOf = new Map(whyRes.items.map((q) => [`${q.key}|${q.i}`, q]));
      p.lengthFt = p.res.lengthM / FT;
      p.shoreM = shoreDistance(p.drawn || p.line);
      if (!p.costEdited) p.cost = Math.round(p.lengthFt * SETTINGS.seawall.unitCost);
    } else {
      if (p.mode === 'area') {
        const xs = p.ring.map((q) => toUtm17(q[0], q[1]));
        await store.ensure(tilesForBox(Math.min(...xs.map((q) => q[0])), Math.min(...xs.map((q) => q[1])),
          Math.max(...xs.map((q) => q[0])), Math.max(...xs.map((q) => q[1])), man.tile_m));
        p.picks = topHomes(store.tiles, p.ring, p.n, ctx);
        p.ranked = p.picks.ranked;
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
    if (!pts || !pts.length) return null;
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
        for (const q of p.res?.perBuilding || []) hits.push({ type: 'Feature', properties: { t: 'raised', k, bk: q.key, bi: q.i }, geometry: { type: 'Point', coordinates: [q.lon, q.lat] } });
      }
      if (p.kind === 'seawall' && p.reasons) {
        for (const q of p.reasons) {
          if (q.reason !== 'protected') continue;
          const c = store.tiles.get(q.key).cols;
          hits.push({ type: 'Feature', properties: { t: 'protected', k, bk: q.key, bi: q.i }, geometry: { type: 'Point', coordinates: [c.lon[q.i], c.lat[q.i]] } });
        }
      }
    });
    map.getSource('wi-walls').setData({ type: 'FeatureCollection', features: walls });
    map.getSource('wi-areas').setData({ type: 'FeatureCollection', features: areas });
    map.getSource('wi-hit').setData({ type: 'FeatureCollection', features: hits });
    const ps = projects[sel];
    const rs = []; const links = [];
    if (why && ps?.kind === 'seawall' && ps.reasons) {
      for (const q of ps.reasons) {
        const t = store.tiles.get(q.key);
        const at = [t.cols.lon[q.i], t.cols.lat[q.i]];
        rs.push({ type: 'Feature', properties: { r: q.reason, k: q.key, i: q.i }, geometry: { type: 'Point', coordinates: at } });
        if (showLinks) {
          const w = nearestWater(t, q.i, man);
          if (w.at) links.push({ type: 'Feature', properties: { r: q.reason }, geometry: { type: 'LineString', coordinates: [at, w.at] } });
        }
      }
    }
    map.getSource('wi-reason').setData({ type: 'FeatureCollection', features: rs });
    map.getSource('wi-links').setData({ type: 'FeatureCollection', features: links });
    renderLegend();
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

  // ---------------------------------------------------------------- results (one compact card, D-208)
  function renderProjectList() {
    if (projects.length < 2) { $('projects').innerHTML = ''; return; }
    $('projects').innerHTML = `<div class="chips-row">${projects.map((p, k) => (
      `<button type="button" data-sel="${k}" class="pchip ${k === sel ? 'on' : ''}" title="${esc(p.name)}">${k + 1} · ${p.res ? `${money(p.res.avoided.mid)}/yr` : '…'}</button>`)).join('')}
      <button type="button" class="btn small ghost" id="clear-all">Clear all</button></div>`;
  }

  /** Warnings and notes: one icon and one line each; the full text on hover or tap (data-tip). */
  function chip(kind, short, full) {
    return `<button type="button" class="wchip ${kind}" data-tip="${esc(full)}"><span class="ic" aria-hidden="true">${kind === 'warn' ? '!' : 'i'}</span>${esc(short)}</button>`;
  }

  function renderResults() {
    renderProjectList();
    const p = projects[sel];
    const el = $('results');
    if (!p || !p.res) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false;
    const r = p.res;
    const s = SETTINGS[p.kind];
    if (p.kind === 'elevation' && p.mode === 'area') $('n-homes').value = String(p.n);
    if (p.kind === 'seawall') { $('crest').value = String(p.crest); $('crest-out').textContent = `${p.crest} ft`; }
    else { $('raise').value = String(p.raise); $('raise-out').textContent = `${p.raise} ft`; }
    const b7 = benefitPerDollar(p.kind, r.avoided.mid, p.cost, SETTINGS.rates.main);
    const b3 = benefitPerDollar(p.kind, r.avoided.mid, p.cost, SETTINGS.rates.sensitivity);
    const b7lo = benefitPerDollar(p.kind, r.avoided.low, p.cost, SETTINGS.rates.main);
    const b7hi = benefitPerDollar(p.kind, r.avoided.high, p.cost, SETTINGS.rates.main);
    const chips = [];
    const notes = [];
    let what;
    if (p.kind === 'seawall') {
      what = `${fmt(p.lengthFt)} ft long, ${p.crest} ft high`;
      if (p.lengthFt < SHORT_WALL_FT) chips.push(chip('warn', 'Short wall: result may be too high', 'Under 200 ft. Water going around the ends of the wall is not modelled, so the result is likely too high.'));
      if (p.snapM == null && p.shoreM > MAX_SHORE_M) {
        chips.push(chip('warn', 'Too far from the coast to value', `This line is ${(p.shoreM / 1000).toFixed(1)} km from FEMA's coastal shoreline (the blue line along the bay and ocean). FEMA's coastal study does not cover the water here (a river, canal or lake), so the model cannot value this wall.`));
      }
      if (r.protectedMedianDistM != null && r.protectedMedianDistM > 600) {
        chips.push(chip('warn', 'Credited buildings are far from the wall', `Half the buildings credited to this wall are more than ${fmt(r.protectedMedianDistM)} m from it. That can be right on low ground, but check for small canals or creeks near them: FEMA's water lines miss some.`));
      }
      if (p.snapM > 5) {
        chips.push(chip('info', 'Moved onto the coast line', `Placed on FEMA's coastal shoreline, ${fmt(p.snapM)} m from where you drew it: the model can only test a wall on that line. Your line is shown dashed.`));
        notes.push(`Moved ${fmt(p.snapM)} m onto FEMA's coastal shoreline.`);
      }
      if (r.removedByInnerWater > 0) {
        chips.push(chip('info', `${plural(r.removedByInnerWater, 'building', 'buildings')} reached by canals not counted`, `${plural(r.removedByInnerWater, 'flooding building', 'flooding buildings')} behind the wall ${r.removedByInnerWater === 1 ? 'is' : 'are'} not counted, because a canal, creek or inner waterway is nearer than the shore, so water would reach ${r.removedByInnerWater === 1 ? 'it' : 'them'} around the wall.${r.removedByCapOnly ? ` ${fmt(r.removedByCapOnly)} more ${r.removedByCapOnly === 1 ? 'is' : 'are'} over 1 km from the wall.` : ''} Turn on Show why to see them.`));
      }
    } else {
      what = `${plural(p.homes, 'home', 'homes')}, raised ${p.raise} ft`;
      if (!p.homes) chips.push(chip('warn', p.mode === 'area' ? 'No flooding homes in this area' : 'No homes chosen yet', p.mode === 'area' ? 'No single-family homes that flood are inside this area. Draw a larger area or move it.' : 'Zoom in and click buildings to add them.'));
    }
    const areaLine = p.kind === 'elevation' && p.mode === 'area' && p.available
      ? `<p class="line">The ${p.homes === 1 ? 'most damaged' : `${fmt(p.homes)} most damaged`} of ${plural(p.available, 'flooding home', 'flooding homes')} here.${p.homes < p.available ? ` <button type="button" class="linkbtn" id="raise-all">Raise all ${fmt(p.available)}</button>` : ''}</p>` : '';
    const unit = p.kind === 'seawall' ? `$${SETTINGS.seawall.unitCost.toLocaleString('en-US')} per foot of wall (median of funded Miami-Dade seawalls)` : `$${SETTINGS.elevation.unitCost.toLocaleString('en-US')} per home (median FEMA home-raising grant in South Florida, 2025 dollars)`;
    const good = b7 >= 1;
    const share = r.valueBasePublished > 0 ? r.valueChangePublished / r.valueBasePublished : 0;
    el.innerHTML = `
      <div class="rhead"><div><b>${esc(p.name)}</b><span class="muted"> · ${what}</span></div><button type="button" class="linkbtn" id="remove">Remove</button></div>
      <p class="headline">Prevents about <b>${money(r.avoided.mid)}</b> a year in flood damage</p>
      ${areaLine}
      <div class="three">
        <div><span class="n">${fmt(r.buildingsProtected)}</span><span class="l">buildings protected</span></div>
        <div><span class="n">${fmt(r.residentsProtected)}</span><span class="l">residents protected</span></div>
        <div class="bcr ${good ? 'good' : 'poor'}"><span class="n">${ratio(b7)}</span><span class="l">back per $1</span><span class="badge">${good ? 'Pays back' : 'Does not pay back'}</span></div>
      </div>
      <div class="costrow">${editingCost
        ? `<label>Cost $<input type="number" id="cost" min="0" step="1000" value="${Math.round(p.cost)}" aria-label="Project cost in dollars"></label><button type="button" class="btn small" id="cost-done">Done</button>`
        : `Cost <b>${money(p.cost)}</b><button type="button" class="pencil" id="cost-edit" aria-label="Edit the cost" title="Edit the cost">✎</button>${p.costEdited ? '<span class="muted">(your cost)</span>' : ''}`}</div>
      <p class="basis">Based on 5 storm sizes, from the 10-year to the 500-year flood.</p>
      ${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}
      <details class="more" id="res-details"><summary>Details</summary>
        <table class="kv">
          <tr><th>Damage prevented a year</th><td>${money(r.avoided.mid)} middle; ${money(r.avoided.low)} to ${money(r.avoided.high)} low to high <span class="tag est">estimated</span></td></tr>
          <tr><th>Damage today, these buildings</th><td>${money(r.before.mid)} a year</td></tr>
          <tr><th>Back per $1 at 7%</th><td>${ratio(b7)} (FEMA rate since 2025; ${ratio(b7lo)} to ${ratio(b7hi)} low to high)</td></tr>
          <tr><th>Back per $1 at 3.1%</th><td>${ratio(b3)} (FEMA rate in 2023 and 2024, shown for comparison)</td></tr>
          <tr><th>Project life</th><td>${s.life} years (FEMA)${s.maint ? `; upkeep ${s.maint * 100}% of the cost a year <span class="tag asm">assumed</span>` : '; no upkeep'}</td></tr>
          <tr><th>Cost source</th><td>${unit} <span class="tag asm">assumed</span>${p.costEdited ? ' <button type="button" class="linkbtn" id="cost-reset">Use the typical cost</button>' : ''}</td></tr>
          <tr><th>Property value</th><td>About zero from local Miami-Dade sales <span class="tag est">estimated</span>. If homes gained value as in a published Miami study (about 3% for the 100-year flood zone): ${money(r.valueChangePublished)}${r.valueBasePublished > 0 ? ` (${(100 * share).toFixed(1)}% of these homes' value)` : ''} <span class="tag asm">assumed</span>. Kept out of benefit per dollar.</td></tr>
        </table>
        ${Math.abs(share) > 0.05 ? '<p class="warn">The property value figure is well above the 3% the study found: the scenario stretches that discount to homes with far more damage than a typical flood-zone home. Treat it as an upper bound.</p>' : ''}
        ${notes.map((n) => `<p class="muted">${esc(n)}</p>`).join('')}
        <p class="muted">Computed in ${r.ms.toFixed(1)} ms in your browser (${fmt(r.buildingsAffected)} buildings rerun${p.kind === 'seawall' ? `, ${fmt(r.candidates)} checked` : ''}).</p>
      </details>`;
    if (editingCost) { const i = $('cost'); i.focus(); i.select(); }
  }

  // ---------------------------------------------------------------- controls
  function setTool(t) {
    cancelDrawing();
    const next = tool === t ? null : t;
    // Examples is a tab of its own: leaving it takes the examples away and brings back the user's projects
    if (tool === 'examples' && next !== 'examples') leaveExamples();
    tool = next;
    document.querySelectorAll('[data-tool]').forEach((b) => { const on = b.dataset.tool === tool; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    $('tool-seawall').hidden = tool !== 'seawall';
    $('tool-elevation').hidden = tool !== 'elevation';
    renderElevHelp();
    applyLayers();
    if (tool === 'examples') loadExamples();
  }

  function leaveExamples() {
    projects.length = 0;
    if (ownProjects) projects.push(...ownProjects);
    ownProjects = null;
    sel = projects.length - 1;
    if (cardPopup) cardPopup.remove();
    drawProjects();
    renderResults();
  }

  function renderElevHelp() {
    document.querySelectorAll('[data-emode]').forEach((b) => { const on = b.dataset.emode === emode; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    $('n-field').hidden = emode !== 'area';
    $('elev-draw').textContent = emode === 'area' ? 'Draw an area' : 'Choose homes';
    $('elev-help').textContent = emode === 'area'
      ? 'Click the corners of an area, then double-click.'
      : `Zoom in and click buildings to add or remove them.`;
  }

  function cancelDrawing() {
    const wasWall = drawing?.kind === 'wall';
    drawing = null;
    map.doubleClickZoom.enable();
    map.getCanvas().style.cursor = '';
    $('wall-draw').classList.remove('active'); $('elev-draw').classList.remove('active');
    $('wall-finish').hidden = true; $('elev-finish').hidden = true;
    status('');
    if (mapReady) { drawProjects(); if (wasWall) applyLayers(); }
  }

  function startDrawing(kind) {
    if (!man) return;
    cancelDrawing();
    drawing = { kind, pts: [] };
    cardPopup.remove();
    map.doubleClickZoom.disable();
    map.getCanvas().style.cursor = 'crosshair';
    if (kind === 'wall') { $('wall-draw').classList.add('active'); $('wall-finish').hidden = false; status('Click along the coast; double-click to finish'); applyLayers(); }
    if (kind === 'area') { $('elev-draw').classList.add('active'); $('elev-finish').hidden = false; status('Click the corners; double-click to finish'); }
    if (kind === 'click') {
      $('elev-draw').classList.add('active'); $('elev-finish').hidden = false;
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
    if (!ownProjects) ownProjects = projects.filter((p) => !p.example);
    projects.length = 0;
    for (const e of examples) {
      if (e.kind === 'seawall') newProject('seawall', { example: true, name: e.label, line: e.line, drawn: e.line, onShore: true, snapM: 0, crest: e.crest_ft });
      else newProject('elevation', { example: true, name: e.label, mode: 'ids', fd_ids: e.fd_ids, tiles: e.tiles, raise: e.raise_ft });
    }
    await Promise.all(projects.map((p) => compute(p)));
    if (removed || tool !== 'examples') return; // the user left the tab while the examples were loading
    sel = 0;
    drawProjects();
    renderResults();
    const pts = projects.flatMap((p) => (p.kind === 'seawall' ? p.line : (p.res?.perBuilding || []).map((q) => [q.lon, q.lat])));
    if (pts.length) {
      const lo = pts.map((q) => q[0]); const la = pts.map((q) => q[1]);
      // fitBounds padding replaces the map's own padding, so keep room for the side column here
      map.fitBounds([[Math.min(...lo), Math.min(...la)], [Math.max(...lo), Math.max(...la)]], { padding: sidePad(), maxZoom: 13.5, duration: 600 });
    }
  }

  function toggleAbout(open) {
    const a = $('about');
    a.hidden = open === undefined ? !a.hidden : !open;
    $('about-btn').setAttribute('aria-expanded', String(!a.hidden));
    $('about-btn').classList.toggle('on', !a.hidden);
    if (!a.hidden) a.scrollIntoView({ block: 'nearest' });
  }

  function onPanelClick(e) {
    const t = e.target;
    if (t.closest('[data-tool]')) setTool(t.closest('[data-tool]').dataset.tool);
    else if (t.closest('[data-emode]')) { emode = t.closest('[data-emode]').dataset.emode; cancelDrawing(); renderElevHelp(); }
    else if (t.id === 'wall-draw') startDrawing('wall');
    else if (t.id === 'elev-draw') startDrawing(emode === 'area' ? 'area' : 'click');
    else if (t.id === 'wall-finish' || t.id === 'elev-finish') { if (drawing) finishDrawing(); else cancelDrawing(); }
    else if (t.id === 'about-btn') toggleAbout();
    else if (t.id === 'about-close') toggleAbout(false);
    else if (t.id === 'hint-close') hideHint();
    else if (t.id === 'clear-all') { cancelDrawing(); projects.length = 0; sel = -1; drawProjects(); renderResults(); }
    else if (t.id === 'remove') { projects.splice(sel, 1); sel = projects.length - 1; drawProjects(); renderResults(); }
    else if (t.id === 'raise-all') { const p = projects[sel]; p.n = p.available; $('n-homes').value = String(p.n); update(p); }
    else if (t.id === 'cost-edit') { editingCost = true; renderResults(); }
    else if (t.id === 'cost-done') { editingCost = false; renderResults(); }
    else if (t.id === 'cost-reset') { const p = projects[sel]; p.costEdited = false; update(p); }
    else if (t.closest('[data-sel]')) { sel = Number(t.closest('[data-sel]').dataset.sel); editingCost = false; drawProjects(); renderResults(); }
  }
  const panel = root.querySelector('.side');
  panel.addEventListener('click', onPanelClick);

  function onPanelInput(e) {
    const t = e.target;
    const p = projects[sel];
    if (t.id === 'crest') { $('crest-out').textContent = `${Number(t.value)} ft`; if (p?.kind === 'seawall') { p.crest = Number(t.value); update(p); } }
    if (t.id === 'raise') { $('raise-out').textContent = `${t.value} ft`; if (p?.kind === 'elevation') { p.raise = Number(t.value); update(p); } }
    if (t.id === 'n-homes' && p?.kind === 'elevation' && p.mode === 'area') { p.n = Math.max(1, Math.round(Number(t.value) || 1)); update(p); }
  }
  function onPanelChange(e) {
    if (e.target.id !== 'cost') return;
    const p = projects[sel];
    if (!p) return;
    p.cost = Math.max(0, Number(e.target.value) || 0);
    p.costEdited = true;
    editingCost = false;
    renderResults();
  }
  function onPanelKey(e) { if (e.target.id === 'cost' && e.key === 'Enter') e.target.blur(); }
  panel.addEventListener('input', onPanelInput);
  panel.addEventListener('change', onPanelChange);
  panel.addEventListener('keydown', onPanelKey);
  renderElevHelp();

  // ---------------------------------------------------------------- tooltips: hover, focus or tap (data-tip)
  const tipbox = $('tipbox');
  let tipFor = null;
  function showTip(el) {
    tipFor = el;
    tipbox.textContent = el.dataset.tip;
    tipbox.hidden = false;
    const r = el.getBoundingClientRect();
    const w = Math.min(280, window.innerWidth - 24);
    tipbox.style.width = `${w}px`;
    tipbox.style.left = `${Math.max(12, Math.min(r.left, window.innerWidth - w - 12))}px`;
    const below = r.bottom + 6;
    tipbox.style.top = `${below + tipbox.offsetHeight > window.innerHeight - 8 ? r.top - tipbox.offsetHeight - 6 : below}px`;
  }
  function hideTip() { tipFor = null; tipbox.hidden = true; }
  const onOver = (e) => { const el = e.target.closest?.('[data-tip]'); if (el && el !== tipFor) showTip(el); };
  const onOut = (e) => { const el = e.target.closest?.('[data-tip]'); if (el && !el.contains(e.relatedTarget)) hideTip(); };
  const onTap = (e) => { const el = e.target.closest?.('[data-tip]'); if (el) { if (tipFor === el) hideTip(); else showTip(el); } else if (tipFor) hideTip(); };
  root.addEventListener('mouseover', onOver);
  root.addEventListener('mouseout', onOut);
  root.addEventListener('focusin', onOver);
  root.addEventListener('focusout', hideTip);
  root.addEventListener('click', onTap);

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
    const layers = ['wi-hit', 'wi-reason', 'wi-buildings', 'wi-dry'].filter((l) => map.getLayoutProperty(l, 'visibility') !== 'none');
    const b = map.queryRenderedFeatures(e.point, { layers })[0];
    if (b && b.layer.id === 'wi-hit') { showCard(b.properties.bk, b.properties.bi); return; }
    if (b && b.properties.dk == null && b.properties.k != null && b.properties.i != null) { showCard(b.properties.k, b.properties.i); return; }
    if (b) { cardPopup.remove(); showDry(b, e.lngLat); return; }
    cardPopup.remove();
    const a = map.queryRenderedFeatures(e.point, { layers: ['wi-areas-fill'] })[0];
    if (a && a.properties.k != null) { sel = Number(a.properties.k); drawProjects(); renderResults(); }
  });

  // ---------------------------------------------------------------- building cards (D-204, short layout D-208)
  function makeCard(key, i) {
    const t = store.tiles.get(key);
    const p = projects[sel];
    const title = `Building ${t.cols.fd_id[i]}`;
    if (p?.kind === 'seawall' && p.reasonOf?.has(`${key}|${i}`)) {
      const q = p.reasonOf.get(`${key}|${i}`);
      const behind = q.reason === 'protected' || q.reason === 'overtopped';
      const water = nearestWater(t, i, man);
      const ex = explainBuilding(t, i, ctx, { crestFt: p.crest, protectedRow: behind && t.cols.ground[i] < p.crest });
      return { key, i, kind: 'seawall', behind, color: REASON_STYLE[q.reason].color, title,
        sentence: shortSentence(q.reason, water, ex), why: reasonSentence(q.reason, water, p.crest),
        facts: facts(t, i, man, { distWallM: q.distWallM }), ex };
    }
    if (p?.kind === 'elevation') {
      const picked = (p.picks || []).some((q) => q.key === key && q.i === i);
      let rank; let sentence; let whyText = '';
      if (p.mode === 'area') {
        const r = (p.ranked || []).findIndex((q) => q.key === key && q.i === i);
        if (r >= 0) {
          rank = `${fmt(r + 1)} of ${fmt(p.ranked.length)} flooding single-family homes in the area`;
          sentence = picked ? `Raised: it is among the ${fmt(p.n)} most damaged homes in the area.` : `Not raised: it ranks ${fmt(r + 1)} by damage, outside the top ${fmt(p.n)}.`;
          if (!picked) whyText = 'The table shows what raising it would do.';
        } else {
          sentence = 'Not a candidate: only single-family homes are raised in an area.';
          whyText = "The typical cost comes from FEMA grants for single-family homes; FEMA's records give no cost for duplexes, small apartment buildings or other types. To test this building, use Click homes and type a cost.";
        }
      } else if (p.mode === 'ids') {
        sentence = picked ? 'Raised: the most damaged single-family home in its census tract.' : 'Not raised.';
      } else sentence = picked ? 'Raised: you chose this building.' : 'Not raised.';
      return { key, i, kind: 'elevation', color: picked ? PROTECTED : '#6b7783', title, sentence, why: whyText,
        facts: facts(t, i, man, { rank }), ex: explainBuilding(t, i, ctx, { raiseFt: p.raise }) };
    }
    if (p?.kind === 'seawall') {
      return { key, i, kind: 'none', color: '#6b7783', title, sentence: 'Not near this wall: it is outside the area the wall is tested on.', facts: facts(t, i, man), ex: explainBuilding(t, i, ctx, {}) };
    }
    return { key, i, kind: 'none', color: '#6b7783', title, sentence: 'Floods in at least one storm today.', facts: facts(t, i, man), ex: explainBuilding(t, i, ctx, {}) };
  }
  // One building at a time (compare removed, D-209), opened on the map next to the building (D-211).
  function showCard(key, i) {
    infoPopup.remove(); popup.remove();
    const c = store.tiles.get(key).cols;
    const at = [c.lon[i], c.lat[i]];
    cardPopup.setLngLat(at).setHTML(cardHtml(makeCard(key, i))).addTo(map);
    // keep the card in view: if the building sits under the side column or near an edge, slide the map a little
    const p = map.project(at);
    const w = map.getContainer().clientWidth; const h = map.getContainer().clientHeight;
    const left = mobile() ? 20 : 400;
    const top = mobile() ? ($('side').getBoundingClientRect().bottom + 20) : 40;
    if (p.x < left + 170 || p.x > w - 170 || p.y < top + 260 || p.y > h - 40) {
      const tx = Math.min(Math.max(p.x, left + 170), w - 170);
      const ty = Math.min(Math.max(p.y, top + 260), h - 40);
      map.panBy([p.x - tx, p.y - ty], { duration: 400 });
    }
  }

  function showDry(f, lngLat) {
    const c = dryStore.tiles.get(f.properties.dk).cols; const i = f.properties.i;
    const html = `<b>Stays dry in all five storms</b><br>${c.res1[i] ? 'Single-family home' : 'Building'}${c.sqft[i] > 0 ? `, ${fmt(c.sqft[i])} sq ft` : ''}<br>About ${fmt(c.residents[i])} residents`;
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
    if (drag || infoPopup.isOpen()) return;
    popup.setLngLat(e.lngLat).setHTML(`Flood damage today: about <b>${money(e.features[0].properties.eyd)}</b> a year<br><span style="color:#6b7783">click for details</span>`).addTo(map);
  });
  map.on('mouseleave', 'wi-buildings', () => popup.remove());

  if (import.meta.env.DEV) {
    // for the timing check in the Part 2 report (drag measurement) and screenshots
    window.__whatIf = { map, projects, dragTimes, loadExamples: () => setTool('examples'), update, compute, showCard, setWhy, setTool, get sel() { return sel; }, get store() { return store; },
      add: (kind, extra) => update(newProject(kind, extra)) };
  }

  return () => {
    removed = true;
    panel.removeEventListener('click', onPanelClick);
    panel.removeEventListener('input', onPanelInput);
    panel.removeEventListener('change', onPanelChange);
    panel.removeEventListener('keydown', onPanelKey);
    root.removeEventListener('mouseover', onOver);
    root.removeEventListener('mouseout', onOut);
    root.removeEventListener('focusin', onOver);
    root.removeEventListener('focusout', hideTip);
    root.removeEventListener('click', onTap);
    popup.remove();
    infoPopup.remove();
    cardPopup.remove();
    map.remove();
    if (import.meta.env.DEV) delete window.__whatIf;
  };
}
