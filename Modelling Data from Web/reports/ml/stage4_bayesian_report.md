# Machine learning scenario module: Stage 4 report (Bayesian multiscale model)

**Stage 4, Part A of prompt 24.** Run 5 November 2026 on branch
`ml-scenario-module`. Preliminary. The dashboard was not changed. Part B (the
unified admin Scenario screen) waits for your go-ahead.

**Commands.** Run these from `Modelling Data from Web/`, in the ML
environment (D-079, D-097):

```bash
bash scripts/ml/run_ml.sh scripts/ml/stage4_graph.py   # once: graph and BYM2 scaling factor
bash scripts/ml/run_ml.sh scripts/ml/stage4_run.py     # everything else, about 25 minutes from scratch
```

- Fits are cached in `outputs/ml/stage4/fits/`. They take about 6 GB and are
  git-ignored. Delete them to refit.
- Seed 12086 everywhere. Packages are pinned in `scripts/ml/requirements.txt`
  and `requirements-lock.txt`.
- Decisions: D-097 to D-103.

## Sources

| Input | Publisher | Product and version | Data years | Where |
|---|---|---|---|---|
| Training frame, features, targets, spatial folds | this project (ML Stage 1) | `ml_table` (697 training tracts, 27 features, T1, sited dollars, 10 spatial k-means folds) | as below | `outputs/ml/stage1/` |
| Projects (outcome) | SCALE-R project team | SCALE-R project database: completed, funded or ongoing projects sited at parcel, neighbourhood or corridor scale | document years 1998 to 2026 | `data/raw/projects/SCALE-R_Database.csv` |
| Social indicators | CDC/ATSDR; US Census Bureau | SVI 2022 EP_* (Florida); ACS 5-year 2024 release | 2018 to 2022; 2020 to 2024 | `data/processed/analysis/tract_analysis.csv` |
| Population exposure | this project, from NOAA OCM sea level rise, NHC SLOSH MOM, Landsat 8/9 surface temperature (summers 2021 to 2024) | prompt 21 | | `data/processed/exposure/exposure_tract.csv` |
| FEMA National Risk Index | FEMA | tract table, December 2025 file, expected annual loss columns | | `../fema_miami_dade_dec_2025.csv` |
| Vulnerability score | this project | PCA component RC1, oriented so that higher means more poverty | | `outputs/pca/pca_scores_tract.csv` |
| Tract polygons (graph) | US Census Bureau | TIGER/Line 2024 tracts | 1 Jan 2024 | `data/raw/boundaries/tl_2024_12_tract.zip` |
| Stage 2 comparison models | this project (ML Stage 2) | logistic regression and XGBoost, nested tuning, same folds | | `scripts/ml/stage2_models.py` |

## In plain language

- **The Bayesian model predicts at least as well as the Stage 2 models.**
  On the same 10 spatial folds as Stage 2, Model 1 has a ROC-AUC of 0.685
  and a log loss of 0.643. Logistic regression has 0.675 and 0.653, and
  XGBoost has 0.660 and 0.651. Every difference is inside the paired
  bootstrap's 95% interval, so this is "as good as", not "better".
- **Most of the variation is between neighbourhoods and tracts, not between
  cities.**
  - Once tract features are known, which city a tract is in adds almost
    nothing.
  - Hialeah is the only city leaning clearly low, and even its interval
    includes zero.
  - Neighbouring tracts are alike beyond what their features explain.
    Allowing for that improves prediction.
- **The exact split of variance between neighbourhood and tract cannot be
  pinned down.**
  - With one yes or no per tract, the size of the spatial effect depends on
    the prior.
  - The effects of the features, read on the population-averaged scale, do
    not.
- **Hazards are still weak drivers of where projects were sited.**
  - More residents on land flooded by 3 ft of sea level rise goes with
    slightly *lower* odds of a sited project. The odds ratio is 0.80 per
    standard deviation, with a 95% interval of 0.60 to 1.03.
  - Category 3 surge exposure goes with slightly higher odds: 1.21, 0.91 to
    1.59.
  - Surface heat shows nothing: 1.08, 0.82 to 1.40.
  - The strongest signals are FEMA expected loss per resident (higher odds)
    and population density (lower odds).
- **Heat (D-106): hotter tracts receive less investment, but after controls
  this is explained mainly by distance from the coast (inland location),
  not by heat itself.**
  - On its own, hotter tracts are less likely to have a sited project, at
    0.67 times the odds per 4°F. They also get 42% fewer dollars per
    resident when they do.
  - With the other features in the model, both effects shrink to about
    zero.
  - Distance from the bay or ocean explains the most: about half on its
    own. The other features remove the rest.
- **Spatially varying hazard effects (Model 2) are not supported.** The local
  hazard slopes hardly vary across the county, and Model 2 is no better than
  Model 1.
- **Recommendation (A7):** use Model 1 (BYM2 plus city intercept for the yes or no part,
  lognormal for dollars) as the module's one model, as prompt 24's rule
  says. Read its spatial effects as "unexplained local pattern", and use the
  population-averaged effects for any statement about features.

## 1. Frame and features

- **Frame:** the same 697 training tracts as Stage 2.
- **Predictors:** the same 27 features, with one measure per hazard family
  (D-080):
  - 19 social indicators;
  - residents on land flooded by 3 ft of sea level rise;
  - residents on land reached by Category 3 surge;
  - population-weighted mean surface temperature;
  - FEMA expected loss per resident and per dollar of buildings;
  - population density, distance from the bay or ocean, and being in a city.
- **Interactions:** three hazard × vulnerability terms, each the product of
  the standardized hazard and the standardized RC1 score. That makes 30
  predictors.
- **Standardization:**
  - every predictor is standardized with the mean and SD of the rows being
    fitted;
  - in cross-validation, the training folds only;
  - interactions are built after standardizing.
- **Missing values:** one tract (12086008904) lacks 8 SVI values and RC1.
  They are filled with the training median (D-099).
- **Outcomes:**
  - Part 1: T1, whether the tract has at least one completed, funded or
    ongoing project sited at parcel, neighbourhood or corridor scale
    (395 of 697 tracts, 56.7%);
  - Part 2: sited dollars per resident, in those 395 tracts.
  - County-wide and other unsited projects are not in the outcome.
- **The county is not a level.** All tracts are in one county, so a county
  random effect cannot be estimated. **The intercept is the county.**

**Tracts per jurisdiction.** Unincorporated Miami-Dade is one jurisdiction.

| Jurisdiction | Tracts | | Jurisdiction | Tracts |
|---|---|---|---|---|
| Unincorporated Miami-Dade | 307 | | Palmetto Bay | 6 |
| Miami | 128 | | Sunny Isles Beach | 6 |
| Hialeah | 57 | | Miami Shores | 5 |
| Miami Gardens | 28 | | Hialeah Gardens | 5 |
| Miami Beach | 24 | | Key Biscayne | 4 |
| Coral Gables | 16 | | Pinecrest | 4 |
| North Miami | 16 | | Opa-locka | 4 |
| Doral | 13 | | Miami Springs | 3 |
| Homestead | 13 | | South Miami | 3 |
| Aventura | 12 | | North Bay Village | **2** |
| Cutler Bay | 10 | | Florida City | **2** |
| North Miami Beach | 8 | | Golden Beach, Biscayne Park, Indian Creek, Bal Harbour, Surfside, Virginia Gardens, West Miami, Medley | **1 each** |
| Sweetwater | 7 | | | |
| Miami Lakes | 6 | | | |

**10 jurisdictions have fewer than 3 tracts** (shown in bold). Their effects
are estimated from 1 or 2 tracts, so they are shrunk almost entirely to the
county average. Read them as "no information", not "no difference".

**Graph (A1, D-098).**
- Queen contiguity on the TIGER 2024 tract polygons gives 2,221 links in 2
  components.
- Key Biscayne's 4 tracts were joined to Miami by one added link (4.1 km).
- The final graph has 2,222 links. Every tract has at least 2 neighbours,
  and the mean is 6.4.
- The BYM2 scaling factor is 0.412.

## 2. The model in words and equations

**In words.**
- **Part 1** asks whether a tract has a sited project. Its log-odds are a
  county intercept, plus the tract's features, plus three random effects:
  - a city effect shared by every tract in the same jurisdiction;
  - a neighbourhood effect that is smooth over the tract map;
  - a tract effect specific to each tract.
- **Part 2** asks, for tracts that have a sited project, how many dollars per
  resident. Its log mean has the same parts, except the tract effect, which
  merges into the noise (D-101).
- The two parts share no parameters, so they are fitted separately. That is
  exact for a hurdle model.

**Equations.** For tract *i* in jurisdiction *j*(*i*), with standardized
predictors *x*<sub>*i*</sub> (30 columns):

Part 1:

  T1<sub>*i*</sub> ~ Bernoulli(*p*<sub>*i*</sub>)

  logit *p*<sub>*i*</sub> = α + *x*<sub>*i*</sub>β + *u*<sub>*j*(*i*)</sub> + *b*<sub>*i*</sub>

  *u*<sub>*j*</sub> = σ<sub>u</sub> *z*<sub>*j*</sub>, *z*<sub>*j*</sub> ~ N(0, 1)

  *b*<sub>*i*</sub> = σ<sub>b</sub> ( √(1 − ρ) θ<sub>*i*</sub> + √(ρ / *s*) φ<sub>*i*</sub> ), θ<sub>*i*</sub> ~ N(0, 1), φ ~ ICAR(graph), Σφ<sub>*i*</sub> ≈ 0

Part 2, for tracts with T1 = 1:

  *y*<sub>*i*</sub> = sited dollars / residents ~ LogNormal(μ<sub>*i*</sub>, σ<sub>*y*</sub>)

  μ<sub>*i*</sub> = α₂ + *x*<sub>*i*</sub>β₂ + *u*₂<sub>*j*(*i*)</sub> + σ₂ φ₂<sub>*i*</sub> / √*s*

Here:
- *s* = 0.412 is the scaling factor, so the structured part has variance
  about 1;
- ρ is the share of the spatial effect's variance that is smooth over the
  map;
- ICAR(graph) is the intrinsic conditional autoregression, with density
  proportional to exp(−½ Σ over neighbour pairs (φ<sub>*i*</sub> −
  φ<sub>*k*</sub>)²).

**Models fitted**

| Model | Part 1 terms | Use |
|---|---|---|
| 0a | α + *x*β | fixed effects only |
| 0b | 0a + city effect | does the jurisdiction matter? |
| 0c | 0a + BYM2 | does the neighbourhood matter? |
| **1** | 0a + city effect + BYM2 | main model; Part 2 as above |
| 2 | 1 + spatially varying slopes for the three hazards: β<sub>*h*</sub> + τ<sub>*h*</sub>ψ<sub>*h,i*</sub>/√*s*, with ψ<sub>*h*</sub> ~ ICAR | A3 |

**Software.** NumPyro 0.22.0 with NUTS: 4 parallel chains; target acceptance
0.95, or 0.99 for Model 2; JAX 0.12 in 64-bit. ArviZ 1.3.0 for R-hat, ESS
and PSIS-LOO.

## 3. Priors (D-100)

| Parameter | Prior | Meaning |
|---|---|---|
| β, β₂ (standardized) | Normal(0, 1) | an SD change in a predictor rarely moves the log-odds by more than 2 |
| α | Normal(0, 2.5) | |
| α₂ | Normal(mean log dollars per resident, 2.5) | |
| σ<sub>u</sub>, σ<sub>b</sub> (Part 1); Model 2 slope SDs | PC prior, exponential with P(σ > 1) = 0.05 | shrinks towards no effect |
| σ<sub>u</sub>, σ₂ (Part 2) | PC prior, P(σ > 2) = 0.05 | |
| ρ | PC prior, P(ρ < 0.5) = 2/3, from this graph's eigenvalues | the INLA default; shrinks towards no smooth spatial part |
| σ<sub>*y*</sub> | HalfNormal(2.5) | |

**Prior predictive checks** (`prior_predictive.csv`, `figures/prior_predictive.png`):

| Quantity | Observed | Prior 5% | Prior median | Prior 95% |
|---|---|---|---|---|
| Share of tracts with a sited project | 0.567 | 0.19 | 0.49 | 0.79 |
| Median log10 dollars per resident | 2.76 ($575) | −2.4 | 2.1 | 4.1 |
| 90th percentile, log10 dollars per resident | 3.89 ($7,838) | 2.7 | 5.2 | 7.5 |

- The priors cover the observed values without forcing them.
- Part 2's prior is wide, allowing up to about $30 million per resident at
  the extreme, but the data dominate it (section 4).

**Prior sensitivity** (narrow and wide versions of every Part 1 prior) is in
section 5.6.

## 4. Checks

### 4.1 MCMC (`diagnostics.csv`, `figures/trace_*.png`)

Every sampled parameter is checked: coefficients, SDs, ρ, and each of the
697 θ and φ values (and the ψ values in Model 2).

| Model | Draws | Divergences | Max R-hat | Min bulk ESS | Min tail ESS | Pass |
|---|---|---|---|---|---|---|
| 0a Part 1 | 4 × 2,000 | 0 | 1.002 | 7,639 | 5,388 | yes |
| 0b Part 1 | 4 × 2,000 | 0 | 1.002 | 3,031 | 3,204 | yes |
| 0c Part 1 | 4 × 5,000 | 0 | 1.003 | 851 | 1,606 | yes |
| **1 Part 1** | 4 × 5,000 | 0 | 1.004 | 998 | 1,828 | **yes** |
| 2 Part 1 | 4 × 5,000 (10,000, thinned by 2) | 0 | 1.009 | 541 | 1,564 | yes |
| 1 Part 1, narrow priors | 4 × 5,000 (thinned) | 0 | 1.002 | 1,830 | 2,373 | yes |
| 1 Part 1, wide priors | 4 × 5,000 | 0 | 1.002 | 1,067 | 1,875 | yes |
| **1 Part 2, lognormal** | 4 × 5,000 (thinned) | 0 | 1.005 | 1,395 | 2,909 | **yes** |
| 1 Part 2, Gamma | 4 × 5,000 (thinned) | **1** | 1.002 | 1,820 | 4,687 | no (1 divergence) |

Tail ESS uses the 5% and 95% quantiles. The Part 2 fits hit the maximum tree
depth in under 0.3% of draws. That costs efficiency, not validity.

**What it took to get there** (D-101):
- A first run with 4 × 1,000 draws left ρ with ESS 230 to 350. The spatial
  models mix slowly in ρ, so they now run 5,000 draws.
- Part 2 with a full BYM2 term failed: the lognormal had 69 divergences and
  R-hat 1.57. With one dollar figure per tract, the BYM2 tract term and the
  observation noise cannot be told apart. Part 2 now uses a structured-only
  spatial effect.

### 4.2 Posterior predictive checks (`posterior_predictive.csv`)

| Check | Observed | Replicated median | 95% range | Inside? |
|---|---|---|---|---|
| Share of tracts with a sited project | 0.567 | 0.567 | 0.539 to 0.593 | yes |
| Share of zeros (no sited project) | 0.433 | 0.433 | 0.407 to 0.461 | yes |
| Lognormal: 10th percentile of $/resident | $41 | $40 | $26 to $58 | yes |
| 25th percentile | $141 | $134 | $97 to $182 | yes |
| 50th percentile | $575 | $539 | $407 to $712 | yes |
| 75th percentile | $2,362 | $2,254 | $1,661 to $3,108 | yes |
| 90th percentile | $7,838 | $8,399 | $5,688 to $12,873 | yes |

The Gamma family also passes every one of these (table in the CSV). The PPCs
cannot choose between the two families, so the choice is made in D-102.

### 4.3 Model comparison: LOO, WAIC and spatial cross-validation

**PSIS-LOO and WAIC** (`loo.csv`):

| Model | elpd LOO | SE | p_loo | Pareto k > 0.7 | elpd WAIC |
|---|---|---|---|---|---|
| 0a Part 1 | −438.3 | 12.8 | 34 | 0 of 697 | −437.9 |
| 0b Part 1 | −434.0 | 13.0 | 42 | 0 | −433.3 |
| 0c Part 1 | −384.8 | 11.4 | 287 | **625** | −257.6 |
| 1 Part 1 | −383.5 | 11.1 | 284 | **626** | −261.2 |
| 2 Part 1 | −385.5 | 11.5 | 286 | **643** | −261.2 |
| 1 Part 2, Gamma | −3,270.1 | 40.2 | 158 | **101 of 395** | −3,243.0 |
| 1 Part 2, lognormal | −3,286.0 | 42.8 | 44 | 0 | −3,284.8 |

**PSIS-LOO and WAIC are not reliable for any Part 1 model with a BYM2 term,
or for the Gamma Part 2.**
- With one yes or no per tract, the tract-level effect lets the model fit
  each tract nearly on its own. The effective number of parameters is about
  285.
- So leaving one tract out changes the posterior too much for importance
  sampling, and 90% of the Pareto k values exceed 0.7.
- Part 1 models are therefore compared by **spatial cross-validation**
  (D-102). It refits the model with each spatial fold held out and does not
  rely on importance sampling.
- The Gamma Part 2's LOO lead (16 elpd) cannot be trusted. The lognormal is
  used.

**Spatial cross-validation, Part 1.**
- The same 10 spatial folds as Stage 2.
- Each fold is refitted from scratch with 4 chains × 2,000 draws, and the
  standardization is fitted on the training folds.
- For held-out tracts, the neighbourhood effect is predicted from the ICAR
  structure, and the tract effect comes from its prior.

| Model | ROC-AUC | PR-AUC | Log loss | Brier | Out-of-fold elpd (SE) |
|---|---|---|---|---|---|
| 0a fixed effects | 0.673 | 0.723 | 0.656 | 0.228 | −457.1 (13.7) |
| 0b + city | 0.677 | 0.721 | 0.656 | 0.228 | −457.5 (14.3) |
| 0c + BYM2 | 0.685 | 0.733 | 0.641 | 0.224 | −447.1 (12.2) |
| **1 + city + BYM2** | **0.685** | **0.730** | **0.643** | **0.224** | **−448.0 (12.2)** |
| 2 + varying hazard slopes | 0.684 | 0.728 | 0.642 | 0.224 | −447.7 (12.1) |
| Logistic regression (Stage 2 map model) | 0.675 | 0.719 | 0.653 | 0.227 | |
| XGBoost (Stage 2) | 0.660 | 0.714 | 0.651 | 0.230 | |

Paired bootstrap (2,000 resamples of tracts, seed 12086), showing the
difference and its 95% interval:

| Comparison | ROC-AUC | PR-AUC | Log loss (lower is better) |
|---|---|---|---|
| Model 1 minus logistic | +0.010 (−0.012 to +0.030) | +0.011 (−0.016 to +0.035) | −0.010 (−0.030 to +0.011) |
| Model 1 minus XGBoost | +0.025 (−0.003 to +0.055) | +0.016 (−0.019 to +0.054) | −0.008 (−0.034 to +0.018) |
| Model 2 minus logistic | +0.009 (−0.014 to +0.030) | +0.009 (−0.018 to +0.034) | −0.010 (−0.031 to +0.011) |
| Model 2 minus XGBoost | +0.024 (−0.006 to +0.052) | +0.014 (−0.024 to +0.053) | −0.009 (−0.033 to +0.019) |

Paired differences in out-of-fold elpd (`spatial_cv_elpd_differences.csv`):

| Comparison | elpd difference (SE) | Reading |
|---|---|---|
| 0c minus 0a (adding BYM2) | +10.0 (5.8) | the spatial effect helps, by about 1.7 SE |
| 0b minus 0a (adding the city effect) | −0.3 (3.4) | the city effect does not help |
| 1 minus 0c (adding the city effect to BYM2) | −0.9 (0.6) | a slight cost, within noise |
| 2 minus 1 (varying slopes) | +0.4 (0.8) | no improvement |

**Fold-fit diagnostics** (`spatial_cv_fold_diagnostics.csv`).
- The worst hyperparameter R-hat across the 50 Bayesian fold fits is 1.025,
  for ρ in one Model 0c fold. Model 1's worst is 1.018.
- There are 26 divergences in 400,000 draws: 22 in Model 0b, 1 in Model 1.
- These fits are used only for out-of-fold predictions, which average over
  draws, so this is adequate. It is not as clean as the main fits.

**Answer to A3.** Model 2 converges (section 4.1) but does not improve fit:
- its out-of-fold elpd is +0.4 (SE 0.8);
- its PSIS-LOO is lower by 2.0, though unreliable;
- its slopes hardly vary (section 5.5).

**Model 1 is kept.**

### 4.4 Residual spatial autocorrelation (`residual_moran.csv`)

Moran's I on residuals (T1 minus predicted probability), using the 6 nearest
neighbours and 999 permutations, seed 12086:

| Model | Residuals | Moran's I | p |
|---|---|---|---|
| Model 1 | spatial out-of-fold | 0.118 | 0.001 |
| Model 2 | spatial out-of-fold | 0.118 | 0.001 |
| Logistic regression | spatial out-of-fold | 0.141 | 0.001 |
| XGBoost (Stage 2 reference) | spatial out-of-fold | 0.132 | 0.001 |
| Model 0a | in-sample posterior mean | 0.081 | 0.001 |
| Model 1 | in-sample posterior mean | −0.018 | 0.21 |

- In sample, the spatial effect removes the residual clustering entirely.
- Out of fold, it only reduces it, from 0.13 to 0.14 down to 0.12.
  - Held-out folds are whole areas, so most of a held-out tract's neighbours
    are also held out.
  - The neighbourhood effect then has little to borrow from.
- So spatial CV scores are still somewhat optimistic for any one area, as
  in Stage 2.

## 5. Results (Model 1)

### 5.1 Variance by scale (`variance_by_scale.csv`)

**Part 1, latent logit scale.** The individual-level residual is the logistic
variance, π²/3 = 3.29.

| Scale | Variance (mean) | Share of latent variance (95% interval) |
|---|---|---|
| City (jurisdiction) | 0.48 | 1.6% (0.0% to 9.9%) |
| Neighbourhood (structured BYM2) | 12.8 | 37.9% (13.4% to 64.3%) |
| Tract (unstructured BYM2) | 16.4 | 49.2% (23.1% to 73.5%) |
| Individual (logistic) | 3.29 | 11.3% (5.5% to 22.1%) |

- BYM2 ρ is 0.43 (0.16 to 0.73), the smooth share of the spatial effect.
- Jurisdiction SD is 0.51 (0.01 to 1.70).
- Spatial SD σ<sub>b</sub> is 5.3 (3.3 to 7.5).
- **Latent ICC** (share of latent variance above the individual level) is
  0.89.
- **Read these with section 5.6.**
  - The size of the spatial effect is not identified by these data. It
    follows the prior: 1.8 under narrow priors, 5.3 under the main priors,
    12.5 under wide priors.
  - The latent ICC moves with it: 0.48, 0.89, 0.98.
  - What is stable across priors:
    - the city share is small;
    - a real spatial effect exists (spatial CV, section 4.3);
    - the population-averaged feature effects are unchanged.

**Part 2, log dollars per resident (lognormal).**

| Scale | Variance (mean) | Share (95% interval) |
|---|---|---|
| City (jurisdiction) | 0.11 | 3.5% (0.0% to 13.5%) |
| Neighbourhood (structured, ICAR) | 0.11 | 3.5% (0.0% to 17.0%) |
| Tract and project residual | 2.77 | 93.1% (77.8% to 99.8%) |

Among tracts that have a sited project, how much they got is almost all
tract-to-tract and project-to-project variation. City and neighbourhood
explain little of it.

### 5.2 Fixed effects (`fixed_effects.csv`)

**How to read Part 1.** The table gives **population-averaged odds ratios**
per SD of each predictor. They are the latent coefficients scaled by
1/√(1 + 0.346 σ²<sub>total</sub>) (Zeger, Liang and Albert 1988).
- They compare tracts across the county, as the Stage 2 logistic model does.
- Unlike the latent, tract-specific coefficients, they do not depend on the
  prior (section 5.6).
- The latent coefficients and odds ratios are in the CSV.

**How to read Part 2.** The table gives the percentage change in dollars per
resident per SD, for tracts that have a sited project.

Predictors whose 95% interval excludes no effect, in either part, and the
hazards:

| Predictor | Part 1: odds ratio (95% CrI) | Part 2: % change (95% CrI) |
|---|---|---|
| FEMA expected yearly loss per resident | **1.45 (1.10 to 1.90)** | +14% (−17 to +52) |
| Population density | **0.70 (0.52 to 0.93)** | **−32% (−53 to −6)** |
| Group quarters share (EP_GROUPQ) | **0.83 (0.68 to 1.00)** | +7% (−16 to +36) |
| Minority share (EP_MINRTY) | 0.83 (0.60 to 1.11) | **−36% (−54 to −14)** |
| Unemployment (EP_UNEMP) | 1.07 (0.88 to 1.30) | **−19% (−34 to −2)** |
| Being in a city | 1.19 (0.89 to 1.57) | **+53% (+1 to +120)** |
| Distance from the bay or ocean | 0.76 (0.48 to 1.12) | −5% (−39 to +43) |
| Residents on land flooded by 3 ft SLR | 0.80 (0.60 to 1.03) | +23% (−7 to +59) |
| Residents on land reached by Category 3 surge | 1.21 (0.91 to 1.59) | +26% (−3 to +62) |
| Surface heat | 1.08 (0.82 to 1.40) | −6% (−31 to +25) |

- No other social indicator has an interval excluding no effect in either
  part.
- **Read the coefficients jointly.** The 19 social indicators overlap
  heavily; that is why Stage 2 used PCA for need. So one indicator's
  coefficient is its effect holding the other 18 fixed, which is a
  narrow comparison.

### 5.3 Hazard × vulnerability (`hazard_by_vulnerability.csv`)

The hazard slope on the latent log-odds scale, at low, average and high
vulnerability (RC1 at −1, 0 and +1 SD):

| Hazard | Low vulnerability | Average | High vulnerability | Interaction, population-averaged (95% CrI) |
|---|---|---|---|---|
| Residents on land flooded by 3 ft SLR | −0.49 (P > 0: 0.22) | −0.77 (0.04) | −1.04 (0.01) | −0.08 (−0.30 to +0.13) |
| Residents on land reached by Category 3 surge | +0.20 (0.63) | +0.60 (0.91) | +1.00 (0.97) | +0.12 (−0.07 to +0.32) |
| Surface heat | +0.18 (0.63) | +0.21 (0.68) | +0.23 (0.66) | +0.01 (−0.20 to +0.21) |

- **No interaction is clearly different from zero.** The direction is
  suggestive for flooding.
  - In more vulnerable tracts, sea level rise exposure goes with *lower*
    odds of a sited project.
  - Surge exposure goes with *higher* odds.
- In Part 2, all three interactions are within ±7% per SD, and every
  interval includes zero.

### 5.4 City effects (`city_effects.csv`, `figures/city_effects.png`)

The ranked plot shows each jurisdiction's effect on the log-odds, with 95%
intervals. Jurisdictions with fewer than 3 tracts are starred.

- **Every interval includes zero.** City effects are small (SD 0.51) beside
  the spatial effect.
- **Lowest:** Hialeah, −0.65 (−3.43 to +0.30), probability above zero 0.23.
  It has 57 tracts and a 25% sited rate, below what its features predict.
- **Highest:** Miami Lakes, +0.26 (−0.79 to +2.27), and Cutler Bay, +0.20.
- **The 1-tract and 2-tract cities sit at about +0.01 to +0.07.** That is
  shrinkage to the county, not evidence.
- Unincorporated Miami-Dade (307 tracts) is −0.09 (−1.57 to +1.12).

### 5.5 Maps (`figures/map_spatial_and_city_effects.png`, `figures/map_model2_hazard_effects.png`)

- **Neighbourhood (structured) effect.** Higher than the features predict:
  - the northeast (North Miami, North Miami Beach, Miami Gardens and nearby
    unincorporated areas);
  - Key Biscayne;
  - parts of the urban core.

  Lower than the features predict:
  - a band of western suburban tracts in unincorporated Miami-Dade;
  - the large rural and Everglades tracts in the south and west.
- These descriptions are read from the map. Per-tract values are in
  `tract_effects.csv`.
- **City effect.** Nearly flat. Hialeah is the visible exception.
- **Model 2 hazard effects with uncertainty:**
  - the local slope maps are almost uniform;
  - the slope SDs τ are small: 0.31, 0.39 and 0.42, with intervals from
    about 0.01 to 1.1 to 1.5;
  - sea level rise: 49 tracts reach a 90% probability of a negative local
    effect, and the other 648 are uncertain;
  - surge: 2 tracts reach a 90% probability of a positive local effect;
  - heat: no tract reaches either.
  - Per-tract slopes and probabilities are in `tract_effects.csv`.

### 5.6 Prior sensitivity (`prior_sensitivity.csv`)

| | Narrow | Main | Wide |
|---|---|---|---|
| Coefficient prior SD; SD prior P(σ > *x*) = 0.05 at | 0.5; 0.5 | 1; 1 | 2.5; 2 |
| Jurisdiction SD | 0.29 | 0.51 | 0.90 |
| Spatial SD σ<sub>b</sub> | 1.8 | 5.3 | 12.5 |
| ρ | 0.65 | 0.43 | 0.39 |
| Latent ICC | 0.48 | 0.89 | 0.98 |
| SLR, latent | −0.38 | −0.77 | −1.85 |
| **SLR, population-averaged** | **−0.26 (−0.54, +0.01)** | **−0.24 (−0.51, +0.03)** | **−0.25 (−0.53, +0.02)** |
| **Surge, population-averaged** | +0.19 | +0.18 | +0.19 |
| **Heat, population-averaged** | +0.08 | +0.07 | +0.07 |
| **Population density, population-averaged** | −0.39 | −0.36 | −0.37 |
| **Distance from coast, population-averaged** | −0.36 | −0.30 | −0.34 |

- **The latent scale is not identified.** The data fix the ratio of each
  coefficient to the total latent SD, not either one alone. So latent
  coefficients and variance shares follow the prior.
- **Population-averaged effects agree to within 0.06 across a five-fold
  change in the priors.** All conclusions in this report rest on those.
- All three runs pass every MCMC check.

### 5.7 Does the heat gap hold after controls? (`heat_gap_after_controls.csv`, `heat_terciles.csv`)

**Descriptive.** Sited dollars only, with the 697 training tracts split into
equal-count terciles:

| Tercile | Tracts | Share with a sited project | Sited $ per resident (pooled) |
|---|---|---|---|
| Coolest | 233 | 64.8% | $3,692 |
| Middle | 232 | 58.2% | $1,716 |
| Hottest | 232 | 47.0% | $899 |

**Modelled, per SD of surface heat (4.0°F):**

| Model | Part 1: odds ratio (95% CrI) | Part 2: % change (95% CrI) |
|---|---|---|
| Heat alone | **0.67 (0.57 to 0.78)** | **−42% (−51 to −32)** |
| Heat plus population density | 0.71 (0.60 to 0.82) | |
| Heat plus FEMA expected loss per resident | 0.72 (0.61 to 0.85) | |
| Heat plus vulnerability (RC1) | 0.65 (0.54 to 0.76) | |
| Heat plus being in a city | 0.67 (0.57 to 0.78) | |
| Heat plus distance from the bay or ocean | 0.83 (0.68 to 0.98) | |
| Model 0a: all controls, no city or spatial effect | 1.13 (0.82 to 1.53) | |
| Model 1, population-averaged | 1.08 (0.82 to 1.40) | −6% (−31 to +25) |

- **In plain words (D-106): hotter tracts receive less investment, but after
  controls this is explained mainly by distance from the coast (inland
  location), not by heat itself.**
  - Hotter tracts are less likely to have a sited project, and get fewer
    dollars when they do.
  - But that is explained by the features that go with heat.
- Distance from the bay or ocean explains the most: heat and distance
  correlate at 0.43, so hot tracts are inland. Alone it removes about half
  the gap.
- The full set of features removes all of it, even without the spatial
  effects (Model 0a).
- **This is not evidence that heat is ignored.** It means heat adds nothing
  once location and the other features are known. Inland tracts get less
  sited money, and inland tracts are hotter. The model cannot say which of
  the two drives the decisions.

## 6. Recommendation (A7)

**Rule (prompt 24):** if the Bayesian model predicts at least as well as
logistic regression and XGBoost on the same spatial folds, within the
bootstrap intervals or better, it becomes the module's one model.

**Result.**
- Model 1 meets the rule on every metric.
  - Against logistic regression: ROC-AUC +0.010, PR-AUC +0.011, log loss
    −0.010.
  - Against XGBoost: +0.025, +0.016, −0.008.
- Every 95% interval includes zero, so it is "as good as", not clearly
  better.
- Its out-of-fold residuals are less clustered: Moran's I 0.118, against
  0.141 and 0.132.

**Recommendation: Model 1 becomes the module's one model.**
- Part 1: BYM2 plus a jurisdiction intercept, on the 30 predictors.
- Part 2: lognormal, with a jurisdiction intercept and an ICAR term.
- It gives in one model what Stage 2 needed several tools for:
  - probabilities with credible intervals, instead of Venn-ABERS and
    conformal intervals added afterwards;
  - effects at the city, neighbourhood and tract scales;
  - a dollar part (Part 2) that passes its posterior predictive checks.
    Stage 2's T5 amount model was unreliable (D-088).

**Points to settle before Part B wires it in:**
1. **Model 0c predicts marginally better than Model 1.** The difference is
   −0.9 elpd (SE 0.6). Model 1 is recommended anyway, because the city
   level is part of the question. Dropping it would cost nothing
   measurable, if you prefer the simpler model.
2. **Scenarios.**
   - The Stage 2 scenario engine uses monotone XGBoost.
   - With Model 1, a scenario changes the three hazard inputs and the
     interactions, and keeps the city and neighbourhood effects fixed.
   - Hazard effects are small and uncertain, so scenario changes in
     predicted investment will be small with wide intervals. That is the
     same conclusion as Stage 2.
   - Need and the gap do not depend on this model.
3. **Use population-averaged effects** in any driver or "why" text. The
   latent, tract-specific effects depend on the prior.
4. **Model 1's Part 2 predicts dollars.** Whether the dashboard should show
   dollar figures needs your decision. D-088 currently says no dollar
   predictions.

Nothing in the dashboard was changed in Part A.

### Decisions after Part A (5 November 2026)

- **D-104.** Model 1 is approved as the main model. Model 0c stays as a
  comparison.
- **D-105.** Dollar figures stay off the dashboard. Model 1's 90% intervals
  for sited dollars per resident (`outputs/ml/stage4/dollar_interval_widths.csv`):

  | Interval | Tracts with a sited project (395) | All 697 training tracts |
  |---|---|---|
  | Predictive: what one tract's figure could be, median width | **$8,635** (about $28 to $8,664; the high end is about 300 times the low end) | $6,286 |
  | Credible: the tract's typical (median) amount, median width | **$990** (typical amount $497; high end about 5.5 times the low end) | $711 |

  Read: the model cannot say much about one tract's dollars. It can say
  roughly what a typical amount for that kind of tract is, within a factor
  of about 5.
- **D-106.** Heat wording, as above.
- **D-107 and D-108.** Project types.
  - The intervention tool offers gray, green, blue and hybrid, with a
    typical cost per resident for each.
  - A four-class type model is not reliable for blue (17 projects) or
    hybrid, so the binary model stays. Part B report.
- **Correction to point 2 above.** Part B found that Model 1's scenario
  changes are not small.
  - Its sea level rise effect is negative and the model is not monotone, so
    under 6 ft and Category 5 its mean likelihood falls by 8.5 points.
    Some tracts fall by up to 61 points, mostly where the inputs are beyond
    the training range.
  - The monotone machine learning model rises by 1.6 points.
  - See `reports/ml/stage4_partB_report.md`.

## 7. Limitations

- **It describes the past, not need.** The model describes where past sited
  money went. It does not say where money should go.
- **Spatial effects absorb what the features miss.** A large neighbourhood
  effect means "more projects here than the features predict". It does not
  say why: local capacity, grant history, or project-database coverage are
  all possible.
- **Latent scale not identified.** Section 5.6. Variance shares and the
  latent ICC are prior-dependent and are reported as ranges, not findings.
- **LOO is unreliable for the spatial Part 1 models.** Model comparison uses
  spatial cross-validation instead (D-102).
- **One tract was imputed** (D-099).
- **Small jurisdictions.** 10 jurisdictions have fewer than 3 tracts. Their
  effects are uninformative.
- **Part 2 has no tract-level spatial term** (D-101). Its "tract" variance
  is merged with the residual.
- **Cross-sectional data.** The model uses one time slice, with 1998 to 2026
  projects against present-day features. Some features may have changed
  because of the projects.
- **Hazard effects are associations**, not effects of hazard on decisions.
- **Model 2 used ICAR-only slope deviations** (no unstructured part), as the
  prompt allowed. Its slope SDs are small and poorly determined.
