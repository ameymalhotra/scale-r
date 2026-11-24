// @vitest-environment node
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { likelihoodFor, median, needFor, summary } from './scenarioModel.js';

// The page recomputes need and the gap from per-family percentiles. These checks tie it to the
// Python pipeline: scenarios.py (single families, Stage 3) and stage4_dashboard.py (presets).
// Private admin data (D-095), git-ignored: built by build_scenario_data.py. Skipped, not failed, where missing.
const DIR = path.resolve(__dirname, '../../../../Modelling Data from Web/outputs/admin_data/scenario');
const HAVE = existsSync(path.join(DIR, 'models.json'));
const read = (name) => JSON.parse(readFileSync(path.join(DIR, name), 'utf8'));
const data = HAVE ? read('models.json') : null;
const compare = HAVE ? read('compare.json') : null;
const tracts = [];
if (HAVE) read('tracts.geojson').features.forEach((f) => { tracts[f.id] = f.properties; });
const t1 = tracts.map((t) => t.T1_observed);
const lv = (slr, surge, heat) => ({ slr, surge, heat });

describe.skipIf(!HAVE)('scenario arithmetic', () => {
  it('reproduces the current need percentiles and primary gap', () => {
    const nd = needFor(data, lv('slr_3ft', 'surge_cat3', 'heat_current'), t1);
    tracts.forEach((t, i) => {
      if (t.need_pct == null) expect(nd.needPct[i]).toBeNull();
      else expect(nd.needPct[i]).toBeCloseTo(t.need_pct, 3);
      if (t.gap_actual != null) expect(nd.gap[i]).toBeCloseTo(t.gap_actual, 3);
    });
  });

  it.each([
    ['current baseline', lv('slr_3ft', 'surge_cat3', 'heat_current'), 72, 275141, 85],
    ['sea level rise 6 ft (Stage 3)', lv('slr_6ft', 'surge_cat3', 'heat_current'), 128, 492480, 139],
    ['heat +3 F (Stage 3)', lv('slr_3ft', 'surge_cat3', 'heat_plus3f'), 112, 434341, 122],
    ...compare.preset_check.map((p) => {
      const pr = data.presets.find((x) => x.label === p.preset);
      return [`preset ${p.preset}`, lv(pr.slr, pr.surge, pr.heat), p.high_need_no_sited_project, p.residents, p['tracts_gap_over_0.5']];
    }),
  ])('%s matches the pipeline', (_, levels, flagged, residents, gapHigh) => {
    for (const model of ['bayes', 'ml']) {
      const s = summary(data, model, levels, tracts);
      expect(s.flagged).toBe(flagged);
      expect(Math.round(s.flaggedPop)).toBe(Math.round(residents));
      expect(s.gapHigh).toBe(gapHigh);
    }
  });

  it('keeps heat from changing either model', () => {
    for (const model of ['bayes', 'ml']) {
      const a = likelihoodFor(data, model, lv('slr_3ft', 'surge_cat4', 'heat_current')).p;
      const b = likelihoodFor(data, model, lv('slr_3ft', 'surge_cat4', 'heat_plus3f')).p;
      expect(b).toEqual(a);
    }
  });

  it('never lowers the machine learning likelihood as hazard rises (monotone)', () => {
    const a = likelihoodFor(data, 'ml', lv('slr_3ft', 'surge_cat3', 'heat_current')).p;
    const b = likelihoodFor(data, 'ml', lv('slr_6ft', 'surge_cat5', 'heat_current')).p;
    a.forEach((v, i) => expect(b[i]).toBeGreaterThanOrEqual(v - 1e-9));
  });

  it('leaves the tract under 100 residents out of the Bayesian model', () => {
    const i = tracts.findIndex((t) => t.low_pop_flag === 1);
    expect(likelihoodFor(data, 'bayes', lv('slr_3ft', 'surge_cat3', 'heat_current')).p[i]).toBeNull();
    expect(likelihoodFor(data, 'ml', lv('slr_3ft', 'surge_cat3', 'heat_current')).p[i]).not.toBeNull();
  });

  it.each([
    ['professor median', lv('slr_3ft', 'surge_cat4', 'heat_plus2f'), 144, 0],
    ['6 ft, Category 3', lv('slr_6ft', 'surge_cat3', 'heat_current'), 0, 253],
    ['6 ft, Category 5', lv('slr_6ft', 'surge_cat5', 'heat_current'), 45, 153],
  ])('counts reliable Bayesian changes as the pipeline does: %s', (_, levels, up, down) => {
    const s = summary(data, 'bayes', levels, tracts);
    expect(s.reliableUp).toBe(up);
    expect(s.reliableDown).toBe(down);
    s.change.forEach((c, i) => {
      if (c == null) return;
      // the shown change lies inside its own interval (to rounding)
      expect(c).toBeGreaterThanOrEqual(s.chLo[i] - 0.02);
      expect(c).toBeLessThanOrEqual(s.chHi[i] + 0.02);
    });
  });

  it('shows the machine learning map probability uncalibrated (D-110)', () => {
    const cur = likelihoodFor(data, 'ml', lv('slr_3ft', 'surge_cat3', 'heat_current')).p;
    const tied = cur.filter((v) => v === 0.385).length;
    expect(tied).toBeLessThan(10); // Venn-ABERS put many tracts on exactly 0.385
  });

  it('computes the median the way pandas does', () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 3, 2])).toBe(2.5);
  });
});
