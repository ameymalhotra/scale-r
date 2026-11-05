# Reorganization plan for `Modelling Data from Web/`

**Plan only. Nothing has been moved.** This document proposes a structure,
maps every current path to its new path, lists every reference that would
break, and sets out the checks to run afterwards. Nothing is deleted:
outdated files go to `archive/`. Large files are moved, not copied. Tracked
files use `git mv`; untracked and git-ignored files use plain `mv`, because
`git mv` refuses them. Nothing will be committed.

Written 5 November 2026. The folder holds about 9.6 GB: 8.6 GB of raw
hazard data, 446 MB of boundaries, 423 MB of block group tables, and 125 MB
of outputs.

---

## 1. Proposed tree

```
Modelling Data from Web/
  README.md                  NEW: map of the folder, what is where, how to rerun
  DECISIONS.md               decision log (stays at the top)
  REORGANIZATION_PLAN.md     this file (moves to archive/ once done)
  data/
    raw/                     downloads, untouched
      projects/              SCALE-R_Database.csv
      boundaries/            TIGER/Line zips
      social/
        acs_tract/           10 ACS table folders (tract)
        acs_blockgroup/      16 ACS table folders (block group, ADI components and population)
        svi/                 FLORIDA.csv (SVI 2022)
        ejscreen/            EJScreen v2.3 reconstruction, column dictionary, tech doc
      physical/
        sea_level_rise/      FL_SE_slr_data_dist/ (4 GB GeoPackage + README)
        storm_surge/         US_SLOSH_MOM_Inundation_v4_20260617/ (folder name kept: it carries the version)
        flood_zones/         FEMAFloodZone CSV (no geometry, pending)
        fema_nri/            README.md pointing to ../../../../fema_miami_dade_dec_2025.csv (stays at repo root)
    processed/               tables we built
      investment/            tract_investment.csv, blockgroup_investment.csv, allocation audits, join keys
      analysis/              tract_analysis.csv, blockgroup_analysis.csv, variable_dictionary.csv
      hazards/               slr_tract.csv, slr_blockgroup.csv, surge_tract.csv, surge_blockgroup.csv
      exposure/              exposure_tract.csv, exposure_blockgroup.csv
  scripts/
    common/                  shared modules + NEW paths.py (every path in one place)
    01_projects/             project profile, spatial join, investment tables, zero-population check
    02_social/               analysis-table build (social indicators joined to investment)
    03_physical/             SLR, surge, NRI processing
    04_exposure/             population exposure layers, description, Stage B
    05_analysis/             parts 2 to 7, correlation screen, PCA, compiled reports, figures
    website/                 scripts that write the website's src/exposure/data (see 3.3)
    ml/                      empty, for prompt 22
  outputs/                   results by analysis
    projects/
    correlation/             parts 2 to 7, correlation screen, professor figures
    pca/
    physical/                SLR and surge checkpoints and logs, NRI audit raw
    exposure/
      stage_a/               exposure_layers/ tables, county totals, website comparison, logs
      stage_b/               exposure-vs-investment tables and log
      checkpoints/           block-level checkpoints (105 MB)
    ml/
  reports/                   the .md, .pdf and .docx reports, by topic
    data/                    DATA_PROCESSING.md, indicator data review (.docx)
    projects/
    physical/
    exposure/
    analysis/
  prompts/                   the Claude prompts (now "Claude outputs/")
  archive/                   outdated files
```

**Two adjustments from the suggested guide:**
- **FEMA NRI.** `fema_miami_dade_dec_2025.csv` sits at the repo root, not in
  this folder. Root scripts (`compare_fema_ratings.py`,
  `refresh_femaindex_from_csv.py`) and `src/admin/viz/gapMap.js` use it. It
  stays where it is, and `data/raw/physical/fema_nri/README.md` points to it.
- **Surface heat.** The composite (`../output/lst/lst_composite_f.tif`) is
  website-owned and stays in the website's `output/lst/`. The README points
  to it.

---

## 2. Current path → new path

`D` marks a folder, which moves whole with its contents unchanged. Counts are
files.

**Paths in this table are relative to `Modelling Data from Web/`.** Git
column:
- `tracked`: `git mv`.
- `ignored`: matched by `.gitignore`, plain `mv`.
- `untracked`: plain `mv`.

### 2.1 Top level

| Current | New | Git |
|---|---|---|
| `DECISIONS.md` | `DECISIONS.md` (unchanged) | untracked |
| `README.md` | NEW, written after the move | |
| `REORGANIZATION_PLAN.md` | `archive/REORGANIZATION_PLAN.md` (after the move is verified) | untracked |
| `SCALE-R_Database.csv` | `data/raw/projects/SCALE-R_Database.csv` | tracked |
| `.Rhistory` (0 bytes) | `archive/.Rhistory` | untracked |
| `.DS_Store` files | left in place (Finder files) | untracked |
| `.claude/` (tool settings) | left in place | untracked |

### 2.2 Raw data

| Current | New | Git |
|---|---|---|
| D `boundaries/` (8 zips, 446 MB) | `data/raw/boundaries/` | ignored |
| D `tract-level/ACS Data/` (10 table folders) | `data/raw/social/acs_tract/` | ignored |
| `tract-level/SVI Data/FLORIDA.csv` | `data/raw/social/svi/FLORIDA.csv` | ignored |
| D `block-group-level/ADI Data/` (16 table folders) | `data/raw/social/acs_blockgroup/` | ignored |
| D `block-group-level/EJScreen-Data/` (3 files) | `data/raw/social/ejscreen/` | ignored |
| D `tract-level/Physical Indicators/FL_SE_slr_data_dist/` (3.8 GB) | `data/raw/physical/sea_level_rise/FL_SE_slr_data_dist/` | ignored |
| D `tract-level/Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617/` (4.8 GB, 40 files + `.claude/`) | `data/raw/physical/storm_surge/US_SLOSH_MOM_Inundation_v4_20260617/` | ignored |
| D `tract-level/Physical Indicators/FLOOD ZONE/` | `data/raw/physical/flood_zones/` | ignored |
| `tract-level/`, `block-group-level/`, `tract-level/Physical Indicators/`, `tract-level/SVI Data/` | left empty, then removed with `rmdir` only if empty (not a deletion of data) | |

Each move is a same-disk `mv`, so it is a rename, instant, with no copy. The
4 GB GeoPackage and the 4.8 GB surge rasters are never duplicated.

### 2.3 Processed tables

| Current | New | Git |
|---|---|---|
| `tract_investment.csv` | `data/processed/investment/tract_investment.csv` | tracked |
| `blockgroup_investment.csv` | `data/processed/investment/blockgroup_investment.csv` | tracked |
| `output/allocation_audit_tract.csv` | `data/processed/investment/allocation_audit_tract.csv` | ignored |
| `output/allocation_audit_bg.csv` | `data/processed/investment/allocation_audit_bg.csv` | ignored |
| `output/project_join_keys.csv` | `data/processed/investment/project_join_keys.csv` | ignored |
| `tract_analysis.csv` | `data/processed/analysis/tract_analysis.csv` | tracked |
| `blockgroup_analysis.csv` | `data/processed/analysis/blockgroup_analysis.csv` | tracked |
| `output/variable_dictionary.csv` | `data/processed/analysis/variable_dictionary.csv` | ignored |
| `slr_tract.csv`, `slr_blockgroup.csv` | `data/processed/hazards/` | tracked |
| `surge_tract.csv`, `surge_blockgroup.csv` | `data/processed/hazards/` | tracked |
| `exposure_tract.csv`, `exposure_blockgroup.csv` | `data/processed/exposure/` | untracked |

**Note on tracking.** `output/` is ignored, so the three files moving out of
it (the allocation audits and the join keys) would become visible to git
under `data/processed/`. They are 1.7 MB, 4.5 MB and 64 KB. Proposal: add
`data/processed/investment/allocation_audit_*.csv` and `project_join_keys.csv`
to `.gitignore`, to keep today's behaviour. Your call.

### 2.4 Scripts (49 files)

| Current `scripts/` | New `scripts/` | Git |
|---|---|---|
| `scaler_projects.py` | `common/scaler_projects.py` | tracked |
| `allocation.py` | `common/allocation.py` | tracked |
| `vulnerability_loaders.py` | `common/vulnerability_loaders.py` | tracked |
| `analysis_variables.py` | `common/analysis_variables.py` | tracked |
| `professor_labels.py` | `common/professor_labels.py` | tracked |
| `gray_classification.py` | `common/gray_classification.py` | tracked |
| `population_surface.py` | `common/population_surface.py` | untracked |
| (new) | `common/paths.py`: every data and output path, defined once | new |
| `fetch_boundaries.sh` | `01_projects/fetch_boundaries.sh` | tracked |
| `profile_projects.py` | `01_projects/profile_projects.py` | tracked |
| `spatial_join_check.py` | `01_projects/spatial_join_check.py` | tracked |
| `build_investment_tables.py` | `01_projects/build_investment_tables.py` | tracked |
| `report_investment_tables.py` | `01_projects/report_investment_tables.py` | tracked |
| `investigate_zero_population.py` | `01_projects/investigate_zero_population.py` | tracked |
| `build_analysis_tables.py` | `02_social/build_analysis_tables.py` | tracked |
| `inspect_slr.py` | `03_physical/inspect_slr.py` | tracked |
| `process_slr.py` | `03_physical/process_slr.py` | tracked |
| `process_surge.py` | `03_physical/process_surge.py` | tracked |
| `audit_nri.py` | `03_physical/audit_nri.py` | tracked |
| `build_exposure_layers.py` | `04_exposure/build_exposure_layers.py` | untracked |
| `describe_exposure_layers.py` | `04_exposure/describe_exposure_layers.py` | untracked |
| `exposure_vs_investment.py` | `04_exposure/exposure_vs_investment.py` | untracked |
| `part2_univariate.py` | `05_analysis/part2_univariate.py` | tracked |
| `part3_correlation.py` | `05_analysis/part3_correlation.py` | tracked |
| `part4_investment_vs_indicators.py` | `05_analysis/part4_investment_vs_indicators.py` | tracked |
| `part5_diagnostics.py` | `05_analysis/part5_diagnostics.py` | tracked |
| `part6b_moran_transforms.py` | `05_analysis/part6b_moran_transforms.py` | tracked |
| `part6c_density_control.py` | `05_analysis/part6c_density_control.py` | tracked |
| `part7a_density_premise.py` | `05_analysis/part7a_density_premise.py` | tracked |
| `part7_gray_decomposition.py` | `05_analysis/part7_gray_decomposition.py` | tracked |
| `correlation_screen.py` | `05_analysis/correlation_screen.py` | tracked |
| `pca_analysis.py` | `05_analysis/pca_analysis.py` | tracked |
| `compile_results_for_review.py` | `05_analysis/compile_results_for_review.py` | tracked |
| `figures_for_professor.py` | `05_analysis/figures_for_professor.py` | tracked |
| `build_population_exposure.py` | `website/build_population_exposure.py` (**decision needed**, see 3.3) | tracked |
| `build_surge_animation.py` | `website/build_surge_animation.py` (**decision needed**, see 3.3) | tracked |
| `__pycache__/` | left in place (Python rebuilds it) | ignored |
| (new) | `ml/` (empty) | |

### 2.5 Outputs (`output/` → `outputs/`)

| Current `output/` | New `outputs/` |
|---|---|
| `profile.json`, `profile_step1_3.txt`, `profile_step4.txt` | `projects/` |
| `investment_tables_report.txt`, `zero_population_report.txt` | `projects/` |
| D `part1_tables/` (empty) | `archive/output_part1_tables/` (kept, empty) |
| D `part2_univariate/` (6) | `correlation/part2_univariate/` |
| D `part3_correlation/` (18) | `correlation/part3_correlation/` |
| D `part4_investment_vs_indicators/` (21) | `correlation/part4_investment_vs_indicators/` |
| D `part5_diagnostics/` (7) | `correlation/part5_diagnostics/` |
| D `part6_followup/` (11) | `correlation/part6_followup/` |
| D `part7_gray/` (17) | `correlation/part7_gray/` |
| D `correlation_screen/` (18) | `correlation/correlation_screen/` |
| D `figures_professor/` (5) | `correlation/figures_professor/` |
| D `pca/` (32) | `pca/` |
| D `slr_checkpoints/` (10), `slr_processing_log.txt` | `physical/slr_checkpoints/`, `physical/` |
| D `surge_checkpoints/` (10), `surge_processing_log.txt` | `physical/surge_checkpoints/`, `physical/` |
| `nri_audit_raw.txt` | `physical/` |
| D `exposure_layers/` (20) | `exposure/stage_a/exposure_layers/` |
| `exposure_county_totals.csv`, `exposure_vs_website_blocks.csv` | `exposure/stage_a/` |
| `exposure_layers_log.txt`, `exposure_describe_log.txt` | `exposure/stage_a/` |
| D `exposure_checkpoints/` (17, 105 MB) | `exposure/checkpoints/` |
| D `exposure/` (10, Stage B) | `exposure/stage_b/` |
| (new) | `ml/` |

All of `output/` is git-ignored today, and so will `outputs/` be (see 3.4).

### 2.6 Reports, prompts, archive

| Current | New | Git |
|---|---|---|
| `DATA_PROCESSING.md` | `reports/data/DATA_PROCESSING.md` | tracked |
| `Claude outputs/SCALE-R_Indicator_Data_Review.docx` | `reports/data/SCALE-R_Indicator_Data_Review.docx` | untracked |
| `project_data_profile.md` | `reports/projects/project_data_profile.md` | tracked |
| `INVESTMENT_TABLES.md` | `reports/projects/INVESTMENT_TABLES.md` | tracked |
| `zero_population_investigation.md` | `reports/projects/zero_population_investigation.md` | tracked |
| `slr_inspection.md`, `slr_processing.md` | `reports/physical/` | tracked |
| `surge_inspection.md`, `nri_audit.md` | `reports/physical/` | tracked |
| `population_exposure.md`, `exposure_vs_investment.md` | `reports/exposure/` | untracked |
| `correlation_screen.md`, `pca_analysis.md` | `reports/analysis/` | tracked |
| `RESULTS_FOR_REVIEW.md`, `followup_analysis.md`, `gray_decomposition.md` | `reports/analysis/` | tracked |
| `FINDINGS_FOR_PROFESSOR.md`, `REVIEW_MEMO.md`, `REVIEW_MEMO.pdf` | `reports/analysis/` | tracked |
| `correlation_analysis.md` | `archive/correlation_analysis.md` (superseded by `RESULTS_FOR_REVIEW.md` and `FINDINGS_FOR_PROFESSOR.md`) | tracked |
| `Claude outputs/claude_code_prompt_21_population_exposure.md` | `prompts/claude_code_prompt_21_population_exposure.md` | untracked |
| `Claude outputs/claude_code_prompt_22_ml_scenario_module.md` | `prompts/claude_code_prompt_22_ml_scenario_module.md` | untracked |

**Only two items go to `archive/`: `correlation_analysis.md` and the empty
`.Rhistory`.** Everything else is current. If you consider other reports
outdated, for example `RESULTS_FOR_REVIEW.md`, which predates the correlation
screen, say so and they go to `archive/` instead.

---

## 3. References that would break, and how each is fixed

### 3.1 The one change that fixes most scripts

Every script in this folder finds its files from its own location
(`Path(__file__).resolve().parent.parent`) and imports its siblings from
`scripts/`. Both break when the scripts move into subfolders.

**Fix:** add `scripts/common/paths.py`, which defines `ROOT` (this folder)
and every data and output path once. In each script:

1. Replace the local `BASE = Path(__file__).resolve().parent.parent` and its
   hard-coded joins with imports from `paths`.
2. Replace `sys.path.insert(0, <script dir>)` with two lines that put
   `scripts/common` (and, where needed, a sibling folder) on the path.

`scaler_projects.py` keeps exporting `BASE`, `BOUNDARY_DIR`, `OUTPUT_DIR` and
`PROJECT_CSV`, now taken from `paths`. That way the 20 scripts importing them
need only the `sys.path` line changed.

### 3.2 Paths inside this folder's scripts

| Script | What it references now | Change |
|---|---|---|
| `common/scaler_projects.py` | `BASE`, `SCALE-R_Database.csv`, `boundaries`, `output` | take all four from `paths` (`data/raw/projects/...`, `data/raw/boundaries`, `outputs`) |
| `common/allocation.py` | `tract-level/ACS Data/B01001-...`, `block-group-level/ADI Data/B01003-...` | `paths.ACS_TRACT_DIR`, `paths.ACS_BG_DIR` |
| `common/vulnerability_loaders.py` | own `BASE`; `tract-level/ACS Data`, `block-group-level/ADI Data`, `SVI Data/FLORIDA.csv`, `EJScreen-Data/...` | from `paths` |
| `common/analysis_variables.py` | `BASE / tract_analysis.csv`, `blockgroup_analysis.csv` | `paths.PROCESSED / "analysis" / ...` |
| `common/population_surface.py` | `BOUNDARY_DIR` (via `scaler_projects`) | none |
| `01_projects/fetch_boundaries.sh` | `$(dirname $0)/../boundaries` | `$(dirname $0)/../../data/raw/boundaries` |
| `01_projects/spatial_join_check.py` | writes `output/project_join_keys.csv` | write to `paths.PROCESSED / "investment"` |
| `01_projects/build_investment_tables.py` | reads `output/project_join_keys.csv`; writes `tract_investment.csv`, `blockgroup_investment.csv`, `output/allocation_audit_*.csv` | `processed/investment/` for all |
| `01_projects/report_investment_tables.py` | imports `build_investment_tables` (same folder); reads the audits | path line plus `processed/investment/` |
| `01_projects/investigate_zero_population.py` | `tract_investment.csv`; audits; `tract-level/SVI Data`; `tract-level/ACS Data`; EJScreen; `ADI Data` | from `paths` |
| `01_projects/profile_projects.py` | `scaler_projects` paths; scans the folder for data files | path line; scan `data/raw/` |
| `02_social/build_analysis_tables.py` | reads `tract_investment.csv`, `blockgroup_investment.csv`, the audits; writes `tract_analysis.csv`, `blockgroup_analysis.csv`, `output/variable_dictionary.csv` | `processed/investment/` and `processed/analysis/` |
| `03_physical/inspect_slr.py` | own `BASE`; GeoPackage path; `boundaries/` zips | from `paths` |
| `03_physical/process_slr.py` | own `BASE`; GeoPackage; `output/slr_checkpoints`; writes `slr_tract.csv`, `slr_blockgroup.csv` | `paths.SLR_GPKG`, `outputs/physical/slr_checkpoints`, `processed/hazards/` |
| `03_physical/process_surge.py` | own `BASE`; surge folder; `output/surge_checkpoints`; writes `surge_*.csv` | `paths.SURGE_DIR`, `outputs/physical/surge_checkpoints`, `processed/hazards/` |
| `03_physical/audit_nri.py` | `BASE.parent / fema_miami_dade_dec_2025.csv`; scans the folder | `paths.NRI_CSV` (repo root, unchanged file) |
| `04_exposure/build_exposure_layers.py` | own `BASE`; imports `process_slr` and `process_surge`; `output/exposure_checkpoints`; `slr_*.csv`, `surge_*.csv`; writes `exposure_*.csv` and `output/exposure_*` files; `../output/lst/...` | path lines for `common` and `03_physical`; outputs to `outputs/exposure/checkpoints` and `stage_a/`; tables to `processed/exposure/` |
| `04_exposure/describe_exposure_layers.py` | own `BASE`; checkpoints; `exposure_*.csv`; NRI | from `paths`; writes `outputs/exposure/stage_a/exposure_layers/` |
| `04_exposure/exposure_vs_investment.py` | own `BASE`; imports `part5_diagnostics`; `output/part7_gray/2b_*`; `exposure_*.csv` | path lines for `common` and `05_analysis`; `outputs/correlation/part7_gray/`; writes `outputs/exposure/stage_b/` |
| `05_analysis/part2` to `part7a` (8 scripts) | `OUTPUT_DIR / "partN_..."`; part7 imports `part6c_density_control`; part6b imports `part5_diagnostics` (same folder) | `OUTPUT_DIR / "correlation" / ...`; path line only |
| `05_analysis/correlation_screen.py` | writes `correlation_screen.md` at the top; `output/correlation_screen` | `reports/analysis/correlation_screen.md`; `outputs/correlation/correlation_screen` |
| `05_analysis/pca_analysis.py` | writes `pca_analysis.md`; `output/pca` | `reports/analysis/`; `outputs/pca` |
| `05_analysis/compile_results_for_review.py` | `P2` to `P5` under `output/`; writes `RESULTS_FOR_REVIEW.md` | `outputs/correlation/...`; `reports/analysis/` |
| `05_analysis/figures_for_professor.py` | `P3`, `P4`, `P7` under `output/`; `output/figures_professor` | `outputs/correlation/...` |

**Inside the reports.**
- Twelve image or link targets point at `output/...`, mostly in
  `REVIEW_MEMO.md` and `FINDINGS_FOR_PROFESSOR.md`. They are rewritten to
  their new relative paths, for example
  `../../outputs/correlation/figures_professor/...`.
- About 120 path mentions in prose (backticks) are rewritten by an exact
  old→new string replacement from the table in Section 2, and the diff is
  reviewed by hand. That includes the Evidence lines in `DECISIONS.md`.
- `REVIEW_MEMO.pdf` is already built and is not regenerated.
- The prompts in `prompts/` are left as written, since they are historical
  records. `README.md` maps their old paths to new ones.

### 3.3 Website scripts in this folder (decision needed)

`build_population_exposure.py` and `build_surge_animation.py` live here but
write the website's `src/exposure/data/` (`slr.json`, `surge.json`,
`heat.json`, `exposure_blocks.json`, the PNGs). Both find the repo with
`Path(__file__).parent.parent.parent` and import `scaler_projects` and
`allocation` from their own folder, so **any move of the shared modules
breaks them.** Two options:

- **A (recommended).** Move them to `scripts/website/` and change only their
  path and import lines, two to four lines each. Then prove nothing changed
  for the website:
  1. Rerun both scripts.
  2. Confirm `git status src/exposure/data` shows no change, meaning every
     JSON and PNG is byte-identical to the committed version.
  3. If anything differs, restore it with `git checkout -- src/exposure/data`
     and report.
- **B.** Leave both scripts untouched, and leave copies of the modules they
  import at `scripts/` top level. That keeps the website script byte-identical
  but duplicates two modules.

Prompt 21 said not to change `build_population_exposure.py`, so I will not do
A without your yes.

### 3.4 References elsewhere in the repo

| File | Line | Now | Change |
|---|---|---|---|
| `.gitignore` | 83 to 86 | ignores `Modelling Data from Web/tract-level/`, `block-group-level/`, `boundaries/`, `output/` | **Changed first, before anything moves.** Add `Modelling Data from Web/data/raw/` and `Modelling Data from Web/outputs/`, and the investment audits (2.3). Keep the old four lines too, so nothing becomes visible mid-move. Without this, 9 GB of data would show up as untracked. |
| `scripts/python/build_viz_exposure.py` | 29, 31 | `.../tract-level/Physical Indicators/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg`; `.../boundaries/tl_2024_12086_areawater.zip` | `.../data/raw/physical/sea_level_rise/FL_SE_slr_data_dist/...`; `.../data/raw/boundaries/...` |
| `scripts/python/build_lst_layer.py` | 53 | `BOUNDARIES = REPO_ROOT / "Modelling Data from Web" / "boundaries"` | `... / "data" / "raw" / "boundaries"`. `build_hhi_layer.py` imports `BOUNDARIES` from it, so it follows with no edit. |
| `scripts/python/build_viz_tracts.py` | 45, 49, 50, 52 | `MODEL / "tract_investment.csv"`, `"slr_tract.csv"`, `"surge_tract.csv"`, `"tract_analysis.csv"` | `MODEL / "data/processed/investment/..."`, `".../hazards/..."`, `".../analysis/..."` |
| `scripts/python/prepare_map_surfaces.py` | 41, 42, 307 | GeoPackage path; Category 3 surge `.tif`; `boundaries/tl_2024_12_tract.zip` | the new raw paths |
| `scripts/python/prepare_footprint_tiles.py` | 10 (docstring only) | "keep them in `Modelling Data from Web/boundaries/`" | `.../data/raw/boundaries/` |
| `public/layers/surface-metadata.json` | 26 | `"source"` string naming the old surge path | **left unchanged.** It is a published output and records where the file was when the layer was built. It is not read as a path. |
| `public/layers/storm-surge-category-3.json` | 2 | the same | **left unchanged**, same reason |
| `src/admin/viz/gapMap.js` | 20 | UI label `'Modelling Data from Web/SCALE-R_Database.csv → tract_investment.csv'` | **left unchanged** unless you want the label updated. It is display text, and the folder name is still right. |
| `compare_fema_ratings.py`, `refresh_femaindex_from_csv.py` (repo root) | | use `fema_miami_dade_dec_2025.csv` at the repo root | none: that file does not move |

Nothing in `package.json`, `vite.config.js` or `vercel.json` references this
folder, so the website build does not depend on it.

---

## 4. Order of work and the checks afterwards

### Order

1. Record the "before" state, saved to `outputs/reorg_check_before.txt` (an
   untracked scratch file):
   - row counts and SHA-256 of every CSV in Sections 2.3 and 2.5;
   - file counts and total bytes of every raw data folder;
   - `git status --short`.
2. Update `.gitignore` (3.4).
3. Create the empty folders, then move the files: `git mv` for tracked, `mv`
   for the rest.
4. Add `scripts/common/paths.py` and edit the scripts (3.1, 3.2). Edit the
   website scripts (3.4), and the two scripts in 3.3 only if you choose A.
5. Rewrite report links and path mentions (3.2), then write `README.md`.

### Checks

1. **Every path resolves.** A check script imports `paths.py` and asserts
   that each path exists. It also scans every `.py` under `scripts/` and
   `../scripts/python/` for string literals naming `tract-level`,
   `block-group-level`, `boundaries/`, `output/` or an old CSV path. Expected
   result: none left, except the two unchanged `public/layers` JSON strings
   and the `gapMap.js` label.
2. **Imports work.** Run `python -c "import <module>"` for every script
   module with the new `sys.path` lines. This catches broken sibling imports
   without running any analysis.
3. **Dry run of the main loaders**, read-only:
   - `analysis_variables.load_tract()` (asserts 698);
   - `load_bg()` (1,843);
   - `vulnerability_loaders` for SVI, EJScreen, the ACS tract tables and the
     ADI tables;
   - `allocation.load_population("tract")` and `("bg")`;
   - `allocation.load_units` for both grains;
   - `population_surface.load_blocks` (25,805 blocks, 2,738,356 residents);
   - `process_slr` and `process_surge` opening their inputs (metadata only).
4. **Data unchanged.** Row counts and SHA-256 of every moved CSV, plus file
   counts and bytes of every raw folder, must match step 1 exactly. A move
   cannot change content, and this proves it.
5. **One cheap end-to-end rerun:** `05_analysis/part6b_moran_transforms.py`
   writes to its new output folder, and its CSV is compared with the
   pre-move copy. Then `04_exposure/exposure_vs_investment.py`, whose tables
   are compared with the current `outputs/exposure/stage_b/`. Both take
   seconds.
6. **Website.**
   - `npm run build` must pass.
   - `python scripts/python/build_viz_tracts.py --help`, or an import check
     where there is no CLI, for each edited website script, to confirm its
     paths resolve without rewriting any published file.
   - If option A is chosen, the `src/exposure/data` byte-identity check in
     3.3.
7. **`git status`** shows only:
   - renames of tracked files;
   - the edited scripts and `.gitignore`;
   - the new untracked files (`README.md`, `DECISIONS.md`, `paths.py` and
     the exposure outputs).

   No raw data may appear. Nothing is committed.

Any failure stops the work and is reported. Moves are renames, so every one
can be undone by moving the file back.

---

## 5. What I need from you before moving anything

1. Approve the tree, or name changes to it.
2. **Website scripts in this folder:** option A (move and edit the
   path/import lines, then prove the outputs are byte-identical) or option B
   (leave them untouched).
3. **Archive:** only `correlation_analysis.md` and `.Rhistory`, or also others
   such as `RESULTS_FOR_REVIEW.md`?
4. **Git-ignore the investment audit CSVs** once they leave `output/` (2.3):
   yes or no.
5. **Leave the two `public/layers` source strings and the `gapMap.js` label**
   unchanged: yes or no.
