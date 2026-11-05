# Model card: SCALE-R scenario module (preliminary)

Version: Stage 2, 5 November 2026, branch `ml-scenario-module`; Bayesian
section added in Stage 4 (same date).
**PRELIMINARY: not reviewed, not for decisions.** Full results:
`reports/ml/stage2_report.md`. Decisions: `DECISIONS.md` D-071 to D-090.

## What it is

The module has four parts:
- A model of **where in Miami-Dade resilience projects have been sited**: a
  tract has, or does not have, a parcel, neighborhood or corridor project
  that is completed, funded or ongoing.
- A second model of **what type** a sited project is: gray, against
  nature-based or hybrid.
- A **need score**, built separately from the models.
- A **scenario engine** that re-predicts tracts under other sea level rise,
  storm surge and heat inputs.

| Part | Model |
|---|---|
| Map model (T1) | L2 logistic regression, class-weighted, C tuned by nested spatial CV (D-091) |
| Scenario model (T1) | the same XGBoost, with monotone increasing constraints on the three hazard features |
| Project type (T4) | XGBoost and LightGBM, with isotonic calibration inside the folds for probabilities |
| Baselines | prevalence; L2 logistic regression |

## Intended use

- Showing, on a preliminary dashboard, **where future projects are likely
  under current patterns of investment**, next to **need** (hazard exposure
  × vulnerability).
- Showing the **gap**:
  - primary: need versus ACTUAL sited investment, with a flag for high need
    and no sited project;
  - secondary: need versus expected investment (D-092).
- Exploring how that picture changes under hazard scenarios. Results outside
  the training range are flagged as extrapolation.
- Describing what a proposed set of projects would **cover**: residents,
  exposed residents, vulnerable residents.

## What it must NOT be used for

- **Deciding where investment should go.** The model learns where projects
  have been placed, not where they are needed or would work. Always read it
  next to need and the gap.
- **Claiming damages avoided or benefits.** There is no outcome data yet. The
  module reports coverage only. The next data step for true impact is NFIP
  flood insurance claims (OpenFEMA).
- **Statements about single parcels or people.** All results are for census
  tracts, and the hazard data are screening-level.
- **Dollar amounts.** The amount model (T5) is unreliable (D-088), and no
  dollar predictions are shown.
- **Forecasting from the year field.** The temporal check (T3) is a
  diagnostic only, because `Reported_Year` is a document year (D-081).

## Data and sources

| Input | Publisher | Product and version | Data years | Released | Where |
|---|---|---|---|---|---|
| Projects | SCALE-R project team | SCALE-R project database, 1,664 projects; 1,405 completed, funded or ongoing used for training; 259 planned used only as the future check | document years 1998 to 2026 | 2026 | `data/raw/projects/SCALE-R_Database.csv` |
| Social indicators | CDC/ATSDR; US Census Bureau | SVI 2022 EP_* (Florida ranking); ACS 5-year 2024 release | 2018 to 2022; 2020 to 2024 | 2024 | `data/processed/analysis/tract_analysis.csv` |
| Population exposure | this project, from NOAA OCM sea level rise (FL_SE), NHC SLOSH MOM v4 06/2026, and Landsat 8/9 C2 L2 summers 2021 to 2024 | prompt 21 | see `reports/exposure/population_exposure.md` | 5 Nov 2026 | `data/processed/exposure/exposure_tract.csv` |
| FEMA National Risk Index | FEMA | tract table (December 2025 file; expected annual loss columns only) | not stated | 2025 | `../fema_miami_dade_dec_2025.csv` |
| Housing units | EPA EJScreen v2.3 (reconstruction) | ACSTOTHU | 2018 to 2022 | 2024 | `data/raw/social/ejscreen/` |
| Boundaries, coast | US Census Bureau | TIGER/Line 2024 | 1 Jan 2024 | 2024 | `data/raw/boundaries/` |
| Vulnerability score | this project | PCA component RC1 of the 19 tract indicators | as SVI and ACS | 27 Sep 2026 | `outputs/pca/pca_scores_tract.csv` |
| FEMA flood zones | FEMA | National Flood Hazard Layer | | | **not available**; an empty slot is kept in the feature list |

**Frame.** 698 tracts. Training uses 697: the one tract under 100 residents is
excluded and kept, flagged, in the outputs.

**Features: 27.**

| Group | Features |
|---|---|
| Social (19) | PCA input list after the 0.75 rule |
| Hazard (3) | one per family: sea level rise 3 ft resident share, Category 3 surge resident share, population-weighted mean surface temperature |
| FEMA loss (2) | expected annual loss per resident and per dollar of buildings |
| Context (3) | population density, distance to the bay or ocean, in a city or unincorporated |

Jurisdiction identity is not a feature. Imputation, scaling and PCA are
fitted inside each training fold.

## Targets

| Target | What it is | n | Base rate |
|---|---|---|---|
| T1 | sited completed, funded or ongoing project present | 697 tracts | 0.567 |
| T2 | planned sited project present (future check, never trained on) | 697 tracts | 0.154 |
| T3 | first project in a 2024 to 2026 document (diagnostic only) | 412 tracts | 0.267 |
| T4 | nature-based or hybrid vs gray | 1,092 projects | 0.164 |
| T5 | log sited dollars per resident (unreliable) | 395 tracts | |

## Validation design

- **Primary:** spatial cross-validation, 10 k-means clusters of tract
  locations, seed 12086.
- **Also reported:** random 10-fold, and leave one jurisdiction out (33
  groups).
- Hyperparameters are tuned by nested, grouped cross-validation inside the
  training folds, over a small stated grid.
- Scores: ROC-AUC, PR-AUC (against the base rate), log loss and Brier.

## Scores (spatial cross-validation)

| Target | Model | ROC-AUC | PR-AUC (base rate) | Log loss | Brier |
|---|---|---|---|---|---|
| T1 | prevalence | 0.50 (fold mean) | 0.47 (0.57) | 0.696 | 0.251 |
| T1 | logistic | **0.675** | **0.719** | 0.653 | 0.227 |
| T1 | XGBoost (map) | 0.660 | 0.714 | 0.651 | 0.230 |
| T1 | XGBoost monotone (scenarios) | 0.660 | 0.712 | 0.651 | 0.230 |
| T1 | LightGBM | 0.644 | 0.712 | 0.664 | 0.236 |
| T4 | XGBoost | 0.803 | 0.536 (0.16) | 0.479 | 0.155 |
| T4 | LightGBM, calibrated | 0.805 | 0.522 | 0.346 | 0.106 |
| T5 | ridge | R² 0.23 | | | |

**The gradient-boosted models do not beat logistic regression on T1.** A
paired bootstrap finds no real difference: logistic minus XGBoost ROC-AUC is
+0.016 [−0.010, +0.042]. So the simpler logistic regression drives the map
(D-091). Random folds score 0.03 to 0.06 higher than spatial folds.

**Future check (T2).** The top 20% of tracts hold 42% (XGBoost) to 58%
(logistic) of planned projects. PR-AUC is 0.29 to 0.32, against a base rate
of 0.15.

**Calibration.**
- T1 is roughly calibrated as is.
- T4 needs isotonic calibration, because class weights inflate its
  probabilities.
- Reliability curves are in `outputs/ml/stage2/figures/`.

**Uncertainty (conformal, inside the spatial folds).**
- T1: 90% prediction sets achieve 90.5% coverage. Each tract gets a
  Venn-ABERS probability interval, average width 0.18.
- T5: intervals achieve 91.7% coverage but are too wide to use.

**Stability.** Across five seeds, ROC-AUC ranges from 0.657 to 0.675. In 50
bootstrap refits, the top two drivers are always the same.

**Spatial residuals.** Moran's I of the out-of-fold residuals is 0.13. Spatial
lags of the inputs did not reduce it.

## Top drivers (T1)

**Map model (logistic, log-odds contribution):**
1. Distance from the bay or ocean (farther lowers).
2. Population density (higher lowers).
3. Being in a city (raises).
4. FEMA expected yearly loss per resident (raises).
5. Limited English households (lowers).
6. No internet access (raises).
7. FEMA building loss per dollar of buildings (lowers).

**XGBoost (SHAP), the scenario model's family:** distance from the bay or
ocean, population density, FEMA loss per resident, single-parent households,
FEMA building loss, being in a city.

Hazard exposure ranks low: surge 13th, heat 18th, sea level rise 20th of 27.
So **hazard scenarios change the predicted likelihood very little** (at most
+0.01 on average), while need and the gap change much more.

## Limitations

- **Small sample.** 697 tracts and weak signals. Models are kept simple:
  depth-2 trees and a small grid. Even so, logistic regression does as well.
- **It learns past placement, not need.** Patterns include municipal
  budgets, programs and data coverage, not only hazard or vulnerability.
- **Where a project sits is a point.** County and municipal projects are
  excluded from the location targets because they are spread by population.
  Corridor projects such as The Underline count only where their point lies.
- **The hazard data carry their own cautions.**
  - Surge is a worst case, not a forecast.
  - Sea level rise is a screening-level bathtub model.
  - Surface heat is ground temperature, not air temperature.
  - The flood maps predate many projects, so they do not show protection
    the projects added.
- **Heat scenarios are illustrative** uniform warming of +1 to +3°F, not
  projections (D-084). They change need and the gap only, not predicted
  investment, because past investment did not follow heat (D-093).
- **Extrapolation.** 6 ft of sea level rise is outside the training range for
  56 tracts (191,028 residents). These are flagged.
- **Spatial dependence.** Residuals still cluster (Moran's I 0.13), so the
  scores are somewhat optimistic for any one area.
- **Hazard focus in T4** is decided together with the project type, so T4
  describes existing projects rather than predicting unproposed ones.
- **TabPFN was not evaluated.** It needs a license key (D-082).

## Bayesian multiscale model (Stage 4, preliminary)

Full report: `reports/ml/stage4_bayesian_report.md`. Decisions: D-097 to
D-103.

**What it is.** A two-part (hurdle) model of sited investment, fitted by
MCMC (NumPyro NUTS, 4 chains):
- **Part 1:** does a tract have a sited project? This is a logit with:
  - the 27 Stage 2 features;
  - three hazard × vulnerability terms;
  - a city (jurisdiction) intercept;
  - a BYM2 spatial effect on the tract adjacency graph.
- **Part 2:** sited dollars per resident where there is one. This is a
  lognormal model with the same features, a city intercept and a structured
  (ICAR) spatial effect.
- The county is the intercept, not a level. There is only one county.

**Checks.**
- Main fits: 0 divergences, R-hat ≤ 1.009, bulk and tail ESS > 400 for every
  parameter.
- Posterior predictive checks pass: the share of tracts with a project, and
  the 10th to 90th percentiles of dollars per resident.
- PSIS-LOO is unreliable for the spatial Part 1 models, so they are
  compared by spatial CV (D-102).

**Scores (same 10 spatial folds as Stage 2).** ROC-AUC 0.685, PR-AUC 0.730,
log loss 0.643, Brier 0.224. Against logistic regression and XGBoost, every
paired-bootstrap interval includes zero, with point estimates slightly
better. Out-of-fold residual Moran's I is 0.118.

**What it found.**
- City effects are small. Every interval includes zero, and jurisdictions
  with fewer than 3 tracts are uninformative.
- Neighbourhood-level spatial effects are real and improve prediction.
- Hazard effects are weak. Population-averaged odds ratios per SD:
  - sea level rise 0.80 (0.60 to 1.03);
  - Category 3 surge 1.21 (0.91 to 1.59);
  - heat 1.08 (0.82 to 1.40).
- The raw heat gap (0.67 per SD) disappears after controls.

**Cautions.**
- The size of the latent spatial variance, and so the variance split and
  ICC, depends on the prior.
- Use the population-averaged effects, which do not depend on it.
- Spatial effects mean "more or fewer projects than the features predict
  here", not why.

**Status.** Recommended as the module's one model (D-103), pending your
decision. The dashboard still uses the Stage 2 models.

## Software and licenses

- Python 3.13.11. Pinned versions are in `scripts/ml/requirements.txt`, and
  the full lock is in `requirements-lock.txt`: scikit-learn 1.9.1, XGBoost
  3.4.1, LightGBM 4.7.0, SHAP 0.54.1. Stage 4: NumPyro 0.22.0, JAX
  0.12.0.1, ArviZ 1.3.0 (all Apache 2.0).
- **TabPFN** 9.2.0 (Hollmann et al., *Nature*, 2025) is installed as a
  challenger for T1 and T4.
  - It is licensed under the **Prior Labs License: Apache 2.0 with an
    attribution requirement**. Any use or publication of TabPFN results must
    credit Prior Labs and the paper.
  - Its model weights need a one-time license acceptance and an API key in
    `TABPFN_TOKEN`.
  - It was **not run** in this version.
- **Rerun:**

  ```bash
  bash scripts/ml/run_ml.sh scripts/ml/stage1_build.py
  bash scripts/ml/run_ml.sh scripts/ml/stage2_models.py
  bash scripts/ml/run_ml.sh scripts/ml/scenarios.py
  bash scripts/ml/run_ml.sh scripts/ml/stage4_graph.py
  bash scripts/ml/run_ml.sh scripts/ml/stage4_run.py
  ```

  Seeds are fixed (12086) everywhere.
