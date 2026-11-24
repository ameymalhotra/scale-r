// Pure scenario arithmetic for the admin Scenario screen (no DOM, no map), so it can be tested
// against the Python pipeline. Data: data/models.json, written by
// "Modelling Data from Web/scripts/ml/stage4_dashboard.py" (D-109).

export const HIGH_NEED = 0.75;
export const MODELS = {
  bayes: 'Bayesian multiscale model',
  ml: 'Machine learning model',
};

/** Percentile of each value of x within base (average rank for ties), as in scenarios.py. */
export function pctWithin(base, x) {
  const b = base.filter((v) => v != null && !Number.isNaN(v)).sort((p, q) => p - q);
  const lower = (v) => { let lo = 0; let hi = b.length; while (lo < hi) { const m = (lo + hi) >> 1; if (b[m] < v) lo = m + 1; else hi = m; } return lo; };
  const upper = (v) => { let lo = 0; let hi = b.length; while (lo < hi) { const m = (lo + hi) >> 1; if (b[m] <= v) lo = m + 1; else hi = m; } return lo; };
  return x.map((v) => (v == null || Number.isNaN(v) ? null : (lower(v) + upper(v) + 1) / 2 / b.length));
}

function nanMean(vals) {
  const v = vals.filter((x) => x != null && !Number.isNaN(x));
  return v.length ? v.reduce((a, c) => a + c, 0) / v.length : null;
}

/**
 * Need percentile, primary gap and the high-need-no-project flag for a combination of levels.
 * These do not depend on the model.
 */
export function needFor(data, levels, t1) {
  const { family_pct: fp, base_expo: baseExpo, base_need: baseNeed, vul_pct: vul, sited_pct: sited } = data.need;
  const a = fp[levels.slr]; const b = fp[levels.surge]; const c = fp[levels.heat];
  const expo = a.map((_, i) => nanMean([a[i], b[i], c[i]]));
  const expoPct = pctWithin(baseExpo, expo);
  const need = expoPct.map((e, i) => (e == null || vul[i] == null ? null : e * vul[i]));
  const needPct = pctWithin(baseNeed, need);
  const gap = needPct.map((n, i) => (n == null || sited[i] == null ? null : n - sited[i]));
  const flag = needPct.map((n, i) => n != null && n >= HIGH_NEED && !t1[i]);
  return { needPct, gap, flag };
}

export const comboKey = (levels) => `${levels.slr}|${levels.surge}`;

/** Likelihood under the chosen model and levels (heat never changes it, D-093), with intervals. */
export function likelihoodFor(data, model, levels) {
  const key = comboKey(levels);
  if (model === 'ml') {
    const base = data.ml.current;
    const ch = data.ml.change[key];
    const p = base.map((v, i) => (v == null ? null : Math.min(1, Math.max(0, v + (ch[i] || 0)))));
    const change = p.map((v, i) => (v == null ? null : v - base[i]));
    // no interval for the machine learning change: every change is shown as a number
    return { p, lo: data.ml.lo, hi: data.ml.hi, current: base, intervalIsCurrent: true, change, chLo: null, chHi: null, reliable: change.map((c) => c != null), countyChange: null };
  }
  const s = data.bayes[key];
  const current = data.bayes['slr_3ft|surge_cat3'].mean;
  const change = s.mean.map((v, i) => (v == null ? null : v - current[i]));
  // a Bayesian change is reliable only when its 90% credible interval excludes zero (D-111)
  const reliable = change.map((c, i) => c != null && s.reliable[i] !== 0);
  return { p: s.mean, lo: s.lo, hi: s.hi, current, intervalIsCurrent: false, change, chLo: s.ch_lo, chHi: s.ch_hi, reliable, sign: s.reliable, countyChange: s.county_change };
}

/** Tracts whose scenario value for any chosen family is outside the training range. */
export function extrapolated(data, levels, n) {
  const out = new Array(n).fill(false);
  [levels.slr, levels.surge, levels.heat].forEach((id) => (data.extrapolated[id] || []).forEach((i) => { out[i] = true; }));
  return out;
}

/** County summary for a scenario under one model. */
export function summary(data, model, levels, tracts) {
  const t1 = tracts.map((t) => t.T1_observed);
  const pop = tracts.map((t) => t.population || 0);
  const nd = needFor(data, levels, t1);
  const lk = likelihoodFor(data, model, levels);
  const ex = extrapolated(data, levels, tracts.length);
  let flagged = 0; let flaggedPop = 0; let gapHigh = 0; let ext = 0; let extPop = 0; let expected = 0; let change = 0; let k = 0;
  let up = 0; let down = 0;
  tracts.forEach((_, i) => {
    if (nd.flag[i]) { flagged += 1; flaggedPop += pop[i]; }
    if (nd.gap[i] != null && nd.gap[i] >= 0.5) gapHigh += 1;
    if (ex[i]) { ext += 1; extPop += pop[i]; }
    if (lk.p[i] != null) { expected += lk.p[i]; change += lk.p[i] - lk.current[i]; k += 1; }
    if (lk.sign && lk.sign[i] > 0) up += 1;
    if (lk.sign && lk.sign[i] < 0) down += 1;
  });
  const predPct = pctWithin(lk.current, lk.p);
  const gapExpected = nd.needPct.map((n, i) => (n == null || predPct[i] == null ? null : n - predPct[i]));
  return {
    ...nd, ...lk, extrap: ex, gapExpected,
    flagged, flaggedPop, gapHigh, ext, extPop, expected, meanChange: k ? change / k : 0, modelled: k, reliableUp: up, reliableDown: down,
    exposedSlr: data.exposed[levels.slr], exposedSurge: data.exposed[levels.surge],
  };
}

/** Median, as pandas computes it (mean of the two middle values for an even count). */
export function median(values) {
  const v = values.filter((x) => x != null && !Number.isNaN(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

/** True when a county or tract change interval excludes zero. */
export const excludesZero = (lo, hi) => lo != null && hi != null && (lo > 0 || hi < 0);
