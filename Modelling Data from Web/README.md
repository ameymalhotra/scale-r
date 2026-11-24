# Modelling Data from Web

This folder holds the data and analysis behind the SCALE-R study: where
climate resilience money went in Miami-Dade, compared with social
vulnerability and with physical hazards (sea level rise, storm surge,
surface heat).

**Start with two files:**
- `DECISIONS.md` has every methods decision, numbered D-001 onward.
- This file says what is where and how to rerun each step.

The folder was reorganized on 5 November 2026 (D-061). If an older report
or prompt names a path that no longer exists, see "Old path → new path" at
the end.

## What is where

```
README.md        this file
DECISIONS.md     the decision log (add an entry for every new decision)
data/
  raw/           downloads, never edited
    projects/      SCALE-R_Database.csv (1,664 projects)
    boundaries/    TIGER/Line zips: 2024 tracts, block groups, water, places,
                   landmarks; 2020 blocks; ZCTAs
    social/
      acs_tract/       10 ACS 2020-2024 tables, tract (CRE components, population)
      acs_blockgroup/  16 ACS 2020-2024 tables, block group (ADI components, population)
      svi/             CDC SVI 2022, Florida (FLORIDA.csv)
      ejscreen/        EJScreen v2.3 reconstruction, column dictionary, tech doc
    physical/
      sea_level_rise/  NOAA FL_SE GeoPackage (3.8 GB) and README
      storm_surge/     NHC SLOSH MOM v4 06/2026, one GeoTIFF per category (4.8 GB)
      flood_zones/     FEMA flood zone CSV (no geometry, not usable yet)
      fema_nri/        empty: the NRI file is ../fema_miami_dade_dec_2025.csv at the repo root
  processed/     tables built from the raw data
    investment/    tract_investment.csv, blockgroup_investment.csv,
                   allocation_audit_{tract,bg}.csv, project_join_keys.csv
    analysis/      tract_analysis.csv (698 tracts), blockgroup_analysis.csv (1,843),
                   variable_dictionary.csv
    hazards/       slr_{tract,blockgroup}.csv, surge_{tract,blockgroup}.csv (land shares)
    exposure/      exposure_{tract,blockgroup}.csv (residents exposed)
scripts/
  common/        shared code; paths.py defines every path in one place
  01_projects/   project profile, spatial join, investment tables
  02_social/     builds the two analysis tables
  03_physical/   sea level rise, storm surge, FEMA NRI
  04_exposure/   population exposure (Stage A) and exposure vs investment (Stage B)
  05_analysis/   univariate, correlation, diagnostics, density, gray split,
                 correlation screen, PCA, compiled reports and figures
  website/       scripts that write website data: src/exposure/data/ (public) and
                 src/admin/viz/scenario/data/ (admin only)
  ml/            machine learning scenario module (prompt 22)
outputs/         results, by analysis (git-ignored)
  projects/      profile and investment-table reports
  correlation/   parts 2 to 7, correlation screen, figures for the professor
  pca/
  physical/      SLR and surge checkpoints and logs, NRI audit output
  exposure/      stage_a/ (layer description), stage_b/ (vs investment),
                 heat_terciles/, checkpoints/
  ml/
reports/         written reports
  data/          DATA_PROCESSING.md (sources and cleaning rules), indicator review (.docx)
  projects/      project data profile, investment tables, zero-population check
  physical/      SLR inspection and processing, surge inspection, NRI audit
  exposure/      population_exposure.md, exposure_vs_investment.md,
                 heat_tercile_investment.md
  analysis/      FINDINGS_FOR_PROFESSOR, REVIEW_MEMO (.md and .pdf),
                 RESULTS_FOR_REVIEW, correlation_screen, pca_analysis,
                 followup_analysis, gray_decomposition
  ml/            machine learning reports: stage1_report.md, stage2_report.md, stage3_report.md, stage4_bayesian_report.md, model_card.md
prompts/         the Claude Code prompts (21 population exposure, 22 machine learning)
archive/         outdated files, kept, not used
```

Inside the reports, file paths are written relative to this folder, for
example `outputs/pca/`. Paths starting `../` point into the website repo, for
example `../output/lst/lst_composite_f.tif`.

**Git.**
- Tracked: the scripts, the reports, the project file and the analysis,
  investment and hazard tables.
- Git-ignored: `data/raw/` (except the project file), `outputs/`, and the
  allocation audits, join keys and variable dictionary.
- Not tracked, but not ignored either: the exposure tables. The same status
  as before the reorganization (D-064).

## How to rerun

Use the repo's Python environment. Run every command from the website repo
root (`Climate-Resilience---Miami-Dade/`):

```bash
PY=.venv/bin/python
M="Modelling Data from Web/scripts"
```

Steps in order. Each writes to the folders shown, and later steps read what
earlier steps wrote. Most steps can be rerun alone, because their inputs are
already on disk.

| Step | Command | Reads | Writes | Time |
|---|---|---|---|---|
| Boundaries (download, only if missing) | `bash "$M/01_projects/fetch_boundaries.sh"` | | `data/raw/boundaries/` | network |
| 1. Project profile | `$PY "$M/01_projects/profile_projects.py"` | project file | prints; `outputs/projects/profile.json` with `--json` | seconds |
| 2. Projects to tracts and block groups | `$PY "$M/01_projects/spatial_join_check.py"` | project file, boundaries | `data/processed/investment/project_join_keys.csv` | seconds |
| 3. Investment tables | `$PY "$M/01_projects/build_investment_tables.py"` then `report_investment_tables.py` | join keys, ACS population | `data/processed/investment/` | about a minute |
| 4. Zero-population check | `$PY "$M/01_projects/investigate_zero_population.py"` | investment tables, social data | prints | seconds |
| 5. Analysis tables | `$PY "$M/02_social/build_analysis_tables.py"` | investment tables, ACS, SVI, EJScreen | `data/processed/analysis/` | about a minute |
| 6. Sea level rise | `$PY "$M/03_physical/process_slr.py"` | GeoPackage, boundaries | `data/processed/hazards/slr_*.csv`, `outputs/physical/slr_checkpoints/` | about 15 minutes |
| 7. Storm surge | `$PY "$M/03_physical/process_surge.py"` | surge GeoTIFFs | `data/processed/hazards/surge_*.csv`, `outputs/physical/surge_checkpoints/` | a few minutes |
| 8. FEMA NRI audit | `$PY "$M/03_physical/audit_nri.py"` | `../fema_miami_dade_dec_2025.csv` | prints | seconds |
| 9. Population exposure (Stage A) | `$PY "$M/04_exposure/build_exposure_layers.py"` | blocks, SLR, surge, Landsat composite | `data/processed/exposure/`, `outputs/exposure/stage_a/`, `outputs/exposure/checkpoints/` | about 25 minutes from scratch; seconds when the checkpoints exist |
| 10. Describe the layers | `$PY "$M/04_exposure/describe_exposure_layers.py"` | exposure tables, checkpoints, NRI, EJScreen | `outputs/exposure/stage_a/exposure_layers/` | about a minute |
| 11. Exposure vs investment (Stage B) | `$PY "$M/04_exposure/exposure_vs_investment.py"` | analysis and exposure tables | `outputs/exposure/stage_b/` | about a minute |
| 11b. Heat terciles by hazard focus | `$PY "$M/04_exposure/heat_tercile_investment.py"` | analysis and exposure tables, allocation ledger, project file | `outputs/exposure/heat_terciles/` | seconds |
| 16. ML Stage 1: modelling table, targets, baselines | `$PY "$M/ml/stage1_build.py"` | analysis, exposure, NRI, EJScreen, boundaries, projects | `outputs/ml/stage1/`; report in `reports/ml/` | about 2 minutes |
| 17. ML Stage 2: models, explanation, need and gap | `bash "$M/ml/run_ml.sh" "$M/ml/stage2_models.py"` (ML environment, D-079) | Stage 1 tables, PCA scores | `outputs/ml/stage2/`, `outputs/ml/dashboard/`; reports in `reports/ml/` | about 18 minutes |
| 18. ML scenarios | `bash "$M/ml/run_ml.sh" "$M/ml/scenarios.py"`; interventions: `interventions.py --tracts ... --type gray|nature-based` | Stage 2 models | `outputs/ml/dashboard/scenarios.json` | seconds |
| 18b. Map model test and gaps | `bash "$M/ml/run_ml.sh" "$M/ml/stage2b_map_model.py"` | Stage 2 outputs | `outputs/ml/stage2/`, `outputs/ml/dashboard/tracts.json` | about 2 minutes |
| 20b. Stage 4 Part B: dashboard data for both models; four-class T4 | `bash "$M/ml/run_ml.sh" "$M/ml/stage4_dashboard.py"`; `bash "$M/ml/run_ml.sh" "$M/ml/stage4_t4_multiclass.py"` | Stage 2 outputs, Stage 4 fits and CV fits | `outputs/ml/dashboard/models.json`, `compare.json`; `outputs/ml/stage4/` (dollar interval widths, cost by type, T4 classes) | about 1 minute; T4 about 5 minutes |
| 19. Admin Scenario view data | `.venv/bin/python "$M/website/build_scenario_data.py"` | `outputs/ml/dashboard/` (run 20b first) | `../src/admin/viz/scenario/data/` (admin panel only, D-094) | seconds |
| 20. ML Stage 4: Bayesian multiscale model | `bash "$M/ml/run_ml.sh" "$M/ml/stage4_graph.py"`, then `bash "$M/ml/run_ml.sh" "$M/ml/stage4_run.py"` | Stage 1 table, PCA scores, tract boundaries, Stage 2 code (for the logistic and XGBoost comparison) | `outputs/ml/stage4/` (fits cached in `fits/`); report `reports/ml/stage4_bayesian_report.md` | about 25 minutes from scratch; about 10 with cached fits |
| 12. Correlation analysis, parts 2 to 7 | `$PY "$M/05_analysis/part2_univariate.py"`, then `part3_correlation`, `part4_investment_vs_indicators`, `part5_diagnostics`, `part6b_moran_transforms`, `part6c_density_control`, `part7a_density_premise`, `part7_gray_decomposition` | analysis tables, audits | `outputs/correlation/part*/` | seconds to minutes each |
| 13. Correlation screen | `$PY "$M/05_analysis/correlation_screen.py"` | analysis tables | `outputs/correlation/correlation_screen/`, `reports/analysis/correlation_screen.md` | seconds |
| 14. PCA | `$PY "$M/05_analysis/pca_analysis.py"` | analysis tables | `outputs/pca/`, `reports/analysis/pca_analysis.md` | about a minute |
| 15. Compiled results and figures | `$PY "$M/05_analysis/compile_results_for_review.py"`; `figures_for_professor.py` | parts 2 to 7 | `reports/analysis/RESULTS_FOR_REVIEW.md`; `outputs/correlation/figures_professor/` | seconds |

Things to know before rerunning:
- **Steps 6, 7 and 9 checkpoint each layer and skip finished ones.** Delete a
  checkpoint file only if you mean to rebuild that layer.
- **Step 13, step 14 and `compile_results_for_review.py` rewrite their
  reports in `reports/analysis/`.** Rerun them only if you want the reports
  regenerated.
- **Step 9 reads the Landsat composite at `../output/lst/lst_composite_f.tif`,**
  which the website's `scripts/python/build_lst_layer.py` builds. It is not
  rebuilt here.

## Website scripts

`scripts/website/` holds two scripts that write the website's Exposure page
data in `../src/exposure/data/`. **Running them changes the website.**

| Script | Writes | Note |
|---|---|---|
| `build_surge_animation.py` | `surge.png`, `surge.json` | downloads the project list from Supabase when it runs |
| `build_population_exposure.py` | adds resident counts to `slr.json`, `surge.json`, `heat.json`; writes `exposure_blocks.json` | reads the website's own PNGs |

On 5 November 2026, `build_population_exposure.py` was rerun into a
temporary copy of that folder after the move. All seven files came out
byte-identical (D-062).

Website scripts elsewhere in the repo that read from this folder:
- `../scripts/python/build_viz_exposure.py`
- `build_viz_tracts.py`
- `prepare_map_surfaces.py`
- `build_lst_layer.py`
- `build_hhi_layer.py`

They point at the new paths. `build_lst_layer.py` and `build_hhi_layer.py`
are now tracked through `.gitignore` exceptions (D-068).

## Possibly outdated, left in place

- `reports/analysis/RESULTS_FOR_REVIEW.md`: compiled 16 Sep 2026, before the
  correlation screen and the PCA.
- `reports/analysis/followup_analysis.md` and `gray_decomposition.md`: their
  findings are summarized in `FINDINGS_FOR_PROFESSOR.md`.
- `REORGANIZATION_PLAN.md`: the plan for this reorganization, now carried
  out. Kept as the record of what moved.

Already in `archive/`: `correlation_analysis.md` (superseded),
`.Rhistory` (empty), `output_part1_tables/` (empty), and `old_empty_folders/`
(old folders that held only Finder files).

## Old path → new path

| Old | New |
|---|---|
| `SCALE-R_Database.csv` | `data/raw/projects/SCALE-R_Database.csv` |
| `boundaries/` | `data/raw/boundaries/` |
| `tract-level/ACS Data/` | `data/raw/social/acs_tract/` |
| `tract-level/SVI Data/FLORIDA.csv` | `data/raw/social/svi/FLORIDA.csv` |
| `block-group-level/ADI Data/` | `data/raw/social/acs_blockgroup/` |
| `block-group-level/EJScreen-Data/` | `data/raw/social/ejscreen/` |
| `tract-level/Physical Indicators/FL_SE_slr_data_dist/` | `data/raw/physical/sea_level_rise/FL_SE_slr_data_dist/` |
| `tract-level/Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617/` | `data/raw/physical/storm_surge/US_SLOSH_MOM_Inundation_v4_20260617/` |
| `tract-level/Physical Indicators/FLOOD ZONE/` | `data/raw/physical/flood_zones/` |
| `tract_investment.csv`, `blockgroup_investment.csv` | `data/processed/investment/` |
| `output/allocation_audit_*.csv`, `output/project_join_keys.csv` | `data/processed/investment/` |
| `tract_analysis.csv`, `blockgroup_analysis.csv`, `output/variable_dictionary.csv` | `data/processed/analysis/` |
| `slr_*.csv`, `surge_*.csv` | `data/processed/hazards/` |
| `exposure_tract.csv`, `exposure_blockgroup.csv` | `data/processed/exposure/` |
| `output/part2_univariate/` to `output/part7_gray/`, `output/correlation_screen/`, `output/figures_professor/` | `outputs/correlation/` |
| `output/pca/` | `outputs/pca/` |
| `output/slr_*`, `output/surge_*`, `output/nri_audit_raw.txt` | `outputs/physical/` |
| `output/profile*`, `output/investment_tables_report.txt`, `output/zero_population_report.txt` | `outputs/projects/` |
| `output/exposure_layers/`, `output/exposure_*.csv`, `output/exposure_*_log.txt` | `outputs/exposure/stage_a/` |
| `output/exposure_checkpoints/` | `outputs/exposure/checkpoints/` |
| `output/exposure/` | `outputs/exposure/stage_b/` |
| `scripts/<name>.py` | `scripts/<step folder>/<name>.py` (see the tree above) |
| top-level `.md` and `.pdf` reports | `reports/<topic>/` |
| `Claude outputs/` | `prompts/` (the `.docx` review is in `reports/data/`) |
