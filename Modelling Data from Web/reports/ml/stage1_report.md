# Machine learning scenario module: Stage 1 report

**Stage 1 of prompt 22: the modelling table, targets and baselines.** No
gradient boosting yet; that is Stage 2. Built 5 November 2026 on branch
`ml-scenario-module`.

- Script, one command from `Modelling Data from Web/`:
  `../.venv/bin/python scripts/ml/stage1_build.py`.
- Outputs: `outputs/ml/stage1/`, git-ignored. They contain:
  - the modelling tables;
  - the feature dictionary, input inventory and target counts;
  - the baseline scores, fold assignments and log.
- Pinned packages: `scripts/ml/requirements.txt`.
- Decisions: D-071 to D-078 in `DECISIONS.md`.

This report sits in `reports/ml/` rather than `outputs/ml/` because
`outputs/` is git-ignored (D-078).

## Short summary

1. **Stage 2 is blocked on packages.** LightGBM, XGBoost and SHAP are not
   installed in any local Python environment, and installing them means
   downloading. I need your go-ahead to install them, or to use
   scikit-learn's own gradient boosting instead (D-071).
2. **The modelling table is ready.**
   - 698 tracts with 30 main features: 19 social, 6 hazard, 2 FEMA loss and
     3 context.
   - The 1 tract under 100 residents in the frame is excluded from training,
     leaving 697. The other 9 tracts under 100 residents have no residents at
     all and are already outside the frame.
   - Missingness is tiny: one tract lacks 8 SVI values.
3. **Logistic regression beats the prevalence baseline** on T1 (where sited
   projects are), T2 (planned projects) and T4 (project type), under spatial
   cross-validation:
   - **T1:** ROC-AUC 0.69, PR-AUC 0.73 against a base rate of 0.57.
   - **T2:** the T1 model's top 20% of tracts holds 57% of planned projects.
   - **T4:** ROC-AUC 0.79, PR-AUC 0.55 against a base rate of 0.16.
4. **Two targets are weak.**
   - **T3 (temporal check):** barely better than chance, ROC-AUC 0.57, and
     its PR-AUC is below the base rate.
   - **T5 (amount):** R² 0.22, Spearman 0.46.
5. **Project type is mostly explained by the project's own hazard focus.**
   - 41 of 45 sited Extreme Heat projects are nature-based or hybrid, against
     0 of 129 Storms & Hurricanes projects and 3 of 107 Infrastructure
     Failure projects.
   - A model with only scale and hazard focus scores ROC-AUC 0.79, as high
     as the full model.
6. **Spatial validation costs about 0.02 to 0.07 ROC-AUC against random
   folds.** That is the optimism that random folds would have reported.

## 1. Sources

| Input | Publisher | Product and version | Data years | Released | Where it came from | File or table ID |
|---|---|---|---|---|---|---|
| Projects | SCALE-R project team | SCALE-R project database | project `Reported_Year` 1998 to 2026 (the year of the source document, not the build year) | 2026 | `data/raw/projects/SCALE-R_Database.csv` | 1,664 projects |
| Project locations | this project | point-in-polygon join to TIGER 2024 tracts | as projects | 2026 | `data/processed/investment/project_join_keys.csv` | `tract_GEOID` |
| Social indicators and frame | CDC/ATSDR; US Census Bureau | SVI 2022 (Florida ranking) EP_*; ACS 5-year 2024 release | SVI 2018 to 2022; ACS 2020 to 2024 | SVI 2024; ACS 2024 5-year release | `data/processed/analysis/tract_analysis.csv` (from svi.cdc.gov and data.census.gov) | 19 PCA input variables (D-026) |
| Population exposure | this project | prompt 21 Stage A | see `reports/exposure/population_exposure.md` | 5 Nov 2026 | `data/processed/exposure/exposure_tract.csv` | hazard population shares, land shares |
| Sea level rise land shares | NOAA OCM | FL_SE inundation polygons | ground survey years not in the local files | layers changed Feb 2023 | `data/processed/hazards/slr_tract.csv` | `slr_*_area_share` (inventory only) |
| Storm surge land shares | NOAA NHC | SLOSH MOM v4, high tide, reprocessed 06/2026 | worst-case storms; DEMs cited 2014 to 2015 | 14 Jun 2026 | `data/processed/hazards/surge_tract.csv` | `surge_cat*_area_share` (inventory only) |
| Surface heat, block groups | USGS Landsat 8/9, via Microsoft Planetary Computer | Collection 2 Level-2 summer median | June to September 2021 to 2024 | composite built 13 Oct 2026 | `../output/lst/lst_blockgroups_miami_dade.geojson` | `lst_mean_f` |
| FEMA National Risk Index | FEMA | NRI tract table; no version field (postdates the inland flooding rebuild, `reports/physical/nri_audit.md`) | not stated in the file | file name says December 2025 | `../fema_miami_dade_dec_2025.csv` | `EAL_VALT`, `EAL_VALB`, `POPULATION`, `BUILDVALUE` |
| Housing units | EPA EJScreen v2.3 (PEDP / Harvard Dataverse reconstruction) | EJScreen 2024 | ACS 2018 to 2022 | 2024 | `data/raw/social/ejscreen/EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv` | `ACSTOTHU` |
| Boundaries and coast | US Census Bureau | TIGER/Line 2024 tracts, places, area water | 1 Jan 2024 | 2024 | `data/raw/boundaries/` | `tl_2024_12_tract`, `tl_2024_12_place`, `tl_2024_12086_areawater` |
| FEMA flood zones | FEMA | National Flood Hazard Layer | | | **not available**: the local CSV has no geometry (D-032) | empty slot |

**Input inventory** (shape, key, missingness): `outputs/ml/stage1/input_inventory.csv`.
- **Every key is unique.**
- **Missingness is high only in columns the module does not use.** Surge
  mean depth class is NA where a tract has no surge (up to 69%). Most NRI
  columns are fully empty for hazards absent from Miami-Dade.
- **The exposure tables exist**, so prompt 21 does not need rerunning.
- **The surface heat block group file was inventoried but is not the main
  heat source.** The exposure table's block-level population-weighted mean is
  finer. The block group file feeds only the land-weighted comparison feature
  (D-076).

## 2. Feature dictionary

Main set: 19 social, 6 hazard, 2 FEMA loss and 3 context features. The land
comparison set swaps the 6 hazard population measures for the 6 land
measures.

| Name | Group | Meaning | Source | Units | Transform |
|---|---|---|---|---|---|
| `EP_POV150` | social | SVI or ACS indicator EP_POV150 (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_UNEMP` | social | SVI or ACS indicator EP_UNEMP (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_HBURD` | social | SVI or ACS indicator EP_HBURD (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_NOHSDP` | social | SVI or ACS indicator EP_NOHSDP (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_UNINSUR` | social | SVI or ACS indicator EP_UNINSUR (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_AGE65` | social | SVI or ACS indicator EP_AGE65 (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_AGE17` | social | SVI or ACS indicator EP_AGE17 (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_DISABL` | social | SVI or ACS indicator EP_DISABL (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_SNGPNT` | social | SVI or ACS indicator EP_SNGPNT (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_LIMENG` | social | SVI or ACS indicator EP_LIMENG (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_MINRTY` | social | SVI or ACS indicator EP_MINRTY (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_MUNIT` | social | SVI or ACS indicator EP_MUNIT (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_MOBILE` | social | SVI or ACS indicator EP_MOBILE (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_CROWD` | social | SVI or ACS indicator EP_CROWD (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_NOVEH` | social | SVI or ACS indicator EP_NOVEH (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_GROUPQ` | social | SVI or ACS indicator EP_GROUPQ (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `EP_NOINT` | social | SVI or ACS indicator EP_NOINT (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `no_fulltime_worker_hh` | social | SVI or ACS indicator no_fulltime_worker_hh (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `crowding_over100` | social | SVI or ACS indicator crowding_over100 (PCA input list, D-026) | CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv) | percent | none; standardized in fold |
| `slr_3ft_pop_share` | hazard | share of residents on land inundated by 3 ft sea level rise (ocean-connected) | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `surge_cat3_any_pop_share` | hazard | share of residents on land with any Category 3 worst-case surge | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `surge_cat4_any_pop_share` | hazard | share of residents on land with any Category 4 worst-case surge | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `surge_cat3_over3ft_pop_share` | hazard | share of residents on land with more than 3 ft of Category 3 surge | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `heat_lst_popwt_mean_f` | hazard | population-weighted mean summer surface temperature, degrees F | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `heat_p95_pop_share` | hazard | share of residents on land at or above the county 95th percentile (113.27 F) | population exposure layers (exposure_tract.csv, prompt 21) | share 0 to 1 or degrees F | none; standardized in fold |
| `slr_3ft_land_share` | land | share of land inundated by 3 ft sea level rise | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `surge_cat3_any_land_share` | land | share of land with any Category 3 surge | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `surge_cat4_any_land_share` | land | share of land with any Category 4 surge | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `surge_cat3_over3ft_land_share` | land | share of land with more than 3 ft of Category 3 surge | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `heat_land_mean_f` | land | land-area-weighted mean of block group surface temperature, degrees F | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `heat_p95_land_share` | land | share of land at or above the county 95th percentile | existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means | share 0 to 1 or degrees F | comparison model only |
| `nri_eal_per_person` | nri | NRI total expected annual loss (EAL_VALT) divided by NRI population | FEMA NRI tract table, December 2025 file | dollars per person per year; dollars per dollar of building value per year | log1p, then standardized in fold |
| `nri_ealb_per_building_value` | nri | NRI building expected annual loss (EAL_VALB) divided by building value (BUILDVALUE) | FEMA NRI tract table, December 2025 file | dollars per person per year; dollars per dollar of building value per year | log1p, then standardized in fold |
| `pop_density` | context | residents per km2 of land (ACS 2020-2024, TIGER ALAND) | TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022) | see meaning | log1p, then standardized in fold |
| `housing_density` | context | housing units per km2 of land (EJScreen ACSTOTHU summed over block groups) | TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022) | see meaning | log1p, then standardized in fold; NOT in the main set (0.75 rule with pop_density, D-073) |
| `land_km2` | context | land area, km2 (TIGER ALAND) | TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022) | see meaning | log1p, then standardized in fold; NOT in the main set (0.75 rule with pop_density, D-073) |
| `dist_coast_km` | context | distance from the tract's representative point to Biscayne Bay, the Atlantic or the sounds, km | TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022) | see meaning | log1p, then standardized in fold |
| `in_municipality` | context | 1 if the tract centroid is in an incorporated municipality, 0 if unincorporated | TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022) | see meaning | standardized in fold |
| `fema_flood_zone_share (slot)` | flood_zone | share of residents in FEMA high-risk flood zones (A, V) | FEMA NFHL, not available | share | PENDING: no geometry in the current file (D-032) |

**Not features:**
- jurisdiction identity, which is used only to group the
  leave-one-jurisdiction-out check;
- the seven race adjunct columns;
- anything built from investment or projects.

**Missingness in the main set.** Only tract 12086008904 (Unincorporated Miami-Dade) is missing anything: 8 SVI values (EP_POV150, EP_HBURD,
EP_SNGPNT, EP_MUNIT, EP_MOBILE, EP_CROWD, EP_NOVEH, EP_NOINT). They are
filled with the training-fold median inside each fold, and a missing-value
indicator column is added.

**Screen at |rho| ≥ 0.75** (`outputs/ml/stage1/feature_screen_pairs.csv`):

| Pair | Spearman | What was done |
|---|---|---|
| heat population-weighted mean vs heat ≥ p95 share | +0.95 | **kept both**: the prompt fixes both heat measures. Flagged |
| population density vs housing density | +0.94 | housing density left out of the main set (D-073) |
| surge Cat 3 any vs Cat 3 more than 3 ft | +0.92 | **kept both**: the prompt fixes the hazard set. Flagged |
| housing density vs land area | −0.87 | land area left out of the main set (D-073) |
| population density vs land area | −0.86 | land area left out of the main set (D-073) |
| surge Cat 3 any vs Cat 4 any | +0.82 | **kept both**: the prompt fixes the hazard set. Flagged |

The three hazard pairs over 0.75 stay because your prompt names that exact
set. Under the 0.75 rule, one of each would normally go. **Say if you want
the rule applied to them too.** L2-regularized logistic regression and tree
models tolerate the overlap, but SHAP credit will be split between each pair.

## 3. Targets

Training tracts: 697.

| Target | Units | n | Positives | Base rate |
|---|---|---|---|---|
| **T1** sited project present (completed, funded or ongoing) | tracts | 697 | 395 | 0.567 |
| **T2** planned sited project present | tracts | 697 | 107 | 0.154 |
| T2 among tracts with no T1 project | tracts | 302 | 16 | 0.053 |
| **T3** train label: first sited project by 2023 | tracts | 697 | 285 | 0.409 |
| T3 test: first sited project 2024 to 2026, among tracts with none by 2023 | tracts | 412 | 110 | 0.267 |
| **T4** nature-based or hybrid (green, blue, hybrid) vs gray | projects | 1,092 | 179 | 0.164 |
| **T5** log sited dollars per resident | tracts with T1 | 395 | | |

**T1** agrees exactly with `investment_any_single_unit` in the analysis
table, in all 698 tracts.

**T2.** There are 217 planned sited projects (parcel, neighborhood,
corridor). 201 of them fall in 108 tracts of the frame, and 107 of those
tracts are training tracts. Planned projects never enter training.

**T3: Reported_Year distribution** of sited completed, funded and ongoing
projects:

| Year | ≤2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| Projects | 79 | **399** | 25 | 62 | 71 | 99 | 246 | 118 |

**`Reported_Year` is the year of the source document, not the year a project
was built or funded.** The 399 projects in 2020 almost certainly come from
one large 2020 source document, not from a 2020 building boom. So T3 tests
"tracts that first appear in documents from 2024 to 2026", which is a weak
proxy for new investment. Read the T3 results with that in mind.

**T4.** There are 1,099 sited completed, funded and ongoing projects (1,092 in
training tracts):

| Type | Projects |
|---|---|
| Gray | 919 |
| Hybrid | 122 |
| Green | 40 |
| Blue | 18 |

Your prompt says blue has 36 projects. That counts every status, including
Planned. Within this target's scope, blue has 18, so it is combined with
green and hybrid as planned.

Hazard focus against type (D-077):

| Hazard focus | Gray | Nature-based or hybrid | Share nature-based or hybrid |
|---|---|---|---|
| Flooding | 588 | 73 | 11% |
| Storms & Hurricanes | 129 | 0 | 0% |
| Infrastructure Failure | 104 | 3 | 3% |
| Coastal Hazards | 46 | 38 | 45% |
| Multi-Hazard | 48 | 25 | 34% |
| Extreme Heat | 4 | 41 | 91% |

**Infrastructure Failure is almost all gray.** It is also the category that
drives most of the investment gap between cool and hot tracts
(`reports/exposure/heat_tercile_investment.md`).

**T5** is log(sited dollars ÷ residents) among the 395 tracts with a sited
project.

## 4. Baselines

**Validation design (D-075)**
- **Spatial CV (primary):** 10 folds from k-means clusters of tract
  representative points (seed 12086). Folds hold 43 to 106 tracts, with T1
  rates from 0.25 to 0.76 (`outputs/ml/stage1/spatial_folds.csv`).
- **Random CV:** 10 stratified folds.
- **Leave one jurisdiction out:** 33 groups. Unincorporated Miami-Dade is
  one group with about 45% of tracts.
- **Logistic regression:** L2, with C chosen from {0.01, 0.1, 1, 10} by an
  inner grouped CV on the training folds only, which makes it nested.
  Imputation, scaling and PCA are all fitted inside each training fold.
- **Prevalence:** predicts the training folds' base rate.

**How the scores are reported.**
- Pooled out-of-fold scores, plus ROC-AUC and PR-AUC averaged over folds.
- Pooling hurts prevalence's ranking scores: its pooled ROC-AUC under
  spatial CV is 0.34, because fold base rates differ. Its fair value is
  0.50, the fold average.
- PR-AUC should be compared with the base rate.

### T1: sited project present (697 tracts, base rate 0.567)

| Model | CV | ROC-AUC (pooled) | ROC-AUC (fold mean) | PR-AUC (pooled) | Log loss | Brier |
|---|---|---|---|---|---|---|
| Prevalence | spatial | (0.34) | 0.50 | 0.47 | 0.696 | 0.251 |
| Logistic, class-weighted | **spatial** | **0.687** | 0.638 | **0.732** | 0.637 | 0.223 |
| Logistic, class-weighted | random | 0.707 | 0.708 | 0.748 | 0.627 | 0.218 |
| Logistic, class-weighted | jurisdiction | 0.665 | 0.569 | 0.710 | 0.642 | 0.225 |
| Logistic, unweighted | spatial | 0.667 | 0.638 | 0.721 | 0.643 | 0.226 |
| Logistic, PCA scores in fold | spatial | 0.689 | 0.649 | 0.739 | 0.642 | 0.223 |
| Logistic, land shares (comparison) | spatial | 0.677 | 0.640 | 0.726 | 0.651 | 0.227 |

- **Logistic regression clearly beats prevalence.**
- **Spatial folds score about 0.02 to 0.07 below random folds.**
- **Five PCA scores (fitted inside each fold) do as well as the 19 social
  variables.**
- **Land shares in place of population shares change almost nothing.**
  That matches Stage B.

### T2 and T3: does the T1 model point to the future?

T2 uses the spatial out-of-fold T1 predictions. T3 retrains on the 2023
label and is tested on tracts with no project by 2023.

| Target | Model | n | Base rate | ROC-AUC | PR-AUC | Positive tracts in the top 20% | Planned projects in the top 20% |
|---|---|---|---|---|---|---|---|
| T2, all tracts | prevalence | 697 | 0.154 | | 0.154 (no ranking) | 20% expected | 20% expected |
| T2, all tracts | logistic, class-weighted | 697 | 0.154 | **0.709** | **0.320** | **45%** | **57%** |
| T2, tracts with no current project | logistic, class-weighted | 302 | 0.053 | 0.634 | 0.099 | 44% | 50% |
| T3, first project 2024 to 2026 | prevalence | 412 | 0.267 | | 0.267 (no ranking) | 20% expected | |
| T3, first project 2024 to 2026 | logistic, class-weighted | 412 | 0.267 | 0.574 | 0.325 | 29% | |

**Reading the results**
- **T2.** The tracts the T1 model ranks highest hold more than twice their
  share of planned projects: 57% of planned projects fall in the top 20% of
  tracts. Among tracts with no project yet, the top 20% holds 44% of those
  that now have a planned project (16 tracts, so a small number).
- **T3 is weak.** Ranking of tracts first appearing in 2024 to 2026
  documents is only a little better than chance. Its PR-AUC (0.325) is about
  the prevalence model's (0.335). The `Reported_Year` problem above is the
  likely reason.

### T4: project type (1,092 projects, base rate 0.164)

| Model | CV | ROC-AUC (pooled) | ROC-AUC (fold mean) | PR-AUC (pooled) | Log loss | Brier |
|---|---|---|---|---|---|---|
| Prevalence | spatial | (0.40) | 0.50 | 0.13 | 0.448 | 0.138 |
| Logistic, all features | **spatial** | **0.793** | 0.794 | **0.549** | 0.515 | 0.168 |
| Logistic, all features | random | 0.825 | 0.831 | 0.562 | 0.502 | 0.163 |
| Logistic, all features | jurisdiction | 0.752 | 0.816 | 0.522 | 0.556 | 0.187 |
| Logistic, scale and hazard focus only | spatial | 0.786 | 0.771 | 0.537 | 0.513 | 0.168 |

- **Hazard focus does almost all the work.**
- **Tract features add little, about 0.01 ROC-AUC.**
- **Log loss and Brier are worse than prevalence for the class-weighted
  model.** That is expected: class weights push probabilities up. Stage 2
  calibrates them.
- **Hazard focus is a property of the project, decided alongside its type.**
  Using it to predict type is fair for describing projects, but it would not
  be known for a project not yet proposed (D-077).

### T5: log sited dollars per resident (395 tracts)

| Model | CV | RMSE | MAE | R² | Spearman |
|---|---|---|---|---|---|
| Mean | spatial | 2.04 | 1.65 | −0.04 | |
| Ridge | **spatial** | **1.76** | 1.41 | **0.22** | **0.46** |
| Ridge | random | 1.73 | 1.38 | 0.25 | 0.50 |
| Ridge | jurisdiction | 1.86 | 1.48 | 0.14 | 0.39 |

**T5 is weak and is flagged as such.** It explains about a fifth of the
variation in how much was sited.

The first run gave ridge an R² of −19 under spatial CV. Raw, very skewed
features (land area, densities) extrapolated wildly in some folds. A fixed
log1p transform of the skewed features fixed it (D-074).

## 5. What Stage 2 needs

1. **The gradient boosting packages.** Install LightGBM, XGBoost and SHAP
   (a download), or use scikit-learn's `HistGradientBoostingClassifier`.
   That one is installed and supports the monotone constraints the scenario
   model needs. SHAP values for it would have to come from permutation
   importance and partial dependence instead (D-071).
2. **The three hazard pairs over 0.75.** Keep them, as now, or apply the rule.
3. **T3.** Accept it as a weak check given `Reported_Year`, or drop it.

The block group grain is not used (optional in the prompt). Nothing was
committed on this branch yet.
