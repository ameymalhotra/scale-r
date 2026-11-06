import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
// Small Stage 2 summary, bundled so the About panel fills in before the map loads.
import scores from './data/scores.json';
import { MODELS, median, pctWithin, summary } from './scenarioModel.js';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

// Admin only (D-094). Built by "Modelling Data from Web/scripts/website/build_scenario_data.py" from the ML
// pipeline's export (stage2b_map_model.py, stage4_dashboard.py). Do not hand-edit. Both models: D-109.
const TRACTS_URL = new URL('./data/tracts.geojson', import.meta.url);
const MODELS_URL = new URL('./data/models.json', import.meta.url);
const COMPARE_URL = new URL('./data/compare.json', import.meta.url);

const SEQ_LIKELY = ['#f1f5f4', '#b8dccf', '#5fae95', '#1f7a5c', '#01321e'];
const SEQ_NEED = ['#fff7ec', '#fdd49e', '#fc8d59', '#d7301f', '#7f0000'];
const DIVERGE = ['#2166ac', '#92c5de', '#f7f7f7', '#f4a582', '#b2182b'];
const PURPLE_GREEN = ['#7b3294', '#c2a5cf', '#f7f7f7', '#a6dba0', '#008837'];
const LAYERS = {
  gap: {
    colors: DIVERGE, domain: [-1, 1], labels: ['more investment', 'balanced', 'more need'],
    note: 'Same for both models. Need rank minus the rank of sited dollars per resident actually received. Tracts outlined in orange have high need and no sited project.',
  },
  need: {
    colors: SEQ_NEED, domain: [0, 1], labels: ['lowest', '', 'highest'],
    note: 'Same for both models. Hazard exposure (sea level rise, storm surge, heat) times social vulnerability, as a percentile.',
  },
  likelihood: {
    colors: SEQ_LIKELY, domain: [0, 1], labels: ['0%', '50%', '100%'],
    note: 'Changes with the model. Chance that a tract has a sited project under current patterns of investment, predicted for each area by a fit that never saw it. It describes past placement, not where investment should go.',
  },
  gapExpected: {
    colors: DIVERGE, domain: [-1, 1], labels: ['more expected', 'balanced', 'more need'],
    note: 'Changes with the model. Need rank minus the rank of the predicted likelihood. A secondary view of the gap.',
  },
  diff: {
    colors: PURPLE_GREEN, domain: [-0.6, 0.6], labels: ['machine learning higher', 'agree', 'Bayesian higher'],
    note: 'Current conditions. Bayesian likelihood minus machine learning likelihood, both out-of-fold.',
  },
  neighbourhood: {
    colors: DIVERGE, domain: [-5, 5], labels: ['fewer projects than features predict', 'as predicted', 'more'],
    note: 'Bayesian only. The smooth spatial effect on the log-odds of a sited project: what neighbouring tracts share beyond their features. It does not say why.',
  },
  city: {
    colors: DIVERGE, domain: [-0.7, 0.7], labels: ['lower', 'county average', 'higher'],
    note: 'Bayesian only. Each jurisdiction\'s effect on the log-odds. Every interval includes zero; see the list below.',
  },
};
const FAMILY_NOTES = {
  slr: 'NOAA ocean-connected flooding. 3 ft is the level the models were trained on.',
  surge: 'NHC worst-case surge by hurricane category. Category 3 is the training level; Category 5 is the corrected version.',
  heat: 'Heat +1 to +3°F are illustrative uniform warming, not projections. Heat changes need and the gap only, for both models.',
};

const pct = (v) => (v == null || Number.isNaN(v) ? 'n/a' : `${Math.round(v * 100)}%`);
const fmt = (n) => (n == null ? 'n/a' : Math.round(n).toLocaleString());
const sgn = (v, d = 2) => (v == null ? 'n/a' : `${v > 0 ? '+' : ''}${v.toFixed(d)}`);
const money = (v) => `$${fmt(v)}`;
const range = (lo, hi) => (lo == null || hi == null ? 'n/a' : `${pct(lo)} to ${pct(hi)}`);

function colorExpr(layer) {
  const { colors, domain: [lo, hi] } = LAYERS[layer];
  const stops = colors.flatMap((c, i) => [lo + ((hi - lo) * i) / (colors.length - 1), c]);
  return ['case', ['==', ['feature-state', 'v'], null], '#d9dde1',
    ['interpolate', ['linear'], ['to-number', ['feature-state', 'v']], ...stops]];
}

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

function bbox(geom) {
  let x0 = Infinity; let y0 = Infinity; let x1 = -Infinity; let y1 = -Infinity;
  const walk = (a) => { if (typeof a[0] === 'number') { x0 = Math.min(x0, a[0]); x1 = Math.max(x1, a[0]); y0 = Math.min(y0, a[1]); y1 = Math.max(y1, a[1]); } else a.forEach(walk); };
  walk(geom.coordinates);
  return [[x0, y0], [x1, y1]];
}

function modelNote(model) {
  return model === 'bayes'
    ? 'Main model (D-104). Bayesian Model 1: tract features, a city effect and a neighbourhood spatial effect, with 90% credible intervals. It is not monotone: because past projects went less often to tracts with more residents in the 3 ft zone, higher sea level lowers its predictions.'
    : 'Stage 2/3 setup: logistic regression for likelihood (Venn-ABERS calibrated), monotone XGBoost for scenario changes, so more hazard can never lower a prediction.';
}

function aboutHtml(cmp) {
  const b = cmp ? cmp.cv.find((r) => r.key === 'bayes') : null;
  const m = cmp ? cmp.cv.find((r) => r.key === 'ml_shown') : null;
  return `
    <p>Both models learn <b>where resilience projects have been sited</b> in Miami-Dade (completed, funded and ongoing projects at parcel, neighborhood or corridor scale) from each tract's social, hazard and location characteristics.</p>
    <ul class="lim">
      <li><b>Bayesian multiscale model</b> (the main model): adds a city effect and a neighbourhood spatial effect, and gives credible intervals.${b ? ` Spatial validation: ROC-AUC ${b.roc_auc.toFixed(2)}.` : ''}</li>
      <li><b>Machine learning model</b> (Stage 2/3): logistic regression for the map, monotone XGBoost for scenarios.${m ? ` Spatial validation, as shown: ROC-AUC ${m.roc_auc.toFixed(2)}.` : ''}</li>
      <li><b>Need and the gap</b> do not depend on either model.</li>
    </ul>
    <h3>Heat</h3>
    <p>Hotter tracts receive less investment. After controls, this is explained mainly by distance from the coast (inland location), not by heat itself.</p>
    <h3>What it shows, and what it does not</h3>
    <ul class="lim">
      <li><b>It learns past patterns.</b> Past investment follows coastal location, density and general risk more than the specific hazard maps.</li>
      <li><b>Coverage, not damages avoided.</b> There is no outcome data yet; flood insurance claims (OpenFEMA NFIP) are the next step.</li>
      <li><b>Not where money should go.</b> Read predicted investment next to need and the gap.</li>
      <li><b>Heat warming steps are illustrative</b> (+1 to +3°F, not projections) and change need and the gap only.</li>
      <li><b>Hatched tracts</b> have scenario values beyond anything in the training data (extrapolation).</li>
      <li><b>No dollar predictions are shown.</b> The Bayesian model's 90% range for one tract's dollars per resident spans about $28 to $8,700.</li>
      <li><b>Preliminary.</b> Census tracts only; hazard maps are screening-level and predate many projects. A project's type (gray, green, blue, hybrid) cannot be predicted reliably for blue or hybrid.</li>
    </ul>
    <div class="caveat">Full details: model card and the Stage 2 and Stage 4 reports in "Modelling Data from Web/reports/ml/". Stage 2 future check: the fifth of tracts ranked highest hold ${pct(scores.T2?.share_of_planned_projects_in_top20pct)} of planned projects.</div>`;
}

function compareHtml(cmp) {
  const f3 = (v) => v.toFixed(3);
  const rows = cmp.cv.map((r) => `<tr><td>${r.model}</td><td>${f3(r.roc_auc)}</td><td>${f3(r.pr_auc)}</td><td>${f3(r.log_loss)}</td><td>${f3(r.brier)}</td></tr>`).join('');
  const ci = (r, k) => `${sgn(r.point[k], 3)}<br><span class="muted">${sgn(r[k][0], 3)} to ${sgn(r[k][1], 3)}</span>`;
  const drows = cmp.cv_diffs.map((r) => `<tr><td>${r.comparison}</td><td>${ci(r, 'roc_auc')}</td><td>${ci(r, 'pr_auc')}</td><td>${ci(r, 'log_loss')}</td><td>${ci(r, 'brier')}</td></tr>`).join('');
  const dis = cmp.disagree.map((r) => `<li><button type="button" class="link" data-tract="${r.i}">${r.jurisdiction}, ${r.GEOID}</button>: Bayesian ${pct(r.bayes)}, machine learning ${pct(r.ml)} (${r.observed ? 'has' : 'no'} sited project)</li>`).join('');
  const dml = cmp.drivers_ml.map((d) => `<li>${d.plain} <span class="muted">(${d.coefficient > 0 ? 'raises' : 'lowers'})</span></li>`).join('');
  const dby = cmp.drivers_bayes.map((d) => `<li>${d.plain} <span class="muted">(odds ×${d.odds_ratio.toFixed(2)}, ${d.or_lo.toFixed(2)} to ${d.or_hi.toFixed(2)})</span></li>`).join('');
  const lo = -3.5; const hi = 2.5;
  const x = (v) => `${((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * 100}%`;
  const city = cmp.city.map((c) => `<div class="forest"><span class="fl">${c.jurisdiction}${c.tracts < 3 ? '*' : ''}</span><span class="fbar"><i class="zero" style="left:${x(0)}"></i><i class="ci" style="left:${x(c.lo)};width:calc(${x(c.hi)} - ${x(c.lo)})"></i><i class="pt" style="left:${x(c.mean)}"></i></span></div>`).join('');
  // the latent (tract-specific) model 1 row depends on the prior (Stage 4 report 5.6); show the population-averaged one
  const heat = cmp.heat.filter((h) => h.part === 'Part 1' && !h.model.startsWith('model 1 (')).map((h) => `<tr><td>${h.model}</td><td>${h.effect.toFixed(2)} <span class="muted">(${h.lo.toFixed(2)} to ${h.hi.toFixed(2)})</span></td></tr>`).join('');
  return `
    <h3>How well each predicts (spatial validation)</h3>
    <table class="small"><thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th><th>Log loss</th><th>Brier</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="note">${cmp.cv_note} Higher ROC-AUC and PR-AUC, and lower log loss and Brier, are better.</p>
    <h3>Difference, with 95% bootstrap interval</h3>
    <table class="small"><thead><tr><th></th><th>ROC-AUC</th><th>PR-AUC</th><th>Log loss</th><th>Brier</th></tr></thead><tbody>${drows}</tbody></table>
    <p class="note">Residual clustering (Moran's I of out-of-fold errors, lower is better): Bayesian ${cmp.moran.bayes.toFixed(3)}, logistic ${cmp.moran.logistic.toFixed(3)}, XGBoost ${cmp.moran.xgb.toFixed(3)}.</p>
    <h3>Where they disagree most</h3>
    <ul class="dis">${dis}</ul>
    <div class="tract" id="ctract" hidden></div>
    <h3>Top drivers</h3>
    <div class="two"><div><b>Machine learning</b><ol>${dml}</ol></div><div><b>Bayesian</b><ol>${dby}</ol></div></div>
    <p class="note">Machine learning: logistic coefficients ranked by average contribution. Bayesian: population-averaged odds ratio per standard deviation, with 95% interval.</p>
    <h3>Only the Bayesian model shows</h3>
    <p><b>City effects</b> (log-odds, 95% interval; * fewer than 3 tracts, so no information):</p>
    <div class="forests">${city}</div>
    <p class="note">The neighbourhood and city effect maps are under "Map shows" above.</p>
    <p><b>Heat after controls</b> (odds ratio of a sited project per 4°F hotter):</p>
    <table class="small"><tbody>${heat}</tbody></table>
    <p class="note">Hotter tracts receive less investment. After controls, this is explained mainly by distance from the coast (inland location), not by heat itself.</p>
    <h3>When to trust each</h3>
    <ul class="lim">
      <li><b>Both predict about equally well</b> on areas they have not seen, against the uncalibrated logistic and XGBoost models. Against the calibrated probabilities the machine learning map shows, the Bayesian model ranks tracts better (ROC-AUC +0.04, interval above zero).</li>
      <li><b>Use the Bayesian model</b> for uncertainty and for questions about scale: city versus neighbourhood, and effects with intervals. Its wide tract intervals are honest: a tract's local pattern is hard to predict from its features.</li>
      <li><b>Use the machine learning model</b> for a narrow, stable ranking and for scenarios where more hazard should never lower a prediction. Its narrow ranges measure calibration only, not all the uncertainty.</li>
      <li><b>Watch the extremes.</b> In large, sparse tracts the Bayesian model can be very sure and still wrong (for example 97% for a rural tract with no sited project), because an area it has not seen gets no neighbourhood correction.</li>
      <li><b>For scenarios beyond 3 ft or Category 3</b>, both extrapolate (hatched tracts). The Bayesian model then follows its negative sea level effect downwards; the machine learning model is held flat or up by design. Treat both as "what past patterns imply", not forecasts.</li>
    </ul>`;
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
    padding: window.innerWidth > 768 ? { left: 400 } : { bottom: window.innerHeight * 0.5 },
  });
  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
  if (import.meta.env.DEV) window.__scenarioMap = map;

  let model = 'bayes';
  let view = 'scenarios';
  let layer = 'gap';
  let clayer = 'diff';
  let levels = { slr: 'slr_3ft', surge: 'surge_cat3', heat: 'heat_current' };
  let selecting = false;
  const selected = new Set();
  let tracts = null;
  let data = null;
  let cmp = null;
  let boxes = null;
  let clickedIndex = null;
  const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, className: 'tip', offset: 8 });

  $('about').innerHTML = aboutHtml(null);
  $('model-note').textContent = modelNote(model);

  const presetOf = () => (data ? data.presets.find((p) => p.slr === levels.slr && p.surge === levels.surge && p.heat === levels.heat) : null);
  const label = (fam, id) => (data.levels[fam].find(([k]) => k === id) || [id, id])[1];

  function renderLegend(id, which) {
    const L = LAYERS[which];
    $(id).style.background = `linear-gradient(90deg, ${L.colors.join(', ')})`;
    $(`${id}-labels`).innerHTML = L.labels.map((t) => `<span>${t}</span>`).join('');
    $(`${id}-note`).textContent = L.note;
  }

  function renderControls() {
    document.querySelectorAll('[data-model]').forEach((b) => b.classList.toggle('on', b.dataset.model === model));
    document.querySelectorAll('[data-view]').forEach((b) => { const on = b.dataset.view === view; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
    document.querySelectorAll('[data-layer]').forEach((b) => b.classList.toggle('on', b.dataset.layer === layer));
    document.querySelectorAll('[data-clayer]').forEach((b) => b.classList.toggle('on', b.dataset.clayer === clayer));
    $('view-scenarios').hidden = view !== 'scenarios';
    $('view-compare').hidden = view !== 'compare';
    $('model-note').textContent = view === 'compare' ? 'The Compare view shows both models; the switch applies to the Scenarios view.' : modelNote(model);
    if (!data) return;
    const pr = presetOf();
    $('presets').innerHTML = data.presets.map((p) => `<button type="button" data-preset="${p.id}" class="${pr && pr.id === p.id ? 'on' : ''}">${p.label}</button>`).join('');
    $('preset-note').textContent = pr ? pr.note : `Custom: ${label('slr', levels.slr)} sea level rise, surge ${label('surge', levels.surge)}, heat ${label('heat', levels.heat)}.`;
    document.querySelectorAll('.levels').forEach((el) => {
      const fam = el.dataset.family;
      el.innerHTML = data.levels[fam].map(([id, l]) => `<button type="button" data-level="${id}" class="${levels[fam] === id ? 'on' : ''}">${l}</button>`).join('');
    });
    $('scenario-note').textContent = `${FAMILY_NOTES.slr} ${FAMILY_NOTES.surge} ${FAMILY_NOTES.heat}`;
  }

  function renderSummary(s) {
    const ch = s.meanChange;
    $('summary').innerHTML = `
      <div class="wide"><div class="n">${fmt(s.flagged)} tracts</div><div class="l">high need and no sited project (${fmt(s.flaggedPop)} residents) · same for both models</div></div>
      <div><div class="n">${fmt(s.exposedSlr)}</div><div class="l">residents on land flooded by ${label('slr', levels.slr)} of sea level rise</div></div>
      <div><div class="n">${fmt(s.exposedSurge)}</div><div class="l">residents reached by ${label('surge', levels.surge)} surge</div></div>
      <div><div class="n">${fmt(s.gapHigh)}</div><div class="l">tracts with a large gap (0.5 or more) · same for both</div></div>
      <div><div class="n">${fmt(s.ext)}</div><div class="l">tracts beyond the training range${s.ext ? ` (${fmt(s.extPop)} residents), hatched` : ''}</div></div>
      <div class="wide model"><div class="n">${fmt(s.expected)} tracts <span class="chg">${sgn(ch * 100, 1)} points</span></div><div class="l">expected to have a sited project under current patterns, and the average change in likelihood from the current baseline · ${MODELS[model]}</div></div>`;
  }

  function tractHtml(i, sb, sm) {
    const t = tracts[i];
    const tags = [];
    if (t.T1_observed) tags.push('<span class="tag">has a sited project</span>');
    if (sb.flag[i]) tags.push('<span class="tag warn">high need, no sited project</span>');
    if (sb.extrap[i]) tags.push('<span class="tag warn">extrapolated in this scenario</span>');
    if (t.low_pop_flag) tags.push('<span class="tag warn">under 100 residents: not in the Bayesian model</span>');
    const bd = data.bayes_drivers[i] || [];
    const md = data.ml.drivers[i] || [];
    const col = (k) => (model === k ? ' class="sel"' : '');
    return `
      <p><b>${t.jurisdiction}</b>, tract ${t.GEOID} · ${fmt(t.population)} residents</p>
      <div>${tags.join('')}</div>
      <table class="both"><thead><tr><th></th><th${col('bayes')}>Bayesian</th><th${col('ml')}>Machine learning</th></tr></thead><tbody>
        <tr><td>Likely investment</td><td${col('bayes')}>${pct(sb.p[i])}</td><td${col('ml')}>${pct(sm.p[i])}</td></tr>
        <tr><td>Range</td><td${col('bayes')}>${range(sb.lo[i], sb.hi[i])}<br><span class="muted">90% credible</span></td><td${col('ml')}>${range(sm.lo[i], sm.hi[i])}<br><span class="muted">Venn-ABERS, current</span></td></tr>
        <tr><td>Change from current (points)</td><td${col('bayes')}>${sb.p[i] == null ? 'n/a' : sgn((sb.p[i] - sb.current[i]) * 100, 1)}</td><td${col('ml')}>${sgn((sm.p[i] - sm.current[i]) * 100, 1)}</td></tr>
        <tr><td>Need vs expected</td><td${col('bayes')}>${sgn(sb.gapExpected[i])}</td><td${col('ml')}>${sgn(sm.gapExpected[i])}</td></tr>
      </tbody></table>
      <dl>
        <dt>Need (percentile) · same for both</dt><dd>${pct(sb.needPct[i])}</dd>
        <dt>Gap: need vs investment · same for both</dt><dd>${sgn(sb.gap[i])}</dd>
        <dt>Planned projects here</dt><dd>${t.T2_planned_projects}</dd>
        <dt>City effect (Bayesian, log-odds)</dt><dd>${sgn(data.bayes_effects.city[i])}</dd>
        <dt>Neighbourhood effect (Bayesian)</dt><dd>${sgn(data.bayes_effects.neighbourhood[i])}</dd>
      </dl>
      <h3>What drives its likelihood most</h3>
      <div class="two"><div><b>Bayesian</b><ul>${bd.filter(Boolean).map((d) => `<li>${d}</li>`).join('') || '<li>not modelled</li>'}</ul></div>
      <div><b>Machine learning</b><ul>${md.filter(Boolean).map((d) => `<li>${d}</li>`).join('')}</ul></div></div>`;
  }

  function renderInterventions(s) {
    const out = $('iresult');
    const ty = $('itype').value;
    const ct = (cmp?.cost_by_type || []).find((r) => r.type === ty);
    $('itype-note').innerHTML = ct
      ? `${ty}. Typical sited cost: <b>${money(ct.median_dollars_per_resident)} per resident</b> (median over ${fmt(ct.tracts)} tracts; ${fmt(ct.projects)} projects).${ct.few_projects_flag ? ` <span class="tag warn">only ${ct.projects} ${ty.toLowerCase()} projects: this figure is unstable</span>` : ''}`
      : '';
    if (!selected.size) { out.innerHTML = '<p class="muted">No tracts selected.</p>'; return; }
    const sel = [...selected];
    const obs = tracts.map((t) => t.sited_dollars_per_resident_observed || 0);
    const pos = obs.filter((v) => v > 0);
    const add = ct ? ct.median_dollars_per_resident : median(pos);
    const after = obs.map((v, i) => (selected.has(i) ? v + add : v));
    const sitedB = pctWithin(obs, obs);
    const sitedA = pctWithin(after, after);
    const gapB = s.needPct.map((n, i) => (n == null ? null : n - sitedB[i]));
    const gapA = s.needPct.map((n, i) => (n == null ? null : n - sitedA[i]));
    const flagA = s.flag.map((f, i) => f && !selected.has(i));
    const pAfter = s.p.map((v, i) => (v == null ? null : (selected.has(i) ? 1 : v)));
    const pp = pctWithin(s.p, pAfter);
    const pb = pctWithin(s.p, s.p);
    const geB = s.needPct.map((n, i) => (n == null || pb[i] == null ? null : n - pb[i]));
    const geA = s.needPct.map((n, i) => (n == null || pp[i] == null ? null : n - pp[i]));
    const sum = (arr) => arr.reduce((a, b) => a + b, 0);
    const pop = tracts.map((t) => t.population || 0);
    const vul = data.need.vul_pct;
    const residents = sum(sel.map((i) => pop[i]));
    const vulnerable = sum(sel.map((i) => (vul[i] != null && vul[i] >= 2 / 3 ? pop[i] : 0)));
    const ex = (k) => sum(sel.map((i) => tracts[i][k] || 0));
    const nB = sum(s.flag.map(Number)); const nA = sum(flagA.map(Number));
    const mean = (arr) => { const v = sel.map((i) => arr[i]).filter((x) => x != null); return v.length ? sum(v) / v.length : null; };
    out.innerHTML = `
      <div class="stats">
        <div><div class="n">${fmt(residents)}</div><div class="l">residents in ${sel.length} tract${sel.length > 1 ? 's' : ''}</div></div>
        <div><div class="n">${fmt(vulnerable)}</div><div class="l">in the most vulnerable third of tracts</div></div>
        <div><div class="n">${fmt(ex('slr_3ft_pop_exposed'))}</div><div class="l">exposed to 3 ft sea level rise</div></div>
        <div><div class="n">${fmt(ex('surge_cat3_any_pop_exposed'))}</div><div class="l">exposed to Category 3 surge</div></div>
        <div><div class="n">${fmt(ex('surge_cat4_any_pop_exposed'))}</div><div class="l">exposed to Category 4 surge</div></div>
        <div><div class="n">${fmt(ex('heat_p95_pop_exposed'))}</div><div class="l">on the hottest 5% of land</div></div>
        <div class="wide"><div class="n">${nB} → ${nA}</div><div class="l">tracts with high need and no sited project, in this scenario, if these got a ${ty.toLowerCase()} project · same for both models</div></div>
        <div class="wide"><div class="n">${sgn(mean(gapB))} → ${sgn(mean(gapA))}</div><div class="l">average gap of the selected tracts, assuming ${money(add)} per resident (typical for ${ty.toLowerCase()}) · same for both</div></div>
        <div class="wide model"><div class="n">${sgn(mean(geB))} → ${sgn(mean(geA))}</div><div class="l">average need vs expected investment of the selected tracts · ${MODELS[model]}</div></div>
      </div>
      <p class="note">Coverage only: no damages avoided are estimated. Coverage figures are the same for every project type.</p>`;
  }

  function renderCompareTract() {
    const el = $('ctract');
    if (!el || clickedIndex == null || view !== 'compare') return;
    const cur = { slr: 'slr_3ft', surge: 'surge_cat3', heat: 'heat_current' };
    el.hidden = false;
    el.innerHTML = tractHtml(clickedIndex, summary(data, 'bayes', cur, tracts), summary(data, 'ml', cur, tracts));
  }

  function render() {
    renderControls();
    if (!tracts) return;
    const sb = summary(data, 'bayes', levels, tracts);
    const sm = summary(data, 'ml', levels, tracts);
    const s = model === 'bayes' ? sb : sm;
    let v; let flag = () => false; let ext = () => false;
    if (view === 'scenarios') {
      v = { gap: s.gap, need: s.needPct, likelihood: s.p, gapExpected: s.gapExpected }[layer];
      flag = (i) => layer === 'gap' && !!s.flag[i];
      ext = (i) => !!s.extrap[i];
    } else {
      v = { diff: data.diff_current, neighbourhood: data.bayes_effects.neighbourhood, city: data.bayes_effects.city }[clayer];
    }
    for (let i = 0; i < tracts.length && map.getSource('tracts'); i += 1) {
      map.setFeatureState({ source: 'tracts', id: i }, { v: v[i], extrap: ext(i), flag: flag(i), sel: selected.has(i) || (view === 'compare' && i === clickedIndex) });
    }
    if (map.getLayer('tract-fill')) map.setPaintProperty('tract-fill', 'fill-color', colorExpr(view === 'scenarios' ? layer : clayer));
    renderLegend('ramp', layer);
    renderLegend('cramp', clayer);
    if (view === 'scenarios') {
      renderSummary(s);
      if (clickedIndex != null) $('tract').innerHTML = tractHtml(clickedIndex, sb, sm);
      renderInterventions(s);
    } else {
      renderCompareTract();
    }
  }

  // The panel fills in as soon as the data arrive; the map layers are added once the basemap has loaded.
  const ready = Promise.all([TRACTS_URL, MODELS_URL, COMPARE_URL].map((u) => fetch(u).then((r) => r.json())))
    .then(([geo, md, cm]) => {
      if (removed) return geo;
      data = md; cmp = cm;
      tracts = []; boxes = [];
      geo.features.forEach((f) => { tracts[f.id] = f.properties; boxes[f.id] = bbox(f.geometry); });
      $('about').innerHTML = aboutHtml(cmp);
      $('compare').innerHTML = compareHtml(cmp);
      $('compare').querySelectorAll('[data-tract]').forEach((b) => b.addEventListener('click', () => {
        clickedIndex = Number(b.dataset.tract);
        map.fitBounds(boxes[clickedIndex], { padding: 80, maxZoom: 13, duration: 600 });
        render();
      }));
      render();
      return geo;
    });
  map.on('load', async () => {
    const geo = await ready;
    if (removed) return;
    map.addImage('hatch', hatchImage());
    map.addSource('tracts', { type: 'geojson', data: geo });
    const below = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;
    map.addLayer({ id: 'tract-fill', type: 'fill', source: 'tracts', paint: { 'fill-color': colorExpr(layer), 'fill-opacity': 0.78 } }, below);
    map.addLayer({ id: 'tract-hatch', type: 'fill', source: 'tracts', paint: { 'fill-pattern': 'hatch', 'fill-opacity': ['case', ['boolean', ['feature-state', 'extrap'], false], 1, 0] } }, below);
    map.addLayer({ id: 'tract-line', type: 'line', source: 'tracts', paint: { 'line-color': 'rgba(255,255,255,0.7)', 'line-width': 0.4 } }, below);
    map.addLayer({ id: 'tract-flag', type: 'line', source: 'tracts', paint: { 'line-color': '#f47321', 'line-width': ['case', ['boolean', ['feature-state', 'flag'], false], 2, 0] } }, below);
    map.addLayer({ id: 'tract-low-pop', type: 'line', source: 'tracts', filter: ['==', ['get', 'low_pop_flag'], 1], paint: { 'line-color': '#6b7783', 'line-width': 1.5, 'line-dasharray': [2, 2] } }, below);
    map.addLayer({ id: 'tract-sel', type: 'line', source: 'tracts', paint: { 'line-color': '#01321e', 'line-width': ['case', ['boolean', ['feature-state', 'sel'], false], 3, 0] } }, below);
    render();

    map.on('mousemove', 'tract-fill', (e) => {
      const t = tracts[e.features[0].id];
      map.getCanvas().style.cursor = 'pointer';
      popup.setLngLat(e.lngLat).setHTML(`${t.jurisdiction} · ${fmt(t.population)} residents`).addTo(map);
    });
    map.on('mouseleave', 'tract-fill', () => { map.getCanvas().style.cursor = ''; popup.remove(); });
    map.on('click', 'tract-fill', (e) => {
      const i = e.features[0].id;
      if (selecting && view === 'scenarios') { if (selected.has(i)) selected.delete(i); else selected.add(i); }
      clickedIndex = i;
      render();
    });
  });

  const controller = new AbortController();
  const on = { signal: controller.signal };
  const panel = document.querySelector('.viz-scenario .panel') || document;
  panel.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.model) { model = b.dataset.model; render(); }
    else if (b.dataset.view) { view = b.dataset.view; render(); }
    else if (b.dataset.layer) { layer = b.dataset.layer; render(); }
    else if (b.dataset.clayer) { clayer = b.dataset.clayer; render(); }
    else if (b.dataset.preset) { const p = data.presets.find((x) => x.id === b.dataset.preset); levels = { slr: p.slr, surge: p.surge, heat: p.heat }; render(); }
    else if (b.dataset.level) { levels = { ...levels, [b.closest('.levels').dataset.family]: b.dataset.level }; render(); }
  }, on);
  $('select-toggle').addEventListener('click', () => {
    selecting = !selecting;
    $('select-toggle').classList.toggle('on', selecting);
    $('select-toggle').textContent = selecting ? 'Selecting: click tracts' : 'Select tracts on the map';
  }, on);
  $('select-clear').addEventListener('click', () => { selected.clear(); render(); }, on);
  $('itype').addEventListener('change', () => render(), on);
  renderControls();
  renderLegend('ramp', layer);
  renderLegend('cramp', clayer);

  return () => {
    removed = true;
    controller.abort();
    popup.remove();
    map.remove();
  };
}

