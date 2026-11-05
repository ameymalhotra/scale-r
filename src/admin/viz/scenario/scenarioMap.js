import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
// Small model summary, bundled so the About panel fills in before the map loads.
import scores from './data/scores.json';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Admin only (D-094). Built by "Modelling Data from Web/scripts/website/build_scenario_data.py" from the ML pipeline's
// export (scripts/ml/stage2b_map_model.py, scripts/ml/scenarios.py). Do not hand-edit.
const TRACTS_URL = new URL('./data/tracts.geojson', import.meta.url);
const SCENARIOS_URL = new URL('./data/scenarios.json', import.meta.url);

const LEVELS = {
  slr: [['slr_1ft', '1 ft'], ['slr_2ft', '2 ft'], ['slr_3ft', '3 ft'], ['slr_6ft', '6 ft']],
  surge: [['surge_cat1', 'Cat 1'], ['surge_cat2', 'Cat 2'], ['surge_cat3', 'Cat 3'], ['surge_cat4', 'Cat 4'], ['surge_cat5', 'Cat 5']],
  heat: [['heat_current', 'Now'], ['heat_plus1f', '+1°F'], ['heat_plus2f', '+2°F'], ['heat_plus3f', '+3°F']],
};
const CURRENT = { slr: 'slr_3ft', surge: 'surge_cat3', heat: 'heat_current' };
const HIGH_NEED = 0.75;

// Sequential ramps for shares and percentiles; a diverging ramp for the gaps (red = more need than investment).
const SEQ_LIKELY = ['#f1f5f4', '#b8dccf', '#5fae95', '#1f7a5c', '#01321e'];
const SEQ_NEED = ['#fff7ec', '#fdd49e', '#fc8d59', '#d7301f', '#7f0000'];
const DIVERGE = ['#2166ac', '#92c5de', '#f7f7f7', '#f4a582', '#b2182b'];
const LAYERS = {
  gap: {
    title: 'Gap: need vs actual investment',
    colors: DIVERGE, domain: [-1, 1], labels: ['more investment', 'balanced', 'more need'],
    note: 'Need rank minus the rank of sited dollars per resident actually received. Tracts outlined in orange have high need and no sited project.',
  },
  need: {
    title: 'Need', colors: SEQ_NEED, domain: [0, 1], labels: ['lowest', '', 'highest'],
    note: 'Hazard exposure (sea level rise, storm surge, heat) times social vulnerability, as a percentile. Kept separate from the model.',
  },
  likelihood: {
    title: 'Likely investment', colors: SEQ_LIKELY, domain: [0, 1], labels: ['0%', '50%', '100%'],
    note: 'Modelled chance that a tract has a sited project under current patterns of investment. It describes past placement, not where investment should go.',
  },
  gapExpected: {
    title: 'Need vs expected investment', colors: DIVERGE, domain: [-1, 1], labels: ['more expected', 'balanced', 'more need'],
    note: 'Need rank minus the rank of the modelled likelihood. A secondary view of the gap.',
  },
};

const pct = (v) => (v == null || Number.isNaN(v) ? 'n/a' : `${Math.round(v * 100)}%`);
const fmt = (n) => Math.round(n).toLocaleString();
const sgn = (v) => (v == null ? 'n/a' : `${v > 0 ? '+' : ''}${v.toFixed(2)}`);

/** Percentile of each value of x within base (average rank for ties), as in the Python pipeline. */
function pctWithin(base, x) {
  const b = base.filter((v) => v != null && !Number.isNaN(v)).sort((p, q) => p - q);
  const lower = (v) => { let lo = 0; let hi = b.length; while (lo < hi) { const m = (lo + hi) >> 1; if (b[m] < v) lo = m + 1; else hi = m; } return lo; };
  const upper = (v) => { let lo = 0; let hi = b.length; while (lo < hi) { const m = (lo + hi) >> 1; if (b[m] <= v) lo = m + 1; else hi = m; } return lo; };
  return x.map((v) => (v == null || Number.isNaN(v) ? null : (lower(v) + upper(v) + 1) / 2 / b.length));
}

function colorExpr(layer) {
  const { colors, domain: [lo, hi] } = LAYERS[layer];
  const stops = colors.flatMap((c, i) => [lo + ((hi - lo) * i) / (colors.length - 1), c]);
  return ['case', ['==', ['feature-state', 'v'], null], '#d9dde1',
    ['interpolate', ['linear'], ['to-number', ['feature-state', 'v']], ...stops]];
}

/** A diagonal hatch for tracts whose scenario values fall outside the training range. */
function hatchImage() {
  const s = 16;
  const c = document.createElement('canvas');
  c.width = s; c.height = s;
  const ctx = c.getContext('2d');
  ctx.strokeStyle = 'rgba(20, 20, 20, 0.55)';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(0, s); ctx.lineTo(s, 0); ctx.moveTo(-4, 4); ctx.lineTo(4, -4); ctx.moveTo(s - 4, s + 4); ctx.lineTo(s + 4, s - 4); ctx.stroke();
  return ctx.getImageData(0, 0, s, s);
}

function aboutHtml() {
  const c = (scores.T1_spatial_map_candidates || []);
  const rows = c.map((r) => `<tr><td>${r.model}</td><td>${r.roc_auc.toFixed(2)}</td><td>${r.pr_auc.toFixed(2)}</td></tr>`).join('');
  const t2 = scores.T2 || {};
  const conf = scores.conformal_T1 || {};
  return `
    <p>The model learns <b>where resilience projects have been sited</b> in Miami-Dade (completed, funded and ongoing projects at parcel, neighborhood or corridor scale) from each tract's social, hazard and location characteristics. A simple logistic regression does as well as the machine learning models, so the map uses it.</p>
    <h3>How well it does (spatial validation)</h3>
    <table><thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th></tr></thead><tbody>${rows}</tbody></table>
    <p>A tract chosen at random has a sited project ${pct(scores.T1_base_rate)} of the time. Spatial validation tests the model on whole areas it never saw.</p>
    <p><b>Future check:</b> the fifth of tracts the model ranks highest hold ${pct(t2.share_of_planned_projects_in_top20pct)} of the planned projects, which the model never saw.</p>
    <p><b>Uncertainty:</b> each tract's range is a conformal interval; the 90% prediction sets covered ${pct(conf.achieved_coverage)} of tracts.</p>
    <h3>What it shows, and what it does not</h3>
    <ul class="lim">
      <li><b>It learns past patterns.</b> Past investment follows coastal location, density and general risk more than the specific hazard maps, so hazard scenarios move it very little. Their value is in need and the gap.</li>
      <li><b>Coverage, not damages avoided.</b> There is no outcome data yet; flood insurance claims (OpenFEMA NFIP) are the next step.</li>
      <li><b>Not where money should go.</b> Read predicted investment next to need and the gap.</li>
      <li><b>Heat warming steps are illustrative</b> (+1 to +3°F, not projections) and change need and the gap only.</li>
      <li><b>Hatched tracts</b> have scenario values beyond anything in the training data (extrapolation).</li>
      <li><b>Preliminary.</b> Census tracts only; hazard maps are screening-level and predate many projects. No dollar predictions are shown: the amount model was not reliable enough.</li>
    </ul>
    <div class="caveat">Full details: model card and Stage 2 report in "Modelling Data from Web/reports/ml/".</div>`;
}

/** Builds the map into the markup already on the page; returns a cleanup function. */
export function mount() {
  let removed = false;
  const $ = (id) => document.getElementById(id);
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/light-v11',
    center: [-80.35, 25.65],
    zoom: 9.4,
    padding: window.innerWidth > 768 ? { left: 380 } : { bottom: window.innerHeight * 0.5 },
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
  if (import.meta.env.DEV) window.__scenarioMap = map;

  let layer = 'gap';
  let family = 'slr';
  let scenarioId = CURRENT.slr;
  let selecting = false;
  const selected = new Set();
  let tracts = null; // feature properties, in tract order
  let byId = null;
  let base = null; // current-state arrays
  let clickedIndex = null;
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, className: 'tip', offset: 8 });

  $('about').innerHTML = aboutHtml();

  /** Arrays for the chosen scenario, with the map model's prediction shifted by the scenario model's change. */
  function current() {
    const s = byId[scenarioId];
    const likelihood = base.pred.map((p, i) => (p == null ? null : Math.min(1, Math.max(0, p + (s.change[i] || 0)))));
    const predPct = pctWithin(base.pred, likelihood);
    const gapExpected = s.need_pct.map((n, i) => (n == null || predPct[i] == null ? null : n - predPct[i]));
    return { s, likelihood, gapExpected, need: s.need_pct, gap: s.gap_actual, flag: s.high_need_no_sited_project, extrap: s.extrapolated };
  }

  function renderLegend() {
    const L = LAYERS[layer];
    $('ramp').style.background = `linear-gradient(90deg, ${L.colors.join(', ')})`;
    $('ramp-labels').innerHTML = L.labels.map((t) => `<span>${t}</span>`).join('');
    $('ramp-note').textContent = L.note;
  }

  function renderLevels() {
    $('levels').innerHTML = LEVELS[family]
      .map(([id, label]) => `<button type="button" data-level="${id}" class="${id === scenarioId ? 'on' : ''}">${label}</button>`).join('');
    $('levels').querySelectorAll('[data-level]').forEach((b) => b.addEventListener('click', () => { scenarioId = b.dataset.level; render(); }));
    const notes = {
      slr: 'Residents on land flooded at each sea level (NOAA, ocean-connected). 3 ft is the current baseline used everywhere else.',
      surge: 'Residents on land reached by worst-case surge for each hurricane category (NHC). Category 3 is the baseline. Category 5 uses the corrected version.',
      heat: 'Heat scenarios change need and the gap only. They do not change predicted investment, because past investment did not follow heat. +1 to +3°F are illustrative uniform warming, not projections.',
    };
    $('scenario-note').textContent = notes[family];
  }

  function renderSummary(cur) {
    const pop = base.population;
    let flagged = 0; let flaggedPop = 0; let gapHigh = 0; let ext = 0; let extPop = 0; let expected = 0;
    cur.flag.forEach((f, i) => { if (f) { flagged += 1; flaggedPop += pop[i]; } });
    cur.gap.forEach((g) => { if (g != null && g >= 0.5) gapHigh += 1; });
    cur.extrap.forEach((e, i) => { if (e) { ext += 1; extPop += pop[i]; } });
    cur.likelihood.forEach((p) => { expected += p || 0; });
    const s = cur.s.summary;
    $('summary').innerHTML = `
      <div class="wide"><div class="n">${fmt(flagged)} tracts</div><div class="l">high need and no sited project (${fmt(flaggedPop)} residents)</div></div>
      <div><div class="n">${fmt(s.residents_exposed)}</div><div class="l">residents exposed in this scenario</div></div>
      <div><div class="n">${fmt(gapHigh)}</div><div class="l">tracts with a large gap (0.5 or more)</div></div>
      <div><div class="n">${fmt(expected)}</div><div class="l">tracts expected to have a sited project, under current patterns</div></div>
      <div><div class="n">${fmt(ext)}</div><div class="l">tracts beyond the training range${ext ? ` (${fmt(extPop)} residents), hatched` : ''}</div></div>`;
  }

  function renderTract(cur) {
    if (clickedIndex == null) return;
    const i = clickedIndex;
    const t = tracts[i];
    const tags = [];
    if (t.T1_observed) tags.push('<span class="tag">has a sited project</span>');
    if (cur.flag[i]) tags.push('<span class="tag warn">high need, no sited project</span>');
    if (cur.extrap[i]) tags.push('<span class="tag warn">extrapolated in this scenario</span>');
    if (t.low_pop_flag) tags.push('<span class="tag warn">under 100 residents: not used in training</span>');
    const changed = scenarioId !== CURRENT[family];
    $('tract').innerHTML = `
      <p><b>${t.jurisdiction}</b>, tract ${t.GEOID} · ${fmt(t.population)} residents</p>
      <div>${tags.join('')}</div>
      <dl>
        <dt>Likely investment${changed ? ' (this scenario)' : ''}</dt><dd>${pct(cur.likelihood[i])}</dd>
        <dt>Range (current, conformal)</dt><dd>${t.interval_lo == null ? 'n/a' : `${pct(t.interval_lo)} to ${pct(t.interval_hi)}`}</dd>
        <dt>Need (percentile)</dt><dd>${pct(cur.need[i])}</dd>
        <dt>Gap: need vs investment</dt><dd>${sgn(cur.gap[i])}</dd>
        <dt>Need vs expected</dt><dd>${sgn(cur.gapExpected[i])}</dd>
        <dt>Planned projects here</dt><dd>${t.T2_planned_projects}</dd>
      </dl>
      <h3>What drives its likelihood most</h3>
      <ul>${[t.driver1, t.driver2, t.driver3].filter(Boolean).map((d) => `<li>${d}</li>`).join('')}</ul>`;
  }

  /** Coverage of the selected tracts, and the change in the actual-investment gap if they were funded. */
  function renderInterventions() {
    const out = $('iresult');
    if (!selected.size) { out.innerHTML = '<p class="muted">No tracts selected.</p>'; return; }
    const sel = [...selected];
    const obs = base.obs;
    const positive = obs.filter((v) => v > 0).sort((a, b) => a - b);
    const mid = positive.length >> 1;
    // the same median as interventions.py (pandas): mean of the two middle values when the count is even
    const add = positive.length ? (positive.length % 2 ? positive[mid] : (positive[mid - 1] + positive[mid]) / 2) : 0;
    const after = obs.map((v, i) => (selected.has(i) ? v + add : v));
    const sitedBefore = pctWithin(obs, obs);
    const sitedAfter = pctWithin(after, after);
    const gapB = base.need.map((n, i) => (n == null ? null : n - sitedBefore[i]));
    const gapA = base.need.map((n, i) => (n == null ? null : n - sitedAfter[i]));
    const flagB = base.need.map((n, i) => n != null && n >= HIGH_NEED && !tracts[i].T1_observed);
    const flagA = flagB.map((f, i) => f && !selected.has(i));
    const sum = (arr) => arr.reduce((a, b) => a + b, 0);
    const residents = sum(sel.map((i) => base.population[i]));
    const vulnerable = sum(sel.map((i) => (base.vulPct[i] != null && base.vulPct[i] >= 2 / 3 ? base.population[i] : 0)));
    const ex = (k) => sum(sel.map((i) => tracts[i][k] || 0));
    const nB = sum(flagB.map(Number)); const nA = sum(flagA.map(Number));
    const mean = (arr) => { const v = sel.map((i) => arr[i]).filter((x) => x != null); return v.length ? sum(v) / v.length : null; };
    const type = $('itype').value === 'gray' ? 'gray' : 'nature-based or hybrid';
    out.innerHTML = `
      <div class="stats">
        <div><div class="n">${fmt(residents)}</div><div class="l">residents in ${sel.length} tract${sel.length > 1 ? 's' : ''}</div></div>
        <div><div class="n">${fmt(vulnerable)}</div><div class="l">in the most vulnerable third of tracts</div></div>
        <div><div class="n">${fmt(ex('slr_3ft_pop_exposed'))}</div><div class="l">exposed to 3 ft sea level rise</div></div>
        <div><div class="n">${fmt(ex('surge_cat3_any_pop_exposed'))}</div><div class="l">exposed to Category 3 surge</div></div>
        <div><div class="n">${fmt(ex('surge_cat4_any_pop_exposed'))}</div><div class="l">exposed to Category 4 surge</div></div>
        <div><div class="n">${fmt(ex('heat_p95_pop_exposed'))}</div><div class="l">on the hottest 5% of land</div></div>
        <div class="wide"><div class="n">${nB} → ${nA}</div><div class="l">tracts with high need and no sited project, if these got a ${type} project</div></div>
        <div class="wide"><div class="n">${sgn(mean(gapB))} → ${sgn(mean(gapA))}</div><div class="l">average gap of the selected tracts (assuming the county median, $${fmt(add)} per resident)</div></div>
      </div>
      <p class="note">Current conditions. Coverage only: no damages avoided are estimated.</p>`;
  }

  function render() {
    if (!tracts) return;
    const cur = current();
    const v = cur[layer === 'likelihood' ? 'likelihood' : layer];
    for (let i = 0; i < tracts.length; i += 1) {
      map.setFeatureState({ source: 'tracts', id: i }, {
        v: v[i], extrap: !!cur.extrap[i], flag: layer === 'gap' && !!cur.flag[i], sel: selected.has(i),
      });
    }
    if (map.getLayer('tract-fill')) map.setPaintProperty('tract-fill', 'fill-color', colorExpr(layer));
    document.querySelectorAll('[data-layer]').forEach((b) => b.classList.toggle('on', b.dataset.layer === layer));
    document.querySelectorAll('[data-family]').forEach((b) => b.classList.toggle('on', b.dataset.family === family));
    renderLevels();
    renderLegend();
    renderSummary(cur);
    renderTract(cur);
    renderInterventions();
  }

  const ready = Promise.all([fetch(TRACTS_URL).then((r) => r.json()), fetch(SCENARIOS_URL).then((r) => r.json())]);
  map.on('load', async () => {
    const [geo, sc] = await ready;
    if (removed) return;
    byId = Object.fromEntries(sc.scenarios.map((s) => [s.id, s]));
    tracts = [];
    geo.features.forEach((f) => { tracts[f.id] = f.properties; });
    const vul = tracts.map((t) => t.vulnerability_rc1);
    base = {
      pred: tracts.map((t) => t.pred_likelihood),
      need: tracts.map((t) => t.need_pct),
      obs: tracts.map((t) => t.sited_dollars_per_resident_observed || 0),
      population: tracts.map((t) => t.population || 0),
      vulPct: pctWithin(vul, vul),
    };
    map.addImage('hatch', hatchImage());
    map.addSource('tracts', { type: 'geojson', data: geo });
    const below = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;
    map.addLayer({ id: 'tract-fill', type: 'fill', source: 'tracts', paint: { 'fill-color': colorExpr(layer), 'fill-opacity': 0.78 } }, below);
    map.addLayer({
      id: 'tract-hatch', type: 'fill', source: 'tracts',
      paint: { 'fill-pattern': 'hatch', 'fill-opacity': ['case', ['boolean', ['feature-state', 'extrap'], false], 1, 0] },
    }, below);
    map.addLayer({ id: 'tract-line', type: 'line', source: 'tracts', paint: { 'line-color': 'rgba(255,255,255,0.7)', 'line-width': 0.4 } }, below);
    map.addLayer({
      id: 'tract-flag', type: 'line', source: 'tracts',
      paint: { 'line-color': '#f47321', 'line-width': ['case', ['boolean', ['feature-state', 'flag'], false], 2, 0] },
    }, below);
    map.addLayer({
      id: 'tract-low-pop', type: 'line', source: 'tracts', filter: ['==', ['get', 'low_pop_flag'], 1],
      paint: { 'line-color': '#6b7783', 'line-width': 1.5, 'line-dasharray': [2, 2] },
    }, below);
    map.addLayer({
      id: 'tract-sel', type: 'line', source: 'tracts',
      paint: { 'line-color': '#01321e', 'line-width': ['case', ['boolean', ['feature-state', 'sel'], false], 3, 0] },
    }, below);
    render();

    map.on('mousemove', 'tract-fill', (e) => {
      const f = e.features[0];
      map.getCanvas().style.cursor = 'pointer';
      const t = tracts[f.id];
      popup.setLngLat(e.lngLat).setHTML(`${t.jurisdiction} · ${fmt(t.population)} residents`).addTo(map);
    });
    map.on('mouseleave', 'tract-fill', () => { map.getCanvas().style.cursor = ''; popup.remove(); });
    map.on('click', 'tract-fill', (e) => {
      const i = e.features[0].id;
      if (selecting) {
        if (selected.has(i)) selected.delete(i); else selected.add(i);
      }
      clickedIndex = i;
      render();
    });
  });

  const controller = new AbortController();
  const listening = { signal: controller.signal };
  document.querySelectorAll('[data-layer]').forEach((b) => b.addEventListener('click', () => { layer = b.dataset.layer; render(); }, listening));
  document.querySelectorAll('[data-family]').forEach((b) => b.addEventListener('click', () => {
    family = b.dataset.family;
    scenarioId = CURRENT[family];
    render();
  }, listening));
  $('select-toggle').addEventListener('click', () => {
    selecting = !selecting;
    $('select-toggle').classList.toggle('on', selecting);
    $('select-toggle').textContent = selecting ? 'Selecting: click tracts' : 'Select tracts on the map';
  }, listening);
  $('select-clear').addEventListener('click', () => { selected.clear(); render(); }, listening);
  $('itype').addEventListener('change', () => renderInterventions(), listening);
  renderLevels();
  renderLegend();

  return () => {
    removed = true;
    controller.abort();
    popup.remove();
    map.remove();
  };
}
