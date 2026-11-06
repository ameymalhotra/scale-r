# Machine learning scenario module: Stage 4 Part B report (unified admin Scenario screen)

**Prompt 24, Part B, with the change asked for on 5 November 2026: the
professor can compare both models.** Built on branch `ml-scenario-module`.
Not committed, not pushed, not deployed. Admin panel only (D-094). The
public site is unchanged.

**Commands.** Run these from `Modelling Data from Web/` after Part A:

```bash
bash scripts/ml/run_ml.sh scripts/ml/stage4_t4_multiclass.py   # four-class T4, about 5 minutes
bash scripts/ml/run_ml.sh scripts/ml/stage4_dashboard.py       # both models' dashboard data, about 1 minute
../.venv/bin/python scripts/website/build_scenario_data.py      # copy into src/admin/viz/scenario/data/
```

**Decisions:** D-104 to D-109.

## In plain language

- **One admin screen, two models.** A switch at the top picks the Bayesian
  multiscale model (the default) or the machine learning model. The map,
  scenario, tract panel, county summary and intervention tool all follow
  it.
- **Need and the main gap are the same for both models.** Every control on
  the screen says whether it "changes with the model" or is the "same for
  both models".
- **Presets combine all three hazards.** The professor's median is 3 ft sea
  level rise, Category 4 surge and +2°F. Under it:
  - 118 high-need tracts have no sited project (454,281 residents);
  - at today's levels it is 72.
- **The two models rank tracts about equally well.** Against the probabilities
  the machine learning map actually shows (Venn-ABERS calibrated), the
  Bayesian model ranks better. ROC-AUC is 0.685 against 0.644, and the
  interval for the difference, +0.003 to +0.079, is above zero.
- **They react to scenarios very differently.**
  - The machine learning model is monotone: more hazard never lowers it.
  - The Bayesian model follows the past pattern. Past projects went less
    often to tracts with more residents in the 3 ft zone, so higher sea level
    lowers its predictions.
  - Under 6 ft and Category 5, average likelihood rises 1.6 points under
    machine learning and falls 8.5 points under the Bayesian model.
  - Both are mostly extrapolating there, and the screen hatches those
    tracts.
- **Bayesian tract intervals are wide, and honestly so.** The median 90%
  credible interval is 73 points wide. The machine learning range (Venn-ABERS)
  is 13 points wide, but it measures calibration only.
- **Dollars stay off the dashboard (D-105).** One tract's 90% predictive range
  for sited dollars per resident has a median width of **$8,635**. The
  typical amount for a tract has a range of about **$990**.
- **Project types (D-107, D-108).** The intervention tool offers gray, green,
  blue and hybrid. Coverage is the same for every type.
  - A four-class type model is not reliable for blue (17 projects) or hybrid,
    so the binary model stays.

## 1. Decisions logged

| No. | Decision |
|---|---|
| D-104 | Bayesian Model 1 is the main model; Model 0c is reported as a comparison; the machine learning setup stays for comparison |
| D-105 | No dollar figures on the dashboard; the interval widths are reported (section 6) |
| D-106 | Heat wording: hotter tracts receive less investment, but after controls this is explained mainly by distance from the coast (inland location), not by heat itself |
| D-107 | Four project types in the intervention tool; typical cost per resident by type, with green and blue flagged |
| D-108 | Four-class T4 is unreliable for blue and hybrid; the binary model stays |
| D-109 | Part B design: out-of-fold predictions for both models, the interval definition, scenario rules, presets, the low-population tract, and the Compare view |

## 2. The screen

**Files:**
- `src/admin/viz/scenario/scenarioMap.html`, `scenarioMap.js`,
  `scenarioMap.css`: the screen.
- `src/admin/viz/scenario/scenarioModel.js`: the scenario arithmetic, with no
  page code, so it can be tested.
- `scenarioModel.test.js`: tests against the Python pipeline.
- **Data:** `data/models.json` (820 KB) and `data/compare.json` (17 KB).
  - Both are written by `scripts/ml/stage4_dashboard.py` and copied by
    `scripts/website/build_scenario_data.py`. Nothing is hand-edited.
  - The Stage 3 `data/scenarios.json` is replaced by `models.json` and was
    removed.

**What changes with the model, and what does not**

| Part of the screen | Same for both | Changes with the model |
|---|---|---|
| Gap: need vs investment (primary) | yes | |
| Need | yes | |
| High-need tracts with no sited project | yes | |
| Likely investment | | yes |
| Need vs expected investment | | yes |
| Expected tracts with a sited project, average change | | yes |
| Tract panel | both models side by side | the chosen model's column is shaded |
| Intervention tool | coverage and the primary gap | need vs expected investment |

**How each model produces its numbers** (D-109)

| | Machine learning | Bayesian |
|---|---|---|
| Current likelihood | logistic regression, spatial out-of-fold, Venn-ABERS calibrated (as in Stage 3) | Model 1, spatial out-of-fold posterior mean from the Stage 4 CV fits |
| Interval | Venn-ABERS range, current conditions only | 90% credible interval: parameter and neighbourhood uncertainty, averaged over the tract's own unexplained effect |
| Scenario change | monotone XGBoost change added to the current likelihood | sea level rise, surge and their vulnerability interactions changed draw by draw; city and neighbourhood effects held fixed |
| Heat scenarios | need and gap only (D-093) | need and gap only (D-093) |
| Tract under 100 residents | predicted (final fit) | not modelled; shown as n/a |

**Scenario presets.** Each can be refined per family under "Choose each
hazard level".

| Preset | Sea level rise | Surge | Heat | High-need tracts, no sited project | Residents | Tracts with gap ≥ 0.5 |
|---|---|---|---|---|---|---|
| Current baseline | 3 ft | Category 3 | now | 72 | 275,141 | 85 |
| Professor's median | 3 ft | Category 4 | +2°F | 118 | 454,281 | 126 |
| Lower | 1 ft | Category 1 | now | 53 | 193,051 | 62 |
| Higher | 6 ft | Category 5 | +3°F | 172 | 665,508 | 186 |

**Average change in likelihood from the current baseline** (points,
percentage):

| Preset | Machine learning | Bayesian |
|---|---|---|
| Professor's median | +0.5 | +1.7 |
| 6 ft and Category 5 | +1.6 | −8.5 (tracts range from −61 to +25) |

**The Compare models view** (both models at once; the switch does not apply):
- **Spatial CV scores** for:
  - Bayesian Model 1;
  - Model 0c;
  - the machine learning map as shown, and its uncalibrated logistic model;
  - XGBoost.
- **Paired bootstrap intervals** for the differences, and residual
  Moran's I.
- **Map layers:**
  - difference in likelihood (Bayesian minus machine learning);
  - the Bayesian neighbourhood effect;
  - the Bayesian city effect.
- **The 12 largest disagreements.** Each is a link that zooms to the tract
  and shows both models' panels.
- **Top drivers side by side:**
  - machine learning: logistic coefficients ranked by average contribution;
  - Bayesian: population-averaged odds ratios with 95% intervals.
- **What only the Bayesian model shows:**
  - city effects as a ranked interval plot, with jurisdictions under 3
    tracts starred;
  - the neighbourhood effect map;
  - the heat result after controls.
- **When to trust each:** a short plain-language note.

**About panel:**
- both models;
- the heat sentence in D-106's words;
- the reasons dollars are not shown;
- the type-model limitation;
- the existing limits.

The PRELIMINARY banner stays.

## 3. Model comparison (`compare.json`)

| Model | ROC-AUC | PR-AUC | Log loss | Brier |
|---|---|---|---|---|
| Bayesian Model 1 (city + BYM2) | 0.685 | 0.730 | 0.643 | 0.224 |
| Bayesian Model 0c (BYM2, no city), comparison | 0.685 | 0.733 | 0.641 | 0.224 |
| Machine learning: logistic, as shown on the map (Venn-ABERS calibrated) | 0.644 | 0.690 | 0.665 | 0.235 |
| Machine learning: logistic, uncalibrated | 0.675 | 0.719 | 0.653 | 0.227 |
| Machine learning: XGBoost | 0.660 | 0.714 | 0.651 | 0.230 |

Bayesian Model 1 minus each, with the 95% paired bootstrap interval:

| Comparison | ROC-AUC | PR-AUC | Log loss | Brier |
|---|---|---|---|---|
| minus machine learning as shown | **+0.040 (+0.003 to +0.079)** | +0.040 (+0.000 to +0.080) | −0.023 (−0.053 to +0.008) | −0.012 (−0.024 to +0.001) |
| minus logistic, uncalibrated | +0.010 (−0.012 to +0.030) | +0.011 (−0.016 to +0.035) | −0.010 (−0.030 to +0.011) | −0.004 (−0.012 to +0.005) |
| minus XGBoost | +0.025 (−0.004 to +0.054) | +0.016 (−0.020 to +0.051) | −0.008 (−0.033 to +0.018) | −0.006 (−0.016 to +0.005) |

**New finding: the calibrated probabilities on the Stage 3 map rank tracts
worse than the uncalibrated model.**
- Venn-ABERS calibration is isotonic. It puts large groups of tracts on the
  same value; many sit at exactly 38.5%.
- That costs ranking (ROC-AUC 0.675 down to 0.644) without improving log
  loss.
- The screen shows both rows. It is worth deciding whether the machine
  learning view should show the uncalibrated logistic probability instead.
  I did not change it, because Amey asked for the Stage 2/3 setup.

**Where the two models disagree most.**
- The 12 largest differences are 42 to 58 points.
- Most are Miami tracts where the machine learning value is that tied
  38.5%, and the Bayesian model's neighbourhood effect lifts them to
  80% to 96%. Ten of the 12 have a sited project.
- The full list is in `compare.json` and on screen.

**Bayesian interval widths** (90%, current conditions, median over
tracts):
- 73 points with neighbourhood uncertainty, as shown;
- 34 points if the neighbourhood effect is also averaged out (reported, not
  shown).

**Watch the extremes.**
- In large, sparse rural tracts, the out-of-fold Bayesian predictions can be
  very high. One tract with no sited project gets 97%.
- An area the fit never saw gets no neighbourhood correction, and the
  in-sample fit's strongly negative neighbourhood effect there is missing.
- The "When to trust each" note says so.

## 4. Project types (D-107, D-108)

**Typical sited cost per resident, by type**
(`outputs/ml/stage4/cost_per_resident_by_type.csv`).
- Definition: the median over tracts that have that type, of that type's
  sited dollars ÷ residents.
- Coverage figures do not depend on type. Only the assumed amount, and so
  the gap change, does.

| Type | Projects | Tracts | Median $ per resident | Middle half | Flag |
|---|---|---|---|---|---|
| Gray | 913 | 365 | $381 | $114 to $1,578 | |
| Green | 40 | 34 | $268 | $85 to $838 | few projects |
| Blue | 17 | 17 | $981 | $169 to $1,823 | few projects |
| Hybrid | 122 | 87 | $922 | $228 to $2,922 | |
| All types (the Stage 3 default) | 1,092 | 395 | $575 | $141 to $2,362 | |

The Stage 3 tool used $580: the median over all 396 tracts with a sited
project, including the tract under 100 residents. $575 leaves that tract
out, as training does. The tool now uses the per-type median.

**Four-class T4 in spatial CV**
(`outputs/ml/stage4/t4_multiclass_per_class.csv`).
- Same 1,092 projects, features and folds as the binary T4.
- Class weights, and tuning inside each training fold.

| Class | Projects | Logistic precision | Logistic recall | XGBoost precision | XGBoost recall |
|---|---|---|---|---|---|
| Gray | 913 | 0.93 | 0.67 | 0.91 | 0.78 |
| Green | 40 | 0.35 | 0.68 | 0.36 | 0.58 |
| Blue | 17 | 0.04 | 0.35 | 0.00 | 0.00 |
| Hybrid | 122 | 0.23 | 0.39 | 0.17 | 0.30 |

- Macro F1 is 0.40 (logistic) and 0.38 (XGBoost).
- Collapsed back to two classes, ROC-AUC is 0.79, the same as the binary
  model.
- **Blue is not predictable and hybrid is weak, so the binary model stays
  (D-108).** No type predictions are shown on the dashboard.

## 5. Checks

| Check | Result |
|---|---|
| Page arithmetic against Python: current need and gap for all 698 tracts | match (to 3 decimals) |
| County summary against Python: current, Stage 3 single-family scenarios (6 ft, +3°F), four presets, both models | match exactly: tracts, residents, large-gap count |
| Heat changes neither model's likelihood | test passes |
| Machine learning likelihood never falls as hazard rises | test passes |
| Bayesian current likelihood equals the Stage 4 CV out-of-fold mean | asserted in `stage4_dashboard.py` |
| Bayesian mean inside its own interval | 0 exceptions |
| eslint (`npx eslint src`) | passes |
| Tests (`npx vitest run`) | 180 passed in 23 files, including 12 new and the existing access tests |
| Production build | passes; `models` and `compare` data are referenced only by the admin `VizPage` chunk |
| Public site | no file outside `src/admin/` changed |
| Browser | checked at desktop (1440 × 900) and phone (375 × 812) |

One robustness fix during testing: the panel used to wait for the basemap
to load before filling in. It now fills in as soon as the data arrive, and
the map layers follow when the basemap is ready.

## 6. Dollar figures (D-105, for your later decision)

Model 1 Part 2, 90% intervals for sited dollars per resident, median over
tracts (`outputs/ml/stage4/dollar_interval_widths.csv`):

| | Tracts with a sited project (395) | All 697 tracts |
|---|---|---|
| Predictive range for the tract's actual figure | **$8,635 wide** (about $28 to $8,664; the high end is about 300 times the low end) | $6,286 wide |
| Credible range for the tract's typical amount | **$990 wide** (typical $497; the high end is about 5.5 times the low end) | $711 wide |

These are too wide for tract-level dollar figures. A typical amount
"within a factor of about 5" might be shown for groups of tracts, if you
want it later.

## 7. Screenshots (`reports/ml/stage4_screenshots/`)

They were taken in the local dev server through a temporary page
(`tmp-preview/scenario.html`). It mounted the same admin module without
the router, because signing in to the admin panel is yours to do. It was
deleted afterwards and never committed.

| File | Shows |
|---|---|
| `1_desktop_bayes_median_likelihood.jpg` | Bayesian model, Professor's median preset, Likely investment layer |
| `2_desktop_bayes_summary_tract_both_models.jpg` | county summary and the tract panel with both models side by side |
| `3_desktop_ml_median_summary_tract.jpg` | the same with the machine learning model selected |
| `4_desktop_compare_difference_scores.jpg` | Compare view: difference map and the scores table |
| `5_desktop_compare_disagreements_tract.jpg` | largest disagreements; zoomed to the top one, with both panels |
| `6_desktop_compare_drivers_city_neighbourhood.jpg` | drivers side by side, city effect intervals, neighbourhood effect map |
| `7_desktop_compare_heat_trust.jpg` | heat after controls and "When to trust each" |
| `8_desktop_intervention_green.jpg` | intervention tool, Green, 3 tracts: cost flag, coverage, gap change |
| `9_phone_gap_median.jpg` | phone width: map above, panel below |
| `10_phone_compare_scores.jpg` | phone width: Compare view scores |

## 8. Not done, and limits

- **Not committed.** Prompt 24 says STOP and report.
- **D-095 still applies.** The data files are hashed static assets. The
  admin login hides the screen, not the files, and `models.json` now adds
  per-tract predictions from both models. The private-bucket plan is still
  on hold.
- **The Venn-ABERS question** in section 3 is open.
- **The Bayesian scenario changes are large beyond 3 ft.** They come from a
  negative, uncertain sea level effect applied outside the training range.
  The screen hatches those tracts and explains this.
