# Machine learning scenario module: Stage 2 report

**Stage 2 of prompt 22: models, validation, explanation, uncertainty, the
scenario engine and the interventions tool.** Run 5 November 2026 on branch
`ml-scenario-module`. Preliminary.

**Commands**, run from `Modelling Data from Web/`, in the ML environment
(D-079):

```bash
bash scripts/ml/run_ml.sh scripts/ml/stage2_models.py   # about 18 minutes
bash scripts/ml/run_ml.sh scripts/ml/scenarios.py
bash scripts/ml/run_ml.sh scripts/ml/interventions.py --tracts <GEOIDs> --type gray|nature-based
```

**Files**
- Outputs: `outputs/ml/stage2/` (git-ignored): results tables, figures,
  saved models, the log.
- Dashboard data: `outputs/ml/dashboard/` (`tracts.json`, `scores.json`,
  `scenarios.json`).
- Model card: `reports/ml/model_card.md`.
- Decisions: D-079 to D-090.

## In plain language

- **The simple model does as well as the machine learning models.** A
  logistic regression predicts where projects have been sited as well as
  XGBoost and LightGBM do. A paired bootstrap finds no real difference
  between them, so the dashboard map uses the simpler model (D-091).
- **Past investment follows coastal location and general risk, not the
  specific hazard maps.**
  - The strongest signals are distance to the bay or ocean, population
    density, being in a city, and FEMA's overall expected loss.
  - The sea level rise, storm surge and heat maps add very little once those
    are known.
- **So the value of the scenarios is in need and the gap, not in predicted
  investment.**
  - Under current patterns, more flooding or heat would hardly change where
    projects go.
  - It would change where need is highest and unmet. Tracts with high need
    and no sited project rise from 72 today (275,141 residents) to 115 under
    Category 5 surge and 128 under 6 ft of sea level rise.
- **Both are coverage and pattern statements.** Neither says where money
  should go, or what damage it would avoid.

## Update after the Stage 2 decisions (5 Nov 2026)

These supersede the matching parts of the sections below.

1. **Map model: logistic regression (D-091).** Spatial out-of-fold scores,
   with paired bootstrap 95% intervals (2,000 resamples):

   | Model | ROC-AUC | PR-AUC | Log loss | Brier |
   |---|---|---|---|---|
   | Logistic | 0.675 | 0.719 | 0.653 | 0.227 |
   | XGBoost | 0.660 | 0.714 | 0.651 | 0.230 |
   | Average of the two | 0.673 | 0.729 | 0.641 | 0.225 |
   | TabPFN | not run (no license key) | | | |

   | Comparison | ROC-AUC difference [95%] | PR-AUC difference [95%] | Log loss difference [95%] |
   |---|---|---|---|
   | Logistic minus XGBoost | +0.016 [−0.010, +0.042] | +0.005 [−0.028, +0.039] | +0.002 [−0.021, +0.027] |
   | Average minus logistic | −0.002 [−0.016, +0.011] | +0.010 [−0.010, +0.027] | −0.012 [−0.028, +0.001] |
   | Average minus XGBoost | +0.013 [+0.001, +0.026] | +0.015 [−0.002, +0.031] | −0.011 [−0.021, −0.001] |

   - **Logistic regression and XGBoost cannot be told apart.**
   - The average is reliably better than XGBoost, but not than logistic
     regression.
   - So the map uses logistic regression. Its Venn-ABERS 90% sets achieve
     89.2% coverage, and the average interval width is 0.21.
   - **Its top drivers** (log-odds contribution):
     1. distance from the bay or ocean (farther lowers)
     2. population density (higher lowers)
     3. being in a city (raises)
     4. FEMA expected loss per resident (raises)
     5. limited English households (lowers)
     6. no internet access (raises)
     7. FEMA building loss per dollar of buildings (lowers)
     8. minority share (lowers)
     9. heat (lowers)
     10. multi-unit housing (lowers)
   - Monotone XGBoost stays the scenario model.
2. **Primary gap: need versus actual investment (D-092).**
   - The gap is need percentile minus the percentile of actual sited dollars
     per resident. A flag marks high need (top quarter) with no sited project.
   - Need and actual sited dollars are unrelated (Spearman +0.02).
   - **72 tracts (275,141 residents) have high need and no sited project:**
     Hialeah 21, Miami 19, Unincorporated 18, Miami Beach 8.
   - The model-based gap stays as a secondary layer, "need versus expected
     investment".
3. **Heat scenarios change need and the gap only (D-093).** Predicted
   likelihood is not changed, because past investment did not follow heat.

**Scenarios with the primary gap:**

| Scenario | Tracts with gap ≥ 0.5 (actual) | Tracts with gap ≥ 0.5 (expected) | High need, no sited project: tracts (residents) |
|---|---|---|---|
| Current | 85 | 81 | 72 (275,141) |
| Sea level rise 1 ft | 80 | 78 | 67 (257,383) |
| Sea level rise 6 ft (56 tracts extrapolated) | 139 | 118 | 128 (492,480) |
| Surge Category 1 | 66 | 67 | 57 (211,125) |
| Surge Category 4 | 101 | 95 | 91 (348,000) |
| Surge Category 5 | 128 | 119 | 115 (445,378) |
| Heat +1°F (illustrative) | 104 | 94 | 93 (359,406) |
| Heat +2°F (illustrative) | 110 | 106 | 104 (395,223) |
| Heat +3°F (illustrative) | 122 | 116 | 112 (434,341) |

"Expected" here uses the scenario model's own predictions, so it differs
slightly from the map's out-of-fold count of 98.

**Interventions, retested** on the three highest-gap tracts that have high
need and no sited project (12086005202, 12086005104, 12086004204),
nature-based:
- 12,484 residents, all in the top vulnerability third.
- Exposed: 2,361 to 3 ft sea level rise, 8,354 to Category 3 surge, 4,795 on
  the hottest land.
- With the median $580 per resident assumed, the high-need, no-project count
  falls from 72 to 69 tracts. Each tract's actual gap falls from about 0.78
  to 0.28.

## Short summary

1. **The machine learning models do not beat simple logistic regression**
   for where projects were sited (T1) under spatial validation:

   | Model | ROC-AUC | PR-AUC |
   |---|---|---|
   | Logistic regression | **0.675** | **0.719** |
   | XGBoost | 0.660 | 0.714 |
   | LightGBM | 0.644 | 0.712 |

   All three clearly beat the prevalence baseline (ROC-AUC 0.50, PR-AUC
   0.57). Your rule says a complex model is only worth using if it clearly
   beats the baselines, so the map model needs your decision (D-089).
2. **Project type (T4) is predicted well,** ROC-AUC 0.80, PR-AUC 0.54 against
   a base rate of 0.16. Almost all of that comes from the project's own hazard
   focus.
3. **Planned projects (T2, the main future check):** the top 20% of tracts by
   predicted likelihood hold 42% (XGBoost) to 58% (logistic) of planned
   projects. PR-AUC is 0.29 to 0.32, against a base rate of 0.15.
4. **Hazard exposure barely drives where projects went.**
   - Distance to the coast and population density are the top drivers. The
     three hazard features rank 13th, 18th and 20th of 27.
   - So the scenarios barely move predicted likelihood: at most +0.01 on
     average.
   - The need and gap layers do move: tracts with a large gap rise from 87 to
     97 at Category 5 surge (D-090).
5. **The conformal intervals reach their 90% target:**
   - T1 coverage is 90.5%, but 63% of tracts get the uninformative set
     {0, 1}.
   - T5 coverage is 91.7%, but the intervals are far too wide to use. T5 is
     flagged as unreliable and has no dashboard numbers (D-088).
6. **TabPFN was not run.** Its weights need a license key in `TABPFN_TOKEN`,
   and it is not set (D-082).

## 1. Results: T1 and T4

Scores are pooled out-of-fold, with ROC-AUC also averaged over folds (D-075).
CV schemes: random (10 stratified folds), spatial (10 k-means folds, the
primary) and leave one jurisdiction out (33 groups). All tuning was nested.
TabPFN rows read "not run (no license key)".

### T1: sited project present (697 tracts, base rate 0.567)

| Model | CV | ROC-AUC | ROC-AUC fold mean | PR-AUC | Log loss | Brier |
|---|---|---|---|---|---|---|
| Prevalence | random | (0.49) | 0.50 | 0.56 | 0.684 | 0.246 |
| Prevalence | spatial | (0.34) | 0.50 | 0.47 | 0.696 | 0.251 |
| Prevalence | jurisdiction | (0.39) | 0.50 | 0.51 | 0.702 | 0.254 |
| Logistic | random | 0.706 | 0.711 | 0.748 | 0.628 | 0.219 |
| **Logistic** | **spatial** | **0.675** | 0.628 | **0.719** | 0.653 | **0.227** |
| Logistic | jurisdiction | 0.677 | 0.585 | 0.729 | 0.634 | 0.222 |
| LightGBM | random | 0.699 | 0.703 | 0.744 | 0.627 | 0.219 |
| LightGBM | spatial | 0.644 | 0.602 | 0.712 | 0.664 | 0.236 |
| LightGBM | jurisdiction | 0.631 | 0.540 | 0.692 | 0.675 | 0.239 |
| XGBoost | random | 0.698 | 0.704 | 0.752 | 0.626 | 0.219 |
| XGBoost | spatial | 0.660 | 0.623 | 0.714 | **0.651** | 0.230 |
| XGBoost | jurisdiction | 0.633 | 0.592 | 0.685 | 0.670 | 0.237 |
| XGBoost monotone (scenario model) | spatial | 0.660 | 0.623 | 0.712 | 0.651 | 0.230 |
| LightGBM monotone | spatial | 0.650 | 0.614 | 0.720 | 0.657 | 0.233 |
| TabPFN | all | not run (no license key) | | | | |

How to read the T1 table:
- **Spatial validation costs 0.03 to 0.06 ROC-AUC compared with random
  folds.** Random folds would have overstated accuracy.
- **Logistic regression is as good as, or better than, the trees.** With 697
  tracts and weak signals, a linear model is hard to beat.
- **The monotone constraint costs nothing** for XGBoost (0.660 either way).

**Other T1 feature sets** (spatial):

| Feature set | Logistic ROC / PR | LightGBM ROC / PR | XGBoost ROC / PR |
|---|---|---|---|
| Main, 27 features | 0.675 / 0.719 | 0.644 / 0.712 | 0.660 / 0.714 |
| Sensitivity, 30 (adds the dropped hazard versions, D-080) | 0.687 / 0.732 | 0.647 / 0.704 | 0.663 / 0.712 |
| Land shares instead of population shares | 0.676 / 0.722 | 0.653 / 0.726 | 0.658 / 0.718 |

The dropped hazard versions and land shares change little, at most 0.01 to
0.02.

### T4: nature-based or hybrid vs gray (1,092 projects, base rate 0.164)

| Model | CV | ROC-AUC | PR-AUC | Log loss | Brier |
|---|---|---|---|---|---|
| Prevalence | spatial | (0.40) | 0.13 | 0.448 | 0.138 |
| Logistic | random | 0.825 | 0.564 | 0.503 | 0.163 |
| Logistic | spatial | 0.792 | 0.521 | 0.523 | 0.171 |
| Logistic | jurisdiction | 0.750 | 0.522 | 0.561 | 0.189 |
| LightGBM | random | 0.829 | 0.554 | 0.471 | 0.152 |
| LightGBM | spatial | 0.796 | 0.517 | **0.464** | **0.150** |
| LightGBM | jurisdiction | 0.798 | 0.519 | 0.480 | 0.157 |
| XGBoost | random | 0.825 | 0.550 | 0.480 | 0.156 |
| **XGBoost** | **spatial** | **0.803** | **0.536** | 0.479 | 0.155 |
| XGBoost | jurisdiction | 0.778 | 0.519 | 0.520 | 0.173 |
| Scale and hazard focus only, LightGBM | spatial | 0.791 | 0.554 | 0.501 | 0.164 |
| Tract features only (no hazard focus), LightGBM | spatial | 0.554 | 0.179 | 0.614 | 0.213 |
| TabPFN | all | not run (no license key) | | | |

**Hazard focus is almost all of T4.** Without it, the tract features alone
score ROC-AUC 0.55, close to chance. Share of each hazard focus that is
nature-based or hybrid:

| Hazard focus | Share |
|---|---|
| Extreme Heat | 91% |
| Coastal Hazards | 45% |
| Multi-Hazard | 34% |
| Flooding | 11% |
| Infrastructure Failure | 3% |
| Storms & Hurricanes | 0% |

(`outputs/ml/stage2/T4_hazard_focus.csv`.)

### T5: log sited dollars per resident (395 tracts), flagged as unreliable

| Model | Spatial RMSE | Spatial R² | Spatial Spearman |
|---|---|---|---|
| Mean | 2.04 | −0.04 | |
| Ridge | 1.76 | **0.23** | 0.47 |
| LightGBM | 1.80 | 0.19 | 0.44 |
| XGBoost | 1.83 | 0.16 | 0.40 |

The best model explains about a fifth of the variation. Its 90% intervals
are 6.5 log units wide on average (D-088). **No dollar predictions are shown
on the dashboard.**

## 2. Future checks

| Check | Model | Base rate | ROC-AUC | PR-AUC | Planned projects in top 20% | Positive tracts in top 20% |
|---|---|---|---|---|---|---|
| **T2**, all tracts | XGBoost (map model) | 0.154 | 0.658 | 0.292 | **42%** | 32% |
| T2, all tracts | monotone XGBoost | 0.154 | 0.660 | 0.288 | 41% | 30% |
| T2, all tracts | logistic | 0.154 | 0.699 | 0.322 | **58%** | 44% |
| T2, tracts with no current project | XGBoost | 0.053 | 0.623 | 0.105 | 50% | 44% |
| T3, diagnostic only | XGBoost, 2023 label | 0.267 | 0.534 | 0.315 | | 20% |

**T2: the model points toward where planned projects are going.** PR-AUC is
about twice the base rate. Logistic regression does better again. Among the
302 tracts with no project yet, the top fifth holds half of the planned
projects. That rests on 16 tracts, so it is a small number.

**T3 is a diagnostic only (D-081).** `Reported_Year` is a document year. T3
is no better than chance and supports no claim.

## 3. Calibration

| Target | Model | | Log loss | Brier | ROC-AUC |
|---|---|---|---|---|---|
| T1 | XGBoost | before | 0.645 | 0.228 | 0.664 |
| T1 | XGBoost | after isotonic, inside the folds | 0.660 | 0.232 | 0.650 |
| T4 | LightGBM | before | 0.480 | 0.156 | 0.806 |
| T4 | LightGBM | after isotonic, inside the folds | **0.346** | **0.106** | 0.805 |

- **T1 is already roughly calibrated.** Isotonic calibration on small
  calibration folds made it slightly worse, so it is not applied.
- **T4's class weights inflate its probabilities.** Isotonic calibration
  fixes that: log loss falls from 0.48 to 0.35.
- Reliability curves: `outputs/ml/stage2/figures/reliability_T1_T4.png`.

## 4. What drives the T1 model (SHAP)

Mean absolute SHAP value, XGBoost final fit, top 10. "Stable" is the share
of 50 bootstrap refits in which the feature ranked in the top 5.

| Rank | Driver, in plain words | Mean abs. SHAP | Stable (top 5 in bootstraps) |
|---|---|---|---|
| 1 | distance from the bay or ocean | 0.460 | 100% |
| 2 | population density | 0.384 | 100% |
| 3 | FEMA expected yearly loss per resident | 0.148 | 80% |
| 4 | single-parent households | 0.118 | 42% |
| 5 | FEMA expected yearly building loss per dollar of buildings | 0.101 | 40% |
| 6 | being in a city rather than unincorporated Miami-Dade | 0.080 | |
| 7 | households with no vehicle | 0.077 | 12% |
| 8 | no internet access | 0.071 | 16% |
| 9 | minority population share | 0.068 | 20% |
| 10 | crowded housing | 0.063 | 8% |

The hazard features rank lower:
- Category 3 surge share: 13th.
- Heat mean: 18th.
- Sea level rise 3 ft share: 20th.

**Partial dependence.** Across each hazard's full range, the average
prediction moves by 0.02 or less, for both the unconstrained and the
monotone model (`figures/partial_dependence_hazards.png`).

Per-tract top 3 drivers are in `outputs/ml/stage2/shap_local_top3.csv` and on
the dashboard.

**Only the top two drivers are stable.** Coast and density are in the top 5
in every bootstrap. Below rank 3, the order changes a lot from refit to
refit, so it should not be read closely.

## 5. Stability and spatial residuals

**Five seeds**, which change both the spatial folds and the model seed:

| Score | Range |
|---|---|
| ROC-AUC | 0.657 to 0.675 (sd 0.008) |
| PR-AUC | 0.723 to 0.739 |
| Log loss | 0.639 to 0.652 |

The scores are stable.

**Residual Moran's I** (k = 6, seed 12086) is **0.132**, p = 0.001. Some
spatial pattern is left after the model.
- Adding spatial lags of the inputs (never of the target) did not help:
  Moran's I fell to 0.129, while PR-AUC fell from 0.714 to 0.690.
- So the lags were not adopted.
- The leftover clustering probably reflects jurisdiction budgets and
  programs that the features do not capture.

## 6. Uncertainty: conformal inside the spatial folds (D-083)

| Target | Method | Target coverage | Achieved | Notes |
|---|---|---|---|---|
| T1 | Inductive conformal sets | 90% | **90.5%** | 90.9% for tracts with a project, 90.1% without. Only 37% of sets are a single label; 63% are {0, 1} |
| T1 | Venn-ABERS interval [p0, p1] | | | average width 0.18; merged probability log loss 0.673 (raw 0.645) |
| T5 | Split conformal, ridge | 90% | **91.7%** | average width 6.5 log units: unusable (D-088) |

**The intervals are honest, and they show the model cannot say much about
most tracts.** The dashboard shows each tract's Venn-ABERS interval. A
bootstrap 5% to 95% range is kept as a cross-check (`boot_p05`, `boot_p95`).

## 7. Need and gap (D-085)

- **Need** = exposure percentile × vulnerability percentile, where:
  - exposure is the mean percentile of SLR 3 ft, Category 3 surge and heat;
  - vulnerability is PCA component RC1, general disadvantage.
- **Gap** = need percentile minus predicted-likelihood percentile.
- **Need and predicted likelihood are unrelated** (Spearman −0.04).
- **Today 80 tracts have a gap of 0.5 or more**, using the map's out-of-fold
  predictions. The scenario table below uses the final monotone model's own
  predictions so that scenarios compare like with like. On that basis the
  current count is 87.
- **The gap compares need with the model's expected likelihood, not with what
  was actually built.**
  - The three highest-gap tracts are in the City of Miami (12086005804,
    12086005701, 12086003005).
  - Two of them already have a sited project. They score low because tracts
    like them usually do not get one.

## 8. Scenario engine (`scripts/ml/scenarios.py`)

The monotone XGBoost model is used. Each scenario replaces the one feature in
its family (D-080) and leaves the other families at the primary scenario.

| Scenario | Mean predicted likelihood | Change vs current | Tracts with gap ≥ 0.5 | Extrapolated tracts (residents) |
|---|---|---|---|---|
| Current (SLR 3 ft, surge Cat 3, heat now) | 0.516 | 0 | 87 | 0 |
| Sea level rise 1 ft | 0.515 | −0.001 | 86 | 0 |
| Sea level rise 2 ft | 0.515 | −0.001 | 86 | 0 |
| Sea level rise 6 ft | 0.522 | +0.006 | 94 | **56 (191,028)** |
| Surge Category 1 | 0.511 | −0.005 | 85 | 0 |
| Surge Category 2 | 0.513 | −0.003 | 86 | 0 |
| Surge Category 4 | 0.521 | +0.005 | 90 | 0 |
| Surge Category 5 (corrected) | 0.525 | +0.010 | 97 | 0 |
| Heat +1°F (illustrative) | 0.516 | 0.000 | 96 | 2 (8,296) |
| Heat +2°F (illustrative) | 0.516 | 0.000 | 99 | 2 (8,296) |
| Heat +3°F (illustrative) | 0.516 | 0.000 | 103 | 5 (21,378) |

- **Monotonicity holds.** No tract's prediction drops as sea level or heat
  rises.
  - Surge categories can go down for individual tracts, because a tract's
    exposed share can be lower at a higher category: the NHC reversals
    reported in prompt 21.
- **Predicted likelihood hardly moves.**
  - Under current patterns, hazard exposure is a weak driver of where
    projects were sited.
  - Heat moves nothing. Past investment fell with heat (Stage B), and the
    "more hazard cannot lower need" constraint flattens that to zero.
- **Need and gap do move.** At 6 ft and at Category 5, more tracts have high
  need that the model does not expect to be met.
- **6 ft is extrapolation for 56 tracts**: their 6 ft shares are above
  anything seen in training at 3 ft. They are flagged on the dashboard.

## 9. Alternative interventions (`scripts/ml/interventions.py`)

The test used the three highest-gap tracts with a nature-based intervention:

| Measure | Value |
|---|---|
| Residents | 11,038 |
| Exposed to 3 ft sea level rise | 193 |
| Exposed to Category 3 surge | 1,359 |
| Exposed to Category 4 surge | 2,150 |
| On the hottest 5% of land | 6,824 |
| Vulnerable residents (all three tracts are in the top vulnerability third) | 11,038 |
| Share of all vulnerable residents | 1.2% |
| Of the 70 top-10% gap tracts, still in the top 10% after funding | 67 |

The three tracts move from gap ranks 1 to 3 to ranks 370 to 436. The output
also gives the historical hazard focus of nature-based projects:

| Hazard focus | Share |
|---|---|
| Flooding | 41% |
| Extreme Heat | 23% |
| Coastal Hazards | 21% |
| Multi-Hazard | 14% |
| Infrastructure Failure | 2% |

**Coverage only: no damages avoided are claimed.** The tool rejects unknown
GEOIDs. Example output: `outputs/ml/stage2/interventions_example.json`.

## 10. Decisions needed before Stage 3

1. **Map model (D-089):** keep XGBoost (with SHAP drivers), or switch the map
   to the logistic out-of-fold predictions, which score better. Monotone
   XGBoost stays the scenario model either way.
2. **TabPFN (D-082):** set `TABPFN_TOKEN` after accepting the Prior Labs
   license if you want it in the comparison. Rerunning `stage2_models.py`
   then includes it.
3. **Heat scenarios (D-084):** keep the illustrative +1 to +3°F shifts, or
   drop heat from the scenario controls, given the model gives heat no
   effect.
